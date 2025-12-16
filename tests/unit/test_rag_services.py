"""RAG服务单元测试

测试EmbeddingService、IndexingService和ConversationService的功能。
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from holoassist.app.models.conversation import DialogueType
from holoassist.app.services.conversation_service import ConversationService
from holoassist.app.services.embedding_service import EmbeddingService
from holoassist.app.services.indexing_service import IndexingService


class TestEmbeddingService:
    """EmbeddingService测试"""

    @pytest.mark.asyncio
    async def test_generate_embedding_ollama(self):
        """测试Ollama后端生成嵌入向量"""
        # Mock OllamaService
        mock_ollama_service = AsyncMock()
        mock_ollama_service.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])

        with patch("holoassist.app.services.embedding_service.get_factory") as mock_factory:
            mock_factory_instance = MagicMock()
            mock_factory_instance.get_ollama_service = MagicMock(return_value=mock_ollama_service)
            mock_factory.return_value = mock_factory_instance

            service = EmbeddingService(embedding_type="ollama", model="test-model")
            embedding = await service.generate_embedding("test text")

            assert isinstance(embedding, list)
            assert len(embedding) == 3
            assert embedding == [0.1, 0.2, 0.3]
            mock_ollama_service.generate_embedding.assert_called_once_with("test text", model="test-model")

    @pytest.mark.asyncio
    async def test_generate_embedding_siliconflow(self):
        """测试SiliconFlow后端生成嵌入向量"""
        # Mock SiliconFlowService
        mock_siliconflow_service = AsyncMock()
        mock_siliconflow_service.generate_embedding = AsyncMock(return_value=[0.4, 0.5, 0.6])

        with patch("holoassist.app.services.embedding_service.get_factory") as mock_factory:
            mock_factory_instance = MagicMock()
            mock_factory_instance.get_siliconflow_service = MagicMock(return_value=mock_siliconflow_service)
            mock_factory.return_value = mock_factory_instance

            service = EmbeddingService(embedding_type="siliconflow", model="test-model")
            embedding = await service.generate_embedding("test text")

            assert isinstance(embedding, list)
            assert len(embedding) == 3
            assert embedding == [0.4, 0.5, 0.6]

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self):
        """测试批量生成嵌入向量"""
        mock_ollama_service = AsyncMock()
        mock_ollama_service.generate_embedding = AsyncMock(side_effect=[[0.1, 0.2], [0.3, 0.4]])

        with patch("holoassist.app.services.embedding_service.get_factory") as mock_factory:
            mock_factory_instance = MagicMock()
            mock_factory_instance.get_ollama_service = MagicMock(return_value=mock_ollama_service)
            mock_factory.return_value = mock_factory_instance

            service = EmbeddingService(embedding_type="ollama")
            embeddings = await service.generate_embeddings(["text1", "text2"])

            assert isinstance(embeddings, list)
            assert len(embeddings) == 2
            assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
            assert mock_ollama_service.generate_embedding.call_count == 2

    def test_calculate_similarity(self):
        """测试余弦相似度计算"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = EmbeddingService.calculate_similarity(vec1, vec2)
        assert abs(similarity - 1.0) < 1e-6  # 完全相同，相似度为1

        vec3 = [1.0, 0.0, 0.0]
        vec4 = [0.0, 1.0, 0.0]
        similarity = EmbeddingService.calculate_similarity(vec3, vec4)
        assert abs(similarity - 0.0) < 1e-6  # 垂直，相似度为0

        vec5 = [1.0, 1.0]
        vec6 = [1.0, 0.0]
        similarity = EmbeddingService.calculate_similarity(vec5, vec6)
        assert 0.0 < similarity < 1.0  # 部分相似

    def test_calculate_similarity_different_dimensions(self):
        """测试不同维度的向量应该抛出错误"""
        vec1 = [1.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        with pytest.raises(ValueError, match="Vector dimensions must match"):
            EmbeddingService.calculate_similarity(vec1, vec2)

    def test_unsupported_embedding_type(self):
        """测试不支持的嵌入类型应该抛出错误"""
        with pytest.raises(ValueError, match="Unsupported embedding type"):
            EmbeddingService(embedding_type="unsupported")


class TestIndexingService:
    """IndexingService测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_embedding_service(self):
        """Mock EmbeddingService"""
        mock_service = AsyncMock()
        mock_service.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_service.generate_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        return mock_service

    def test_chunk_text(self, temp_dir, mock_embedding_service):
        """测试文本分块"""
        service = IndexingService(embedding_service=mock_embedding_service, index_dir=str(temp_dir))
        text = "这是一个测试文本。" * 20  # 创建长文本
        chunks = service.chunk_text(text, chunk_size=50, chunk_overlap=10)

        assert isinstance(chunks, list)
        assert len(chunks) > 0
        # 检查所有chunks都是非空的
        assert all(chunk.strip() for chunk in chunks)

    def test_chunk_text_empty(self, temp_dir, mock_embedding_service):
        """测试空文本分块"""
        service = IndexingService(embedding_service=mock_embedding_service, index_dir=str(temp_dir))
        chunks = service.chunk_text("")
        assert chunks == []

    def test_chunk_text_short(self, temp_dir, mock_embedding_service):
        """测试短文本分块"""
        service = IndexingService(embedding_service=mock_embedding_service, index_dir=str(temp_dir))
        text = "短文本"
        chunks = service.chunk_text(text, chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0] == text

    @pytest.mark.asyncio
    async def test_create_index(self, temp_dir, mock_embedding_service):
        """测试创建索引"""
        service = IndexingService(embedding_service=mock_embedding_service, index_dir=str(temp_dir))
        documents = ["文档1", "文档2"]

        index_path = await service.create_index(documents, "test_index")

        assert Path(index_path).exists()
        assert Path(temp_dir / "test_index.documents.txt").exists()

    @pytest.mark.asyncio
    async def test_create_index_empty_documents(self, temp_dir, mock_embedding_service):
        """测试创建空文档索引应该抛出错误"""
        service = IndexingService(embedding_service=mock_embedding_service, index_dir=str(temp_dir))
        with pytest.raises(ValueError, match="documents list cannot be empty"):
            await service.create_index([], "test_index")

    @pytest.mark.asyncio
    async def test_search_similar(self, temp_dir, mock_embedding_service):
        """测试相似度搜索"""
        service = IndexingService(embedding_service=mock_embedding_service, index_dir=str(temp_dir))
        documents = ["这是第一个文档", "这是第二个文档"]

        # 先创建索引
        await service.create_index(documents, "test_index")

        # 搜索相似文档
        results = await service.search_similar("第一个", "test_index", top_k=2)

        assert isinstance(results, list)
        assert len(results) > 0
        # 每个结果应该是(document, distance)元组
        assert all(isinstance(result, tuple) and len(result) == 2 for result in results)

    @pytest.mark.asyncio
    async def test_search_similar_index_not_found(self, temp_dir, mock_embedding_service):
        """测试搜索不存在的索引应该抛出错误"""
        service = IndexingService(embedding_service=mock_embedding_service, index_dir=str(temp_dir))
        with pytest.raises(FileNotFoundError, match="Index not found"):
            await service.search_similar("query", "nonexistent_index")

    def test_delete_index(self, temp_dir, mock_embedding_service):
        """测试删除索引"""
        service = IndexingService(embedding_service=mock_embedding_service, index_dir=str(temp_dir))

        # 创建索引文件
        index_file = temp_dir / "test_index.index"
        doc_file = temp_dir / "test_index.documents.txt"
        index_file.write_text("fake index")
        doc_file.write_text("fake documents")

        # 删除索引
        result = service.delete_index("test_index")

        assert result is True
        assert not index_file.exists()
        assert not doc_file.exists()

    def test_delete_index_not_found(self, temp_dir, mock_embedding_service):
        """测试删除不存在的索引"""
        service = IndexingService(embedding_service=mock_embedding_service, index_dir=str(temp_dir))
        result = service.delete_index("nonexistent_index")
        assert result is False


class TestConversationService:
    """ConversationService测试"""

    @pytest.mark.asyncio
    async def test_create_conversation(self, db_session):
        """测试创建会话"""
        from holoassist.app.models.user import User

        # 创建测试用户
        user = User(username="testuser", email="test@example.com", password_hash="hash")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        service = ConversationService(db_session)
        conversation = await service.create_conversation(
            user_id=user.id,
            title="测试会话",
            dialogue_type=DialogueType.NORMAL,
        )

        assert conversation is not None
        assert conversation.user_id == user.id
        assert conversation.title == "测试会话"
        assert conversation.dialogue_type == DialogueType.NORMAL
        assert conversation.status == "ongoing"

    @pytest.mark.asyncio
    async def test_create_conversation_empty_title(self, db_session):
        """测试创建空标题会话应该抛出错误"""
        from holoassist.app.models.user import User

        user = User(username="testuser2", email="test2@example.com", password_hash="hash")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        service = ConversationService(db_session)
        with pytest.raises(ValueError, match="Title cannot be empty"):
            await service.create_conversation(user_id=user.id, title="", dialogue_type=DialogueType.NORMAL)

    @pytest.mark.asyncio
    async def test_get_conversation(self, db_session):
        """测试获取会话"""
        from holoassist.app.models.conversation import Conversation
        from holoassist.app.models.user import User

        # 创建测试用户和会话
        user = User(username="testuser3", email="test3@example.com", password_hash="hash")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        conversation = Conversation(user_id=user.id, title="测试会话", dialogue_type=DialogueType.NORMAL)
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        service = ConversationService(db_session)
        retrieved = await service.get_conversation(conversation.id, user.id)

        assert retrieved is not None
        assert retrieved.id == conversation.id
        assert retrieved.title == "测试会话"

    @pytest.mark.asyncio
    async def test_get_conversation_wrong_user(self, db_session):
        """测试获取其他用户的会话应该返回None"""
        from holoassist.app.models.conversation import Conversation
        from holoassist.app.models.user import User

        # 创建两个用户
        user1 = User(username="user1", email="user1@example.com", password_hash="hash")
        user2 = User(username="user2", email="user2@example.com", password_hash="hash")
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        # user1创建会话
        conversation = Conversation(user_id=user1.id, title="user1会话", dialogue_type=DialogueType.NORMAL)
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        # user2尝试获取user1的会话
        service = ConversationService(db_session)
        retrieved = await service.get_conversation(conversation.id, user2.id)

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_conversations(self, db_session):
        """测试获取会话列表"""
        from holoassist.app.models.conversation import Conversation
        from holoassist.app.models.user import User

        user = User(username="testuser4", email="test4@example.com", password_hash="hash")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # 创建多个会话
        for i in range(5):
            conversation = Conversation(user_id=user.id, title=f"会话{i}", dialogue_type=DialogueType.NORMAL)
            db_session.add(conversation)
        await db_session.commit()

        service = ConversationService(db_session)
        conversations = await service.list_conversations(user.id, skip=0, limit=10)

        assert len(conversations) == 5
        assert all(conv.user_id == user.id for conv in conversations)

    @pytest.mark.asyncio
    async def test_update_conversation(self, db_session):
        """测试更新会话"""
        from holoassist.app.models.conversation import Conversation
        from holoassist.app.models.user import User

        user = User(username="testuser5", email="test5@example.com", password_hash="hash")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        conversation = Conversation(user_id=user.id, title="原始标题", dialogue_type=DialogueType.NORMAL)
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        service = ConversationService(db_session)
        updated = await service.update_conversation(conversation.id, user.id, title="新标题")

        assert updated is not None
        assert updated.title == "新标题"

    @pytest.mark.asyncio
    async def test_delete_conversation(self, db_session):
        """测试删除会话"""
        from holoassist.app.models.conversation import Conversation
        from holoassist.app.models.user import User

        user = User(username="testuser6", email="test6@example.com", password_hash="hash")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        conversation = Conversation(user_id=user.id, title="待删除会话", dialogue_type=DialogueType.NORMAL)
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        service = ConversationService(db_session)
        result = await service.delete_conversation(conversation.id, user.id)

        assert result is True

        # 验证会话已删除
        retrieved = await service.get_conversation(conversation.id, user.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_add_message(self, db_session):
        """测试添加消息"""
        from holoassist.app.models.conversation import Conversation
        from holoassist.app.models.user import User

        user = User(username="testuser7", email="test7@example.com", password_hash="hash")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        conversation = Conversation(user_id=user.id, title="测试会话", dialogue_type=DialogueType.NORMAL)
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        service = ConversationService(db_session)
        message = await service.add_message(conversation.id, "user", "这是一条测试消息")

        assert message is not None
        assert message.conversation_id == conversation.id
        assert message.sender == "user"
        assert message.content == "这是一条测试消息"
        assert message.message_type == "text"

    @pytest.mark.asyncio
    async def test_add_message_empty_content(self, db_session):
        """测试添加空内容消息应该抛出错误"""
        from holoassist.app.models.conversation import Conversation
        from holoassist.app.models.user import User

        user = User(username="testuser8", email="test8@example.com", password_hash="hash")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        conversation = Conversation(user_id=user.id, title="测试会话", dialogue_type=DialogueType.NORMAL)
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        service = ConversationService(db_session)
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            await service.add_message(conversation.id, "user", "")

    @pytest.mark.asyncio
    async def test_get_messages(self, db_session):
        """测试获取消息列表"""
        from holoassist.app.models.conversation import Conversation
        from holoassist.app.models.message import Message
        from holoassist.app.models.user import User

        user = User(username="testuser9", email="test9@example.com", password_hash="hash")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        conversation = Conversation(user_id=user.id, title="测试会话", dialogue_type=DialogueType.NORMAL)
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        # 添加多条消息
        for i in range(3):
            message = Message(conversation_id=conversation.id, sender="user", content=f"消息{i}")
            db_session.add(message)
        await db_session.commit()

        service = ConversationService(db_session)
        messages = await service.get_messages(conversation.id, user.id)

        assert len(messages) == 3
        assert all(msg.conversation_id == conversation.id for msg in messages)

    @pytest.mark.asyncio
    async def test_get_messages_wrong_user(self, db_session):
        """测试获取其他用户会话的消息应该抛出错误"""
        from holoassist.app.models.conversation import Conversation
        from holoassist.app.models.user import User

        user1 = User(username="user1_msg", email="user1_msg@example.com", password_hash="hash")
        user2 = User(username="user2_msg", email="user2_msg@example.com", password_hash="hash")
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        conversation = Conversation(user_id=user1.id, title="user1会话", dialogue_type=DialogueType.NORMAL)
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        service = ConversationService(db_session)
        with pytest.raises(ValueError, match="not found or access denied"):
            await service.get_messages(conversation.id, user2.id)
