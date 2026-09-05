"""代码执行服务 - 安全执行用户代码（多语言支持）"""

import subprocess
import tempfile
import os
import re
import platform
from abc import ABC, abstractmethod
from typing import Dict


# ---------------------------------------------------------------------------
# Python 安全检查常量
# ---------------------------------------------------------------------------

BLOCKED_MODULES = {
    'os', 'sys', 'subprocess', 'shutil', 'pathlib',
    'socket', 'http', 'urllib', 'requests',
    'ctypes', 'importlib',
}

BLOCKED_PATTERNS = [
    r'\bexec\s*\(',
    r'\beval\s*\(',
    r'\b__import__\s*\(',
    r'\bglobals\s*\(',
    r'\blocals\s*\(',
    r'\bcompile\s*\(',
]

# ---------------------------------------------------------------------------
# JavaScript / TypeScript 安全检查常量
# ---------------------------------------------------------------------------

JS_BLOCKED_PATTERNS = [
    r"require\s*\(\s*['\"]child_process['\"]\s*\)",
    r"require\s*\(\s*['\"]fs['\"]\s*\)",
    r"\bprocess\.exit\s*\(",
    r"\bprocess\.kill\s*\(",
    r"import\s+.*\s+from\s+['\"]fs['\"]",
    r"import\s+.*\s+from\s+['\"]child_process['\"]",
]

# ---------------------------------------------------------------------------
# Bash 安全检查常量
# ---------------------------------------------------------------------------

BASH_SAFE_COMMANDS = {
    'echo', 'ls', 'cat', 'pwd', 'env', 'printf', 'date', 'whoami', 'uname',
}

# Operators: always dangerous via substring match
BASH_BLOCKED_OPERATORS = ['|', '>', '<', '$(', '`', ';', '&&', '||']

# Commands: only dangerous as whole words (avoids false positives like "sh" in "show")
BASH_BLOCKED_COMMANDS = [
    r'\bsh\b', r'\bbash\b', r'\bpython\b',
    r'\bsudo\b', r'\bchmod\b', r'\brm\b', r'\bmv\b', r'\bcp\b', r'\bdd\b',
    r'\bcurl\b', r'\bwget\b', r'\bnc\b',
]


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseExecutor(ABC):
    """All language executors inherit from this."""

    def __init__(self, timeout: int = 10, max_output: int = 5000):
        self.timeout = timeout
        self.max_output = max_output

    @abstractmethod
    def execute(self, code: str) -> Dict:
        ...

    def _truncate(self, text: str | None) -> str:
        if not text:
            return ""
        if len(text) > self.max_output:
            return text[:self.max_output] + "\n... (输出过长，已截断)"
        return text

    def _timeout_result(self) -> Dict:
        return {
            "success": False,
            "output": "",
            "error": f"执行超时（超过{self.timeout}秒）",
            "exit_code": -1,
        }

    def _exception_result(self, exc: Exception) -> Dict:
        return {
            "success": False,
            "output": "",
            "error": f"执行失败: {str(exc)}",
            "exit_code": -1,
        }

    def _safety_result(self, msg: str) -> Dict:
        return {
            "success": False,
            "output": "",
            "error": f"安全检查失败: {msg}",
            "exit_code": -1,
        }

    def _run_subprocess(self, cmd: list, temp_file: str) -> Dict:
        """Run a subprocess, handle timeout / error, clean up temp file."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=self.timeout,
                cwd=tempfile.gettempdir(),
            )
            output = self._truncate(result.stdout)
            error = self._truncate(result.stderr)
            return {
                "success": result.returncode == 0,
                "output": output,
                "error": error,
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return self._timeout_result()
        except Exception as e:
            return self._exception_result(e)
        finally:
            try:
                os.unlink(temp_file)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Python executor
# ---------------------------------------------------------------------------

class PythonExecutor(BaseExecutor):
    """Executes Python code inside a safety-wrapped temp file."""

    def _check_safety(self, code: str) -> str:
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, code):
                raise ValueError(f"代码包含不允许的操作: {pattern}")

        import_pattern = r'(?:from|import)\s+(\w+)'
        imports = re.findall(import_pattern, code)
        for module in imports:
            if module in BLOCKED_MODULES:
                raise ValueError(f"不允许导入模块: {module}")

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
        indented = '\n'.join(f'    {line}' for line in code.split('\n'))
        return wrapper.replace('{_code}', indented)

    def execute(self, code: str) -> Dict:
        try:
            safe_code = self._check_safety(code)
        except ValueError as e:
            return self._safety_result(str(e))

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False, encoding='utf-8',
        ) as f:
            f.write(safe_code)
            temp_file = f.name

        return self._run_subprocess(['python', temp_file], temp_file)


# ---------------------------------------------------------------------------
# JavaScript executor
# ---------------------------------------------------------------------------

class JavaScriptExecutor(BaseExecutor):
    """Executes JavaScript via Node.js."""

    def _check_safety(self, code: str) -> None:
        for pattern in JS_BLOCKED_PATTERNS:
            if re.search(pattern, code):
                raise ValueError(f"代码包含不允许的操作: {pattern}")

    def execute(self, code: str) -> Dict:
        try:
            self._check_safety(code)
        except ValueError as e:
            return self._safety_result(str(e))

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.js', delete=False, encoding='utf-8',
        ) as f:
            f.write(code)
            temp_file = f.name

        return self._run_subprocess(['node', temp_file], temp_file)


# ---------------------------------------------------------------------------
# TypeScript executor
# ---------------------------------------------------------------------------

class TypeScriptExecutor(BaseExecutor):
    """Executes TypeScript via node --experimental-strip-types (Node 22+), 
    falls back to npx tsx for advanced features (enums, decorators, etc.)."""

    def __init__(self):
        # npx first-run download can be slow → 30s timeout
        super().__init__(timeout=30)

    def _check_safety(self, code: str) -> None:
        for pattern in JS_BLOCKED_PATTERNS:
            if re.search(pattern, code):
                raise ValueError(f"代码包含不允许的操作: {pattern}")

    def _resolve_npx(self) -> str:
        """Return the correct npx command for the current platform."""
        return 'npx.cmd' if platform.system() == 'Windows' else 'npx'

    def _try_cmd(self, cmd: list, code: str, temp_file: str) -> Dict:
        """Run a subprocess, re-creating temp_file (since _run_subprocess cleans it up)."""
        # Re-create file (may have been deleted by a previous _run_subprocess)
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(code)
        except OSError:
            pass
        return self._run_subprocess(cmd, temp_file)

    def execute(self, code: str) -> Dict:
        try:
            self._check_safety(code)
        except ValueError as e:
            return self._safety_result(str(e))

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.ts', delete=False, encoding='utf-8',
        ) as f:
            f.write(code)
            temp_file = f.name

        # Primary: node --experimental-strip-types (fast, no download needed)
        # --no-warnings suppresses ExperimentalWarning from stderr
        result = self._try_cmd(['node', '--no-warnings', '--experimental-strip-types', temp_file], code, temp_file)
        if result['success']:
            return result

        # Fallback: npx tsx — handles TS features strip-types doesn't support
        npx_cmd = self._resolve_npx()
        result = self._try_cmd([npx_cmd, '--yes', 'tsx', temp_file], code, temp_file)
        return result


# ---------------------------------------------------------------------------
# Bash executor
# ---------------------------------------------------------------------------

class BashExecutor(BaseExecutor):
    """Executes Shell commands.

    On Linux/Mac: uses bash.
    On Windows: uses sh (Git Bash) if available, falls back to PowerShell.
    """

    @staticmethod
    def _find_shell() -> str | None:
        """Locate a usable Unix-compatible shell."""
        if platform.system() != 'Windows':
            return 'bash'

        # On Windows, try 'sh' (Git Bash etc.)
        import shutil
        sh_path = shutil.which('sh')
        if sh_path:
            return sh_path

        # Check common Git Bash install paths
        common_paths = [
            r'C:\Program Files\Git\bin\sh.exe',
            r'C:\Program Files (x86)\Git\bin\sh.exe',
        ]
        for p in common_paths:
            if os.path.exists(p):
                return p

        return None

    def _check_safety(self, code: str, use_powershell: bool = False) -> None:
        if use_powershell:
            # PowerShell: block dangerous operators (substring match)
            blocked_ops = ['$(', '`', ';']
            # PowerShell: block dangerous cmdlets/commands (word-boundary regex)
            blocked_cmds = [
                r'\brm\b', r'\bRemove-Item\b', r'\bsudo\b', r'\bchmod\b',
                r'\bcurl\b', r'\bwget\b', r'\bInvoke-WebRequest\b', r'\biwr\b',
            ]
            safe_commands = {
                'echo', 'Write-Output', 'Get-ChildItem', 'ls', 'dir',
                'Get-Content', 'cat', 'pwd', 'Get-Location',
                'Get-Date', 'date', 'whoami', 'Get-Command', 'Write-Host',
                'Get-EnvironmentVariable', 'env',
            }
        else:
            blocked_ops = BASH_BLOCKED_OPERATORS
            blocked_cmds = BASH_BLOCKED_COMMANDS
            safe_commands = BASH_SAFE_COMMANDS

        # Check operators (plain substring — dangerous anywhere)
        for op in blocked_ops:
            if op in code:
                raise ValueError(f"代码包含不允许的操作符: {repr(op)}")

        # Check blocked commands (word boundary regex — no false positives)
        for pattern in blocked_cmds:
            if re.search(pattern, code):
                raise ValueError(f"代码包含不允许的命令: {pattern}")

        # Verify every line starts with an allowed command
        for line in code.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            first_word = stripped.split()[0]
            if first_word not in safe_commands:
                raise ValueError(f"不允许的命令: {first_word}")

    def execute(self, code: str) -> Dict:
        shell = self._find_shell()
        use_powershell = shell is None

        try:
            self._check_safety(code, use_powershell=use_powershell)
        except ValueError as e:
            return self._safety_result(str(e))

        if use_powershell:
            # Execute via PowerShell with encoded command
            try:
                import base64
                encoded = base64.b64encode(code.encode('utf-16le')).decode()
                result = subprocess.run(
                    ['powershell.exe', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', encoded],
                    capture_output=True, text=True, encoding='utf-8', errors='replace',
                    timeout=self.timeout,
                )
                output = self._truncate(result.stdout)
                error = self._truncate(result.stderr)
                return {
                    "success": result.returncode == 0,
                    "output": output,
                    "error": error,
                    "exit_code": result.returncode,
                }
            except subprocess.TimeoutExpired:
                return self._timeout_result()
            except Exception as e:
                return self._exception_result(e)
        else:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.sh', delete=False, encoding='utf-8',
            ) as f:
                f.write(code)
                temp_file = f.name
            return self._run_subprocess([shell, temp_file], temp_file)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class CodeExecutorRegistry:
    """Routes code to the appropriate language executor."""

    def __init__(self):
        self._executors = {
            "python": PythonExecutor(),
            "javascript": JavaScriptExecutor(),
            "typescript": TypeScriptExecutor(),
            "bash": BashExecutor(),
        }

    def execute(self, code: str, language: str) -> Dict:
        executor = self._executors.get(language)
        if not executor:
            return {
                "success": False,
                "output": "",
                "error": f"不支持的语言: {language}",
                "exit_code": -1,
            }
        return executor.execute(code)

    def supported_languages(self) -> list:
        return list(self._executors.keys())


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_executor = None


def get_executor() -> CodeExecutorRegistry:
    """获取代码执行器实例（单例）"""
    global _executor
    if _executor is None:
        _executor = CodeExecutorRegistry()
    return _executor
