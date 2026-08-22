"""
解析Agent - 负责解析 OpenAPI/Swagger 文档

这是"智能体层"里第一个不需要 LLM 的 Agent——
它的活是确定性的（读文档、提取结构），用普通 Python 类就够了。
"""

import yaml
import json
import requests
from pathlib import Path


class ParserAgent:
    """解析 OpenAPI/Swagger 文档，提取接口清单"""

    # OpenAPI 里常见的 HTTP 方法
    HTTP_METHODS = ["get", "post", "put", "delete", "patch"]

    def parse_file(self, file_path):
        """解析文档文件，返回接口列表

        Args:
            file_path: OpenAPI 文档路径（支持 .yaml / .yml / .json）

        Returns:
            接口列表，每个接口是一个字典：
            [
                {
                    "path": "/users",
                    "method": "GET",
                    "parameters": [...],      # 请求参数
                    "responses": {...}        # 各状态码的响应
                },
                ...
            ]
        """
        text = Path(file_path).read_text(encoding="utf-8")
        return self.parse_text(text)

    def parse_url(self, url):
        """从 URL 抓取 OpenAPI 文档并解析

        Args:
            url: OpenAPI 文档的网址（如 https://httpbin.org/spec.json）

        Returns:
            接口列表
        """
        try:
            # 用 requests 抓取网络上的文档内容
            resp = requests.get(url, timeout=30)
            # 非 200 状态码会抛异常
            resp.raise_for_status()
        except requests.RequestException as e:
            # 抓取失败（如 503 服务不可用、网络超时），不崩溃，返回空列表
            print(f"[警告] 从 URL 抓取文档失败：{e}")
            return []

        # 抓到的内容和本地文件一样，复用 parse_text 解析
        return self.parse_text(resp.text)

    def parse_text(self, text):
        """解析文档文本，自动判断 JSON 还是 YAML

        Args:
            text: OpenAPI 文档内容（字符串，前端直接传这个）

        Returns:
            接口列表
        """
        text = text.strip()

        # 空输入直接返回空列表，避免 yaml.safe_load("") 返回 None 导致后续崩溃
        if not text:
            return []

        # 先尝试按 JSON 解析，失败则按 YAML 解析
        # （JSON 也是合法的 YAML，但反过来不成立，所以先试 JSON）
        try:
            openapi_dict = json.loads(text)
        except json.JSONDecodeError:
            openapi_dict = yaml.safe_load(text)

        return self.extract_endpoints(openapi_dict)

    def extract_endpoints(self, openapi_dict):
        """从 OpenAPI 结构里提取所有接口

        Args:
            openapi_dict: 解析后的 OpenAPI 字典

        Returns:
            接口列表
        """
        endpoints = []

        # 类型检查：解析结果可能是 None 或非 dict（如 yaml 解析出字符串），直接返回空
        if not isinstance(openapi_dict, dict):
            return endpoints

        # paths 可能缺失或为 None，统一兜底为空字典
        paths = openapi_dict.get("paths") or {}

        for path, path_item in paths.items():
            # path_item 也可能不是 dict（不规范文档），跳过
            if not isinstance(path_item, dict):
                continue
            # 每个 path 下可能有多个方法（get、post 等）
            for method in self.HTTP_METHODS:
                if method in path_item:
                    operation = path_item[method]
                    endpoints.append({
                        "path": path,
                        "method": method.upper(),
                        "summary": operation.get("summary", ""),
                        "parameters": operation.get("parameters", []),
                        "request_body": operation.get("requestBody", None),
                        "responses": operation.get("responses", {}),
                    })

        return endpoints

    def get_expected_status(self, endpoint, case_type="normal"):
        """根据接口定义和用例类型，推断期望的状态码

        Args:
            endpoint: 单个接口字典
            case_type: 用例类型，normal / boundary / error

        Returns:
            期望的状态码（int）
        """
        responses = endpoint.get("responses", {})

        if case_type == "normal":
            # 正常情况：优先找 2xx 成功状态码
            for code in responses:
                if code.startswith("2"):
                    return int(code)

        elif case_type == "error":
            # 异常情况：优先找 4xx 客户端错误状态码
            for code in responses:
                if code.startswith("4"):
                    return int(code)

        # 兜底：返回第一个声明的状态码
        for code in responses:
            return int(code)

        # 文档里什么都没声明，默认 200
        return 200
