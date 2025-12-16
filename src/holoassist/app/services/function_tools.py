"""函数工具注册表

提供工具注册和管理功能，支持Function Calling机制。
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class FunctionTool:
    """函数工具定义"""

    name: str
    description: str
    parameters: dict
    handler: Callable


class ToolRegistry:
    """工具注册中心

    管理所有可用的工具，支持工具注册、查询和执行。
    """

    def __init__(self):
        """初始化工具注册中心"""
        self._tools: dict[str, FunctionTool] = {}

    def register(self, tool: FunctionTool):
        """注册工具

        Args:
            tool: 函数工具实例
        """
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> FunctionTool | None:
        """获取工具

        Args:
            name: 工具名称

        Returns:
            FunctionTool | None: 工具实例，如果不存在则返回None
        """
        return self._tools.get(name)

    def get_tools_definition(self) -> list[dict]:
        """获取工具定义列表（用于API调用）

        Returns:
            List[Dict]: OpenAI格式的工具定义列表
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    async def execute_tool(self, name: str, arguments: str) -> Any:
        """执行工具

        Args:
            name: 工具名称
            arguments: JSON格式的参数字符串

        Returns:
            Any: 工具执行结果

        Raises:
            ValueError: 如果工具不存在
        """
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool {name} not found")

        args = json.loads(arguments)
        return await tool.handler(**args)
