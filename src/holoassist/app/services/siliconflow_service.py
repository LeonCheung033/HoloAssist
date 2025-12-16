"""SiliconFlow服务

提供与SiliconFlow API的交互功能，支持对话、嵌入向量生成和视觉模型。
SiliconFlow兼容OpenAI API格式。
"""
from typing import AsyncGenerator, Dict, List, Optional

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from holoassist.app.core.config import settings
from holoassist.app.core.logger import get_logger

logger = get_logger(service="siliconflow_service")


class SiliconFlowService:
    """SiliconFlow服务类

    提供与SiliconFlow API的交互功能，支持对话、嵌入向量生成和视觉模型。
    SiliconFlow兼容OpenAI API格式，可以使用OpenAI客户端。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
        vision_model: Optional[str] = None,
        chat_model: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """初始化SiliconFlow服务

        Args:
            api_key: SiliconFlow API密钥，如果为None则使用settings.SILICONFLOW_API_KEY
            base_url: SiliconFlow API地址，如果为None则使用settings.SILICONFLOW_BASE_URL
            embedding_model: Embedding模型名称，如果为None则使用settings.SILICONFLOW_EMBEDDING_MODEL
            vision_model: 视觉模型名称，如果为None则使用settings.SILICONFLOW_VISION_MODEL
            chat_model: 对话模型名称，如果为None则使用settings.SILICONFLOW_CHAT_MODEL
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key or settings.SILICONFLOW_API_KEY
        self.base_url = base_url or settings.SILICONFLOW_BASE_URL
        self.embedding_model = embedding_model or settings.SILICONFLOW_EMBEDDING_MODEL
        self.vision_model = vision_model or settings.SILICONFLOW_VISION_MODEL
        self.chat_model = chat_model or settings.SILICONFLOW_CHAT_MODEL
        self.timeout = timeout

        # 初始化OpenAI客户端（SiliconFlow兼容OpenAI API）
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    async def close(self):
        """关闭客户端连接"""
        # OpenAI客户端会自动管理连接，这里可以留空或添加清理逻辑
        pass

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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = True,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """与SiliconFlow模型进行对话（流式响应）

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}, ...]
            model: 模型名称，如果为None则使用self.chat_model
            stream: 是否使用流式响应
            max_tokens: 最大token数
            temperature: 温度参数
            top_p: top_p参数
            **kwargs: 其他API参数（enable_thinking, thinking_budget, min_p, top_k等）

        Yields:
            str: 流式响应中的文本片段

        Raises:
            ValueError: 如果模型未指定
            Exception: API调用错误
        """
        model = model or self.chat_model
        if not model:
            raise ValueError("Chat model not specified")

        formatted_messages = self._format_messages(messages)

        # 构建API参数
        api_params = {
            "model": model,
            "messages": formatted_messages,
            "stream": stream,
        }

        # 添加可选参数
        if max_tokens is not None:
            api_params["max_tokens"] = max_tokens
        if temperature is not None:
            api_params["temperature"] = temperature
        if top_p is not None:
            api_params["top_p"] = top_p

        # 添加其他kwargs参数
        api_params.update(kwargs)

        try:
            response = await self.client.chat.completions.create(**api_params)

            if stream:
                # 流式响应
                async for chunk in response:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            yield delta.content
            else:
                # 非流式响应
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    if content:
                        yield content

        except Exception as e:
            logger.error(f"Error in SiliconFlow chat: {str(e)}")
            raise

    async def chat_complete(
        self, messages: List[Dict[str, str]], model: Optional[str] = None
    ) -> str:
        """与SiliconFlow模型进行对话（非流式，返回完整响应）

        Args:
            messages: 消息列表
            model: 模型名称，如果为None则使用self.chat_model

        Returns:
            str: 完整的响应文本
        """
        full_response = ""
        async for chunk in self.chat(messages, model=model, stream=False):
            full_response += chunk
        return full_response

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None,
        encoding_format: str = "float",
        dimensions: Optional[int] = None,
    ) -> List[float]:
        """生成文本的嵌入向量

        Args:
            text: 要生成嵌入向量的文本（可以是字符串或字符串列表）
            model: 嵌入模型名称，如果为None则使用self.embedding_model（默认：BAAI/bge-large-zh-v1.5）
            encoding_format: 编码格式，默认为"float"
            dimensions: 向量维度（可选）

        Returns:
            List[float]: 嵌入向量（如果输入是列表，返回第一个向量的embedding）

        Raises:
            ValueError: 如果模型未指定
            Exception: API调用错误
        """
        model = model or self.embedding_model
        if not model:
            # 使用默认模型
            model = "BAAI/bge-large-zh-v1.5"

        try:
            # SiliconFlow兼容OpenAI的embeddings API
            api_params = {
                "model": model,
                "input": text,
                "encoding_format": encoding_format,
            }

            # 添加可选的dimensions参数
            if dimensions is not None:
                api_params["dimensions"] = dimensions

            response = await self.client.embeddings.create(**api_params)

            if response.data and len(response.data) > 0:
                return response.data[0].embedding
            else:
                raise ValueError("Empty embedding response")

        except Exception as e:
            logger.error(f"Error in SiliconFlow embedding: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def vision(
        self,
        messages: List[Dict[str, str]],
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        model: Optional[str] = None,
        stream: bool = True,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """调用视觉模型进行图像理解（流式响应）

        Args:
            messages: 消息列表，包含图像相关的提示
            image_url: 图像URL（如果提供）
            image_base64: 图像base64编码（如果提供）
            model: 视觉模型名称，如果为None则使用self.vision_model（默认：Qwen/Qwen2.5-VL-32B-Instruct）
            stream: 是否使用流式响应
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他API参数

        Yields:
            str: 流式响应中的文本片段

        Raises:
            ValueError: 如果图像未提供
            Exception: API调用错误
        """
        model = model or self.vision_model
        if not model:
            # 使用默认模型
            model = "Qwen/Qwen2.5-VL-32B-Instruct"

        if not image_url and not image_base64:
            raise ValueError("Either image_url or image_base64 must be provided")

        # 格式化消息，添加图像内容
        formatted_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # 构建消息内容，包含图像
            message_content = [{"type": "text", "text": content}]

            if image_url:
                message_content.append({"type": "image_url", "image_url": {"url": image_url}})
            elif image_base64:
                # base64格式：data:image/jpeg;base64,{base64_string}
                image_data = (
                    image_base64
                    if image_base64.startswith("data:")
                    else f"data:image/jpeg;base64,{image_base64}"
                )
                message_content.append(
                    {"type": "image_url", "image_url": {"url": image_data}}
                )

            formatted_messages.append({"role": role, "content": message_content})

        # 构建API参数
        api_params = {
            "model": model,
            "messages": formatted_messages,
            "stream": stream,
        }

        # 添加可选参数
        if max_tokens is not None:
            api_params["max_tokens"] = max_tokens
        if temperature is not None:
            api_params["temperature"] = temperature

        # 添加其他kwargs参数
        api_params.update(kwargs)

        try:
            response = await self.client.chat.completions.create(**api_params)

            if stream:
                # 流式响应
                async for chunk in response:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            yield delta.content
            else:
                # 非流式响应
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    if content:
                        yield content

        except Exception as e:
            logger.error(f"Error in SiliconFlow vision: {str(e)}")
            raise

    async def vision_complete(
        self,
        messages: List[Dict[str, str]],
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """调用视觉模型进行图像理解（非流式，返回完整响应）

        Args:
            messages: 消息列表
            image_url: 图像URL
            image_base64: 图像base64编码
            model: 视觉模型名称

        Returns:
            str: 完整的响应文本
        """
        full_response = ""
        async for chunk in self.vision(
            messages, image_url=image_url, image_base64=image_base64, model=model, stream=False
        ):
            full_response += chunk
        return full_response
