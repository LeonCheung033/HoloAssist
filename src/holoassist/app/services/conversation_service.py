"""会话服务

提供会话和消息的完整CRUD操作。
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from holoassist.app.core.logger import get_logger
from holoassist.app.models.conversation import Conversation, DialogueType
from holoassist.app.models.message import Message

logger = get_logger(service="conversation_service")


class ConversationService:
    """会话服务类

    提供会话和消息的完整CRUD操作。
    """

    def __init__(self, db: AsyncSession):
        """初始化会话服务

        Args:
            db: 数据库会话
        """
        self.db = db

    async def create_conversation(
        self,
        user_id: int,
        title: str,
        dialogue_type: DialogueType,
    ) -> Conversation:
        """创建新会话

        Args:
            user_id: 用户ID
            title: 会话标题
            dialogue_type: 对话类型

        Returns:
            Conversation: 创建的会话对象

        Raises:
            ValueError: 如果参数无效
        """
        if not title or not title.strip():
            raise ValueError("Title cannot be empty")

        conversation = Conversation(
            user_id=user_id,
            title=title.strip(),
            dialogue_type=dialogue_type,
            status="ongoing",
        )

        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)

        logger.info(f"Created conversation {conversation.id} for user {user_id}")
        return conversation

    async def get_conversation(
        self,
        conversation_id: int,
        user_id: int,
    ) -> Conversation | None:
        """获取会话（验证用户权限）

        Args:
            conversation_id: 会话ID
            user_id: 用户ID（用于验证权限）

        Returns:
            Conversation | None: 会话对象，如果不存在或用户无权限则返回None
        """
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if conversation:
            logger.debug(f"Retrieved conversation {conversation_id} for user {user_id}")
        else:
            logger.warning(f"Conversation {conversation_id} not found or access denied for user {user_id}")

        return conversation

    async def list_conversations(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Conversation]:
        """获取用户的会话列表

        Args:
            user_id: 用户ID
            skip: 跳过的记录数（用于分页）
            limit: 返回的记录数（默认20）

        Returns:
            list[Conversation]: 会话列表，按更新时间倒序排列
        """
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        conversations = result.scalars().all()

        logger.debug(f"Retrieved {len(conversations)} conversations for user {user_id} (skip={skip}, limit={limit})")
        return list(conversations)

    async def update_conversation(
        self,
        conversation_id: int,
        user_id: int,
        title: str | None = None,
        status: str | None = None,
    ) -> Conversation | None:
        """更新会话信息

        Args:
            conversation_id: 会话ID
            user_id: 用户ID（用于验证权限）
            title: 新的标题（可选）
            status: 新的状态（可选）

        Returns:
            Conversation | None: 更新后的会话对象，如果不存在或用户无权限则返回None
        """
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            return None

        updated = False
        if title is not None and title.strip():
            conversation.title = title.strip()  # type: ignore[assignment]
            updated = True

        if status is not None:
            conversation.status = status  # type: ignore[assignment]
            updated = True

        if updated:
            conversation.updated_at = datetime.now(UTC)  # type: ignore[assignment]
            await self.db.commit()
            await self.db.refresh(conversation)
            logger.info(f"Updated conversation {conversation_id} for user {user_id}")

        return conversation

    async def delete_conversation(
        self,
        conversation_id: int,
        user_id: int,
    ) -> bool:
        """删除会话（级联删除消息）

        Args:
            conversation_id: 会话ID
            user_id: 用户ID（用于验证权限）

        Returns:
            bool: 是否成功删除
        """
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            return False

        await self.db.delete(conversation)
        await self.db.commit()

        logger.info(f"Deleted conversation {conversation_id} for user {user_id}")
        return True

    async def add_message(
        self,
        conversation_id: int,
        sender: str,
        content: str,
        message_type: str = "text",
    ) -> Message:
        """添加消息到会话

        Args:
            conversation_id: 会话ID
            sender: 发送者（通常是"user"或"assistant"）
            content: 消息内容
            message_type: 消息类型（默认"text"）

        Returns:
            Message: 创建的消息对象

        Raises:
            ValueError: 如果会话不存在或参数无效
        """
        # 验证会话存在
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        if not content or not content.strip():
            raise ValueError("Message content cannot be empty")

        message = Message(
            conversation_id=conversation_id,
            sender=sender,
            content=content.strip(),
            message_type=message_type,
        )

        self.db.add(message)

        # 更新会话的更新时间
        conversation.updated_at = datetime.now(UTC)  # type: ignore[assignment]

        await self.db.commit()
        await self.db.refresh(message)

        logger.info(f"Added message {message.id} to conversation {conversation_id}")
        return message

    async def get_messages(
        self,
        conversation_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Message]:
        """获取会话的消息列表

        Args:
            conversation_id: 会话ID
            user_id: 用户ID（用于验证权限）
            skip: 跳过的记录数（用于分页）
            limit: 返回的记录数（默认100）

        Returns:
            list[Message]: 消息列表，按创建时间正序排列

        Raises:
            ValueError: 如果会话不存在或用户无权限
        """
        # 验证会话存在且用户有权限
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found or access denied")

        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        messages = result.scalars().all()

        logger.debug(
            f"Retrieved {len(messages)} messages for conversation {conversation_id} (skip={skip}, limit={limit})"
        )
        return list(messages)
