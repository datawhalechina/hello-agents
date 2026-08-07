from hello_agents.tools import SearchTool, ToolRegistry
import time

def search(query: str) -> str:
    """调用框架的搜索工具"""
    search_tool = SearchTool(backend="hybrid")
    try:
        response = search_tool.run(
            {
                "input": query,
                "backend": "tavily",
                "mode": "structured",
                "fetch_full_page": True,
                "max_results": 5,
                "max_tokens_per_source": 2000,
                "loop_count": 0,
            })
    except Exception as exc:
        print("搜索工具调用失败:", exc)

    results = response.get("results", [])
    prompt_info = ""
    for i in range(len(results)):
        result = results[i]
        title = result.get("title", "No Title")
        url = result.get("url", "No URL")
        content = result.get("content", "No Content")
        prompt_info += f"来源{i+1}:\n标题: {title}\n链接: {url}\n内容: {content}\n\n"
    return prompt_info

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    rr = search("AMD最新型的GPU有哪些？")
    print(rr)