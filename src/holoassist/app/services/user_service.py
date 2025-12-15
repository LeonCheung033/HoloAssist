from datetime import datetime
from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from holoassist.app.core.hashing import get_password_hash, verify_password
from holoassist.app.core.logger import get_logger
from holoassist.app.models.user import User
from holoassist.app.schemas.user import UserCreate

logger = get_logger(service="user_service")


class UserService:
    """用户服务类

    提供用户相关的业务逻辑，包括用户创建、认证、查询等功能。
    """

    def __init__(self, db: AsyncSession):
        """初始化用户服务

        Args:
            db: 数据库会话
        """
        self.db = db

    async def create_user(self, user_data: UserCreate) -> User:
        """创建新用户

        Args:
            user_data: 用户创建数据（包含username、email、password）

        Returns:
            User: 创建的用户对象

        Raises:
            ValueError: 如果邮箱或用户名已存在
        """
        # 同时检查用户名和邮箱是否已存在
        query = select(User).where(or_(User.email == user_data.email, User.username == user_data.username))

        result = await self.db.execute(query)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            if existing_user.email == user_data.email:
                raise ValueError("该邮箱已经被注册！")
            else:
                raise ValueError("用户名已被占用！")

        # 创建新用户
        db_user = User(
            username=user_data.username, email=user_data.email, password_hash=get_password_hash(user_data.password)
        )
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        return db_user

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """验证用户

        Args:
            email: 用户邮箱
            password: 前端传来的 SHA256 哈希密码

        Returns:
            Optional[User]: 如果认证成功返回用户对象，否则返回None
        """
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User not found: {email}")
            return None

        if not verify_password(password, user.password_hash):
            logger.warning(f"Invalid password for user: {email}")
            return None

        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        await self.db.commit()

        return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID查询用户

        Args:
            user_id: 用户ID

        Returns:
            Optional[User]: 用户对象，如果不存在返回None
        """
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱查询用户

        Args:
            email: 用户邮箱

        Returns:
            Optional[User]: 用户对象，如果不存在返回None
        """
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
