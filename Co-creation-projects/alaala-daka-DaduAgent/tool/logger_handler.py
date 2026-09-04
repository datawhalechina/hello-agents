"""
日志工具模块 —— 基于 loguru 的简易日志封装
============================================

loguru 是什么？
  - 一个第三方日志库，比 Python 自带的 logging 好用得多
  - 导入就能用，不需要复杂的配置
  - 自带彩色输出、自动分割文件、压缩旧日志等功能

本模块做了什么？
  1. 配置控制台输出（开发时实时查看）
  2. 配置文件输出（保存到磁盘，方便排查历史问题）
  3. 提供一个 setup_logger() 函数，方便在不同环境下切换配置

如何使用（在其他 .py 文件中）？
  from tool.logger_handler import logger

  logger.info("程序启动")
  logger.debug("这是调试信息")
  logger.error("出错了！")
"""

import os
import sys

# ----------------------------------------------------------------
# 导入项目路径工具，获取项目根目录（用于存放日志文件）
# ----------------------------------------------------------------
try:
    from tool.path_tool import get_project_root
    PROJECT_ROOT = get_project_root()
except ImportError:
    # 如果导入失败（比如单独运行本文件），回退到手写逻辑
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from loguru import logger


# ================================================================
#  第一步：移除 loguru 自带的默认 handler
#  这样我们才能完全按自己的需求来配置
# ================================================================
logger.remove()


# ================================================================
#  第二步：配置控制台输出（stderr）
#  开发时在终端里实时看到日志，不同级别显示不同颜色
# ================================================================
logger.add(
    sys.stderr,                                              # 输出到控制台
    format=(                                                 # 日志格式
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "       # 时间（绿色）
        "<level>{level: <8}</level> | "                      # 级别标签（带颜色）
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:"       # 模块:函数:
        "<cyan>{line}</cyan> - "                             # 行号
        "<level>{message}</level>"   
        "{extra}"                        # 日志正文
    ),
    level="INFO",                                           # 控制台显示 INFO 及以上的全部级别
    colorize=True,                                           # 开启彩色输出
)


# ================================================================
#  第三步：配置文件输出（写入磁盘）
#  日志按天分文件 → 单个文件超 10MB 分割 → 旧文件压缩 → 30天后自动删除
# ================================================================

# 在项目根目录下创建 logs 文件夹（如果不存在）
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger.add(
    os.path.join(LOG_DIR, "app_{time:YYYY-MM-DD}.log"),      # 文件名：app_2026-07-22.log
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | "
           "{level: <8} | "
           "{name}:{function}:{line} | "
           "{message}",
    level="INFO",        # 文件只记录 INFO 及以上（减少磁盘占用）
    rotation="10 MB",    # 单个日志文件超过 10MB 就分割成新文件
    retention="30 days", # 只保留最近 30 天的日志
    compression="zip",   # 旧日志自动压缩成 .zip，节省空间
    encoding="utf-8",    # 用 UTF-8 编码，避免中文乱码
    enqueue=True,        # 多线程安全模式（写入排队，不会冲突）
)


# ================================================================
#  第四步：提供 setup_logger() 函数
#  如果你的程序在不同环境（开发/生产）需要不同配置，调用它即可
# ================================================================

def setup_logger(level: str = "INFO", log_dir: str | None = None):
    """
    重新配置日志系统（清空旧配置，应用新配置）。

    参数:
        level:   日志最低级别。可选 "DEBUG" / "INFO" / "WARNING" / "ERROR"
                 设为 DEBUG 可以看到最详细的信息（适合开发调试）
                 设为 INFO  只记录关键节点（适合正式运行）
        log_dir: 日志文件存放路径，不传则默认 "项目根目录/logs/"

    使用示例:
        # 开发时想看所有调试信息
        setup_logger(level="DEBUG")

        # 上线后只记录警告和错误
        setup_logger(level="WARNING")

        # 把日志存到指定位置
        setup_logger(log_dir="D:/my_project/logs")
    """
    logger.remove()     # 先清空所有旧配置

    # --- 重新添加控制台输出 ---
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<level>{message}</level>",
        level=level,
        colorize=True,
    )

    # --- 重新添加文件输出 ---
    target_dir = log_dir or os.path.join(PROJECT_ROOT, "logs")
    os.makedirs(target_dir, exist_ok=True)

    logger.add(
        os.path.join(target_dir, "app_{time:YYYY-MM-DD}.log"),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
               "{name}:{function}:{line} | {message}",
        level=level,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
    )

    logger.info(f"日志系统已重新配置 | 级别={level} | 目录={target_dir}")


# ================================================================
#  第五步：直接运行本文件可以查看演示效果
#  运行方法：python tool/logger_handler.py
# ================================================================
if __name__ == "__main__":
    print("=" * 55)
    print("  日志工具演示")
    print("=" * 55)

    # ---- 1. 五个常用级别 ----
    logger.debug("这是 DEBUG —— 最详细的调试信息")
    logger.info("这是 INFO —— 记录关键流程节点")
    logger.success("这是 SUCCESS —— 操作成功（loguru 独有功能）")
    logger.warning("这是 WARNING —— 有潜在问题但不影响运行")
    logger.error("这是 ERROR —— 出错了但程序还能继续")

    # ---- 2. 在日志里插入变量（用 {} 占位，自动填入）----
    name = "张三"
    count = 5
    logger.info("用户 [{}] 完成了 {} 个任务", name, count)

    # ---- 3. 用 exception() 自动记录异常堆栈 ----
    try:
        result = 1 / 0
    except ZeroDivisionError:
        logger.exception("捕获到一个异常！")

    # ---- 4. bind() 绑定固定信息，后续日志都会带上 ----
    req_log = logger.bind(request_id="REQ-2026")
    req_log.info("收到请求")
    req_log.info("处理完成")

    print(f"\n日志文件保存在: {LOG_DIR}")
