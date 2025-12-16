"""搜索服务

提供带搜索功能的流式对话服务，支持Function Calling机制。
"""

import asyncio
import json
from collections.abc import AsyncGenerator, Callable
from datetime import datetime

from openai import AsyncOpenAI

from holoassist.app.core.config import settings
from holoassist.app.core.logger import get_logger
from holoassist.app.prompts.search_prompts import (
    SEARCH_SUMMARY_PROMPT,
    SEARCH_SYSTEM_PROMPT,
)
from holoassist.app.services.function_tools import FunctionTool, ToolRegistry
from holoassist.app.tools.definitions import SEARCH_TOOL
from holoassist.app.tools.search import SearchTool

logger = get_logger(service="search")


class SearchService:
    """搜索服务类

    集成LLM和搜索工具，提供带搜索功能的流式对话服务。
    """

    def __init__(self):
        """初始化搜索服务"""
        logger.info("Initializing SearchService...")
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
        self.model = settings.DEEPSEEK_MODEL
        self.search_tool = SearchTool()

        # 初始化工具注册中心
        self.tool_registry = ToolRegistry()

        # 注册搜索工具 - 直接使用定义好的描述
        self.tool_registry.register(
            FunctionTool(
                **SEARCH_TOOL,  # 展开工具定义
                handler=self._handle_search,
            )
        )

        # 生成工具描述提示
        self.tools_description = self._generate_tools_description()

    def _generate_tools_description(self) -> str:
        """根据工具定义生成工具描述提示

        Returns:
            str: 格式化的工具描述字符串
        """
        tool_descriptions = []

        for tool_def in self.tool_registry.get_tools_definition():
            func = tool_def["function"]
            name = func["name"]
            desc = func["description"]
            params = []

            # 获取必需参数及其描述
            for param_name, param_info in func["parameters"]["properties"].items():
                if param_name in func["parameters"].get("required", []):
                    params.append(f"{param_name}，作用是：{param_info['description']}")

            tool_desc = f"{name}，{desc}{'，必须解析出来的参数是：' if params else ''}{', '.join(params)}"
            tool_descriptions.append(tool_desc)

        return "你现在可用的工具有：\n\n" + "\n".join(tool_descriptions)

    async def _handle_search(self, query: str) -> list[dict]:
        """处理搜索请求

        Args:
            query: 搜索查询字符串

        Returns:
            list[dict]: 搜索结果列表
        """
        return await asyncio.to_thread(self.search_tool.search, query)

    async def _call_with_tool(self, messages: list[dict]):
        """调用模型并获取工具调用结果

        Args:
            messages: 消息列表

        Returns:
            OpenAI Choice对象

        Raises:
            Exception: 如果调用失败
        """
        try:
            logger.info(f"Calling model with messages: {len(messages)} messages")

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tool_registry.get_tools_definition(),
                tool_choice="auto",  # 让模型自己决定是否使用工具
            )

            logger.info(f"Model response finish_reason: {response.choices[0].finish_reason}")
            return response.choices[0]  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"Error in _call_with_tool: {str(e)}", exc_info=True)
            raise

    async def generate_stream(
        self,
        query: str,
        user_id: int | None = None,
        conversation_id: int | None = None,
        on_complete: Callable | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式生成带搜索功能的回复

        Args:
            query: 用户查询
            user_id: 用户ID（可选）
            conversation_id: 会话ID（可选）
            on_complete: 完成回调函数（可选）

        Yields:
            str: SSE格式的数据流

        Raises:
            Exception: 如果生成失败
        """
        try:
            logger.info(f"Starting search generation for query: {query}")

            # 使用格式化的系统提示
            messages = [
                {
                    "role": "system",
                    "content": SEARCH_SYSTEM_PROMPT.format(tools_description=self.tools_description),
                },
                {"role": "user", "content": query},
            ]

            # 第一步：获取工具调用
            choice = await self._call_with_tool(messages)
            logger.info(f"Tool call response finish_reason: {choice.finish_reason}")

            # 根据finish_reason决定处理方式
            if choice.finish_reason == "tool_calls":
                # 需要搜索的情况
                tool_calls = choice.message.tool_calls
                if tool_calls:
                    tool_call = tool_calls[0]
                    logger.info(f"Processing tool call: {tool_call.function.name}")

                    try:
                        # 执行工具调用
                        search_results = await self.tool_registry.execute_tool(
                            tool_call.function.name, tool_call.function.arguments
                        )
                        logger.info(f"Got {len(search_results)} search results")

                        if search_results:
                            # 构建上下文内容
                            context = []
                            for result in search_results:
                                context.append(
                                    f"来源：{result['title']}\n链接：{result['url']}\n内容：{result['snippet']}\n"
                                )

                            # 构造带上下文的提示
                            context_prompt = SEARCH_SUMMARY_PROMPT.format(
                                context="\n---\n".join(context),
                                query=query,
                                cur_date=datetime.now().strftime("%Y年%m月%d日"),
                            )

                            # 先返回一个类型标识，告诉前端这是搜索结果
                            yield f"data: {json.dumps({'type': 'search_start'}, ensure_ascii=False)}\n\n"

                            # 返回搜索结果
                            search_data = {
                                "type": "search_results",  # 保持原有的类型标识
                                "total": len(search_results),
                                "query": json.loads(tool_call.function.arguments)["query"],
                                "results": [
                                    {
                                        "title": result["title"],
                                        "url": result["url"],
                                        "snippet": result["snippet"],
                                    }
                                    for result in search_results
                                ],
                            }
                            yield f"data: {json.dumps(search_data, ensure_ascii=False)}\n\n"

                            # 使用新的消息上下文生成回复
                            stream_response = await self.client.chat.completions.create(
                                model=self.model,
                                messages=[{"role": "system", "content": context_prompt}],
                                stream=True,
                            )

                            async for chunk in stream_response:
                                if chunk.choices[0].delta.content:
                                    content = json.dumps(chunk.choices[0].delta.content, ensure_ascii=False)
                                    yield f"data: {content}\n\n"

                    except Exception as e:
                        logger.error(f"Error processing tool call: {str(e)}", exc_info=True)
                        # 搜索失败时返回错误信息
                        yield f"data: {json.dumps({'type': 'error', 'message': '搜索失败'}, ensure_ascii=False)}\n\n"

            elif choice.finish_reason == "stop":
                # 直接回答的情况，使用流式响应
                logger.info("Model chose to answer directly, streaming response...")

                # 先返回一个类型标识，告诉前端这是直接回答
                yield f"data: {json.dumps({'type': 'direct_answer'}, ensure_ascii=False)}\n\n"

                # 使用流式API重新生成回答
                stream_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True,
                )

                full_response = []
                async for chunk in stream_response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response.append(content)
                        # 包装直接回答的内容
                        yield f"data: {
                            json.dumps({'type': 'direct_content', 'content': content}, ensure_ascii=False)
                        }\n\n"

                # 如果需要保存对话
                if on_complete and user_id is not None and conversation_id is not None:
                    complete_response = "".join(full_response)
                    await on_complete(
                        user_id,
                        conversation_id,
                        [{"role": "user", "content": query}],
                        complete_response,
                    )

        except Exception as e:
            logger.error(f"Error in generate_stream: {str(e)}", exc_info=True)
            raise
