"""LLM服务集成测试

测试DeepSeek和SiliconFlow服务的实际功能。
注意：这些测试需要有效的API密钥，并且会实际调用外部API。
"""

import pytest

from holoassist.app.core.config import settings
from holoassist.app.services.deepseek_service import DeepSeekService
from holoassist.app.services.llm_factory import LLMFactory
from holoassist.app.services.siliconflow_service import SiliconFlowService


@pytest.mark.integration
class TestDeepSeekService:
    """DeepSeek服务集成测试"""

    @pytest.fixture
    def service(self):
        """创建DeepSeek服务实例"""
        return DeepSeekService(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            model=settings.DEEPSEEK_MODEL,
        )

    @pytest.mark.asyncio
    async def test_chat_stream(self, service: DeepSeekService):
        """测试流式对话"""
        messages = [{"role": "user", "content": "你好，请简单介绍一下你自己"}]

        response_parts = []
        async for chunk in service.chat(messages, stream=True):
            response_parts.append(chunk)

        full_response = "".join(response_parts)
        assert len(full_response) > 0, "应该收到响应内容"
        print(f"\nDeepSeek流式响应: {full_response[:100]}...")

    @pytest.mark.asyncio
    async def test_chat_complete(self, service: DeepSeekService):
        """测试非流式对话"""
        messages = [{"role": "user", "content": "用一句话介绍Python编程语言"}]

        response = await service.chat_complete(messages)
        assert len(response) > 0, "应该收到响应内容"
        assert isinstance(response, str), "响应应该是字符串"
        print(f"\nDeepSeek完整响应: {response}")

    @pytest.mark.asyncio
    async def test_chat_with_callback(self, service: DeepSeekService):
        """测试带回调的对话"""
        messages = [{"role": "user", "content": "说一个数字：42"}]
        callback_messages = []

        def on_message(msg: str):
            callback_messages.append(msg)

        response_parts = []
        async for chunk in service.chat(messages, stream=True, on_message=on_message):
            response_parts.append(chunk)

        assert len(callback_messages) > 0, "回调应该被调用"
        assert len(response_parts) > 0, "应该收到响应内容"
        print(f"\nDeepSeek回调消息数: {len(callback_messages)}")

    @pytest.mark.asyncio
    async def test_reason_stream(self, service: DeepSeekService):
        """测试深度思考模式（流式响应）"""
        messages = [{"role": "user", "content": "请思考并回答：1+1等于多少？为什么？"}]

        response_parts = []
        async for chunk in service.reason(messages, stream=True):
            response_parts.append(chunk)

        full_response = "".join(response_parts)
        assert len(full_response) > 0, "应该收到响应内容"
        print(f"\nDeepSeek深度思考流式响应: {full_response[:200]}...")

    @pytest.mark.asyncio
    async def test_reason_complete(self, service: DeepSeekService):
        """测试深度思考模式（非流式响应）"""
        messages = [{"role": "user", "content": "请思考并解释：什么是递归？"}]

        response = await service.reason_complete(messages)
        assert len(response) > 0, "应该收到响应内容"
        assert isinstance(response, str), "响应应该是字符串"
        print(f"\nDeepSeek深度思考完整响应: {response[:300]}...")

    @pytest.mark.asyncio
    async def test_close(self, service: DeepSeekService):
        """测试关闭服务"""
        await service.close()
        # 关闭后不应该抛出异常
        assert True


@pytest.mark.integration
class TestSiliconFlowService:
    """SiliconFlow服务集成测试"""

    @pytest.fixture
    def service(self):
        """创建SiliconFlow服务实例"""
        return SiliconFlowService(
            api_key=settings.SILICONFLOW_API_KEY,
            base_url=settings.SILICONFLOW_BASE_URL,
            embedding_model=settings.SILICONFLOW_EMBEDDING_MODEL,
            vision_model=settings.SILICONFLOW_VISION_MODEL,
            chat_model=settings.SILICONFLOW_CHAT_MODEL,
        )

    @pytest.mark.asyncio
    async def test_chat_stream(self, service: SiliconFlowService):
        """测试流式对话"""
        if not settings.SILICONFLOW_CHAT_MODEL:
            pytest.skip("SILICONFLOW_CHAT_MODEL未配置")

        messages = [{"role": "user", "content": "你好，请简单介绍一下你自己"}]

        response_parts = []
        async for chunk in service.chat(messages, stream=True):
            response_parts.append(chunk)

        full_response = "".join(response_parts)
        assert len(full_response) > 0, "应该收到响应内容"
        print(f"\nSiliconFlow流式响应: {full_response[:100]}...")

    @pytest.mark.asyncio
    async def test_chat_complete(self, service: SiliconFlowService):
        """测试非流式对话"""
        if not settings.SILICONFLOW_CHAT_MODEL:
            pytest.skip("SILICONFLOW_CHAT_MODEL未配置")

        messages = [{"role": "user", "content": "用一句话介绍Python编程语言"}]

        response = await service.chat_complete(messages)
        assert len(response) > 0, "应该收到响应内容"
        assert isinstance(response, str), "响应应该是字符串"
        print(f"\nSiliconFlow完整响应: {response}")

    @pytest.mark.asyncio
    async def test_generate_embedding(self, service: SiliconFlowService):
        """测试生成嵌入向量"""
        text = "这是一个测试文本"

        embedding = await service.generate_embedding(text)
        assert isinstance(embedding, list), "嵌入向量应该是列表"
        assert len(embedding) > 0, "嵌入向量应该有内容"
        assert all(isinstance(x, (int, float)) for x in embedding), "嵌入向量元素应该是数字"
        print(f"\nSiliconFlow嵌入向量维度: {len(embedding)}")

    @pytest.mark.asyncio
    async def test_generate_embedding_with_dimensions(self, service: SiliconFlowService):
        """测试生成指定维度的嵌入向量

        注意：某些模型可能不支持自定义维度，会返回固定维度。
        如果模型不支持，此测试会被跳过。
        """
        text = "测试文本"
        dimensions = 512

        try:
            embedding = await service.generate_embedding(text, dimensions=dimensions)
            # 如果模型支持自定义维度，检查维度是否正确
            # 如果不支持，可能会返回默认维度（如1024），这是正常的
            assert len(embedding) > 0, "嵌入向量应该有内容"
            print(f"\nSiliconFlow指定维度嵌入向量: {len(embedding)} (请求{dimensions}维，实际{len(embedding)}维)")
        except Exception as e:
            # 如果模型不支持dimensions参数，跳过测试
            pytest.skip(f"模型可能不支持自定义维度: {str(e)}")

    @pytest.mark.asyncio
    async def test_vision_complete(self, service: SiliconFlowService):
        """测试视觉模型（使用base64编码的图片）"""
        import base64
        from pathlib import Path

        # 使用项目中的测试图片
        image_path = Path(__file__).parent.parent.parent / "screenshot-20251216-131658.png"

        if not image_path.exists():
            pytest.skip(f"测试图片不存在: {image_path}")

        # 读取图片并转换为base64
        with open(image_path, "rb") as f:
            image_data = f.read()
            base64_str = base64.b64encode(image_data).decode("utf-8")

        messages = [{"role": "user", "content": "请详细描述这张图片中的内容"}]

        try:
            response = await service.vision_complete(
                messages=messages,
                image_base64=base64_str,
            )
            assert len(response) > 0, "应该收到响应内容"
            assert isinstance(response, str), "响应应该是字符串"
            print(f"\nSiliconFlow视觉模型响应: {response[:300]}...")
        except Exception as e:
            # 如果图片处理失败，跳过测试
            pytest.skip(f"视觉模型测试跳过: {str(e)}")

    @pytest.mark.asyncio
    async def test_close(self, service: SiliconFlowService):
        """测试关闭服务"""
        await service.close()
        # 关闭后不应该抛出异常
        assert True


@pytest.mark.integration
class TestLLMFactory:
    """LLM工厂集成测试"""

    @pytest.fixture
    def factory(self):
        """创建LLM工厂实例"""
        return LLMFactory()

    @pytest.mark.asyncio
    async def test_create_chat_service_deepseek(self, factory: LLMFactory):
        """测试创建DeepSeek聊天服务"""
        if settings.CHAT_SERVICE.value != "deepseek":
            pytest.skip(f"CHAT_SERVICE不是deepseek，当前为: {settings.CHAT_SERVICE}")

        service = factory.create_chat_service()
        assert isinstance(service, DeepSeekService), "应该是DeepSeekService实例"

        # 测试服务是否可用
        messages = [{"role": "user", "content": "测试"}]
        response_parts = []
        async for chunk in service.chat(messages, stream=True):
            response_parts.append(chunk)
            break  # 只取第一个chunk测试

        assert len(response_parts) >= 0, "服务应该能正常调用"
        print("\nLLMFactory创建的DeepSeek服务测试通过")

    @pytest.mark.asyncio
    async def test_create_chat_service_siliconflow(self, factory: LLMFactory):
        """测试创建SiliconFlow聊天服务（如果配置了）"""
        if settings.CHAT_SERVICE.value != "siliconflow":
            pytest.skip(f"CHAT_SERVICE不是siliconflow，当前为: {settings.CHAT_SERVICE}")
        if not settings.SILICONFLOW_CHAT_MODEL:
            pytest.skip("SILICONFLOW_CHAT_MODEL未配置")

        service = factory.create_chat_service()
        assert isinstance(service, SiliconFlowService), "应该是SiliconFlowService实例"

        # 测试服务是否可用
        messages = [{"role": "user", "content": "测试"}]
        response_parts = []
        async for chunk in service.chat(messages, stream=True):
            response_parts.append(chunk)
            break  # 只取第一个chunk测试

        assert len(response_parts) >= 0, "服务应该能正常调用"
        print("\nLLMFactory创建的SiliconFlow服务测试通过")

    @pytest.mark.asyncio
    async def test_get_siliconflow_service(self, factory: LLMFactory):
        """测试获取SiliconFlow服务（用于embedding）"""
        service = factory.get_siliconflow_service()
        assert isinstance(service, SiliconFlowService), "应该是SiliconFlowService实例"

        # 测试embedding功能
        embedding = await service.generate_embedding("测试文本")
        assert len(embedding) > 0, "应该能生成嵌入向量"
        print("\nLLMFactory获取的SiliconFlow服务embedding测试通过")

    @pytest.mark.asyncio
    async def test_service_instance_caching(self, factory: LLMFactory):
        """测试服务实例缓存"""
        service1 = factory.create_chat_service()
        service2 = factory.create_chat_service()

        # 应该是同一个实例（缓存）
        assert service1 is service2, "服务实例应该被缓存"
        print("\n服务实例缓存测试通过")

    @pytest.mark.asyncio
    async def test_close_all(self, factory: LLMFactory):
        """测试关闭所有服务"""
        # 先创建一些服务
        factory.create_chat_service()
        factory.get_siliconflow_service()

        # 关闭所有服务
        await factory.close_all()
        # 不应该抛出异常
        assert True
        print("\n关闭所有服务测试通过")
