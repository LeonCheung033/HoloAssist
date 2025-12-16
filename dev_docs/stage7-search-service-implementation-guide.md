# 阶段七：搜索服务模块实现总结与工具添加指南

## 📋 目录

1. [实现概述](#实现概述)
2. [架构设计](#架构设计)
3. [核心组件详解](#核心组件详解)
4. [如何添加新工具](#如何添加新工具)
5. [最佳实践](#最佳实践)
6. [常见问题](#常见问题)

---

## 实现概述

### 本阶段实现的功能

本阶段实现了完整的搜索服务模块，支持通过 **Function Calling** 机制调用外部工具（Tavily搜索），并提供流式响应。主要特性：

- ✅ **Function Calling 支持**：LLM自动判断是否需要调用工具
- ✅ **流式响应**：支持SSE格式的数据流
- ✅ **工具注册机制**：统一的工具管理和调用接口
- ✅ **Tavily搜索集成**：使用Tavily API获取实时网络信息
- ✅ **向后兼容**：支持TAVILY_API_KEY和SERPAPI_KEY

### 技术栈

- **Tavily Python SDK**：用于网络搜索
- **OpenAI兼容API**：DeepSeek API（支持Function Calling）
- **异步编程**：使用`asyncio`处理异步操作
- **流式响应**：Server-Sent Events (SSE) 格式

---

## 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                    SearchService                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │  - AsyncOpenAI Client                           │  │
│  │  - ToolRegistry (工具注册中心)                  │  │
│  │  - generate_stream() (流式响应生成)             │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          │ 注册工具
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  ToolRegistry                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  - register() (注册工具)                         │  │
│  │  - execute_tool() (执行工具)                     │  │
│  │  - get_tools_definition() (获取工具定义)        │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          │ 管理
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  FunctionTool                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  - name (工具名称)                               │  │
│  │  - description (工具描述)                        │  │
│  │  - parameters (参数定义)                         │  │
│  │  - handler (处理函数)                            │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          │ 调用
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    SearchTool                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  - TavilyClient                                 │  │
│  │  - search() (执行搜索)                          │  │
│  │  - _parse_results() (解析结果)                   │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 数据流

```
用户查询
   │
   ▼
SearchService.generate_stream()
   │
   ▼
调用LLM (带工具定义)
   │
   ├─→ finish_reason == "tool_calls" ──→ 执行工具 ──→ 获取结果 ──→ 生成回答
   │
   └─→ finish_reason == "stop" ───────────────→ 直接回答
```

---

## 核心组件详解

### 1. 工具定义 (`tools/definitions.py`)

**作用**：定义工具的元数据，包括名称、描述和参数结构。

**关键代码**：

```python
SEARCH_TOOL = {
    "name": "search",
    "description": "使用Tavily搜索从互联网获取更多的实时信息",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "通过搜索从互联网获取的信息的问题、内容、关键词等"
            }
        },
        "required": ["query"]
    }
}
```

**要点**：
- 使用OpenAI Function Calling格式
- `description`要清晰说明工具用途和使用场景
- `parameters`要详细描述每个参数的作用

### 2. 工具实现 (`tools/search.py`)

**作用**：实现具体的工具功能逻辑。

**关键代码**：

```python
class SearchTool:
    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY or settings.SERPAPI_KEY
        self.client = TavilyClient(api_key=self.api_key)
    
    def search(self, query: str, num_results: int = 3) -> list[dict]:
        """执行搜索并返回结构化结果"""
        response = self.client.search(query=query, max_results=num_results)
        return self._parse_results(response)
    
    def _parse_results(self, response: dict) -> list[dict]:
        """解析响应格式，统一返回格式"""
        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),  # 字段映射
            })
        return results[:settings.SEARCH_RESULT_COUNT]
```

**要点**：
- 工具类应该封装外部API调用
- 统一返回格式，便于后续处理
- 做好错误处理和日志记录
- 同步方法通过`asyncio.to_thread()`转换为异步

### 3. 工具注册表 (`services/function_tools.py`)

**作用**：统一管理所有工具，提供注册、查询和执行功能。

**关键代码**：

```python
@dataclass
class FunctionTool:
    """函数工具定义"""
    name: str
    description: str
    parameters: dict
    handler: Callable

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, FunctionTool] = {}
    
    def register(self, tool: FunctionTool):
        """注册工具"""
        self._tools[tool.name] = tool
    
    def get_tools_definition(self) -> list[dict]:
        """获取OpenAI格式的工具定义列表"""
        return [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
        } for tool in self._tools.values()]
    
    async def execute_tool(self, name: str, arguments: str) -> Any:
        """执行工具"""
        tool = self.get_tool(name)
        args = json.loads(arguments)
        return await tool.handler(**args)
```

**要点**：
- `FunctionTool`是工具的数据结构
- `ToolRegistry`是单例模式，管理所有工具
- `get_tools_definition()`返回OpenAI兼容格式
- `execute_tool()`处理JSON参数解析和异步调用

### 4. 搜索服务 (`services/search_service.py`)

**作用**：集成LLM和工具，提供流式对话服务。

**关键流程**：

```python
class SearchService:
    def __init__(self):
        self.client = AsyncOpenAI(...)
        self.tool_registry = ToolRegistry()
        # 注册搜索工具
        self.tool_registry.register(FunctionTool(
            **SEARCH_TOOL,
            handler=self._handle_search
        ))
    
    async def generate_stream(self, query: str) -> AsyncGenerator[str, None]:
        """流式生成回复"""
        # 1. 构建消息（包含工具描述）
        messages = [
            {"role": "system", "content": SEARCH_SYSTEM_PROMPT.format(...)},
            {"role": "user", "content": query}
        ]
        
        # 2. 调用LLM（带工具定义）
        choice = await self._call_with_tool(messages)
        
        # 3. 根据finish_reason处理
        if choice.finish_reason == "tool_calls":
            # 执行工具调用
            search_results = await self.tool_registry.execute_tool(...)
            # 使用搜索结果生成回答
            yield search_results
            yield stream_response
        elif choice.finish_reason == "stop":
            # 直接回答
            yield stream_response
```

**要点**：
- 系统提示词要说明工具的使用场景
- `tool_choice="auto"`让LLM自己决定是否使用工具
- 根据`finish_reason`判断是否需要调用工具
- 流式响应使用SSE格式

---

## 如何添加新工具

### 快速上手指南

添加新工具需要5个步骤：

### 步骤1：定义工具元数据

在 `src/holoassist/app/tools/definitions.py` 中添加工具定义：

```python
WEATHER_TOOL = {
    "name": "get_weather",
    "description": "获取指定城市的天气信息，包括温度、湿度、天气状况等",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市名称，例如：北京、上海、New York"
            },
            "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "温度单位，celsius表示摄氏度，fahrenheit表示华氏度",
                "default": "celsius"
            }
        },
        "required": ["city"]
    }
}

# 添加到工具定义集合
TOOL_DEFINITIONS = {
    "search": SEARCH_TOOL,
    "weather": WEATHER_TOOL,  # 新增
}
```

**关键点**：
- `description`要详细说明工具用途和使用场景
- `parameters`要清晰描述每个参数的作用和类型
- `required`列出必需参数

### 步骤2：实现工具类

创建 `src/holoassist/app/tools/weather.py`：

```python
"""天气工具

获取城市天气信息。
"""

from typing import Any

from holoassist.app.core.config import settings
from holoassist.app.core.logger import get_logger

logger = get_logger(service="weather_tool")


class WeatherTool:
    """天气工具类
    
    封装天气API调用功能。
    """
    
    def __init__(self):
        """初始化天气工具"""
        self.api_key = settings.WEATHER_API_KEY  # 需要在config.py中添加
        if not self.api_key:
            raise ValueError("未设置WEATHER_API_KEY环境变量")
        
        # 初始化天气API客户端
        # self.client = WeatherAPIClient(api_key=self.api_key)
        logger.info("WeatherTool initialized")
    
    def get_weather(self, city: str, unit: str = "celsius") -> dict[str, Any]:
        """获取天气信息
        
        Args:
            city: 城市名称
            unit: 温度单位
            
        Returns:
            dict: 天气信息，包含temperature、humidity、condition等字段
        """
        try:
            logger.info(f"Getting weather for {city}, unit: {unit}")
            
            # 调用天气API
            # response = self.client.get_weather(city, unit)
            
            # 示例返回格式
            return {
                "city": city,
                "temperature": 25,
                "unit": unit,
                "humidity": 60,
                "condition": "晴天",
                "wind_speed": 10,
            }
            
        except Exception as e:
            logger.error(f"获取天气失败: {str(e)}", exc_info=True)
            raise
```

**关键点**：
- 工具类应该封装外部API调用
- 统一返回格式（字典）
- 做好错误处理和日志记录
- 同步方法在服务层通过`asyncio.to_thread()`转换为异步

### 步骤3：在服务中注册工具

在 `src/holoassist/app/services/search_service.py` 或新建服务文件中注册：

```python
from holoassist.app.tools.definitions import WEATHER_TOOL
from holoassist.app.tools.weather import WeatherTool

class SearchService:
    def __init__(self):
        # ... 现有代码 ...
        
        # 初始化天气工具
        self.weather_tool = WeatherTool()
        
        # 注册天气工具
        self.tool_registry.register(FunctionTool(
            **WEATHER_TOOL,
            handler=self._handle_weather  # 处理函数
        ))
    
    async def _handle_weather(self, city: str, unit: str = "celsius") -> dict:
        """处理天气查询请求"""
        # 同步方法转换为异步
        return await asyncio.to_thread(
            self.weather_tool.get_weather, city, unit
        )
```

**关键点**：
- 在`__init__`中初始化工具实例
- 使用`FunctionTool`注册工具
- `handler`函数处理工具调用，同步方法需要转换为异步

### 步骤4：更新提示词

在 `src/holoassist/app/prompts/search_prompts.py` 中更新系统提示词：

```python
SEARCH_SYSTEM_PROMPT = """你是一个智能助手，可以通过调用外部的工具获取实时信息。
你可以使用的工具及使用方法如下：

{tools_description}  

当你遇到以下情况时，请调用相应的工具：
1. **搜索工具**：问题涉及实时数据（如新闻、股票）、最新事件、外部知识
2. **天气工具**：问题涉及天气查询（如"北京天气"、"今天温度"）
3. 其他情况下，请直接回答用户的问题。"""
```

**关键点**：
- 在系统提示词中说明工具的使用场景
- `{tools_description}`会自动填充工具描述

### 步骤5：添加配置（如需要）

在 `src/holoassist/app/core/config.py` 中添加配置项：

```python
class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # Weather settings
    WEATHER_API_KEY: str = ""  # 天气API密钥
```

### 步骤6：编写测试

在 `tests/unit/test_search_service.py` 中添加测试：

```python
class TestWeatherTool:
    """WeatherTool测试"""
    
    @pytest.mark.asyncio
    async def test_get_weather(self):
        """测试获取天气信息"""
        with patch("holoassist.app.tools.weather.settings") as mock_settings:
            mock_settings.WEATHER_API_KEY = "test-key"
            
            tool = WeatherTool()
            result = tool.get_weather("北京", "celsius")
            
            assert result["city"] == "北京"
            assert "temperature" in result
```

---

## 最佳实践

### 1. 工具设计原则

- **单一职责**：每个工具只做一件事
- **统一接口**：所有工具返回统一格式（字典）
- **错误处理**：妥善处理API调用失败的情况
- **日志记录**：记录关键操作和错误信息

### 2. 工具描述编写技巧

好的工具描述应该：
- ✅ 清晰说明工具用途："获取指定城市的天气信息"
- ✅ 说明使用场景："当用户询问天气时使用"
- ✅ 参数描述详细："city - 城市名称，例如：北京、上海"

不好的描述：
- ❌ "天气工具"（太简单）
- ❌ "获取天气"（没有说明参数）
- ❌ "weather"（只有名称）

### 3. 参数设计

- **必需参数**：放在`required`列表中
- **可选参数**：提供默认值
- **枚举值**：使用`enum`限制可选值
- **类型明确**：使用正确的JSON Schema类型

### 4. 异步处理

```python
# 同步工具方法
def sync_tool_method(self, param: str) -> dict:
    # 同步操作
    return result

# 在服务中转换为异步
async def _handle_tool(self, param: str) -> dict:
    return await asyncio.to_thread(self.tool.sync_tool_method, param)
```

### 5. 错误处理

```python
try:
    result = await self.tool_registry.execute_tool(name, arguments)
except ValueError as e:
    # 工具不存在
    logger.error(f"Tool not found: {e}")
except Exception as e:
    # 工具执行失败
    logger.error(f"Tool execution failed: {e}", exc_info=True)
    # 返回错误信息给用户
    yield f"data: {json.dumps({'type': 'error', 'message': '工具执行失败'})}\n\n"
```

---

## 常见问题

### Q1: 如何让LLM更准确地调用工具？

**A**: 
1. 在工具描述中明确说明使用场景
2. 在系统提示词中给出示例
3. 参数描述要详细，说明每个参数的作用

### Q2: 工具返回的数据格式不统一怎么办？

**A**: 
1. 在工具类中统一格式化返回数据
2. 使用`_parse_results()`方法转换格式
3. 保持返回格式的一致性（字典结构）

### Q3: 如何调试工具调用？

**A**: 
1. 查看日志：`logger.info()`记录关键步骤
2. 检查`finish_reason`：确认LLM是否决定调用工具
3. 验证参数：检查`tool_call.function.arguments`是否正确

### Q4: 同步API如何转换为异步？

**A**: 
使用`asyncio.to_thread()`：
```python
async def _handle_tool(self, param: str):
    return await asyncio.to_thread(self.tool.sync_method, param)
```

### Q5: 如何支持多个工具？

**A**: 
1. 在`ToolRegistry`中注册多个工具
2. LLM会自动选择最合适的工具
3. 工具描述要区分不同工具的使用场景

---

## 总结

### 核心概念

1. **工具定义**：描述工具是什么（元数据）
2. **工具实现**：工具做什么（具体逻辑）
3. **工具注册**：将工具加入系统（注册表）
4. **工具调用**：LLM决定何时使用工具（Function Calling）

### 添加新工具的检查清单

- [ ] 在`definitions.py`中定义工具元数据
- [ ] 创建工具实现类（`tools/xxx.py`）
- [ ] 在服务中注册工具
- [ ] 更新系统提示词（如需要）
- [ ] 添加配置项（如需要）
- [ ] 编写单元测试
- [ ] 测试工具调用流程

### 下一步

- 可以添加更多工具：天气、计算器、翻译等
- 优化工具描述，提高LLM调用准确性
- 添加工具调用链（一个工具调用另一个工具）

---

**文档版本**: v1.0  
**最后更新**: 2024-12-16  
**作者**: HoloAssist Team

