"""DeepSeek服务

提供与DeepSeek API的交互功能，支持流式对话、消息保存回调和语义缓存集成。
"""
from typing import AsyncGenerator, Callable, Dict, List, Optional

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from holoassist.app.core.config import settings
from holoassist.app.core.logger import get_logger
from holoassist.app.services.redis_semantic_cache import RedisSemanticCache

logger = get_logger(service="deepseek_service")


class DeepSeekService:
    """DeepSeek服务类

    提供与DeepSeek API的交互功能，支持流式对话、消息保存回调和语义缓存。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
        enable_cache: bool = True,
    ):
        """初始化DeepSeek服务

        Args:
            api_key: DeepSeek API密钥，如果为None则使用settings.DEEPSEEK_API_KEY
            base_url: DeepSeek API地址，如果为None则使用settings.DEEPSEEK_BASE_URL
            model: 模型名称，如果为None则使用settings.DEEPSEEK_MODEL
            timeout: 请求超时时间（秒）
            enable_cache: 是否启用语义缓存
        """
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.base_url = base_url or settings.DEEPSEEK_BASE_URL
        self.model = model or settings.DEEPSEEK_MODEL
        self.timeout = timeout
        self.enable_cache = enable_cache

        # 初始化OpenAI客户端（DeepSeek使用OpenAI兼容的API）
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

        # 初始化语义缓存（如果启用）
        self.cache: Optional[RedisSemanticCache] = None
        if self.enable_cache:
            self.cache = RedisSemanticCache()

    async def close(self):
        """关闭客户端连接"""
        if self.cache:
            await self.cache.close()

    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """格式化消息列表为OpenAI API格式

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}, ...]

        Returns:
            List[Dict[str, str]]: 格式化后的消息列表
        """
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted.append({"role": role, "content": content})
        return formatted

    def _get_last_user_message(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """获取最后一条用户消息

        Args:
            messages: 消息列表

        Returns:
            Optional[str]: 最后一条用户消息的内容，如果没有则返回None
        """
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content")
        return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        on_message: Optional[Callable[[str], None]] = None,
        use_cache: bool = True,
        enable_thinking: bool = False,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """与DeepSeek模型进行对话（流式响应）

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}, ...]
            stream: 是否使用流式响应
            on_message: 消息保存回调函数，每收到一个文本片段时调用
            use_cache: 是否使用语义缓存
            enable_thinking: 是否启用思考模式（仅对deepseek-reasoner模型有效）
            **kwargs: 其他API参数（如max_tokens, temperature等）

        Yields:
            str: 流式响应中的文本片段

        Raises:
            Exception: API调用错误
        """
        # 检查语义缓存
        cached_response = None
        if self.enable_cache and use_cache and self.cache:
            try:
                # 获取最后一条用户消息用于缓存查询
                last_user_message = self._get_last_user_message(messages)
                if last_user_message:
                    # 注意：这里需要embedding，但embedding需要从Ollama服务获取
                    # 为了简化，这里先跳过缓存查询，后续在集成时再完善
                    # cached_response = await self.cache.get_cache(last_user_message, embedding)
                    pass
            except Exception as e:
                logger.warning(f"Error checking cache: {str(e)}")

        # 如果缓存命中，直接返回缓存结果
        if cached_response:
            logger.info("Using cached response")
            if on_message:
                on_message(cached_response)
            yield cached_response
            return

        # 格式化消息
        formatted_messages = self._format_messages(messages)

        # 构建API参数
        api_params = {
            "model": self.model,
            "messages": formatted_messages,
            "stream": stream,
        }

        # 添加思考模式（如果启用）
        if enable_thinking:
            api_params["extra_body"] = {"thinking": {"type": "enabled"}}

        # 添加其他kwargs参数
        api_params.update(kwargs)

        try:
            # 调用DeepSeek API
            response = await self.client.chat.completions.create(**api_params)

            if stream:
                # 流式响应
                full_response = ""
                async for chunk in response:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            content = delta.content
                            full_response += content
                            if on_message:
                                on_message(content)
                            yield content

                # 保存到缓存（如果启用）
                if self.enable_cache and use_cache and self.cache and full_response:
                    try:
                        last_user_message = self._get_last_user_message(messages)
                        if last_user_message:
                            # 注意：这里需要embedding，但embedding需要从Ollama服务获取
                            # 为了简化，这里先跳过缓存存储，后续在集成时再完善
                            # embedding = await self._get_embedding(last_user_message)
                            # await self.cache.set_cache(last_user_message, full_response, embedding)
                            pass
                    except Exception as e:
                        logger.warning(f"Error saving to cache: {str(e)}")

            else:
                # 非流式响应
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    if content:
                        if on_message:
                            on_message(content)
                        yield content

                        # 保存到缓存（如果启用）
                        if self.enable_cache and use_cache and self.cache:
                            try:
                                last_user_message = self._get_last_user_message(messages)
                                if last_user_message:
                                    # 注意：这里需要embedding，但embedding需要从Ollama服务获取
                                    # 为了简化，这里先跳过缓存存储，后续在集成时再完善
                                    # embedding = await self._get_embedding(last_user_message)
                                    # await self.cache.set_cache(last_user_message, content, embedding)
                                    pass
                            except Exception as e:
                                logger.warning(f"Error saving to cache: {str(e)}")

        except Exception as e:
            logger.error(f"Error in DeepSeek chat: {str(e)}")
            raise

    async def chat_complete(
        self,
        messages: List[Dict[str, str]],
        on_message: Optional[Callable[[str], None]] = None,
        use_cache: bool = True,
        enable_thinking: bool = False,
        **kwargs,
    ) -> str:
        """与DeepSeek模型进行对话（非流式，返回完整响应）

        Args:
            messages: 消息列表
            on_message: 消息保存回调函数
            use_cache: 是否使用语义缓存
            enable_thinking: 是否启用思考模式（仅对deepseek-reasoner模型有效）
            **kwargs: 其他API参数（如max_tokens, temperature等）

        Returns:
            str: 完整的响应文本
        """
        full_response = ""
        async for chunk in self.chat(
            messages, stream=False, on_message=on_message, use_cache=use_cache, enable_thinking=enable_thinking, **kwargs
        ):
            full_response += chunk
        return full_response

    async def reason(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        on_message: Optional[Callable[[str], None]] = None,
        use_cache: bool = False,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """使用深度思考模型进行推理（流式响应）

        使用 deepseek-reasoner 模型，自动启用思考模式。

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}, ...]
            stream: 是否使用流式响应
            on_message: 消息保存回调函数，每收到一个文本片段时调用
            use_cache: 是否使用语义缓存（默认False，因为推理结果可能每次不同）
            **kwargs: 其他API参数（如max_tokens, temperature等）

        Yields:
            str: 流式响应中的文本片段

        Raises:
            Exception: API调用错误
        """
        # 使用 reasoner 模型，并启用思考模式
        reasoner_model = settings.DEEPSEEK_REASONER_MODEL
        original_model = self.model
        
        try:
            # 临时切换到 reasoner 模型
            self.model = reasoner_model
            # 调用 chat 方法，启用思考模式
            async for chunk in self.chat(
                messages, stream=stream, on_message=on_message, use_cache=use_cache, enable_thinking=True, **kwargs
            ):
                yield chunk
        finally:
            # 恢复原始模型
            self.model = original_model

    async def reason_complete(
        self,
        messages: List[Dict[str, str]],
        on_message: Optional[Callable[[str], None]] = None,
        use_cache: bool = False,
        **kwargs,
    ) -> str:
        """使用深度思考模型进行推理（非流式，返回完整响应）

        Args:
            messages: 消息列表
            on_message: 消息保存回调函数
            use_cache: 是否使用语义缓存（默认False）
            **kwargs: 其他API参数

        Returns:
            str: 完整的响应文本
        """
        full_response = ""
        async for chunk in self.reason(messages, stream=False, on_message=on_message, use_cache=use_cache, **kwargs):
            full_response += chunk
        return full_response
