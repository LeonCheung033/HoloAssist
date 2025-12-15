from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from holoassist.app.core.database import Base


class User(Base):
    """用户模型

    存储用户的基本信息，包括用户名、邮箱、密码哈希等。
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    status = Column(String(20), default="active")

    # 关系：一个用户可以有多个会话
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
