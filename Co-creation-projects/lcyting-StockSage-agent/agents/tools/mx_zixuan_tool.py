"""
智能股票分析助手 — HelloAgents 自选股工具封装

将东方财富 mx-zixuan Skill 封装为符合 HelloAgents 标准 Tool 接口的工具类。
Agent可通过此工具调用查询/添加/删除自选股操作。
"""

import sys
from pathlib import Path

# 将HelloAgents框架和skills路径加入sys.path
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_HELLO_PATH = _PROJECT_ROOT / "HelloAgents Optimized"
_SKILLS_PATH = _PROJECT_ROOT / "skills" / "自选股管理" / "mx-zixuan"

for p in [_HELLO_PATH, _SKILLS_PATH]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from hello_agents.tools import Tool, ToolParameter


class MXZixuanTool(Tool):
    """自选股管理工具 — 封装东方财富妙想mx-zixuan Skill

    支持查询、添加、删除东方财富自选股列表。

    使用示例:
        tool = MXZixuanTool(api_key="your_mx_apikey")
        result = tool.run({"action": "query"})
        result = tool.run({"action": "add", "query": "把贵州茅台加入自选"})
        result = tool.run({"action": "delete", "query": "把贵州茅台从自选删除"})
    """

    def __init__(self, api_key: str = None):
        super().__init__(
            name="mx_zixuan",
            description=(
                "东方财富自选股管理工具。支持查询我的自选股列表、"
                "添加股票到自选股列表、从自选股列表删除股票。"
                "操作类型：query（查询自选股列表）、add（添加自选股）、delete（删除自选股）。"
                "添加/删除时需提供自然语言描述，如'把贵州茅台加入自选'、'把600519从自选删除'。"
            ),
        )

        # 获取API密钥：优先参数 > 环境变量
        import os
        self.api_key = api_key or os.getenv("MX_APIKEY", "")

        # 延迟导入mx_zixuan模块
        self._mx_module = None

    def _get_mx_module(self):
        """延迟导入mx_zixuan模块（避免初始化时的导入错误）"""
        if self._mx_module is None:
            import mx_zixuan as _mx_zixuan
            self._mx_module = _mx_zixuan
        return self._mx_module

    def get_parameters(self) -> list:
        return [
            ToolParameter(
                name="action",
                type="string",
                description=(
                    "操作类型：\n"
                    "- query: 查询所有自选股列表\n"
                    "- add: 添加股票到自选股\n"
                    "- delete: 从自选股删除股票"
                ),
                required=True,
            ),
            ToolParameter(
                name="query",
                type="string",
                description=(
                    "自然语言操作指令（add/delete时必需）。例如：\n"
                    "- 添加: '把贵州茅台加入自选', '添加600519到自选'\n"
                    "- 删除: '把贵州茅台从自选删除', '删除600519'"
                ),
                required=False,
            ),
        ]

    def run(self, parameters: dict) -> str:
        """执行自选股操作

        Args:
            parameters: {"action": "query|add|delete", "query": "自然语言指令"}

        Returns:
            格式化的操作结果文本
        """
        action = parameters.get("action", "").lower()
        query = parameters.get("query", "")

        if not self.api_key:
            return "错误：MX_APIKEY 未配置，无法操作自选股。请设置环境变量 MX_APIKEY"

        if action not in ("query", "add", "delete"):
            return f"错误：不支持的操作类型 '{action}'，请使用 query / add / delete"

        if action in ("add", "delete") and not query:
            return f"错误：{action} 操作需要提供 query 参数描述操作内容"

        try:
            mx = self._get_mx_module()

            if action == "query":
                result = mx.query_self_select(self.api_key)
                return self._format_query_result(result)
            elif action == "add":
                result = mx.manage_self_select(self.api_key, query)
                return self._format_manage_result(result, action)
            elif action == "delete":
                result = mx.manage_self_select(self.api_key, query)
                return self._format_manage_result(result, action)

        except Exception as e:
            return f"自选股操作异常: {str(e)}"

    def _format_query_result(self, result: dict) -> str:
        """格式化查询结果"""
        lines = ["## 我的自选股列表"]

        # 检查API状态
        status = result.get("status", -1)
        code = result.get("code", -1)
        if status != 0 and code != 0:
            msg = result.get("message", "未知错误")
            lines.append(f"查询失败: {msg}")
            return "\n".join(lines)

        # 解析查询结果
        data = result.get("data", {})
        all_results = data.get("allResults", {})
        result_data = all_results.get("result", {})
        columns = result_data.get("columns", [])
        data_list = result_data.get("dataList", [])

        if not data_list:
            lines.append("\n自选股列表为空")
            return "\n".join(lines)

        lines.append(f"\n共 {len(data_list)} 只自选股：\n")

        # 提取关键字段并格式化
        display_fields = [
            ("SECURITY_CODE", "代码"),
            ("SECURITY_SHORT_NAME", "名称"),
            ("NEWEST_PRICE", "最新价"),
            ("CHG", "涨跌幅(%)"),
            ("PCHG", "涨跌额"),
        ]

        # 表头
        header = " | ".join([f"{name:^8}" for _, name in display_fields])
        lines.append(f"| {header} |")
        lines.append(f"|{'|'.join([':---:'] * len(display_fields))}|")

        # 数据行
        for stock in data_list[:20]:  # 最多显示20只
            values = []
            for key, _ in display_fields:
                val = str(stock.get(key, "-"))
                if key == "CHG" and val != "-":
                    try:
                        chg = float(val)
                        if chg > 0:
                            val = f"+{val}"
                    except (ValueError, TypeError):
                        pass
                values.append(val)
            lines.append(f"| {' | '.join(values)} |")

        if len(data_list) > 20:
            lines.append(f"\n*(仅显示前20只，共{len(data_list)}只)*")

        return "\n".join(lines)

    def _format_manage_result(self, result: dict, action: str) -> str:
        """格式化操作结果"""
        action_cn = {"add": "添加", "delete": "删除"}.get(action, action)

        status = result.get("status", -1)
        code = result.get("code", -1)
        if status != 0 and code != 0:
            msg = result.get("message", "未知错误")
            return f"自选股{action_cn}失败: {msg}"

        msg = result.get("message", "操作完成")
        return f"✅ 自选股{action_cn}成功: {msg}"
