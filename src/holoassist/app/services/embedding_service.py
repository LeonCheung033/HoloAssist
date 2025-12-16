"""嵌入服务

提供统一的嵌入向量生成接口，支持多种后端（Ollama、sentence-transformers、SiliconFlow）。
"""

import asyncio

import numpy as np

from holoassist.app.core.config import settings
from holoassist.app.core.logger import get_logger
from holoassist.app.services.llm_factory import get_factory

logger = get_logger(service="embedding_service")


class EmbeddingService:
    """嵌入服务类

    提供统一的嵌入向量生成接口，支持多种后端。
    """

    def __init__(
        self,
        embedding_type: str | None = None,
        model: str | None = None,
    ):
        """初始化嵌入服务

        Args:
            embedding_type: 嵌入类型（ollama、sentence_transformer、siliconflow），
                           如果为None则使用settings.EMBEDDING_TYPE
            model: 模型名称，如果为None则使用settings.EMBEDDING_MODEL
        """
        self.embedding_type = (embedding_type or settings.EMBEDDING_TYPE).lower()
        self.model = model or settings.EMBEDDING_MODEL

        # 根据类型初始化对应的后端
        self._ollama_service = None
        self._siliconflow_service = None
        self._sentence_transformer_model = None
        self._sentence_transformer_class = None

        if self.embedding_type == "ollama":
            factory = get_factory()
            self._ollama_service = factory.get_ollama_service()
        elif self.embedding_type == "siliconflow":
            factory = get_factory()
            self._siliconflow_service = factory.get_siliconflow_service()
        elif self.embedding_type == "sentence_transformer":
            # sentence-transformers是同步库，延迟加载
            try:
                from sentence_transformers import SentenceTransformer

                self._sentence_transformer_class = SentenceTransformer
            except ImportError:
                logger.error("sentence-transformers not installed. Please install it: uv add sentence-transformers")
                raise
        else:
            raise ValueError(f"Unsupported embedding type: {self.embedding_type}")

        logger.info(f"Initialized EmbeddingService with type: {self.embedding_type}, model: {self.model}")

    async def generate_embedding(self, text: str) -> list[float]:
        """生成单个文本的嵌入向量

        Args:
            text: 要生成嵌入向量的文本

        Returns:
            list[float]: 嵌入向量

        Raises:
            ValueError: 如果嵌入类型不支持
            Exception: 后端服务错误
        """
        if self.embedding_type == "ollama":
            if not self._ollama_service:
                factory = get_factory()
                self._ollama_service = factory.get_ollama_service()
            return await self._ollama_service.generate_embedding(text, model=self.model)

        elif self.embedding_type == "siliconflow":
            if not self._siliconflow_service:
                factory = get_factory()
                self._siliconflow_service = factory.get_siliconflow_service()
            return await self._siliconflow_service.generate_embedding(text, model=self.model)

        elif self.embedding_type == "sentence_transformer":
            # sentence-transformers是同步库，需要在线程池中运行
            return await asyncio.to_thread(self._generate_sentence_transformer_embedding, text)

        else:
            raise ValueError(f"Unsupported embedding type: {self.embedding_type}")

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """批量生成文本的嵌入向量

        Args:
            texts: 要生成嵌入向量的文本列表

        Returns:
            list[list[float]]: 嵌入向量列表

        Raises:
            ValueError: 如果嵌入类型不支持
            Exception: 后端服务错误
        """
        if self.embedding_type == "ollama":
            # Ollama不支持批量，需要逐个生成
            if not self._ollama_service:
                factory = get_factory()
                self._ollama_service = factory.get_ollama_service()
            embeddings = []
            for text in texts:
                embedding = await self._ollama_service.generate_embedding(text, model=self.model)
                embeddings.append(embedding)
            return embeddings

        elif self.embedding_type == "siliconflow":
            # SiliconFlow支持批量（通过input参数传递列表）
            if not self._siliconflow_service:
                factory = get_factory()
                self._siliconflow_service = factory.get_siliconflow_service()
            # SiliconFlow的generate_embedding支持列表输入
            # 但当前实现只返回第一个，需要修改或使用不同的方法
            # 暂时逐个生成
            embeddings = []
            for text in texts:
                embedding = await self._siliconflow_service.generate_embedding(text, model=self.model)
                embeddings.append(embedding)
            return embeddings

        elif self.embedding_type == "sentence_transformer":
            # sentence-transformers支持批量，在线程池中运行
            return await asyncio.to_thread(self._generate_sentence_transformer_embeddings, texts)

        else:
            raise ValueError(f"Unsupported embedding type: {self.embedding_type}")

    def _generate_sentence_transformer_embedding(self, text: str) -> list[float]:
        """使用sentence-transformers生成嵌入向量（同步方法）

        Args:
            text: 要生成嵌入向量的文本

        Returns:
            list[float]: 嵌入向量
        """
        if self._sentence_transformer_model is None:
            if self._sentence_transformer_class is None:
                raise ValueError("SentenceTransformer class not initialized")
            self._sentence_transformer_model = self._sentence_transformer_class(self.model)

        # mypy类型断言
        assert self._sentence_transformer_model is not None
        embedding = self._sentence_transformer_model.encode(text, convert_to_numpy=True)
        result = embedding.tolist()
        if isinstance(result, list):
            return [float(x) for x in result]
        return list(result)

    def _generate_sentence_transformer_embeddings(self, texts: list[str]) -> list[list[float]]:
        """使用sentence-transformers批量生成嵌入向量（同步方法）

        Args:
            texts: 要生成嵌入向量的文本列表

        Returns:
            list[list[float]]: 嵌入向量列表
        """
        if self._sentence_transformer_model is None:
            if self._sentence_transformer_class is None:
                raise ValueError("SentenceTransformer class not initialized")
            self._sentence_transformer_model = self._sentence_transformer_class(self.model)

        # mypy类型断言
        assert self._sentence_transformer_model is not None
        embeddings = self._sentence_transformer_model.encode(texts, convert_to_numpy=True)
        result = []
        for emb in embeddings:
            emb_list = emb.tolist()
            if isinstance(emb_list, list):
                result.append([float(x) for x in emb_list])
            else:
                result.append(list(emb_list))
        return result

    @staticmethod
    def calculate_similarity(vec1: list[float], vec2: list[float]) -> float:
        """计算两个向量的余弦相似度

        Args:
            vec1: 第一个向量
            vec2: 第二个向量

        Returns:
            float: 余弦相似度（0-1之间，1表示完全相同）

        Raises:
            ValueError: 如果向量长度不一致
        """
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions must match: {len(vec1)} != {len(vec2)}")

        # 转换为numpy数组
        v1 = np.array(vec1)
        v2 = np.array(vec2)

        # 计算余弦相似度
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        # 确保返回值在[0, 1]范围内
        return float(max(0.0, min(1.0, similarity)))
