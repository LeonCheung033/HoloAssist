"""实际测试搜索服务功能

测试Tavily搜索是否能正常工作并返回真实结果。
"""

import asyncio
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from holoassist.app.tools.search import SearchTool
from holoassist.app.services.search_service import SearchService


async def test_search_tool():
    """测试SearchTool的实际搜索功能"""
    print("=" * 60)
    print("测试 SearchTool 实际搜索功能")
    print("=" * 60)
    
    try:
        tool = SearchTool()
        print(f"✓ SearchTool 初始化成功")
        print(f"  使用的API Key: {tool.api_key[:10]}...{tool.api_key[-4:] if len(tool.api_key) > 14 else ''}")
        
        # 执行搜索
        query = "Python异步编程"
        print(f"\n执行搜索查询: {query}")
        results = tool.search(query, num_results=3)
        
        print(f"\n✓ 搜索完成，返回 {len(results)} 个结果\n")
        
        for i, result in enumerate(results, 1):
            print(f"结果 {i}:")
            print(f"  标题: {result['title']}")
            print(f"  URL: {result['url']}")
            print(f"  摘要: {result['snippet'][:100]}...")
            print()
        
        return True
        
    except Exception as e:
        print(f"✗ 搜索失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_search_service_stream():
    """测试SearchService的流式响应（需要配置DeepSeek API）"""
    print("=" * 60)
    print("测试 SearchService 流式响应功能")
    print("=" * 60)
    
    try:
        # 检查必要的配置
        from holoassist.app.core.config import settings
        
        if not settings.DEEPSEEK_API_KEY:
            print("⚠ 未配置 DEEPSEEK_API_KEY，跳过流式响应测试")
            return False
        
        service = SearchService()
        print("✓ SearchService 初始化成功")
        
        # 测试查询
        query = "什么是Python异步编程？"
        print(f"\n执行查询: {query}")
        print("\n流式响应:")
        print("-" * 60)
        
        chunk_count = 0
        async for chunk in service.generate_stream(query):
            chunk_count += 1
            # 只显示前几个chunk，避免输出太长
            if chunk_count <= 5:
                print(chunk[:200] if len(chunk) > 200 else chunk)
            elif chunk_count == 6:
                print("... (更多内容)")
        
        print("-" * 60)
        print(f"✓ 流式响应完成，共收到 {chunk_count} 个数据块")
        
        return True
        
    except Exception as e:
        print(f"✗ 流式响应测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("搜索服务实际功能测试")
    print("=" * 60 + "\n")
    
    # 测试1: SearchTool实际搜索
    result1 = await test_search_tool()
    
    print("\n")
    
    # 测试2: SearchService流式响应（可选）
    result2 = await test_search_service_stream()
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"SearchTool 测试: {'✓ 通过' if result1 else '✗ 失败'}")
    print(f"SearchService 测试: {'✓ 通过' if result2 else '⚠ 跳过或失败'}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

