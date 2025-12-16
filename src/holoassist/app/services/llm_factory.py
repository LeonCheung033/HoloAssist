"""LLM工厂

使用工厂模式创建和管理LLM服务实例。
"""

from holoassist.app.core.config import ServiceType, settings
from holoassist.app.core.logger import get_logger
from holoassist.app.services.deepseek_service import DeepSeekService
from holoassist.app.services.ollama_service import OllamaService
from holoassist.app.services.siliconflow_service import SiliconFlowService

logger = get_logger(service="llm_factory")


class LLMFactory:
    """LLM工厂类

    根据配置创建对应的LLM服务实例，支持服务实例缓存。
    """

    def __init__(self):
        """初始化LLM工厂"""
        # 服务实例缓存
        self._chat_service: DeepSeekService | OllamaService | SiliconFlowService | None = None
        self._reason_service: DeepSeekService | OllamaService | SiliconFlowService | None = None
        self._agent_service: DeepSeekService | OllamaService | SiliconFlowService | None = None
        self._ollama_service: OllamaService | None = None
        self._deepseek_service: DeepSeekService | None = None
        self._siliconflow_service: SiliconFlowService | None = None

    def _create_deepseek_service(self) -> DeepSeekService:
        """创建DeepSeek服务实例

        Returns:
            DeepSeekService: DeepSeek服务实例
        """
        if self._deepseek_service is None:
            self._deepseek_service = DeepSeekService(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                model=settings.DEEPSEEK_MODEL,
            )
            logger.info("Created DeepSeek service instance")
        return self._deepseek_service

    def _create_ollama_service(self) -> OllamaService:
        """创建Ollama服务实例

        Returns:
            OllamaService: Ollama服务实例
        """
        if self._ollama_service is None:
            self._ollama_service = OllamaService(
                base_url=settings.OLLAMA_BASE_URL,
                chat_model=settings.OLLAMA_CHAT_MODEL,
                reason_model=settings.OLLAMA_REASON_MODEL,
                embedding_model=settings.OLLAMA_EMBEDDING_MODEL,
                agent_model=settings.OLLAMA_AGENT_MODEL,
            )
            logger.info("Created Ollama service instance")
        return self._ollama_service

    def _create_siliconflow_service(self) -> SiliconFlowService:
        """创建SiliconFlow服务实例

        Returns:
            SiliconFlowService: SiliconFlow服务实例
        """
        if self._siliconflow_service is None:
            self._siliconflow_service = SiliconFlowService(
                api_key=settings.SILICONFLOW_API_KEY,
                base_url=settings.SILICONFLOW_BASE_URL,
                embedding_model=settings.SILICONFLOW_EMBEDDING_MODEL,
                vision_model=settings.SILICONFLOW_VISION_MODEL,
                chat_model=settings.SILICONFLOW_CHAT_MODEL,
            )
            logger.info("Created SiliconFlow service instance")
        return self._siliconflow_service

    def create_chat_service(self) -> DeepSeekService | OllamaService | SiliconFlowService:
        """创建聊天服务实例

        根据settings.CHAT_SERVICE配置创建对应的服务实例。

        Returns:
            DeepSeekService | OllamaService | SiliconFlowService: 聊天服务实例

        Raises:
            ValueError: 如果服务类型不支持
        """
        if self._chat_service is None:
            if settings.CHAT_SERVICE == ServiceType.DEEPSEEK:
                self._chat_service = self._create_deepseek_service()
            elif settings.CHAT_SERVICE == ServiceType.OLLAMA:
                self._chat_service = self._create_ollama_service()
            elif settings.CHAT_SERVICE == ServiceType.SILICONFLOW:
                self._chat_service = self._create_siliconflow_service()
            else:
                raise ValueError(f"Unsupported chat service type: {settings.CHAT_SERVICE}")
            logger.info(f"Created chat service: {settings.CHAT_SERVICE}")
        # mypy需要类型断言
        assert self._chat_service is not None
        # 类型转换以帮助mypy理解
        from typing import cast

        return cast(DeepSeekService | OllamaService | SiliconFlowService, self._chat_service)

    def create_reason_service(self) -> DeepSeekService | OllamaService | SiliconFlowService:
        """创建推理服务实例

        根据settings.REASON_SERVICE配置创建对应的服务实例。

        注意：
        - 如果返回的是 DeepSeekService，可以使用 reason() 和 reason_complete() 方法
          进行深度思考推理（使用 deepseek-reasoner 模型）。
        - 如果返回的是其他服务，使用普通的 chat() 方法。

        Returns:
            DeepSeekService | OllamaService | SiliconFlowService: 推理服务实例

        Raises:
            ValueError: 如果服务类型不支持
        """
        if self._reason_service is None:
            if settings.REASON_SERVICE == ServiceType.DEEPSEEK:
                self._reason_service = self._create_deepseek_service()
            elif settings.REASON_SERVICE == ServiceType.OLLAMA:
                self._reason_service = self._create_ollama_service()
            elif settings.REASON_SERVICE == ServiceType.SILICONFLOW:
                self._reason_service = self._create_siliconflow_service()
            else:
                raise ValueError(f"Unsupported reason service type: {settings.REASON_SERVICE}")
            logger.info(f"Created reason service: {settings.REASON_SERVICE}")
        # mypy需要类型断言
        assert self._reason_service is not None
        # 类型转换以帮助mypy理解
        from typing import cast

        return cast(DeepSeekService | OllamaService | SiliconFlowService, self._reason_service)

    def create_agent_service(self) -> DeepSeekService | OllamaService | SiliconFlowService:
        """创建Agent服务实例

        根据settings.AGENT_SERVICE配置创建对应的服务实例。

        Returns:
            DeepSeekService | OllamaService | SiliconFlowService: Agent服务实例

        Raises:
            ValueError: 如果服务类型不支持
        """
        if self._agent_service is None:
            if settings.AGENT_SERVICE == ServiceType.DEEPSEEK:
                self._agent_service = self._create_deepseek_service()
            elif settings.AGENT_SERVICE == ServiceType.OLLAMA:
                self._agent_service = self._create_ollama_service()
            elif settings.AGENT_SERVICE == ServiceType.SILICONFLOW:
                self._agent_service = self._create_siliconflow_service()
            else:
                raise ValueError(f"Unsupported agent service type: {settings.AGENT_SERVICE}")
            logger.info(f"Created agent service: {settings.AGENT_SERVICE}")
        # mypy需要类型断言
        assert self._agent_service is not None
        # 类型转换以帮助mypy理解
        from typing import cast

        return cast(DeepSeekService | OllamaService | SiliconFlowService, self._agent_service)

    def get_ollama_service(self) -> OllamaService:
        """获取Ollama服务实例（用于生成embedding等）

        Returns:
            OllamaService: Ollama服务实例
        """
        return self._create_ollama_service()

    def get_deepseek_service(self) -> DeepSeekService:
        """获取DeepSeek服务实例（用于深度思考等）

        返回的 DeepSeekService 实例可以使用 reason() 和 reason_complete() 方法
        进行深度思考推理。

        Returns:
            DeepSeekService: DeepSeek服务实例
        """
        return self._create_deepseek_service()

    def get_siliconflow_service(self) -> SiliconFlowService:
        """获取SiliconFlow服务实例（用于生成embedding、视觉模型等）

        Returns:
            SiliconFlowService: SiliconFlow服务实例
        """
        return self._create_siliconflow_service()

    async def close_all(self):
        """关闭所有服务实例的连接"""
        if self._deepseek_service:
            await self._deepseek_service.close()
        if self._ollama_service:
            await self._ollama_service.close()
        if self._siliconflow_service:
            await self._siliconflow_service.close()
        logger.info("Closed all LLM service connections")


# 创建全局工厂实例（单例模式）
_factory: LLMFactory | None = None


def get_factory() -> LLMFactory:
    """获取全局LLM工厂实例（单例模式）

    Returns:
        LLMFactory: LLM工厂实例
    """
    global _factory
    if _factory is None:
        _factory = LLMFactory()
    return _factory
