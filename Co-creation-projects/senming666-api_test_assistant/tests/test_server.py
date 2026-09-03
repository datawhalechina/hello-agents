"""server.py HTTP 响应边界的回归测试"""
import json

from server import _json_safe


def test_json_safe_replaces_binary_multipart_content():
    result = {
        "files": {
            "file": ("file.png", b"\x89PNG\x00\xff", "image/png"),
        },
    }

    safe = _json_safe(result)

    assert safe["files"]["file"] == [
        "file.png",
        "<binary data: 6 bytes>",
        "image/png",
    ]
    # 关键回归断言：处理后的结果可以被 JSON 序列化。
    json.dumps(safe)
