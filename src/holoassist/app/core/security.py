from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from holoassist.app.core.config import settings
from holoassist.app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

# OAuth2 密码承载方案，用于从请求头中提取 Bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问token
    
    Args:
        data: 要编码到token中的数据字典（通常包含用户标识信息）
        expires_delta: 可选的过期时间增量，如果不提供则使用配置中的默认值
        
    Returns:
        str: 编码后的JWT token字符串
    """
    to_encode = data.copy()
    
    # 设置过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # 使用配置中的默认过期时间（分钟）
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 添加过期时间到payload
    to_encode.update({"exp": expire})
    
    # 使用配置的密钥和算法编码JWT
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """获取当前认证用户
    
    从JWT token中提取用户信息并验证用户是否存在。
    此函数依赖UserService，该服务在阶段三实现。
    
    Args:
        token: JWT token（通过OAuth2PasswordBearer自动提取）
        db: 数据库会话（通过依赖注入）
        
    Returns:
        用户对象
        
    Raises:
        HTTPException: 如果token无效或用户不存在，返回401未授权错误
        
    TODO: 在阶段三实现UserService后，取消注释UserService相关代码
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 解码并验证JWT token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # TODO: 在阶段三实现UserService后，取消以下注释并删除占位代码
    # from holoassist.app.services.user_service import UserService
    # user_service = UserService(db)
    # user = await user_service.get_user_by_email(email)
    # if user is None:
    #     raise credentials_exception
    # return user
    
    # 临时占位实现：返回包含email的字典
    # 在实际使用前需要实现UserService
    return {"email": email}