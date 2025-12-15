"""
数据模型单元测试
"""

from holoassist.app.models import Conversation, Message, User
from holoassist.app.models.conversation import DialogueType


class TestUserModel:
    """用户模型测试"""

    def test_user_model_attributes(self):
        """测试用户模型的属性"""
        assert hasattr(User, "__tablename__")
        assert User.__tablename__ == "users"
        assert hasattr(User, "id")
        assert hasattr(User, "username")
        assert hasattr(User, "email")
        assert hasattr(User, "password_hash")
        assert hasattr(User, "conversations")

    def test_user_model_import(self):
        """测试用户模型可以正确导入"""
        assert User is not None
        assert isinstance(User.__tablename__, str)


class TestConversationModel:
    """会话模型测试"""

    def test_conversation_model_attributes(self):
        """测试会话模型的属性"""
        assert hasattr(Conversation, "__tablename__")
        assert Conversation.__tablename__ == "conversations"
        assert hasattr(Conversation, "id")
        assert hasattr(Conversation, "user_id")
        assert hasattr(Conversation, "title")
        assert hasattr(Conversation, "dialogue_type")
        assert hasattr(Conversation, "user")
        assert hasattr(Conversation, "messages")

    def test_dialogue_type_enum(self):
        """测试DialogueType枚举"""
        assert DialogueType.NORMAL.value == "普通对话"
        assert DialogueType.DEEP_THINKING.value == "深度思考"
        assert DialogueType.WEB_SEARCH.value == "联网检索"
        assert DialogueType.RAG.value == "RAG 问答"
        assert isinstance(DialogueType.NORMAL.value, str)


class TestMessageModel:
    """消息模型测试"""

    def test_message_model_attributes(self):
        """测试消息模型的属性"""
        assert hasattr(Message, "__tablename__")
        assert Message.__tablename__ == "messages"
        assert hasattr(Message, "id")
        assert hasattr(Message, "conversation_id")
        assert hasattr(Message, "sender")
        assert hasattr(Message, "content")
        assert hasattr(Message, "created_at")
        assert hasattr(Message, "message_type")
        assert hasattr(Message, "conversation")

    def test_message_model_import(self):
        """测试消息模型可以正确导入"""
        assert Message is not None
        assert isinstance(Message.__tablename__, str)


class TestModelRelationships:
    """模型关系测试"""

    def test_models_can_be_imported_together(self):
        """测试所有模型可以一起导入"""
        from holoassist.app.models import Conversation, Message, User

        assert User is not None
        assert Conversation is not None
        assert Message is not None
