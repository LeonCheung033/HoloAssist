"""搜索工具

使用Tavily API进行网络搜索。
"""

from tavily import TavilyClient

from holoassist.app.core.config import settings
from holoassist.app.core.logger import get_logger

logger = get_logger(service="search_tool")


class SearchTool:
    """搜索工具类

    封装Tavily搜索功能，提供统一的搜索接口。
    """

    def __init__(self):
        """初始化搜索工具

        Raises:
            ValueError: 如果未设置TAVILY_API_KEY或SERPAPI_KEY
        """
        # 优先使用TAVILY_API_KEY（也支持TAVILY_KEY别名），如果未设置则使用SERPAPI_KEY（向后兼容）
        self.api_key = settings.TAVILY_API_KEY or settings.SERPAPI_KEY
        if not self.api_key:
            raise ValueError("未设置TAVILY_API_KEY（或TAVILY_KEY）或SERPAPI_KEY环境变量")

        self.client = TavilyClient(api_key=self.api_key)
        logger.info("SearchTool initialized with TavilyClient")

    def search(self, query: str, num_results: int = 3) -> list[dict]:
        """执行搜索并返回结构化结果

        Args:
            query: 搜索查询字符串
            num_results: 返回结果数量（默认使用配置中的值）

        Returns:
            List[Dict]: 搜索结果列表，每个结果包含title、url、snippet字段
        """
        try:
            # 使用配置中的结果数量，如果没有则使用传入的参数
            num_results = settings.SEARCH_RESULT_COUNT or num_results

            logger.info(f"Searching for: {query}, max_results: {num_results}")

            # 调用Tavily API
            response = self.client.search(query=query, max_results=num_results)

            return self._parse_results(response)

        except Exception as e:
            logger.error(f"搜索失败: {str(e)}", exc_info=True)
            return []

    def _parse_results(self, response: dict) -> list[dict]:
        """解析Tavily响应格式

        Args:
            response: Tavily API响应字典

        Returns:
            List[Dict]: 格式化的搜索结果列表
        """
        results = []

        # Tavily响应格式：
        # {
        #     "query": "...",
        #     "answer": "...",  # 可选，直接答案
        #     "results": [
        #         {
        #             "title": "...",
        #             "url": "...",
        #             "content": "...",
        #             "score": 0.9,
        #             ...
        #         }
        #     ]
        # }

        if "results" in response and isinstance(response["results"], list):
            for item in response["results"]:
                # 将content字段映射为snippet，保持与原有格式兼容
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("content", ""),  # content -> snippet
                    }
                )

        # 限制返回结果数量
        max_results = settings.SEARCH_RESULT_COUNT or len(results)
        return results[:max_results]
