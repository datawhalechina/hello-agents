"""记忆工具 - 支持记忆检索和更新"""

from typing import List, Dict, Any, Optional
import re

from hello_agents.tools import Tool, ToolParameter, ToolResponse, tool_action


class MemoryTool(Tool):
    """记忆管理工具

    可展开为多个子工具：
    - memory_search: 搜索记忆（返回带行号的上下文）
    - memory_get: 读取特定记忆文件或行范围
    - memory_add: 添加每日记忆
    - memory_update_longterm: 更新长期记忆
    - memory_list: 列出所有记忆文件
    """

    def __init__(self, workspace_manager):
        """初始化记忆工具

        Args:
            workspace_manager: 工作空间管理器实例
        """
        super().__init__(
            name="memory",
            description="记忆管理工具，支持搜索、读取、添加和更新记忆",
            expandable=True
        )
        self.workspace = workspace_manager

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """默认执行：搜索记忆"""
        keyword = parameters.get("keyword", "")
        return self._search_memory(keyword)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="keyword",
                type="string",
                description="搜索关键词",
                required=True
            )
        ]

    def _search_memory(self, keyword: str, context_lines: int = 3) -> ToolResponse:
        """搜索记忆（增强版，返回带行号的上下文）"""
        if not keyword:
            return ToolResponse.error(
                code="INVALID_INPUT",
                message="请提供搜索关键词"
            )

        # 使用增强搜索
        results = self.workspace.search_memory_enhanced(
            keyword,
            context_lines=context_lines
        )

        if not results:
            return ToolResponse.success(
                text=f"未找到与 '{keyword}' 相关的记忆",
                data={"results": [], "keyword": keyword}
            )

        # 格式化结果
        formatted_parts = []
        total_matches = 0

        for r in results:
            source = r["source"]
            matches = r["matches"]
            total_matches += len(matches)

            for m in matches:
                start = m["start_line"]
                end = m["end_line"]
                content = m["content"]
                line_range = f"行 {start}" if start == end else f"行 {start}-{end}"
                formatted_parts.append(
                    f"**{source}** ({line_range}):\n```\n{content}\n```"
                )

        return ToolResponse.success(
            text=f"找到 {total_matches} 处匹配 '{keyword}':\n\n" + "\n\n".join(formatted_parts),
            data={"results": results, "count": total_matches, "keyword": keyword}
        )

    @tool_action("memory_search", "搜索历史记忆")
    def _search(self, keyword: str, context_lines: int = 3) -> str:
        """搜索记忆

        Args:
            keyword: 搜索关键词
            context_lines: 上下文行数，默认 3
        """
        response = self._search_memory(keyword, context_lines)
        return response.text

    @tool_action("memory_get", "读取特定记忆文件或行范围")
    def _get_memory(
        self,
        filename: str = None,
        start_line: int = None,
        end_line: int = None,
        lines: str = None,
    ) -> str:
        """读取记忆文件内容

        Args:
            filename: 文件名（MEMORY.md 或 YYYY-MM-DD.md），默认为今天的日记
            start_line: 起始行号（从 1 开始）
            end_line: 结束行号
            lines: 行范围字符串，如 "10-20" 或 "15"
        """
        from datetime import datetime

        # 解析 lines 参数
        if lines:
            match = re.match(r"(\d+)(?:\s*-\s*(\d+))?", lines)
            if match:
                start_line = int(match.group(1))
                if match.group(2):
                    end_line = int(match.group(2))

        # 默认文件名
        if not filename:
            filename = datetime.now().strftime("%Y-%m-%d.md")

        # 确保文件名以 .md 结尾
        if not filename.endswith(".md"):
            filename += ".md"

        # 读取文件
        content = self.workspace.read_memory_lines(filename, start_line, end_line)

        if content is None:
            available = self._list_memory_files_brief()
            return f"文件 '{filename}' 不存在。可用文件:\n{available}"

        if not content:
            return f"文件 '{filename}' 为空"

        display_name = filename
        if start_line or end_line:
            range_str = f"行 {start_line or 1}"
            if end_line and end_line != start_line:
                range_str += f"-{end_line}"
            display_name += f" ({range_str})"

        return f"**{display_name}**:\n```\n{content}\n```"

    @tool_action("memory_add", "添加内容到今日记忆")
    def _add_daily(self, content: str, category: str = None) -> str:
        """添加每日记忆

        Args:
            content: 记忆内容
            category: 分类标签（preference/decision/entity/fact），可选
        """
        if category:
            # 使用带分类标签的存储
            self.workspace.append_classified_memory(content, category)
            return f"已添加到今日记忆 [{category}]: {content[:50]}..."
        else:
            # 使用原有方法
            self.workspace.append_to_daily_memory(content)
            return f"已添加到今日记忆: {content[:50]}..."

    @tool_action("memory_update_longterm", "更新长期记忆")
    def _update_longterm(self, content: str) -> str:
        """更新长期记忆

        Args:
            content: 要添加到长期记忆的内容
        """
        current = self.workspace.load_config("MEMORY") or ""
        updated = current + f"\n\n## 新增\n\n{content}\n"
        self.workspace.save_config("MEMORY", updated)
        return "已更新长期记忆"

    @tool_action("memory_list", "列出所有记忆文件")
    def _list(self) -> str:
        """列出所有记忆文件"""
        files = self.workspace.list_memory_files()

        if not files:
            return "暂无记忆文件"

        lines = ["# 记忆文件列表\n"]

        # 按类型分组
        longterm = [f for f in files if f["type"] == "longterm"]
        daily = [f for f in files if f["type"] == "daily"]

        if longterm:
            lines.append("## 长期记忆")
            for f in longterm:
                size_kb = f["size"] / 1024
                lines.append(f"- **{f['name']}** ({size_kb:.1f} KB)")

        if daily:
            lines.append("\n## 每日记忆")
            for f in daily:
                size_kb = f["size"] / 1024
                lines.append(f"- **{f['name']}** ({size_kb:.1f} KB)")

        return "\n".join(lines)

    @tool_action("memory_cleanup", "清理过期的每日记忆")
    def _cleanup(self, days: int = 30) -> str:
        """清理过期记忆

        Args:
            days: 保留天数，超过此天数将被清理，默认 30 天
        """
        deleted = self.workspace.cleanup_old_memories(days)

        if not deleted:
            return f"没有需要清理的记忆（保留最近 {days} 天）"

        return f"已清理 {len(deleted)} 个过期记忆文件:\n" + "\n".join(f"- {f}" for f in deleted)

    def _list_memory_files_brief(self) -> str:
        """简要列出记忆文件"""
        files = self.workspace.list_memory_files()
        if not files:
            return "无"
        return "\n".join(f"- {f['name']}" for f in files)
