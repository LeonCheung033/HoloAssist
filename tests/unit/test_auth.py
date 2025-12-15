"""
认证API单元测试
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from holoassist.app.core.database import AsyncSessionLocal
from holoassist.app.models.user import User
from holoassist.app.schemas.user import UserCreate
from holoassist.app.services.user_service import UserService


@pytest.fixture
async def db_session():
    """提供数据库会话fixture"""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """创建测试用户fixture"""
    user_service = UserService(db_session)
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="hashed_password_123"
    )
    user = await user_service.create_user(user_data)
    return user


class TestUserService:
    """UserService测试类"""

    @pytest.mark.asyncio
    async def test_create_user_success(self, db_session: AsyncSession):
        """测试成功创建用户"""
        user_service = UserService(db_session)
        user_data = UserCreate(
            username="newuser",
            email="newuser@example.com",
            password="password123"
        )
        user = await user_service.create_user(user_data)
        assert user is not None
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.password_hash is not None
        assert user.id is not None

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, db_session: AsyncSession, test_user: User):
        """测试重复邮箱"""
        user_service = UserService(db_session)
        user_data = UserCreate(
            username="differentuser",
            email="test@example.com",  # 重复邮箱
            password="password123"
        )
        with pytest.raises(ValueError, match="该邮箱已经被注册"):
            await user_service.create_user(user_data)

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, db_session: AsyncSession, test_user: User):
        """测试重复用户名"""
        user_service = UserService(db_session)
        user_data = UserCreate(
            username="testuser",  # 重复用户名
            email="different@example.com",
            password="password123"
        )
        with pytest.raises(ValueError, match="用户名已被占用"):
            await user_service.create_user(user_data)

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, db_session: AsyncSession, test_user: User):
        """测试成功认证"""
        user_service = UserService(db_session)
        user = await user_service.authenticate_user("test@example.com", "hashed_password_123")
        assert user is not None
        assert user.email == "test@example.com"
        assert user.last_login is not None

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, db_session: AsyncSession):
        """测试用户不存在"""
        user_service = UserService(db_session)
        user = await user_service.authenticate_user("nonexistent@example.com", "password")
        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, db_session: AsyncSession, test_user: User):
        """测试密码错误"""
        user_service = UserService(db_session)
        user = await user_service.authenticate_user("test@example.com", "wrong_password")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, db_session: AsyncSession, test_user: User):
        """测试根据ID查询用户"""
        user_service = UserService(db_session)
        user = await user_service.get_user_by_id(test_user.id)
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db_session: AsyncSession, test_user: User):
        """测试根据邮箱查询用户"""
        user_service = UserService(db_session)
        user = await user_service.get_user_by_email("test@example.com")
        assert user is not None
        assert user.email == "test@example.com"
        assert user.id == test_user.id


# 注意：API端点测试需要使用httpx.AsyncClient或集成测试环境
# 这里先专注于UserService的单元测试
# API端点测试将在集成测试中实现
