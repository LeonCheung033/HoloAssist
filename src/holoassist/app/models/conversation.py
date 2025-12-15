import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from holoassist.app.core.database import Base
from holoassist.app.core.logger import get_logger

logger = get_logger(service="conversation")


class DialogueType(enum.Enum):
    """对话类型枚举"""

    NORMAL = "普通对话"
    DEEP_THINKING = "深度思考"
    WEB_SEARCH = "联网检索"
    RAG = "RAG 问答"


class Conversation(Base):
    """会话模型

    存储用户的会话信息，包括会话标题、类型、状态等。
    一个用户可以有多个会话，一个会话可以包含多条消息。
    """

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    status = Column(String(20), default="ongoing")
    dialogue_type = Column(Enum(DialogueType), nullable=False)  # type: ignore[var-annotated]

    # 关系：会话属于一个用户
    user = relationship("User", back_populates="conversations")
    # 关系：一个会话可以有多条消息
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
