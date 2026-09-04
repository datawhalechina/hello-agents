"""settings.py

数据目录的**唯一**解析点（对应需求清单 DATA-10 与 ARCH-03）。

为什么需要它
------------
所有 store 原先各自硬编码 `Path("data") / ...`，这是相对**当前工作目录**的
路径。带来两个问题：

1. 从非项目根目录启动，会在别处凭空建一个 `data/`，老数据看起来"消失"了；
2. 容器里数据目录不可配置，只能寄希望于有人把整个项目目录 bind-mount 进去。
   `docker-compose.yml` 原先只挂了 `./:/app`（为了源码热重载），一旦有人按
   正常方式跑镜像——不挂源码——所有健康数据就写在容器可写层里，**容器重建即
   全量丢失**。DATA-02 里那些 `/opt/project/...` 的绝对路径就是这个问题的实证：
   数据确实在环境之间漂移过。

约定
----
* 环境变量 `FITHEALTH_DATA_DIR` 指定数据目录；未设置时回落到仓库根目录的 `data`。
* 默认路径必须与当前工作目录无关。从其他目录启动脚本时，不能悄悄创建第二份数据。
* 每次调用都重新读环境变量，不做模块级缓存——同样是为了让测试能在运行中
  切换目录，而不必重新导入整个包。
"""

from __future__ import annotations

import os
from pathlib import Path


DATA_DIR_ENV = "FITHEALTH_DATA_DIR"
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def data_dir() -> Path:
    """返回数据目录。设了环境变量就用它，否则使用仓库内绝对路径。"""
    configured = os.environ.get(DATA_DIR_ENV, "").strip()
    return Path(configured) if configured else DEFAULT_DATA_DIR


def data_path(*parts: str) -> Path:
    """拼出数据目录下的一个路径，例如 `data_path("health.db")`。"""
    return data_dir().joinpath(*parts)
