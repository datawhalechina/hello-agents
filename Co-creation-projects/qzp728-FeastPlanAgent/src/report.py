"""Markdown rendering for a transparent banquet plan."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .models import BanquetRequest


def render_markdown(
    request: BanquetRequest,
    venues: list[dict[str, Any]],
    seating: list[dict[str, Any]],
    etiquette: dict[str, Any],
    menu_budget: dict[str, Any],
    menu_examples: list[dict[str, Any]],
    research: dict[str, Any],
    warnings: list[str],
) -> str:
    lines = [
        f"# {request.city}{request.banquet_type}策划方案",
        "",
        "> 本报告由 FeastPlanAgent 生成。座次与菜单属于建议方案；价格、档期和现场座位朝向必须向商家及主办方确认。",
        "",
        "## 1. 宴席概览",
        "",
        f"- 宴请类型：{request.banquet_type}",
        f"- 城市：{request.city}",
        f"- 日期：{request.date}",
        f"- 地域偏好：{request.regional_preference}",
        f"- 宾客人数：{request.guest_count} 人",
        f"- 桌数：{request.table_count} 桌，每桌最多 {request.seats_per_table} 人",
        f"- 总预算：¥{request.budget:,}",
        "",
        "## 2. 场地候选（公开套餐/目录参考）",
        "",
        "| 场地 | 地区 | 公开起价 | 公开容纳范围 | 菜单套数 | 联系方式 | 信息来源 |",
        "|---|---|---:|---|---:|---|---|",
    ]
    if venues:
        for venue in venues:
            price = venue.get("price_from") or "未检索到，需向宴会销售询价"
            source_name = venue.get("source", "待确认")
            source_url = venue.get("source_url", "")
            source = f"[{source_name}]({source_url})" if source_url else source_name
            menu_count = venue.get("menu_count") or "未公开"
            lines.append(
                f"| {venue.get('name', '未命名')} | {venue.get('district') or venue.get('address', '待确认')} | "
                f"{price} | {venue.get('capacity', '待商家确认')} | {menu_count} | "
                f"{venue.get('phone', '待确认')} | {source}（采集：{venue.get('source_date', '待确认')}） |"
            )
    else:
        lines.append("| 未找到候选 | 请配置高德 Key 或补充本地场地目录 | - | - | - |")

    lines.extend(["", "### 已审校的场地网络证据", ""])
    claims = research.get("venue_claims", [])
    if claims:
        for claim in claims:
            lines.append(
                f"- {claim.get('venue', '场地')}：{claim.get('evidence', '已由证据审校员保留')}"
                f"（[来源]({claim.get('source_url', '')})）"
            )
    else:
        lines.append("- 暂无经多智能体证据审校后可写入的场地报价、容量或套餐信息。")

    lines.extend(["", "## 3. 分桌与座次", ""])
    for table in seating:
        lines.extend([f"### {table['name']}（{len(table['guests'])}/{table['capacity']} 人）", "", "| 座位角色 | 宾客 | 身份 | 安排说明 |", "|---|---|---|---|"])
        for guest in table["guests"]:
            lines.append(f"| {guest['seat_role']} | {guest['name']} | {guest['guest_role']} | {guest['reason']} |")
        lines.append("")

    lines.extend(
        [
            "## 4. 地域礼俗适配", "",
            f"- 当前采用的参考地域：{etiquette['profile']}",
            f"- 座次侧重点：{etiquette['seating_focus']}",
            f"- 菜品与口味侧重点：{etiquette['menu_focus']}",
            f"- 酒水与待客侧重点：{etiquette['beverage_focus']}",
            "",
            "> 同一批宾客在不同地域办宴，核心宾客名单可以不变，但主陪角色、菜品结构、酒水准备和待客习惯可能不同。本报告按所选地域给出建议，并保留人工确认项。",
            "", "## 5. 同城酒店公开菜单样本（仅供比较）", "",
        ]
    )
    if menu_examples:
        for example in menu_examples:
            lines.extend([
                f"### {example.get('venue', '未命名场地')}｜{example.get('package_name', '公开套餐')}",
                "",
                f"- 公开价格：{example.get('price', '未公开')}",
                f"- 菜品举例：{'、'.join(example.get('dishes', []))}",
                f"- 说明：{example.get('notes', '最终以酒店书面套餐为准。')}",
                f"- [查看来源]({example.get('source_url', '')})（采集：{example.get('source_date', '待确认')}）",
                "",
            ])
    else:
        lines.extend(["- 未找到与当前城市、宴请类型相匹配的公开菜单样本。", ""])
    lines.extend(["## 6. 菜品与酒水建议", "", "### 每桌菜品结构", ""])
    lines.extend([f"- {item}" for item in menu_budget["每桌菜品结构"]])
    lines.extend(["", f"> {menu_budget['结构说明']}"])
    if menu_budget.get("菜单来源"):
        lines.extend(["", "### 本地菜单证据来源", ""])
        lines.extend([f"- [公开来源]({url})" for url in menu_budget["菜单来源"]])
    lines.extend(["", "### 主菜建议", ""])
    lines.extend([f"- {item}" for item in menu_budget["主菜建议"]])
    lines.extend(["", "### 忌口处理", ""])
    lines.extend([f"- {item}" for item in menu_budget["忌口处理"]])
    lines.extend(["", "### 酒水建议", ""])
    lines.extend([f"- {item}" for item in menu_budget["酒水建议"]])
    lines.extend(["", "## 7. 预算明细", "", "| 项目 | 预算 |", "|---|---:|"])
    for item, amount in menu_budget["预算"].items():
        lines.append(f"| {item} | ¥{amount:,} |")
    lines.extend(
        [
            f"| 合计 | ¥{sum(menu_budget['预算'].values()):,} |",
            "",
            f"- 每桌总预算上限：¥{menu_budget['每桌总预算上限']:,}",
            f"- 建议每桌用于餐饮和酒水：¥{menu_budget['每桌可用餐饮预算']:,}",
            "",
            "## 8. 信息状态与待确认事项",
            "",
            "- **公开目录/官网参考**：起价、桌数和菜单套数均保留来源页与采集日期；它们适合初筛，不能替代实时询价或书面合同。",
            "- **地图事实**：地图仅适合补充场地名称、地址、电话等公开字段；“地图未公开”不等于场地没有电话。",
            "- **必须询价的信息**：可订档期、最低桌数、宴会厅容量、套餐价、服务费、开瓶费和菜单份量，不能由地图 POI 推断。",
            "- **公开参考信息**：套餐起价仅在明确给出来源、采集日期和适用条件时才能用于比较。",
            f"- **本次多智能体审校状态**：{research.get('status', '未运行')}；审校不通过的内容不会写入场地报价或菜单建议。",
            "- **推导建议**：座次、菜单、酒水和预算由规则工具生成，并非唯一正确答案。",
            "- **必须确认**：档期、最终桌餐价格、服务费、开瓶费、菜单份量及主桌实际朝向。",
            "",
            "### 风险与提醒",
            "",
        ]
    )
    lines.extend([f"- {warning}" for warning in dict.fromkeys(warnings)])
    lines.extend(["", f"生成日期：{date.today().isoformat()}", ""])
    return "\n".join(lines)


def write_report(markdown: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path
