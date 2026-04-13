"""网页搜索工具 - 使用 Brave Search API 进行网络搜索"""

import os
import json
from typing import List, Dict, Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from hello_agents.tools import Tool, ToolParameter, ToolResponse, tool_action


class WebSearchTool(Tool):
    """网页搜索工具

    使用 Brave Search API 进行网络搜索。
    需要配置环境变量 BRAVE_API_KEY 或在初始化时传入 API key。
    """

    def __init__(
        self,
        api_key: str = None,
        max_results: int = 5,
        timeout: int = 10,
    ):
        """初始化网页搜索工具

        Args:
            api_key: Brave Search API key，如未提供则从环境变量 BRAVE_API_KEY 读取
            max_results: 最大返回结果数，默认 5
            timeout: 请求超时时间（秒），默认 10
        """
        super().__init__(
            name="web_search",
            description="使用搜索引擎搜索网络信息",
            expandable=True
        )

        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        self.max_results = max_results
        self.timeout = timeout
        self._base_url = "https://api.search.brave.com/res/v1/web/search"

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行搜索（默认行为）"""
        query = parameters.get("query", "")
        count = parameters.get("count", self.max_results)
        return self._search(query, count)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="搜索查询词",
                required=True
            ),
            ToolParameter(
                name="count",
                type="integer",
                description=f"返回结果数量，默认 {self.max_results}",
                required=False
            ),
        ]

    def _search(self, query: str, count: int = None) -> ToolResponse:
        """执行搜索的核心实现

        Args:
            query: 搜索查询
            count: 返回结果数量

        Returns:
            ToolResponse: 搜索结果
        """
        if not query:
            return ToolResponse.error(
                code="INVALID_INPUT",
                message="搜索查询不能为空"
            )

        if not self.api_key:
            return ToolResponse.error(
                code="MISSING_API_KEY",
                message="未配置 Brave API Key。请设置环境变量 BRAVE_API_KEY 或在初始化时传入 api_key 参数"
            )

        try:
            # 构建请求
            params = {
                "q": query,
                "count": count or self.max_results,
            }

            url = f"{self._base_url}?q={query}&count={params['count']}"
            request = Request(url)
            request.add_header("Accept", "application/json")
            request.add_header("Accept-Encoding", "gzip")
            request.add_header("X-Subscription-Token", self.api_key)

            # 发送请求
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))

            # 解析结果
            results = self._parse_search_results(data)

            if not results:
                return ToolResponse.success(
                    text=f"未找到与 '{query}' 相关的结果",
                    data={"query": query, "results": []}
                )

            # 格式化输出
            formatted = self._format_results(results)

            return ToolResponse.success(
                text=formatted,
                data={
                    "query": query,
                    "results": results,
                    "count": len(results),
                }
            )

        except HTTPError as e:
            if e.code == 401:
                return ToolResponse.error(
                    code="AUTH_ERROR",
                    message="API Key 无效或已过期"
                )
            elif e.code == 429:
                return ToolResponse.error(
                    code="RATE_LIMIT",
                    message="API 请求频率超限，请稍后再试"
                )
            else:
                return ToolResponse.error(
                    code="HTTP_ERROR",
                    message=f"搜索请求失败 (HTTP {e.code}): {e.reason}"
                )
        except URLError as e:
            return ToolResponse.error(
                code="NETWORK_ERROR",
                message=f"网络错误: {str(e)}"
            )
        except Exception as e:
            return ToolResponse.error(
                code="SEARCH_ERROR",
                message=f"搜索失败: {str(e)}"
            )

    def _parse_search_results(self, data: dict) -> List[dict]:
        """解析 Brave Search API 响应

        Args:
            data: API 响应数据

        Returns:
            搜索结果列表
        """
        results = []

        # 提取 web 搜索结果
        web_results = data.get("web", {}).get("results", [])

        for item in web_results:
            result = {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
            }
            results.append(result)

        return results

    def _format_results(self, results: List[dict]) -> str:
        """格式化搜索结果

        Args:
            results: 搜索结果列表

        Returns:
            格式化的文本
        """
        lines = [f"找到 {len(results)} 个结果:\n"]

        for i, result in enumerate(results, 1):
            lines.append(f"{i}. **{result['title']}**")
            lines.append(f"   URL: {result['url']}")
            if result['description']:
                lines.append(f"   {result['description'][:200]}")
            lines.append("")

        return "\n".join(lines)

    @tool_action("search_web", "搜索网络信息")
    def _search_action(self, query: str, count: int = None) -> str:
        """搜索网络

        Args:
            query: 搜索查询词
            count: 返回结果数量（可选）
        """
        response = self._search(query, count)
        return response.text
