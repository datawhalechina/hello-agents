"""上传体积上限与限量读取（main.py 拆分：阶段 1）。

`read_upload_with_limit` 被餐盘分析、三条上传链路和备份导入/预检共用（8 处）。放在
runtime 层而不是 upload workflow 里：备份端点不属于上传编排，让它 import upload
workflow 只为了拿一个通用 HTTP 工具，会把依赖方向拧反。

体积上限跟着读取函数一起放这里——它们就是这个函数的实参取值，分开放会让"改上限"
要动两个文件。

这些常量和函数都**不会被测试替换**，所以调用方按名字导入即可，不必绕 `upload_io.X`
（区别见 `deps.py` 顶部关于"为什么必须写 deps.X"的说明）。
"""

from __future__ import annotations

from fastapi import UploadFile


MIB = 1024 * 1024
FIT_FILE_MAX_BYTES = 50 * MIB
PLAN_FILE_CONFIRM_BYTES = 256 * 1024
PLAN_FILE_MAX_BYTES = 1 * MIB
HEALTH_ZIP_MAX_BYTES = 50 * MIB
HEALTH_CSV_MAX_BYTES = 2 * MIB
HEALTH_UPLOAD_MAX_FILES = 5


async def read_upload_with_limit(file: UploadFile, max_bytes: int) -> bytes | None:
    """Read at most max_bytes, returning None when the upload exceeds the limit."""
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        return None
    return content
