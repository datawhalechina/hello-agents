"""VulnAuditAgent 自定义审计工具集
规则引擎（AST）+ 污点追踪（source->sink）+ LLM 研判，三通道协同。
"""
import ast
import json
import os
import re
from typing import Any, Dict, List

from hello_agents.tools import Tool, ToolParameter


def _emit(tool, msg):
    hook = getattr(tool, "progress_hook", None)
    if callable(hook):
        hook(msg)


def _line_snippet(source: str, lineno: int) -> str:
    lines = source.splitlines()
    if 1 <= lineno <= len(lines):
        return lines[lineno - 1].strip()
    return ""


class RuleEngineTool(Tool):
    """规则引擎：基于 AST + 正则的危险模式扫描，输出带行号的候选漏洞清单。"""

    # (规则ID, 严重级, 说明)
    SINK_RULES = {
        "eval": ("VULN-EVAL", "严重", "eval() 执行动态代码"),
        "exec": ("VULN-EXEC", "严重", "exec() 执行动态代码"),
        "os.system": ("VULN-CMDI", "严重", "os.system() 直接调用 shell"),
        "os.popen": ("VULN-CMDI", "严重", "os.popen() 直接调用 shell"),
        "pickle.loads": ("VULN-DESER", "严重", "pickle.loads() 反序列化不可信数据可致 RCE"),
        "yaml.load": ("VULN-YAML", "高危", "yaml.load() 未指定 SafeLoader，可致任意对象构造"),
        "hashlib.md5": ("VULN-WEAKHASH", "中危", "MD5 已破解，不应用于密码哈希"),
        "hashlib.sha1": ("VULN-WEAKHASH", "中危", "SHA1 已破解，不应用于密码哈希"),
        "tempfile.mktemp": ("VULN-TMP", "中危", "mktemp() 存在竞态条件，应使用 mkstemp()"),
    }
    SECRET_RE = re.compile(
        r"(?i)^\s*(?:\w*(?:password|passwd|secret|api_?key|token|pwd)\w*)\s*=\s*[\"'][^\"']{5,}[\"']"
    )

    def __init__(self):
        super().__init__(
            name="rule_scan",
            description="规则引擎扫描：用内置规则库（危险函数/硬编码密钥/弱加密等）对 Python 源码做初步审计，返回带行号的候选漏洞 JSON 列表",
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [ToolParameter(name="file_path", type="string", description="待审计的 Python 文件相对路径，如 data/vulnerable_sample.py")]

    @staticmethod
    def _dotted(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = RuleEngineTool._dotted(node.value)
            return f"{base}.{node.attr}" if base else node.attr
        return ""

    def run(self, parameters: Dict[str, Any]) -> str:
        _emit(self, "规则引擎扫描中...")
        source = parameters.get("source_code", "")
        file_path = parameters.get("file_path", "").strip()
        if not source.strip() and file_path:
            if not os.path.isfile(file_path):
                return f"错误：文件不存在 {file_path}"
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
        if not source.strip():
            return "错误：请通过 file_path 指定待审计文件"
        findings = []
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return f"语法错误，无法解析：{e}"

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = self._dotted(node.func)
            if name in self.SINK_RULES:
                rid, sev, desc = self.SINK_RULES[name]
                findings.append({
                    "rule_id": rid, "severity": sev, "line": node.lineno,
                    "snippet": _line_snippet(source, node.lineno), "description": desc,
                })
            # subprocess.*(shell=True)
            if name in ("subprocess.call", "subprocess.run", "subprocess.Popen"):
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        findings.append({
                            "rule_id": "VULN-SHELLTRUE", "severity": "高危", "line": node.lineno,
                            "snippet": _line_snippet(source, node.lineno),
                            "description": "subprocess 使用 shell=True，存在命令注入风险",
                        })
            # requests.*(verify=False)
            if name.startswith("requests."):
                for kw in node.keywords:
                    if kw.arg == "verify" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                        findings.append({
                            "rule_id": "VULN-TLS", "severity": "高危", "line": node.lineno,
                            "snippet": _line_snippet(source, node.lineno),
                            "description": "requests 关闭 TLS 证书验证（verify=False），易受中间人攻击",
                        })
            # 弱随机数用于安全场景
            if name in ("random.randint", "random.random", "random.choice"):
                findings.append({
                    "rule_id": "VULN-WEAKRAND", "severity": "低危", "line": node.lineno,
                    "snippet": _line_snippet(source, node.lineno),
                    "description": "random 模块非密码学安全随机源，安全场景应使用 secrets 模块",
                })

        # 正则：硬编码密钥
        for i, line in enumerate(source.splitlines(), 1):
            if self.SECRET_RE.match(line):
                findings.append({
                    "rule_id": "VULN-SECRET", "severity": "严重", "line": i,
                    "snippet": line.strip(), "description": "硬编码敏感凭据（密码/密钥/Token 明文写入源码）",
                })

        findings.sort(key=lambda f: f["line"])
        _emit(self, f"规则扫描完成：{len(findings)} 条候选")
        return json.dumps({"total": len(findings), "findings": findings}, ensure_ascii=False, indent=2)


class TaintTrackTool(Tool):
    """污点追踪：跟踪 外部输入(source) -> 危险函数(sink) 的数据流链路。"""

    SOURCE_CALLS = {"input", "open"}
    SOURCE_ATTRS = ("request.args", "request.form", "request.data", "request.values",
                    "request.json", "request.get_json", "sys.argv", "os.environ", "os.getenv")
    SINKS = {"eval", "exec", "os.system", "os.popen", "pickle.loads", "yaml.load",
             "subprocess.call", "subprocess.run", "subprocess.Popen", "execute"}

    def __init__(self):
        super().__init__(
            name="taint_track",
            description="污点追踪：分析源码中外部输入（request/input/sys.argv 等）是否未经清洗流入危险函数（eval/os.system/SQL 执行等），输出 source->sink 链路",
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [ToolParameter(name="file_path", type="string", description="待分析的 Python 文件相对路径，如 data/vulnerable_sample.py")]

    def _is_source(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Call):
            name = RuleEngineTool._dotted(node.func)
            if name in self.SOURCE_CALLS:
                return True
            if any(name.startswith(s) for s in self.SOURCE_ATTRS):
                return True
        name = RuleEngineTool._dotted(node)
        return any(name.startswith(s) for s in self.SOURCE_ATTRS)

    def _expr_tainted(self, node: ast.AST, tainted: set) -> bool:
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id in tainted:
                return True
            if self._is_source(child):
                return True
        return False

    def run(self, parameters: Dict[str, Any]) -> str:
        _emit(self, "污点追踪分析中...")
        source = parameters.get("source_code", "")
        file_path = parameters.get("file_path", "").strip()
        if not source.strip() and file_path:
            if not os.path.isfile(file_path):
                return f"错误：文件不存在 {file_path}"
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
        if not source.strip():
            return "错误：请通过 file_path 指定待审计文件"
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return f"语法错误，无法解析：{e}"

        tainted: Dict[str, int] = {}   # 变量名 -> 被污染的行号
        chains = []
        for node in ast.walk(tree):
            # 赋值传播：x = <含污点表达式>
            if isinstance(node, ast.Assign):
                if self._expr_tainted(node.value, set(tainted)):
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            tainted[tgt.id] = node.lineno
            # 汇点检测
            if isinstance(node, ast.Call):
                name = RuleEngineTool._dotted(node.func)
                short = name.split(".")[-1]
                if name in self.SINKS or short in self.SINKS:
                    for arg in list(node.args) + [kw.value for kw in node.keywords]:
                        for sub in ast.walk(arg):
                            if isinstance(sub, ast.Name) and sub.id in tainted:
                                chains.append({
                                    "sink": name, "sink_line": node.lineno,
                                    "tainted_var": sub.id, "source_line": tainted[sub.id],
                                    "snippet": _line_snippet(source, node.lineno),
                                })
                                break
        _emit(self, f"污点追踪完成：{len(chains)} 条链路")
        return json.dumps({"total": len(chains), "chains": chains}, ensure_ascii=False, indent=2)


class LLMVerifyTool(Tool):
    """LLM 研判：对规则/污点命中的候选项做二次验证，过滤误报并给出修复建议。"""

    def __init__(self, llm):
        super().__init__(
            name="llm_verify",
            description="LLM 研判：输入一条候选漏洞（类型/行号/代码片段），由大模型判断真阳性/误报/存疑，给出风险等级、理由和修复建议",
        )
        self.llm = llm

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="finding_type", type="string", description="漏洞类型（规则ID或污点链描述）"),
            ToolParameter(name="code_snippet", type="string", description="命中行的代码片段"),
            ToolParameter(name="line_number", type="string", description="命中行号", required=False),
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        ftype = parameters.get("finding_type", "")
        snippet = parameters.get("code_snippet", "")
        line = parameters.get("line_number", "?")
        prompt = (
            "你是资深代码审计员。请研判以下候选漏洞是否为真阳性。\n"
            f"候选类型：{ftype}\n命中行号：{line}\n代码片段：{snippet}\n\n"
            "请严格按以下格式输出（不要输出其他内容）：\n"
            "研判: 真阳性/误报/存疑\n"
            "风险等级: 严重/高危/中危/低危\n"
            "理由: <一句话>\n"
            "修复建议: <一句话>"
        )
        try:
            return self.llm.invoke([{"role": "user", "content": prompt}])
        except Exception as e:
            return f"LLM 研判失败：{e}"
