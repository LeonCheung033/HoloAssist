from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from holoassist.app.core.database import Base
from holoassist.app.core.logger import get_logger

logger = get_logger(service="message")


class Message(Base):
    """消息模型

    存储会话中的消息内容，包括发送者、消息内容、消息类型等。
    一个会话可以包含多条消息。
    """

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    message_type = Column(String(20), default="text")

    # 关系：消息属于一个会话
    conversation = relationship("Conversation", back_populates="messages")
