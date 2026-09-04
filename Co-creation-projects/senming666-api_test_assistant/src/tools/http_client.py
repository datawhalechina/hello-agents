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

    def request(self, method, url, headers=None, params=None, body=None,
                files=None, content_type="application/json"):
        """发送 HTTP 请求（带自动重试）

        Args:
            method: HTTP 方法，如 "GET"、"POST"
            url: 完整的请求地址
            headers: 请求头字典，如 {"Authorization": "Bearer xxx"}
            params: 查询参数（URL 中 ? 后面的部分）
            body: 请求体（JSON 时的 dict，或表单字段）
            files: 上传的文件，格式 {"字段名": ("文件名", 字节内容, "MIME")}，传了就走 multipart
            content_type: 请求体媒体类型，如 "application/json" / "multipart/form-data"

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
                return self._do_request(method, url, headers, params, body, files, content_type)
            except requests.RequestException as e:
                last_error = e
                # 如果不是最后一次，休息 1 秒再重试
                if attempt < self.max_retries:
                    time.sleep(1)

        # 所有重试都失败，返回错误结果
        return self._error_result(f"请求失败（已重试 {self.max_retries} 次）: {last_error}")

    def _do_request(self, method, url, headers, params, body, files, content_type):
        """真正执行一次请求（不重试，被 request 方法调用）

        根据请求体类型选择序列化方式：
        - 有 files：multipart 文件上传（body 作为表单字段，files 作为文件字段）
        - content_type 是 multipart：纯表单字段（无文件）
        - 其它：JSON 请求体
        """
        start = time.time()

        kwargs = {
            "method": method,
            "url": url,
            "headers": headers,
            "params": params,
            "timeout": self.timeout,
        }

        if files is not None:
            # multipart/form-data：文件字段走 files，普通字段走 data
            kwargs["data"] = body or {}
            kwargs["files"] = files
        elif content_type and "multipart" in content_type.lower():
            # multipart 但没有文件（纯表单字段）
            kwargs["data"] = body or {}
        elif body is not None:
            # 默认 JSON 请求体，自动把 dict 转成 JSON 格式
            kwargs["json"] = body

        response = requests.request(**kwargs)

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
