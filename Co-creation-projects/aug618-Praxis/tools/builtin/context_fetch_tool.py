"""上下文获取工具 - 让模型按需获取扩展上下文

设计理念（借鉴 Claude Code）：
- 保底上下文由 ContextBuilder 自动注入（系统提示、对话历史、上次工具摘要）
- 扩展上下文通过此工具按需获取（notes、memory、files、tests）
- 模型自行决定何时需要更多证据，避免盲目全局扫描
"""

from typing import Dict, Any, List, Optional
import subprocess
import os

from ..base import Tool, ToolParameter


class ContextFetchTool(Tool):
    """上下文获取工具
    
    让模型按需获取扩展上下文，支持多种数据源：
    - notes: 检索笔记（blocker、insight、decision 等）
    - memory: 检索情景记忆（之前的对话/经验）
    - files: 搜索代码文件（rg + 上下文行）
    - tests: 获取最近测试失败信息
    
    使用场景：
    - 模型发现证据不足时主动调用
    - 提到类名/函数名/错误栈时获取相关代码
    - 询问"之前做了什么"时检索记忆
    """
    
    def __init__(
        self,
        workspace: str,
        note_tool: Optional[Any] = None,
        memory_tool: Optional[Any] = None,
        max_tokens_per_source: int = 800,
        context_lines: int = 5,  # 命中行前后各取 k 行
    ):
        super().__init__(
            name="context_fetch",
            description=(
                "获取扩展上下文。当保底上下文不足以回答问题时调用。"
                "可指定数据源：notes(笔记)、memory(记忆)、files(代码文件)、tests(测试结果)。"
                "返回结构化的证据块。"
            ),
        )
        self.workspace = workspace
        self.note_tool = note_tool
        self.memory_tool = memory_tool
        self.max_tokens_per_source = max_tokens_per_source
        self.context_lines = context_lines
        
        # 缓存最近的查询结果，避免重复查询
        self._cache: Dict[str, str] = {}
        self._cache_max_size = 20
    
    def get_parameters(self) -> List[ToolParameter]:
        """遵循基类接口返回参数定义"""
        return [
            ToolParameter(
                name="sources",
                type="array",
                description="要查询的数据源列表，可选: notes, memory, files, tests",
                required=True,
            ),
            ToolParameter(
                name="query",
                type="string",
                description="搜索关键词/符号名/错误栈片段",
                required=True,
            ),
            ToolParameter(
                name="paths",
                type="string",
                description="限定文件搜索范围的 glob 模式，如 'src/**/*.py'",
                required=False,
            ),
            ToolParameter(
                name="budget_tokens",
                type="integer",
                description="单个数据源的 token 上限，默认 800",
                required=False,
            ),
        ]
    
    def run(self, parameters: Dict[str, Any]) -> str:
        """执行上下文获取"""
        sources = parameters.get("sources", [])
        query = parameters.get("query", "")
        paths = parameters.get("paths", "")
        budget = parameters.get("budget_tokens", self.max_tokens_per_source)
        
        if not sources or not query:
            return "错误：必须指定 sources 和 query 参数"
        
        # 检查缓存
        cache_key = f"{','.join(sorted(sources))}|{query}|{paths}"
        if cache_key in self._cache:
            return f"[缓存命中]\n{self._cache[cache_key]}"
        
        results: List[str] = []
        
        for source in sources:
            if source == "notes":
                result = self._fetch_notes(query, budget)
            elif source == "memory":
                result = self._fetch_memory(query, budget)
            elif source == "files":
                result = self._fetch_files(query, paths, budget)
            elif source == "tests":
                result = self._fetch_tests(query, budget)
            else:
                result = f"[{source}] 未知数据源"
            
            if result:
                results.append(result)
        
        output = "\n\n".join(results) if results else "未找到相关上下文"
        
        # 更新缓存
        if len(self._cache) >= self._cache_max_size:
            # 简单 LRU：删除最早的
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[cache_key] = output
        
        return output
    
    def _fetch_notes(self, query: str, budget: int) -> str:
        """从笔记中检索"""
        if not self.note_tool:
            return "[notes] 笔记工具未配置"
        
        try:
            # 搜索相关笔记
            result = self.note_tool.run({
                "action": "search",
                "query": query,
                "limit": 5,
            })
            if result and "未找到" not in result:
                return f"[notes] 相关笔记:\n{self._truncate(result, budget)}"
            return "[notes] 未找到相关笔记"
        except Exception as e:
            return f"[notes] 检索失败: {e}"
    
    def _fetch_memory(self, query: str, budget: int) -> str:
        """从记忆中检索"""
        if not self.memory_tool:
            return "[memory] 记忆工具未配置"
        
        try:
            result = self.memory_tool.run({
                "action": "search",
                "query": query,
                "memory_types": getattr(self.memory_tool, "memory_types", ["episodic"]),
                "limit": 5,
                "min_importance": 0.0,
            })
            if result and "未找到" not in result:
                return f"[memory] 相关记忆:\n{self._truncate(result, budget)}"
            return "[memory] 未找到相关记忆"
        except Exception as e:
            return f"[memory] 检索失败: {e}"
    
    def _fetch_files(self, query: str, paths: str, budget: int) -> str:
        """从代码文件中检索"""
        try:
            # 使用 ripgrep 搜索
            cmd = ["rg", "--color=never", "-n", "-C", str(self.context_lines)]
            
            if paths:
                cmd.extend(["-g", paths])
            
            cmd.append(query)
            cmd.append(self.workspace)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.workspace,
            )
            
            output = result.stdout.strip()
            if output:
                # 结构化输出
                lines = output.split("\n")
                # 按文件分组
                grouped = self._group_by_file(lines)
                formatted = self._format_file_results(grouped, budget)
                return f"[files] 代码搜索结果:\n{formatted}"
            return f"[files] 未找到匹配 '{query}' 的内容"
        except subprocess.TimeoutExpired:
            return "[files] 搜索超时"
        except FileNotFoundError:
            # ripgrep 未安装，降级到 grep
            return self._fetch_files_fallback(query, paths, budget)
        except Exception as e:
            return f"[files] 搜索失败: {e}"
    
    def _fetch_files_fallback(self, query: str, paths: str, budget: int) -> str:
        """ripgrep 不可用时的降级方案"""
        try:
            cmd = f"grep -rn '{query}' {self.workspace}"
            if paths:
                cmd = f"find {self.workspace} -path '{paths}' -type f | xargs grep -n '{query}'"
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout.strip()
            if output:
                return f"[files] grep 结果:\n{self._truncate(output, budget)}"
            return f"[files] 未找到匹配 '{query}' 的内容"
        except Exception as e:
            return f"[files] grep 搜索失败: {e}"
    
    def _fetch_tests(self, query: str, budget: int) -> str:
        """获取测试相关信息"""
        # 查找最近的测试输出/日志
        test_patterns = [
            ".pytest_cache/v/cache/lastfailed",
            "test-results.xml",
            ".coverage",
        ]
        
        results = []
        for pattern in test_patterns:
            path = os.path.join(self.workspace, pattern)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    if query.lower() in content.lower():
                        results.append(f"[tests] {pattern}:\n{self._truncate(content, budget // 2)}")
                except Exception:
                    pass
        
        if results:
            return "\n".join(results)
        return "[tests] 未找到相关测试信息"
    
    def _group_by_file(self, lines: List[str]) -> Dict[str, List[str]]:
        """按文件分组 ripgrep 输出"""
        grouped: Dict[str, List[str]] = {}
        current_file = None
        
        for line in lines:
            if ":" in line:
                # 格式: file:line:content 或 file-line-content
                parts = line.split(":", 2) if ":" in line else line.split("-", 2)
                if len(parts) >= 2:
                    file_path = parts[0]
                    if file_path != current_file:
                        current_file = file_path
                        grouped[current_file] = []
                    grouped[current_file].append(line)
            elif current_file:
                grouped[current_file].append(line)
        
        return grouped
    
    def _format_file_results(self, grouped: Dict[str, List[str]], budget: int) -> str:
        """格式化文件搜索结果"""
        output_parts = []
        tokens_used = 0
        tokens_per_file = budget // max(len(grouped), 1)
        
        for file_path, lines in grouped.items():
            content = "\n".join(lines)
            truncated = self._truncate(content, tokens_per_file)
            
            # 相对路径
            rel_path = file_path.replace(self.workspace, "").lstrip("/")
            output_parts.append(f"--- {rel_path} ---\n{truncated}")
            
            tokens_used += len(truncated) // 4  # 粗略估算
            if tokens_used >= budget:
                output_parts.append("...(更多结果已截断)...")
                break
        
        return "\n\n".join(output_parts)
    
    def _truncate(self, text: str, max_tokens: int) -> str:
        """截断文本到指定 token 上限"""
        # 粗略估算：1 token ≈ 4 字符（英文），2 字符（中文）
        max_chars = max_tokens * 3
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n...(已截断)..."
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
