"""Redis语义缓存服务

提供基于语义相似度的缓存功能，使用嵌入向量计算相似度。
"""

import hashlib
import json

import numpy as np
import redis.asyncio as redis
from redis.asyncio import Redis

from holoassist.app.core.config import settings
from holoassist.app.core.logger import get_logger

logger = get_logger(service="redis_semantic_cache")


class RedisSemanticCache:
    """Redis语义缓存类

    使用嵌入向量计算语义相似度，实现智能缓存查询。
    """

    def __init__(
        self,
        redis_url: str | None = None,
        cache_expire: int | None = None,
        cache_threshold: float | None = None,
    ):
        """初始化Redis语义缓存

        Args:
            redis_url: Redis连接URL，如果为None则使用settings.REDIS_URL
            cache_expire: 缓存过期时间（秒），如果为None则使用settings.REDIS_CACHE_EXPIRE
            cache_threshold: 语义相似度阈值，如果为None则使用settings.REDIS_CACHE_THRESHOLD
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.cache_expire = cache_expire or settings.REDIS_CACHE_EXPIRE
        self.cache_threshold = cache_threshold or settings.REDIS_CACHE_THRESHOLD
        self._redis_client: Redis | None = None

    async def _get_redis_client(self) -> Redis:
        """获取Redis客户端（懒加载）

        Returns:
            Redis: Redis异步客户端实例
        """
        if self._redis_client is None:
            self._redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis_client

    async def close(self):
        """关闭Redis连接"""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None

    def _calculate_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算两个向量的余弦相似度

        Args:
            vec1: 第一个向量
            vec2: 第二个向量

        Returns:
            float: 余弦相似度（0-1之间）
        """
        try:
            v1 = np.array(vec1, dtype=np.float32)
            v2 = np.array(vec2, dtype=np.float32)

            # 计算余弦相似度
            dot_product = np.dot(v1, v2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            # 确保返回值在0-1之间
            return float(max(0.0, min(1.0, similarity)))
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0

    def _get_cache_key(self, embedding: list[float]) -> str:
        """根据嵌入向量生成缓存key

        Args:
            embedding: 嵌入向量

        Returns:
            str: 缓存key（格式：semantic_cache:{hash}）
        """
        # 将向量转换为字符串并计算hash
        vec_str = json.dumps(embedding, sort_keys=True)
        vec_hash = hashlib.md5(vec_str.encode()).hexdigest()
        return f"semantic_cache:{vec_hash}"

    async def get_cache(self, query: str, embedding: list[float]) -> str | None:
        """查询语义缓存

        如果找到相似度超过阈值的缓存结果，则返回该结果。

        Args:
            query: 查询文本（用于日志）
            embedding: 查询的嵌入向量

        Returns:
            Optional[str]: 如果找到相似度超过阈值的缓存，返回缓存结果；否则返回None
        """
        try:
            client = await self._get_redis_client()

            # 首先尝试精确匹配（使用相同的key）
            exact_key = self._get_cache_key(embedding)
            exact_match = await client.get(exact_key)
            if exact_match:
                logger.info(f"Cache hit (exact match) for query: {query[:50]}...")
                return str(exact_match)

            # 如果没有精确匹配，遍历所有缓存查找最相似的
            pattern = "semantic_cache:*"
            keys = await client.keys(pattern)

            if not keys:
                logger.debug(f"No cache found for query: {query[:50]}...")
                return None

            best_match: str | None = None
            best_similarity = 0.0

            # 遍历所有缓存，计算相似度（排除embedding key）
            for key in keys:
                # 跳过embedding key
                if key.endswith(":embedding"):
                    continue

                try:
                    # 获取缓存的响应
                    cached_response = await client.get(key)
                    if not cached_response:
                        continue

                    # 获取缓存的嵌入向量
                    cached_embedding = await self._get_cached_embedding(key)
                    if cached_embedding is None:
                        continue

                    # 计算相似度
                    similarity = self._calculate_similarity(embedding, cached_embedding)

                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = cached_response

                except Exception as e:
                    logger.warning(f"Error processing cache key {key}: {str(e)}")
                    continue

            # 如果最佳相似度超过阈值，返回缓存结果
            if best_match and best_similarity >= self.cache_threshold:
                logger.info(f"Cache hit (similarity: {best_similarity:.3f}) for query: {query[:50]}...")
                return best_match

            logger.debug(
                f"Cache miss (best similarity: {best_similarity:.3f} < {self.cache_threshold}) "
                f"for query: {query[:50]}..."
            )
            return None

        except Exception as e:
            logger.error(f"Error getting cache for query: {query[:50]}... Error: {str(e)}")
            return None

    async def set_cache(self, query: str, response: str, embedding: list[float] | None = None):
        """设置语义缓存

        Args:
            query: 查询文本（用于日志）
            response: 响应内容
            embedding: 查询的嵌入向量，如果为None则不会存储（需要后续提供）
        """
        if embedding is None:
            logger.warning(f"Cannot cache without embedding for query: {query[:50]}...")
            return

        try:
            client = await self._get_redis_client()
            cache_key = self._get_cache_key(embedding)

            # 存储响应
            await client.setex(cache_key, self.cache_expire, response)

            # 存储嵌入向量（用于后续相似度计算）
            # 使用另一个key存储embedding
            embedding_key = f"{cache_key}:embedding"
            await client.setex(embedding_key, self.cache_expire, json.dumps(embedding))

            logger.info(f"Cached response for query: {query[:50]}... (key: {cache_key})")

        except Exception as e:
            logger.error(f"Error setting cache for query: {query[:50]}... Error: {str(e)}")

    async def _get_cached_embedding(self, cache_key: str) -> list[float] | None:
        """获取缓存的嵌入向量

        Args:
            cache_key: 缓存key

        Returns:
            Optional[List[float]]: 嵌入向量，如果不存在则返回None
        """
        try:
            client = await self._get_redis_client()
            embedding_key = f"{cache_key}:embedding"
            embedding_str = await client.get(embedding_key)
            if embedding_str:
                result = json.loads(embedding_str)
                if isinstance(result, list):
                    return [float(x) for x in result]
                return None
            return None
        except Exception as e:
            logger.warning(f"Error getting cached embedding for key {cache_key}: {str(e)}")
            return None
