"""
执行Agent - 负责真正执行测试用例

这是"智能体层"里第一个"用工具"的 Agent——
它自己不发请求，而是调用 http_client 工具去发。
"""

import re

from src.tools.http_client import HttpClient


class ExecutorAgent:
    """执行测试用例，调用目标 API"""

    def __init__(self):
        # 依赖 HttpClient 工具：发请求的活交给它
        self.http_client = HttpClient()

    def execute(self, test_cases, base_url, headers=None):
        """执行一组测试用例

        Args:
            test_cases: GeneratorAgent 生成的用例列表
            base_url: 目标 API 的基础地址，如 "https://api.example.com"
            headers: 全局请求头（可选），如认证信息

        Returns:
            执行结果列表，每个元素是：
            {
                "case": {...},     # 原始用例（含期望的状态码）
                "result": {...},   # http_client 返回的请求结果
            }
        """
        results = []

        for case in test_cases:
            result = self.execute_one(case, base_url, headers)
            results.append(result)

        return results

    def _replace_path_params(self, path, params):
        """把 path 里的 {xxx} 占位符替换成 params 里的对应值

        Args:
            path: 接口路径，如 "/status/{codes}"
            params: 用例的参数字典，如 {"codes": "200"}

        Returns:
            (替换后的 path, 移除路径参数后的 params)
        """
        # 拷贝一份，避免修改原始的 case["params"]
        params = dict(params or {})

        def replacer(match):
            key = match.group(1)
            # 从 params 里取值并移除（路径参数不应再作为查询参数发出）
            value = params.pop(key, None)
            if value is None:
                # params 里没有对应值，保留占位符原样（如 error 用例缺参数）
                return match.group(0)
            return str(value)

        new_path = re.sub(r"\{(\w+)\}", replacer, path)
        return new_path, params

    def execute_one(self, case, base_url, headers=None):
        """执行单个测试用例

        Args:
            case: 单个用例字典，含 method/path/params/body
            base_url: 目标 API 基础地址
            headers: 全局请求头

        Returns:
            {"case": ..., "result": ...} 打包结果
        """
        # 1. 替换路径参数（如 /status/{codes} → /status/200）
        path, params = self._replace_path_params(case["path"], case.get("params"))

        # 2. 拼接完整 URL
        url = base_url.rstrip("/") + "/" + path.lstrip("/")

        # 3. 调用工具发请求（params 已移除路径参数）
        # 认证头从全局 headers 传入；multipart 上传的文件从 case["files"] 传入
        response = self.http_client.request(
            method=case["method"],
            url=url,
            headers=headers,
            params=params,
            body=case.get("body"),
            files=case.get("files"),
            content_type=case.get("content_type", "application/json"),
        )

        # 3. 把"用例"和"结果"打包在一起返回
        return {
            "case": case,
            "result": response,
        }
