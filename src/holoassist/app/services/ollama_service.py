"""Ollama服务

提供与Ollama本地模型的交互功能，支持对话和嵌入向量生成。
"""
import json
from typing import AsyncGenerator, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from holoassist.app.core.config import settings
from holoassist.app.core.logger import get_logger

logger = get_logger(service="ollama_service")


class OllamaService:
    """Ollama服务类

    提供与Ollama API的交互功能，支持流式对话和嵌入向量生成。
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        chat_model: Optional[str] = None,
        reason_model: Optional[str] = None,
        embedding_model: Optional[str] = None,
        agent_model: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """初始化Ollama服务

        Args:
            base_url: Ollama服务地址，如果为None则使用settings.OLLAMA_BASE_URL
            chat_model: 聊天模型名称，如果为None则使用settings.OLLAMA_CHAT_MODEL
            reason_model: 推理模型名称，如果为None则使用settings.OLLAMA_REASON_MODEL
            embedding_model: 嵌入模型名称，如果为None则使用settings.OLLAMA_EMBEDDING_MODEL
            agent_model: Agent模型名称，如果为None则使用settings.OLLAMA_AGENT_MODEL
            timeout: 请求超时时间（秒）
        """
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.chat_model = chat_model or settings.OLLAMA_CHAT_MODEL
        self.reason_model = reason_model or settings.OLLAMA_REASON_MODEL
        self.embedding_model = embedding_model or settings.OLLAMA_EMBEDDING_MODEL
        self.agent_model = agent_model or settings.OLLAMA_AGENT_MODEL
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端（懒加载）

        Returns:
            httpx.AsyncClient: HTTP异步客户端实例
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        """关闭HTTP客户端连接"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """格式化消息列表为Ollama API格式

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
    ) -> AsyncGenerator[str, None]:
        """与Ollama模型进行对话（流式响应）

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}, ...]
            model: 模型名称，如果为None则使用self.chat_model
            stream: 是否使用流式响应

        Yields:
            str: 流式响应中的文本片段

        Raises:
            httpx.HTTPError: HTTP请求错误
            ValueError: 模型响应格式错误
        """
        model = model or self.chat_model
        client = await self._get_client()
        formatted_messages = self._format_messages(messages)

        try:
            if stream:
                # 流式响应
                async with client.stream(
                    "POST",
                    "/api/chat",
                    json={
                        "model": model,
                        "messages": formatted_messages,
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                            if "message" in chunk and "content" in chunk["message"]:
                                content = chunk["message"]["content"]
                                if content:
                                    yield content
                            if chunk.get("done", False):
                                break
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse JSON line: {line[:100]}")
                            continue
            else:
                # 非流式响应
                response = await client.post(
                    "/api/chat",
                    json={
                        "model": model,
                        "messages": formatted_messages,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                data = response.json()
                if "message" in data and "content" in data["message"]:
                    yield data["message"]["content"]
                else:
                    raise ValueError(f"Unexpected response format: {data}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error in Ollama chat: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in Ollama chat: {str(e)}")
            raise

    async def chat_complete(
        self, messages: List[Dict[str, str]], model: Optional[str] = None
    ) -> str:
        """与Ollama模型进行对话（非流式，返回完整响应）

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
        self, text: str, model: Optional[str] = None
    ) -> List[float]:
        """生成文本的嵌入向量

        Args:
            text: 要生成嵌入向量的文本
            model: 嵌入模型名称，如果为None则使用self.embedding_model

        Returns:
            List[float]: 嵌入向量

        Raises:
            httpx.HTTPError: HTTP请求错误
            ValueError: 模型响应格式错误
        """
        model = model or self.embedding_model
        client = await self._get_client()

        try:
            response = await client.post(
                "/api/embeddings",
                json={
                    "model": model,
                    "prompt": text,
                },
            )
            response.raise_for_status()
            data = response.json()

            if "embedding" in data:
                return data["embedding"]
            else:
                raise ValueError(f"Unexpected response format: {data}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error in Ollama embedding: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in Ollama embedding: {str(e)}")
            raise
