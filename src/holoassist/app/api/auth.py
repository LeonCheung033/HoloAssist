"""认证API端点

提供用户注册、登录和获取当前用户信息的功能。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from holoassist.app.core.database import get_db
from holoassist.app.core.security import create_access_token, get_current_user
from holoassist.app.models.user import User
from holoassist.app.schemas.user import Token, UserCreate, UserLogin, UserResponse
from holoassist.app.services.user_service import UserService

# 创建认证路由
router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """用户注册端点

    Args:
        user_data: 用户注册数据（包含username、email、password）
        db: 数据库会话（依赖注入）

    Returns:
        UserResponse: 创建的用户信息

    Raises:
        HTTPException: 如果邮箱或用户名已存在，返回400错误
    """
    user_service = UserService(db)
    try:
        user = await user_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/token", response_model=Token)
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """用户登录端点

    Args:
        user_data: 用户登录数据（包含email、password）
        db: 数据库会话（依赖注入）

    Returns:
        Token: 包含access_token和token_type的响应

    Raises:
        HTTPException: 如果邮箱或密码错误，返回401错误
    """
    user_service = UserService(db)
    user = await user_service.authenticate_user(user_data.email, user_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 创建JWT token，payload包含用户邮箱
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """获取当前用户信息端点

    Args:
        current_user: 当前认证用户（通过依赖注入获取）

    Returns:
        UserResponse: 当前用户信息
    """
    return current_user
