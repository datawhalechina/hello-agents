"""
解析Agent - 负责解析 OpenAPI/Swagger 文档

这是"智能体层"里第一个不需要 LLM 的 Agent——
它的活是确定性的（读文档、提取结构），用普通 Python 类就够了。

除了提取接口清单，这里还负责两件对后续流程很关键的确定性工作：
1. 展开本地 $ref 引用（#/components/schemas/...），让生成Agent和验证Agent
   能直接看到真实字段，而不是一个干巴巴的引用字符串。
2. 根据文档的 responses 推断"期望状态码"和"期望响应 schema"，
   不把状态码的判断交给 LLM。
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
                    "parameters": [...],          # 参数（$ref 已展开）
                    "request_body": {...},        # 请求体 schema（$ref 已展开，无则 None）
                    "request_content_type": "...",# 请求体媒体类型，如 application/json
                    "responses": {...},           # 各状态码的响应（schema 已展开）
                    "response_schema": {...},     # 主成功响应的 schema（无则 None）
                    "security": [...],            # 安全要求（如 Bearer 认证）
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

    # ============ $ref 展开 ============

    def _resolve_ref(self, ref, openapi_dict, _stack):
        """解析单个本地 $ref 引用（如 #/components/schemas/User）

        沿 #/components/schemas/User 逐级取值，再递归展开目标里的嵌套引用。
        用 _stack 记录当前解析链，避免循环引用（A → B → A）导致无限递归。

        Args:
            ref: 引用字符串
            openapi_dict: 完整文档字典
            _stack: 解析链集合（用于循环检测）

        Returns:
            展开后的 schema；引用指向不存在的目标或成环时，原样返回引用字符串
        """
        if not isinstance(ref, str) or not ref.startswith("#/"):
            return ref
        if ref in _stack:
            # 循环引用：保留引用原样，避免死循环
            return ref

        parts = ref.lstrip("#/").split("/")
        node = openapi_dict
        for part in parts:
            node = node.get(part) if isinstance(node, dict) else None
            if node is None:
                # 引用指向不存在的目标，原样返回
                return ref

        _stack.add(ref)
        resolved = self._expand(node, openapi_dict, _stack)
        _stack.discard(ref)
        return resolved

    def _expand(self, node, openapi_dict, _stack=None):
        """递归展开 node 里所有嵌套的 $ref 引用，返回全新结构（不改原文档）

        Args:
            node: 任意 JSON/YAML 结构
            openapi_dict: 完整文档字典
            _stack: 解析链集合

        Returns:
            展开后的全新结构
        """
        if _stack is None:
            _stack = set()

        if isinstance(node, dict):
            if "$ref" in node:
                resolved = self._resolve_ref(node["$ref"], openapi_dict, _stack)
                # OpenAPI 3.1 允许 $ref 与其它字段共存，兄弟字段覆盖引用结果
                siblings = {
                    k: self._expand(v, openapi_dict, _stack)
                    for k, v in node.items() if k != "$ref"
                }
                if isinstance(resolved, dict) and siblings:
                    merged = dict(resolved)
                    merged.update(siblings)
                    return merged
                return resolved
            return {
                k: self._expand(v, openapi_dict, _stack)
                for k, v in node.items()
            }
        if isinstance(node, list):
            return [self._expand(v, openapi_dict, _stack) for v in node]
        return node

    # ============ 提取接口 ============

    def extract_endpoints(self, openapi_dict):
        """从 OpenAPI 结构里提取所有接口（含 $ref 展开）

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
                    # 请求体：解析出 schema 和媒体类型（application/json / multipart/form-data）
                    request_body, content_type = self._extract_request_body(
                        operation, openapi_dict
                    )
                    # 参数和响应都要展开 $ref，方便后续生成/校验
                    parameters = self._resolve_parameters(
                        operation.get("parameters", []), openapi_dict
                    )
                    responses = self._resolve_responses(
                        operation.get("responses", {}), openapi_dict
                    )
                    endpoints.append({
                        "path": path,
                        "method": method.upper(),
                        "summary": operation.get("summary", ""),
                        "parameters": parameters,
                        "request_body": request_body,
                        "request_content_type": content_type,
                        "responses": responses,
                        "response_schema": self._primary_response_schema(responses),
                        "security": operation.get("security"),
                    })

        return endpoints

    def _extract_request_body(self, operation, openapi_dict):
        """提取请求体的 schema 与媒体类型

        Args:
            operation: 单个方法对应的 operation 字典
            openapi_dict: 完整文档字典

        Returns:
            (schema, content_type) 二元组；没有请求体时返回 (None, None)
        """
        request_body = operation.get("requestBody")
        if not isinstance(request_body, dict):
            return None, None

        # requestBody 本身也可能是个 $ref
        if "$ref" in request_body:
            request_body = self._expand(request_body, openapi_dict)

        content = request_body.get("content") or {}
        # 优先 JSON，其次 multipart/form-data，最后取第一个可用媒体类型
        for media_type in ("application/json", "multipart/form-data"):
            media = content.get(media_type)
            if isinstance(media, dict) and "schema" in media:
                return self._expand(media["schema"], openapi_dict), media_type
        for media_type, media in content.items():
            if isinstance(media, dict) and "schema" in media:
                return self._expand(media["schema"], openapi_dict), media_type

        return None, None

    def _resolve_parameters(self, parameters, openapi_dict):
        """展开参数列表里的 $ref（参数本身和参数里的 schema）

        Args:
            parameters: operation 的 parameters 列表
            openapi_dict: 完整文档字典

        Returns:
            展开后的参数列表
        """
        resolved = []
        for param in parameters or []:
            if not isinstance(param, dict):
                continue
            # 参数本身可能是 $ref（#/components/parameters/...）
            if "$ref" in param:
                param = self._expand(param, openapi_dict)
            param = dict(param)
            if "schema" in param:
                param["schema"] = self._expand(param["schema"], openapi_dict)
            resolved.append(param)
        return resolved

    def _resolve_responses(self, responses, openapi_dict):
        """展开 responses 里每个响应体 schema 的 $ref

        Args:
            responses: operation 的 responses 字典
            openapi_dict: 完整文档字典

        Returns:
            展开后的 responses 字典
        """
        resolved = {}
        for code, resp in responses.items():
            if not isinstance(resp, dict):
                resolved[code] = resp
                continue
            content = resp.get("content") or {}
            new_content = {}
            for media_type, media in content.items():
                if isinstance(media, dict) and "schema" in media:
                    media = dict(media)
                    media["schema"] = self._expand(media["schema"], openapi_dict)
                new_content[media_type] = media
            new_resp = dict(resp)
            new_resp["content"] = new_content
            resolved[code] = new_resp
        return resolved

    def _primary_response_schema(self, responses):
        """取第一个 2xx 成功响应的 schema（作为正常用例的校验依据）

        Args:
            responses: 已展开的 responses 字典

        Returns:
            成功响应的 schema，没有则 None
        """
        for code in responses:
            if str(code).startswith("2"):
                schema = self._extract_response_schema(responses, code)
                if schema is not None:
                    return schema
        return None

    @staticmethod
    def _extract_response_schema(responses, status):
        """从 responses 里按状态码取响应体 schema

        Args:
            responses: 已展开的 responses 字典
            status: 状态码（int 或 str）

        Returns:
            对应状态码的响应 schema，没有则 None
        """
        resp = responses.get(str(status)) or responses.get(status)
        if not isinstance(resp, dict):
            return None
        content = resp.get("content") or {}
        # 优先 JSON，兼容 */* 和任意媒体类型
        for media_type in ("application/json", "*/*"):
            media = content.get(media_type)
            if isinstance(media, dict) and "schema" in media:
                return media["schema"]
        for media in content.values():
            if isinstance(media, dict) and "schema" in media:
                return media["schema"]
        return None

    # ============ 结构判断辅助 ============
    # 这些是"这个接口有没有可测试的输入"之类的确定性判断，
    # 生成Agent 用它们决定要不要生成 boundary/error 用例。

    @staticmethod
    def _query_params(endpoint):
        return [
            p for p in endpoint.get("parameters", [])
            if isinstance(p, dict) and p.get("in") == "query"
        ]

    @staticmethod
    def _path_params(endpoint):
        return [
            p for p in endpoint.get("parameters", [])
            if isinstance(p, dict) and p.get("in") == "path"
        ]

    @staticmethod
    def _required_body_fields(endpoint):
        body = endpoint.get("request_body")
        if isinstance(body, dict) and isinstance(body.get("required"), list):
            return body["required"]
        return []

    @staticmethod
    def has_validation_input(endpoint):
        """是否有必填的 query 参数或必填请求体字段

        这类接口缺少输入时会触发参数/请求体校验失败（通常 422）。
        """
        if any(p.get("required") for p in ParserAgent._query_params(endpoint)):
            return True
        return bool(ParserAgent._required_body_fields(endpoint))

    @staticmethod
    def has_required_path_param(endpoint):
        """是否有必填的路径参数

        路径参数缺失会导致路由不匹配（通常 404），和校验失败（422）要区分开。
        """
        return any(p.get("required") for p in ParserAgent._path_params(endpoint))

    @staticmethod
    def has_testable_inputs(endpoint):
        """是否有可测试的输入（query 参数或请求体），决定是否生成 boundary 用例"""
        return bool(ParserAgent._query_params(endpoint)) or endpoint.get("request_body") is not None

    # ============ 期望状态码 / 期望 schema ============

    def get_expected_status(self, endpoint, case_type="normal"):
        """根据接口定义和用例类型，确定期望的状态码

        这一步是确定性的，不交给 LLM，避免 LLM 随意生成错误的状态码。

        Args:
            endpoint: 单个接口字典
            case_type: 用例类型，normal / boundary / error

        Returns:
            期望的状态码（int）
        """
        responses = endpoint.get("responses", {})

        if case_type in ("normal", "boundary"):
            # 正常/边界场景：优先 2xx 成功状态码
            for code in responses:
                if str(code).startswith("2"):
                    return int(code)

        elif case_type == "error":
            # 异常场景要区分两类：
            #   - 有必填 query/请求体 → 缺字段/传错类型 → 校验失败 4xx（通常 422）
            #   - 只有必填路径参数 → 缺路径参数 → 路由不匹配 → 404
            if self.has_validation_input(endpoint):
                for code in responses:
                    if str(code).startswith("4"):
                        return int(code)
                # 文档没声明 4xx 时，按 FastAPI 校验错误约定默认 422
                return 422
            if self.has_required_path_param(endpoint):
                return 404
            for code in responses:
                if str(code).startswith("4"):
                    return int(code)
            return 400

        # 兜底：返回第一个声明的状态码
        for code in responses:
            return int(code)

        # 文档里什么都没声明，默认 200
        return 200

    def get_response_schema(self, endpoint, status):
        """按状态码取接口的响应 schema（$ref 已展开）

        Args:
            endpoint: 单个接口字典
            status: 状态码（int 或 str）

        Returns:
            对应状态码的响应 schema，没有则 None
        """
        return self._extract_response_schema(endpoint.get("responses", {}), status)
