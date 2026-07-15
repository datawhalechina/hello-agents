"""代码执行服务 - 安全执行用户代码"""

import subprocess
import tempfile
import os
import re
from typing import Dict


# 危险模块黑名单
BLOCKED_MODULES = {
    'os', 'sys', 'subprocess', 'shutil', 'pathlib',
    'socket', 'http', 'urllib', 'requests',
    'ctypes', 'importlib',
}

# 危险函数黑名单
BLOCKED_PATTERNS = [
    r'\bexec\s*\(',
    r'\beval\s*\(',
    r'\b__import__\s*\(',
    r'\bglobals\s*\(',
    r'\blocals\s*\(',
    r'\bcompile\s*\(',
]


def _check_code_safety(code: str) -> str:
    """
    检查代码安全性，返回安全版本的代码
    
    Args:
        code: 原始代码
        
    Returns:
        安全包装后的代码
        
    Raises:
        ValueError: 如果代码包含危险操作
    """
    # 检查危险函数调用
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, code):
            raise ValueError(f"代码包含不允许的操作: {pattern}")
    
    # 检查危险import
    import_pattern = r'(?:from|import)\s+(\w+)'
    imports = re.findall(import_pattern, code)
    for module in imports:
        if module in BLOCKED_MODULES:
            raise ValueError(f"不允许导入模块: {module}")
    
    # 包装代码，限制危险操作
    wrapper = '''
import sys
import io

# 重定向stdout/stderr
_old_stdout = sys.stdout
_old_stderr = sys.stderr
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()

try:
    # 用户代码开始
{_code}
    # 用户代码结束
finally:
    # 恢复stdout/stderr并获取输出
    _stdout_output = sys.stdout.getvalue()
    _stderr_output = sys.stderr.getvalue()
    sys.stdout = _old_stdout
    sys.stderr = _old_stderr
    
    # 输出结果
    if _stdout_output:
        print(_stdout_output, end='')
    if _stderr_output:
        print(_stderr_output, end='', file=sys.stderr)
'''
    
    # 给用户代码整体缩进4个空格，确保在 try 块内
    indented = '\n'.join(f'    {line}' for line in code.split('\n'))
    return wrapper.replace('{_code}', indented)


class CodeExecutor:
    """Python代码执行器"""
    
    def __init__(self):
        self.timeout = 10  # 超时时间（秒）
        self.max_output = 5000  # 最大输出长度
    
    def execute(self, code: str) -> Dict:
        """
        执行Python代码
        
        Args:
            code: Python代码字符串
            
        Returns:
            包含output和error的字典
        """
        # 安全检查
        try:
            safe_code = _check_code_safety(code)
        except ValueError as e:
            return {
                "success": False,
                "output": "",
                "error": f"安全检查失败: {str(e)}",
                "exit_code": -1,
            }
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.py', 
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(safe_code)
            temp_file = f.name
        
        try:
            # 执行代码
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=tempfile.gettempdir(),
            )
            
            output = result.stdout
            error = result.stderr
            
            # 截断过长的输出
            if len(output) > self.max_output:
                output = output[:self.max_output] + "\n... (输出过长，已截断)"
            if len(error) > self.max_output:
                error = error[:self.max_output] + "\n... (错误信息过长，已截断)"
            
            return {
                "success": result.returncode == 0,
                "output": output,
                "error": error,
                "exit_code": result.returncode,
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": f"执行超时（超过{self.timeout}秒）",
                "exit_code": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"执行失败: {str(e)}",
                "exit_code": -1,
            }
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except OSError:
                pass


# 全局实例
_executor = None


def get_executor() -> CodeExecutor:
    """获取代码执行器实例（单例）"""
    global _executor
    if _executor is None:
        _executor = CodeExecutor()
    return _executor
