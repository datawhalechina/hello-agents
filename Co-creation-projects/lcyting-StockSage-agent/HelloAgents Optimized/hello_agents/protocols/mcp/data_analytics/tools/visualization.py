"""数据可视化工具

提供图表生成功能，支持多种图表类型。
"""

from typing import Dict, Any, List, Optional
import base64
import json


SUPPORTED_CHART_TYPES = ["bar", "line", "pie", "scatter", "area"]


def _validate_chart_data(
    data: List[Dict[str, Any]], x_axis: str, y_axis: str
) -> Optional[str]:
    """验证图表数据"""
    if not data:
        return "Data cannot be empty"
    if not x_axis:
        return "x_axis is required"
    if not y_axis:
        return "y_axis is required"
    if x_axis not in data[0]:
        return f"x_axis '{x_axis}' not found in data"
    if y_axis not in data[0]:
        return f"y_axis '{y_axis}' not found in data"
    return None


def _generate_ascii_chart(
    data: List[Dict[str, Any]], x_axis: str, y_axis: str, chart_type: str
) -> str:
    """生成 ASCII 艺术图表"""
    if not data:
        return "No data to display"

    values = [float(row.get(y_axis, 0)) for row in data]
    labels = [str(row.get(x_axis, "")) for row in data]
    max_val = max(values) if values else 1
    max_label_len = max(len(str(label)) for label in labels) if labels else 10

    chart_lines = []
    chart_lines.append(f"\n{'=' * (max_label_len + 50)}")
    chart_lines.append(f"Chart: {chart_type.upper()}")
    chart_lines.append(f"{'=' * (max_label_len + 50)}\n")

    if chart_type == "bar":
        for label, value in zip(labels, values):
            bar_length = int((value / max_val) * 40)
            chart_lines.append(
                f"{label:>{max_label_len}} | {'█' * bar_length} {value:.2f}"
            )
    elif chart_type == "line":
        for i, (label, value) in enumerate(zip(labels, values)):
            dot_pos = int((value / max_val) * 40)
            chart_lines.append(
                f"{label:>{max_label_len}} | {' ' * dot_pos}● {value:.2f}"
            )
    elif chart_type == "pie":
        total = sum(values)
        for label, value in zip(labels, values):
            percentage = (value / total * 100) if total > 0 else 0
            chart_lines.append(f"{label:>{max_label_len}} | {percentage:.1f}%")
    elif chart_type == "scatter":
        for label, value in zip(labels, values):
            dot_pos = int((value / max_val) * 40)
            chart_lines.append(
                f"{' ' * max_label_len} | {' ' * dot_pos}● ({label}, {value:.2f})"
            )

    chart_lines.append(f"\n{'─' * (max_label_len + 50)}")
    return "\n".join(chart_lines)


def _generate_svg_chart(
    data: List[Dict[str, Any]], x_axis: str, y_axis: str, chart_type: str, title: str
) -> str:
    """生成 SVG 格式图表"""
    if not data:
        return ""

    values = [float(row.get(y_axis, 0)) for row in data]
    labels = [str(row.get(x_axis, "")) for row in data]
    max_val = max(values) if values else 1

    width, height = 600, 300
    padding = 50
    chart_width = width - 2 * padding
    chart_height = height - 2 * padding

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#f8f9fa"/>',
        f'<text x="{width // 2}" y="30" text-anchor="middle" font-size="18" font-weight="bold">{title}</text>',
        f'<g transform="translate({padding}, {padding})">',
    ]

    if chart_type == "bar":
        bar_width = chart_width / len(data) * 0.7
        gap = chart_width / len(data) * 0.3
        for i, (label, value) in enumerate(zip(labels, values)):
            bar_height = (value / max_val) * chart_height
            x = i * (bar_width + gap) + gap / 2
            y = chart_height - bar_height
            svg_parts.append(
                f'  <rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" '
                f'fill="#4a90d9" stroke="#2c5282" stroke-width="1"/>'
            )
            svg_parts.append(
                f'  <text x="{x + bar_width / 2}" y="{chart_height + 15}" '
                f'text-anchor="middle" font-size="10">{label}</text>'
            )
            svg_parts.append(
                f'  <text x="{x + bar_width / 2}" y="{y - 5}" '
                f'text-anchor="middle" font-size="9">{value:.0f}</text>'
            )
    elif chart_type == "line":
        points = []
        for i, value in enumerate(values):
            x = i * (chart_width / (len(data) - 1 if len(data) > 1 else 1))
            y = chart_height - (value / max_val) * chart_height
            points.append(f"{x},{y}")

        svg_parts.append(
            f'  <polyline points="{" ".join(points)}" fill="none" stroke="#4a90d9" stroke-width="2"/>'
        )
        for i, (label, value) in enumerate(zip(labels, values)):
            x = i * (chart_width / (len(data) - 1 if len(data) > 1 else 1))
            y = chart_height - (value / max_val) * chart_height
            svg_parts.append(f'  <circle cx="{x}" cy="{y}" r="4" fill="#4a90d9"/>')
            svg_parts.append(
                f'  <text x="{x}" y="{chart_height + 15}" text-anchor="middle" font-size="10">{label}</text>'
            )

    svg_parts.append("</g>")
    svg_parts.append(
        f'<text x="{padding}" y="{height - 10}" font-size="11" fill="#666">{x_axis}</text>'
    )
    svg_parts.append(
        f'<text x="15" y="{height // 2}" font-size="11" fill="#666" transform="rotate(-90, 15, {height // 2})">{y_axis}</text>'
    )
    svg_parts.append("</svg>")

    return "\n".join(svg_parts)


def visualize_data(
    data: List[Dict[str, Any]],
    chart_type: str,
    title: str,
    x_axis: str,
    y_axis: str,
    output_format: str = "base64",
) -> Dict[str, Any]:
    """生成数据可视化图表

    Args:
        data: 数据列表，每个元素是一个字典
        chart_type: 图表类型，支持 bar/line/pie/scatter/area
        title: 图表标题
        x_axis: X 轴字段名
        y_axis: Y 轴字段名
        output_format: 输出格式，支持 base64/svg/markdown/json/ascii

    Returns:
        包含图表数据的字典
    """
    error = _validate_chart_data(data, x_axis, y_axis)
    if error:
        return {"success": False, "error": error}

    chart_type = chart_type.lower()
    if chart_type not in SUPPORTED_CHART_TYPES:
        return {
            "success": False,
            "error": f"Unsupported chart type: {chart_type}. Supported: {SUPPORTED_CHART_TYPES}",
        }

    try:
        if output_format == "base64":
            svg_content = _generate_svg_chart(data, x_axis, y_axis, chart_type, title)
            image_data = base64.b64encode(svg_content.encode()).decode()
            result_format = "svg_base64"
        elif output_format == "svg":
            image_data = _generate_svg_chart(data, x_axis, y_axis, chart_type, title)
            result_format = "svg"
        elif output_format == "markdown":
            image_data = _generate_ascii_chart(data, x_axis, y_axis, chart_type)
            result_format = "ascii_markdown"
        elif output_format == "json":
            image_data = json.dumps(
                {
                    "chart_type": chart_type,
                    "title": title,
                    "x_axis": x_axis,
                    "y_axis": y_axis,
                    "data": data,
                    "summary": {
                        "total_rows": len(data),
                        "max_value": max(float(row.get(y_axis, 0)) for row in data),
                        "min_value": min(float(row.get(y_axis, 0)) for row in data),
                        "avg_value": sum(float(row.get(y_axis, 0)) for row in data)
                        / len(data),
                    },
                },
                indent=2,
            )
            result_format = "json"
        elif output_format == "ascii":
            image_data = _generate_ascii_chart(data, x_axis, y_axis, chart_type)
            result_format = "ascii"
        else:
            return {
                "success": False,
                "error": f"Unsupported output format: {output_format}",
            }

        return {
            "success": True,
            "chart_type": chart_type,
            "title": title,
            "image_data": image_data,
            "format": result_format,
            "x_axis": x_axis,
            "y_axis": y_axis,
            "metadata": {
                "data_points": len(data),
                "x_labels": [str(row.get(x_axis, "")) for row in data],
                "y_values": [float(row.get(y_axis, 0)) for row in data],
            },
        }
    except Exception as e:
        return {"success": False, "error": f"Visualization error: {str(e)}"}


def visualize_summary(
    data: List[Dict[str, Any]], title: str = "Data Summary"
) -> Dict[str, Any]:
    """生成数据摘要可视化

    Args:
        data: 数据列表
        title: 摘要标题

    Returns:
        数据摘要字典
    """
    if not data:
        return {"success": False, "error": "Empty data"}

    numeric_fields = []
    for key, value in data[0].items():
        if isinstance(value, (int, float)):
            numeric_fields.append(key)

    summary = {
        "title": title,
        "total_records": len(data),
        "fields": list(data[0].keys()),
        "numeric_fields": numeric_fields,
    }

    for field in numeric_fields:
        values = [float(row.get(field, 0)) for row in data]
        summary[field] = {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "sum": sum(values),
        }

    return {"success": True, "summary": summary}
