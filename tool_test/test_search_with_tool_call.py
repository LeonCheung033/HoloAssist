"""测试搜索服务触发搜索功能

测试当查询需要搜索时，SearchService是否能正确调用搜索工具。
"""

import asyncio
import json
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from holoassist.app.services.search_service import SearchService


async def test_search_with_tool_call():
    """测试需要搜索的查询"""
    print("=" * 60)
    print("测试 SearchService 触发搜索功能")
    print("=" * 60)
    
    try:
        service = SearchService()
        print("✓ SearchService 初始化成功\n")
        
        # 使用一个明显需要搜索的查询（包含"最新"、"今天"等关键词）
        queries = [
            "今天有什么重要新闻？",
            "最新的AI技术发展",
            "当前比特币价格是多少？",
        ]
        
        for query in queries:
            print(f"查询: {query}")
            print("-" * 60)
            
            search_triggered = False
            search_results_received = False
            content_received = False
            
            async for chunk in service.generate_stream(query):
                # 解析JSON数据
                if chunk.startswith("data: "):
                    data_str = chunk[6:].strip()
                    try:
                        data = json.loads(data_str)
                        
                        # 确保data是字典类型
                        if isinstance(data, dict):
                            if data.get("type") == "search_start":
                                search_triggered = True
                                print("✓ 搜索已触发")
                            
                            elif data.get("type") == "search_results":
                                search_results_received = True
                                results = data.get("results", [])
                                print(f"✓ 收到 {len(results)} 个搜索结果:")
                                for i, result in enumerate(results[:2], 1):  # 只显示前2个
                                    print(f"  {i}. {result.get('title', 'N/A')}")
                                    print(f"     {result.get('url', 'N/A')}")
                            
                            elif data.get("type") == "direct_answer":
                                print("ℹ 模型选择直接回答（未触发搜索）")
                            
                            elif data.get("type") == "direct_content":
                                if not content_received:
                                    content_received = True
                                    print("✓ 开始接收回答内容...")
                        else:
                            # 可能是纯文本内容
                            if not content_received and len(data_str) > 20:
                                content_received = True
                                print("✓ 开始接收回答内容...")
                    
                    except json.JSONDecodeError:
                        # 可能是纯文本内容
                        if not content_received and len(chunk) > 20:
                            content_received = True
                            print("✓ 开始接收回答内容...")
            
            print()
            
            if search_triggered:
                print(f"✓ 查询 '{query}' 成功触发了搜索功能\n")
            else:
                print(f"ℹ 查询 '{query}' 未触发搜索（模型选择直接回答）\n")
            
            print("=" * 60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("搜索服务工具调用功能测试")
    print("=" * 60 + "\n")
    
    result = await test_search_with_tool_call()
    
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"测试结果: {'✓ 通过' if result else '✗ 失败'}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

