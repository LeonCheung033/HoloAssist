from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """用户基础Schema

    包含用户的基本信息字段。
    """

    username: str
    email: EmailStr


class UserCreate(UserBase):
    """用户创建Schema

    用于用户注册，继承自UserBase，添加密码字段。
    """

    password: str


class UserLogin(BaseModel):
    """用户登录Schema

    用于用户登录验证。
    """

    email: EmailStr
    password: str


class UserResponse(UserBase):
    """用户响应Schema

    用于返回用户信息，继承自UserBase，添加数据库字段。
    使用from_attributes = True支持从SQLAlchemy模型转换。
    """

    id: int
    status: str
    created_at: datetime
    last_login: datetime | None = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token响应Schema

    用于返回JWT token信息。
    """

    access_token: str
    token_type: str = "bearer"
