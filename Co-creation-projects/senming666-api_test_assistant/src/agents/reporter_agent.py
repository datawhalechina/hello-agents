"""
报告Agent - 负责生成测试报告

这是流水线的最后一环，把验证结论渲染成 HTML 报告。
"""

from jinja2 import Template


# HTML 报告模板（用 jinja2 语法写占位符）
HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>API 测试报告</title>
    <style>
        body { font-family: sans-serif; margin: 40px; }
        h1 { color: #333; }
        .summary { background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .summary span { margin-right: 30px; font-size: 18px; }
        .passed { color: green; font-weight: bold; }
        .failed { color: red; font-weight: bold; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #4CAF50; color: white; }
    </style>
</head>
<body>
    <h1>API 测试报告</h1>

    <div class="summary">
        <span>总用例数：<b>{{ summary.total }}</b></span>
        <span class="passed">通过：{{ summary.passed }}</span>
        <span class="failed">失败：{{ summary.failed }}</span>
        <span>通过率：{{ summary.pass_rate }}%</span>
    </div>

    <table>
        <tr>
            <th>用例名称</th>
            <th>类型</th>
            <th>状态码</th>
            <th>耗时(秒)</th>
            <th>结果</th>
            <th>错误信息</th>
        </tr>
        {% for r in results %}
        <tr>
            <td>{{ r.case.name }}</td>
            <td>{{ r.case.case_type }}</td>
            <td>{{ r.result.status_code | default('-', true) }}</td>
            <td>{{ r.result.elapsed | default('-', true) }}</td>
            <td class="{{ 'passed' if r.passed else 'failed' }}">
                {{ '通过' if r.passed else '失败' }}
            </td>
            <td>{{ r.errors }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""


class ReporterAgent:
    """生成测试报告"""

    def summarize(self, validated_results):
        """统计测试结果

        Args:
            validated_results: ValidatorAgent 返回的验证结果列表

        Returns:
            统计信息字典：总数、通过、失败、通过率
        """
        total = len(validated_results)
        passed = sum(1 for r in validated_results if r["passed"])
        failed = total - passed
        # 通过率 = 通过数 / 总数 * 100%，保留 1 位小数
        pass_rate = round(passed / total * 100, 1) if total > 0 else 0

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
        }

    def generate_html(self, validated_results):
        """生成 HTML 报告

        Args:
            validated_results: 验证结果列表

        Returns:
            HTML 字符串
        """
        summary = self.summarize(validated_results)
        template = Template(HTML_TEMPLATE)
        return template.render(summary=summary, results=v alidated_results)

    def generate_markdown(self, validated_results):
        """生成 Markdown 报告

        Args:
            validated_results: 验证结果列表

        Returns:
            Markdown 字符串
        """
        summary = self.summarize(validated_results)

        lines = []
        lines.append("# API 测试报告\n")
        lines.append("## 汇总\n")
        lines.append(f"- 总用例数：**{summary['total']}**")
        lines.append(f"- 通过：**{summary['passed']}**")
        lines.append(f"- 失败：**{summary['failed']}**")
        lines.append(f"- 通过率：**{summary['pass_rate']}%**\n")
        lines.append("## 用例明细\n")
        lines.append("| 用例名称 | 类型 | 状态码 | 耗时(秒) | 结果 | 错误信息 |")
        lines.append("|---|---|---|---|---|---|")

        for r in validated_results:
            case = r["case"]
            result = r["result"]
            name = case.get("name", "-")
            case_type = case.get("case_type", "-")
            # 请求失败时 status_code / elapsed 是 None，表格里应显示 "-" 而不是 "None"
            status_code = result.get("status_code")
            status_code = "-" if status_code is None else status_code
            elapsed = result.get("elapsed")
            elapsed = "-" if elapsed is None else elapsed
            mark = "✅ 通过" if r["passed"] else "❌ 失败"
            errors = "; ".join(r["errors"]) if r["errors"] else "-"
            # Markdown 表格里出现 | 或换行会破坏表格结构，做简单转义
            errors = errors.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {name} | {case_type} | {status_code} | {elapsed} | {mark} | {errors} |")

        return "\n".join(lines)
