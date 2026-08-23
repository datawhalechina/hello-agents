"""
日志系统模块

提供统一的日志管理
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import json


class Logger:
    """日志管理器类"""
    
    def __init__(self, name: str = "MathModelAgent", log_dir: str = "./logs",
                 level: int = logging.INFO):
        """
        初始化日志管理器
        
        Args:
            name: 日志名称
            log_dir: 日志目录
            level: 日志级别
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.level = level
        
        # 创建日志目录
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建日志器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """设置日志处理器"""
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # 文件处理器
        log_file = self.log_dir / f"{self.name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(self.level)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)
    
    def info(self, message: str, **kwargs):
        """记录信息日志"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """记录警告日志"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """记录错误日志"""
        self.logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """记录调试日志"""
        self.logger.debug(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """记录严重错误日志"""
        self.logger.critical(message, **kwargs)
    
    def log_execution(self, code: str, result: dict):
        """
        记录代码执行日志
        
        Args:
            code: 执行的代码
            result: 执行结果
        """
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "code": code[:200] + "..." if len(code) > 200 else code,
            "success": result.get('success', False),
            "stdout_length": len(result.get('stdout', '')),
            "stderr_length": len(result.get('stderr', '')),
            "has_figure": result.get('figure') is not None
        }
        
        if result.get('success'):
            self.info(f"代码执行成功: {json.dumps(log_data, ensure_ascii=False)}")
        else:
            self.error(f"代码执行失败: {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_api_call(self, endpoint: str, method: str, status_code: int, 
                     duration: float):
        """
        记录API调用日志
        
        Args:
            endpoint: API端点
            method: HTTP方法
            status_code: 状态码
            duration: 耗时（秒）
        """
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "duration": f"{duration:.3f}s"
        }
        
        self.info(f"API调用: {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_template_generation(self, template_name: str, output_path: str, 
                                success: bool):
        """
        记录模板生成日志
        
        Args:
            template_name: 模板名称
            output_path: 输出路径
            success: 是否成功
        """
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "template_name": template_name,
            "output_path": output_path,
            "success": success
        }
        
        if success:
            self.info(f"模板生成成功: {json.dumps(log_data, ensure_ascii=False)}")
        else:
            self.error(f"模板生成失败: {json.dumps(log_data, ensure_ascii=False)}")


class PerformanceLogger:
    """性能日志记录器"""
    
    def __init__(self, logger: Logger):
        """
        初始化性能日志记录器
        
        Args:
            logger: 日志管理器
        """
        self.logger = logger
        self.metrics = {}
    
    def start_timer(self, name: str):
        """
        开始计时
        
        Args:
            name: 计时器名称
        """
        self.metrics[name] = {
            "start_time": datetime.now(),
            "end_time": None,
            "duration": None
        }
    
    def stop_timer(self, name: str) -> float:
        """
        停止计时
        
        Args:
            name: 计时器名称
            
        Returns:
            耗时（秒）
        """
        if name not in self.metrics:
            self.logger.warning(f"计时器不存在: {name}")
            return 0.0
        
        self.metrics[name]["end_time"] = datetime.now()
        duration = (self.metrics[name]["end_time"] - 
                   self.metrics[name]["start_time"]).total_seconds()
        self.metrics[name]["duration"] = duration
        
        self.logger.info(f"性能计时 {name}: {duration:.3f}s")
        return duration
    
    def get_metrics(self) -> dict:
        """获取所有性能指标"""
        return self.metrics
    
    def log_summary(self):
        """记录性能摘要"""
        summary = {}
        for name, metric in self.metrics.items():
            if metric["duration"] is not None:
                summary[name] = f"{metric['duration']:.3f}s"
        
        self.logger.info(f"性能摘要: {json.dumps(summary, ensure_ascii=False)}")


# 全局日志实例
_logger: Optional[Logger] = None
_performance_logger: Optional[PerformanceLogger] = None


def get_logger(name: str = "MathModelAgent") -> Logger:
    """
    获取日志管理器实例
    
    Args:
        name: 日志名称
        
    Returns:
        日志管理器实例
    """
    global _logger
    if _logger is None:
        _logger = Logger(name)
    return _logger


def get_performance_logger() -> PerformanceLogger:
    """
    获取性能日志记录器实例
    
    Returns:
        性能日志记录器实例
    """
    global _performance_logger
    if _performance_logger is None:
        _performance_logger = PerformanceLogger(get_logger())
    return _performance_logger


# 测试代码
if __name__ == "__main__":
    # 测试日志系统
    logger = get_logger("TestLogger")
    
    logger.info("这是一条信息日志")
    logger.warning("这是一条警告日志")
    logger.error("这是一条错误日志")
    
    # 测试代码执行日志
    test_result = {
        "success": True,
        "stdout": "Hello, World!",
        "stderr": "",
        "figure": None
    }
    logger.log_execution("print('Hello, World!')", test_result)
    
    # 测试性能日志
    perf_logger = get_performance_logger()
    
    perf_logger.start_timer("test_operation")
    import time
    time.sleep(1)
    perf_logger.stop_timer("test_operation")
    
    perf_logger.log_summary()
    
    print("日志系统测试完成！")
