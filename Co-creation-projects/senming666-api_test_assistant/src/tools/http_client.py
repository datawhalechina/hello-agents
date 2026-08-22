"""
HTTP 请求工具
负责真正发送 HTTP 请求，并统一处理超时、重试和错误。

这是"工具层"——没有大脑，只会老老实实发请求、拿结果。
"""

import time
import requests
from src.config import REQUEST_TIMEOUT, REQUEST_MAX_RETRIES


class HttpClient:
    """HTTP 客户端工具

    封装 requests 库，提供：
    - 统一的超时控制
    - 失败自动重试
    - 标准化的返回结果（方便后面的验证Agent使用）
    """

    # 支持的 HTTP 方法列表
    SUPPORTED_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH"]

    def __init__(self, timeout=REQUEST_TIMEOUT, max_retries=REQUEST_MAX_RETRIES):
        """
        初始化工具

        Args:
            timeout: 单次请求超时时间（秒），默认从 config 读取
            max_retries: 失败后重试次数，默认从 config 读取
        """
        self.timeout = timeout
        self.max_retries = max_retries

    def request(self, method, url, headers=None, params=None, body=None):
        """发送 HTTP 请求（带自动重试）

        Args:
            method: HTTP 方法，如 "GET"、"POST"
            url: 完整的请求地址
            headers: 请求头字典，如 {"Authorization": "Bearer xxx"}
            params: 查询参数（URL 中 ? 后面的部分）
            body: 请求体（POST/PUT 等要发送的 JSON 数据）

        Returns:
            标准化结果字典：
            {
                "success": bool,        # 是否成功
                "status_code": int,     # 状态码，如 200、404
                "body": dict 或 str,    # 解析后的响应体
                "elapsed": float,       # 耗时（秒）
                "error": str 或 None    # 错误信息（成功时为 None）
            }
        """
        method = method.upper()

        # 检查方法是否支持
        if method not in self.SUPPORTED_METHODS:
            return self._error_result(f"不支持的 HTTP 方法: {method}")

        # 带重试的请求循环：最多试 (max_retries + 1) 次
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return self._do_request(method, url, headers, params, body)
            except requests.RequestException as e:
                last_error = e
                # 如果不是最后一次，休息 1 秒再重试
                if attempt < self.max_retries:
                    time.sleep(1)

        # 所有重试都失败，返回错误结果
        return self._error_result(f"请求失败（已重试 {self.max_retries} 次）: {last_error}")

    def _do_request(self, method, url, headers, params, body):
        """真正执行一次请求（不重试，被 request 方法调用）"""
        start = time.time()

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=body,          # 自动把 dict 转成 JSON 格式
            timeout=self.timeout,
        )

        elapsed = time.time() - start

        return {
            "success": True,
            "status_code": response.status_code,
            "body": self._parse_body(response),
            "elapsed": round(elapsed, 3),
            "error": None,
        }

    def _parse_body(self, response):
        """把响应体解析成 dict（如果是 JSON）或字符串"""
        try:
            return response.json()
        except ValueError:
            return response.text

    def _error_result(self, message):
        """构造一个标准的"失败"结果字典"""
        return {
            "success": False,
            "status_code": None,
            "body": None,
            "elapsed": 0.0,
            "error": message,
        }
