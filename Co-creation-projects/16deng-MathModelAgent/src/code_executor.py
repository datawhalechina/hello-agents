"""
代码执行器模块

提供安全的Python代码执行功能
"""

import sys
import io
import traceback
import signal
from typing import Dict, Any, Optional, Tuple
from contextlib import contextmanager
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt
import base64
from pathlib import Path


class CodeExecutor:
    """代码执行器类"""
    
    def __init__(self, timeout: int = 30, max_output_length: int = 10000):
        """
        初始化代码执行器
        
        Args:
            timeout: 代码执行超时时间（秒）
            max_output_length: 最大输出长度
        """
        self.timeout = timeout
        self.max_output_length = max_output_length
        self.execution_history = []
    
    @contextmanager
    def _capture_output(self):
        """捕获标准输出和错误输出"""
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        old_plt_show = plt.show
        
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        sys.stdout = stdout_buffer
        sys.stderr = stderr_buffer
        
        # 禁用plt.show()，改为保存到内存
        plt.show = lambda: None
        
        try:
            yield stdout_buffer, stderr_buffer
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            plt.show = old_plt_show
    
    def _execute_with_timeout(self, code: str, global_vars: Dict[str, Any]) -> Tuple[bool, str, str, Optional[str]]:
        """
        执行代码并捕获输出
        
        Args:
            code: 要执行的Python代码
            global_vars: 全局变量字典
            
        Returns:
            (成功标志, 标准输出, 错误输出, 图表base64)
        """
        with self._capture_output() as (stdout_buffer, stderr_buffer):
            try:
                exec(code, global_vars)
                success = True
            except Exception as e:
                traceback.print_exc()
                success = False
        
        stdout = stdout_buffer.getvalue()
        stderr = stderr_buffer.getvalue()
        
        # 截断过长的输出
        if len(stdout) > self.max_output_length:
            stdout = stdout[:self.max_output_length] + "\n... (输出已截断)"
        if len(stderr) > self.max_output_length:
            stderr = stderr[:self.max_output_length] + "\n... (输出已截断)"
        
        # 获取当前图表
        figure_base64 = None
        if plt.get_fignums():
            fig = plt.gcf()
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            figure_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            plt.close('all')
        
        return success, stdout, stderr, figure_base64
    
    def execute(self, code: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行Python代码
        
        Args:
            code: 要执行的Python代码
            context: 执行上下文（变量字典）
            
        Returns:
            执行结果字典
        """
        # 准备全局变量
        global_vars = {
            '__builtins__': __builtins__,
            '__name__': '__main__',
        }
        
        # 添加常用库
        try:
            import numpy as np
            import pandas as pd
            import matplotlib.pyplot as plt
            global_vars['np'] = np
            global_vars['pd'] = pd
            global_vars['plt'] = plt
        except ImportError:
            pass
        
        # 合并用户上下文
        if context:
            global_vars.update(context)
        
        # 执行代码
        success, stdout, stderr, figure_base64 = self._execute_with_timeout(code, global_vars)
        
        # 构建结果
        result = {
            'success': success,
            'stdout': stdout,
            'stderr': stderr,
            'figure': figure_base64,
            'variables': {k: v for k, v in global_vars.items() 
                         if not k.startswith('_') and k not in ['np', 'pd', 'plt']}
        }
        
        # 记录执行历史
        self.execution_history.append({
            'code': code,
            'result': result
        })
        
        return result
    
    def execute_with_fix(self, code: str, max_retries: int = 3, 
                         fix_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        执行代码并在失败时尝试修复
        
        Args:
            code: 要执行的Python代码
            max_retries: 最大重试次数
            fix_callback: 修复回调函数，接收(代码, 错误信息)返回修复后的代码
            
        Returns:
            执行结果字典
        """
        current_code = code
        
        for attempt in range(max_retries):
            result = self.execute(current_code)
            
            if result['success']:
                result['attempts'] = attempt + 1
                return result
            
            # 如果有修复回调，尝试修复
            if fix_callback and attempt < max_retries - 1:
                try:
                    fixed_code = fix_callback(current_code, result['stderr'])
                    if fixed_code and fixed_code != current_code:
                        current_code = fixed_code
                        continue
                except Exception:
                    pass
            
            # 修复失败，返回错误结果
            result['attempts'] = attempt + 1
            return result
        
        return result
    
    def get_execution_history(self) -> list:
        """获取执行历史"""
        return self.execution_history
    
    def clear_history(self):
        """清空执行历史"""
        self.execution_history = []


class SafeCodeExecutor(CodeExecutor):
    """安全代码执行器（限制危险操作）"""
    
    # 危险函数和模块列表
    DANGEROUS_BUILTINS = [
        'eval', 'exec', 'compile', '__import__', 'open',
        'input', 'breakpoint', 'exit', 'quit'
    ]
    
    DANGEROUS_MODULES = [
        'os', 'sys', 'subprocess', 'shutil', 'pathlib',
        'socket', 'http', 'urllib', 'requests'
    ]
    
    def __init__(self, timeout: int = 30, max_output_length: int = 10000,
                 allow_dangerous: bool = False):
        """
        初始化安全代码执行器
        
        Args:
            timeout: 超时时间
            max_output_length: 最大输出长度
            allow_dangerous: 是否允许危险操作
        """
        super().__init__(timeout, max_output_length)
        self.allow_dangerous = allow_dangerous
    
    def _check_code_safety(self, code: str) -> Tuple[bool, str]:
        """
        检查代码安全性
        
        Args:
            code: 要检查的代码
            
        Returns:
            (安全标志, 警告信息)
        """
        if self.allow_dangerous:
            return True, ""
        
        warnings = []
        
        # 检查危险内置函数
        for func in self.DANGEROUS_BUILTINS:
            if func in code:
                warnings.append(f"代码中包含危险函数: {func}")
        
        # 检查危险模块导入
        for module in self.DANGEROUS_MODULES:
            if f"import {module}" in code or f"from {module}" in code:
                warnings.append(f"代码中导入了受限模块: {module}")
        
        if warnings:
            return False, "\n".join(warnings)
        
        return True, ""
    
    def execute(self, code: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        安全执行Python代码
        
        Args:
            code: 要执行的Python代码
            context: 执行上下文
            
        Returns:
            执行结果字典
        """
        # 检查代码安全性
        is_safe, warning = self._check_code_safety(code)
        
        if not is_safe:
            return {
                'success': False,
                'stdout': '',
                'stderr': f"安全检查未通过:\n{warning}",
                'figure': None,
                'variables': {},
                'safety_warning': warning
            }
        
        return super().execute(code, context)


# 测试代码
if __name__ == "__main__":
    # 测试基本执行
    executor = CodeExecutor()
    
    test_code = """
import numpy as np
import matplotlib.pyplot as plt

# 创建数据
x = np.linspace(0, 10, 100)
y = np.sin(x)

# 绘制图形
plt.figure(figsize=(10, 6))
plt.plot(x, y)
plt.title('Sine Wave')
plt.xlabel('x')
plt.ylabel('y')
plt.grid(True)
plt.show()

print("代码执行成功！")
print(f"x的范围: {x.min():.2f} 到 {x.max():.2f}")
print(f"y的范围: {y.min():.2f} 到 {y.max():.2f}")
"""
    
    result = executor.execute(test_code)
    
    print("=" * 50)
    print("执行结果:")
    print(f"成功: {result['success']}")
    print(f"输出: {result['stdout']}")
    if result['stderr']:
        print(f"错误: {result['stderr']}")
    if result['figure']:
        print(f"图表: 已生成 (base64长度: {len(result['figure'])})")
