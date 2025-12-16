"""搜索服务单元测试

测试SearchTool、ToolRegistry和SearchService的功能。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from holoassist.app.services.function_tools import FunctionTool, ToolRegistry
from holoassist.app.services.search_service import SearchService
from holoassist.app.tools.search import SearchTool


class TestSearchTool:
    """SearchTool测试"""

    @pytest.mark.asyncio
    async def test_search_tool_search(self):
        """测试搜索工具执行（mock TavilyClient）"""
        # Mock Tavily响应格式
        mock_response = {
            "query": "test query",
            "answer": "test answer",
            "results": [
                {
                    "title": "Test Title 1",
                    "url": "https://example.com/1",
                    "content": "Test content 1",
                    "score": 0.9,
                },
                {
                    "title": "Test Title 2",
                    "url": "https://example.com/2",
                    "content": "Test content 2",
                    "score": 0.8,
                },
            ],
        }

        with patch("holoassist.app.tools.search.TavilyClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.search = MagicMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch("holoassist.app.tools.search.settings") as mock_settings:
                mock_settings.TAVILY_API_KEY = "test-key"
                mock_settings.SERPAPI_KEY = ""
                mock_settings.SEARCH_RESULT_COUNT = 3

                tool = SearchTool()
                results = tool.search("test query")

                assert len(results) == 2
                assert results[0]["title"] == "Test Title 1"
                assert results[0]["url"] == "https://example.com/1"
                assert results[0]["snippet"] == "Test content 1"  # content -> snippet
                mock_client.search.assert_called_once_with(query="test query", max_results=3)

    @pytest.mark.asyncio
    async def test_search_tool_parse_results(self):
        """测试Tavily响应解析"""
        # Mock Tavily响应格式
        mock_response = {
            "query": "test query",
            "answer": "test answer",
            "results": [
                {
                    "title": "Test Title",
                    "url": "https://example.com",
                    "content": "Test content",
                    "score": 0.9,
                }
            ],
        }

        with patch("holoassist.app.tools.search.TavilyClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.search = MagicMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch("holoassist.app.tools.search.settings") as mock_settings:
                mock_settings.TAVILY_API_KEY = "test-key"
                mock_settings.SERPAPI_KEY = ""
                mock_settings.SEARCH_RESULT_COUNT = 3

                tool = SearchTool()
                results = tool._parse_results(mock_response)

                assert len(results) == 1
                assert results[0]["title"] == "Test Title"
                assert results[0]["url"] == "https://example.com"
                assert results[0]["snippet"] == "Test content"  # 验证content映射为snippet

    def test_search_tool_init_without_key(self):
        """测试未设置API密钥时的错误"""
        with patch("holoassist.app.tools.search.settings") as mock_settings:
            mock_settings.TAVILY_API_KEY = ""
            mock_settings.SERPAPI_KEY = ""

            with pytest.raises(ValueError, match="未设置TAVILY_API_KEY"):
                SearchTool()

    def test_search_tool_init_with_serpapi_fallback(self):
        """测试使用SERPAPI_KEY作为后备"""
        with patch("holoassist.app.tools.search.TavilyClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            with patch("holoassist.app.tools.search.settings") as mock_settings:
                mock_settings.TAVILY_API_KEY = ""
                mock_settings.SERPAPI_KEY = "serpapi-key"
                mock_settings.SEARCH_RESULT_COUNT = 3

                tool = SearchTool()
                assert tool.api_key == "serpapi-key"


class TestToolRegistry:
    """ToolRegistry测试"""

    def test_tool_registry_register(self):
        """测试工具注册"""
        registry = ToolRegistry()

        async def test_handler(query: str):
            return [{"title": "Test", "url": "https://example.com", "snippet": "Test"}]

        tool = FunctionTool(
            name="test_tool",
            description="Test tool",
            parameters={"type": "object", "properties": {}},
            handler=test_handler,
        )

        registry.register(tool)
        assert registry.get_tool("test_tool") == tool

    def test_tool_registry_get_tools_definition(self):
        """测试获取工具定义"""
        registry = ToolRegistry()

        async def test_handler(query: str):
            return []

        tool = FunctionTool(
            name="test_tool",
            description="Test tool",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            handler=test_handler,
        )

        registry.register(tool)
        definitions = registry.get_tools_definition()

        assert len(definitions) == 1
        assert definitions[0]["type"] == "function"
        assert definitions[0]["function"]["name"] == "test_tool"
        assert definitions[0]["function"]["description"] == "Test tool"

    @pytest.mark.asyncio
    async def test_tool_registry_execute(self):
        """测试工具执行"""
        registry = ToolRegistry()

        async def test_handler(query: str):
            return [{"title": "Test", "url": "https://example.com", "snippet": "Test"}]

        tool = FunctionTool(
            name="test_tool",
            description="Test tool",
            parameters={"type": "object", "properties": {}},
            handler=test_handler,
        )

        registry.register(tool)

        result = await registry.execute_tool("test_tool", '{"query": "test"}')
        assert len(result) == 1
        assert result[0]["title"] == "Test"

    @pytest.mark.asyncio
    async def test_tool_registry_execute_not_found(self):
        """测试执行不存在的工具"""
        registry = ToolRegistry()

        with pytest.raises(ValueError, match="Tool nonexistent not found"):
            await registry.execute_tool("nonexistent", '{"query": "test"}')


class TestSearchService:
    """SearchService测试"""

    @pytest.mark.asyncio
    async def test_search_service_generate_stream_with_search(self):
        """测试需要搜索的流式响应"""
        # Mock SearchTool
        mock_search_results = [
            {
                "title": "Test Title",
                "url": "https://example.com",
                "snippet": "Test content",
            }
        ]

        with patch("holoassist.app.services.search_service.SearchTool") as mock_search_tool_class:
            mock_search_tool = MagicMock()
            mock_search_tool.search = MagicMock(return_value=mock_search_results)
            mock_search_tool_class.return_value = mock_search_tool

            # Mock AsyncOpenAI
            with patch("holoassist.app.services.search_service.AsyncOpenAI") as mock_openai_class:
                mock_client = AsyncMock()

                # Mock第一次调用（工具调用）
                mock_tool_call = MagicMock()
                mock_tool_call.function.name = "search"
                mock_tool_call.function.arguments = '{"query": "test query"}'

                mock_choice_tool = MagicMock()
                mock_choice_tool.finish_reason = "tool_calls"
                mock_choice_tool.message.tool_calls = [mock_tool_call]

                # Mock第二次调用（流式响应）
                mock_chunk = MagicMock()
                mock_chunk.choices = [MagicMock()]
                mock_chunk.choices[0].delta.content = "Test response"

                mock_stream = AsyncMock()
                mock_stream.__aiter__ = MagicMock(return_value=iter([mock_chunk]))

                mock_client.chat.completions.create = AsyncMock(
                    side_effect=[
                        MagicMock(choices=[mock_choice_tool]),
                        mock_stream,
                    ]
                )
                mock_openai_class.return_value = mock_client

                with patch("holoassist.app.services.search_service.settings") as mock_settings:
                    mock_settings.DEEPSEEK_API_KEY = "test-key"
                    mock_settings.DEEPSEEK_BASE_URL = "https://api.deepseek.com"
                    mock_settings.DEEPSEEK_MODEL = "deepseek-chat"

                    service = SearchService()
                    results = []
                    async for chunk in service.generate_stream("test query"):
                        results.append(chunk)

                    # 验证返回了搜索相关的数据
                    assert len(results) > 0
                    assert any("search_start" in chunk for chunk in results)
                    assert any("search_results" in chunk for chunk in results)

    @pytest.mark.asyncio
    async def test_search_service_generate_stream_direct_answer(self):
        """测试直接回答的流式响应"""
        with patch("holoassist.app.services.search_service.SearchTool") as mock_search_tool_class:
            mock_search_tool = MagicMock()
            mock_search_tool_class.return_value = mock_search_tool

            # Mock AsyncOpenAI
            with patch("holoassist.app.services.search_service.AsyncOpenAI") as mock_openai_class:
                mock_client = AsyncMock()

                # Mock第一次调用（直接回答）
                mock_choice_stop = MagicMock()
                mock_choice_stop.finish_reason = "stop"

                # Mock第二次调用（流式响应）
                mock_chunk = MagicMock()
                mock_chunk.choices = [MagicMock()]
                mock_chunk.choices[0].delta.content = "Direct answer"

                async def mock_stream_generator():
                    yield mock_chunk

                mock_stream = mock_stream_generator()

                mock_client.chat.completions.create = AsyncMock(
                    side_effect=[
                        MagicMock(choices=[mock_choice_stop]),
                        mock_stream,
                    ]
                )
                mock_openai_class.return_value = mock_client

                with patch("holoassist.app.services.search_service.settings") as mock_settings:
                    mock_settings.DEEPSEEK_API_KEY = "test-key"
                    mock_settings.DEEPSEEK_BASE_URL = "https://api.deepseek.com"
                    mock_settings.DEEPSEEK_MODEL = "deepseek-chat"

                    service = SearchService()
                    results = []
                    async for chunk in service.generate_stream("test query"):
                        results.append(chunk)

                    # 验证返回了直接回答相关的数据
                    assert len(results) > 0
                    assert any("direct_answer" in chunk for chunk in results)
                    assert any("direct_content" in chunk for chunk in results)
