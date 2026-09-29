"""Normalize a bounded subset of Figma's document format into a safe UI tree.

This is a deterministic design adapter, not a pixel-perfect Figma renderer. The
warnings and visible placeholders are part of its contract: unsupported artwork
must remain apparent to someone reviewing the generated page.
"""

from __future__ import annotations

import math
import re
from typing import Any

MAX_NODES = 500
MAX_DEPTH = 40
SUPPORTED = {"FRAME", "GROUP", "COMPONENT", "INSTANCE", "COMPONENT_SET", "SECTION", "RECTANGLE", "ELLIPSE", "LINE", "TEXT"}


def _number(value: Any, default: float = 0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return default
    return float(value)


def _px(value: Any, minimum: float = 0) -> str:
    return f"{min(10000, max(minimum, _number(value))):g}px"


def _color(value: Any, opacity: Any = 1) -> str | None:
    if not isinstance(value, dict):
        return None
    channels = [round(max(0, min(1, _number(value.get(c)))) * 255) for c in ("r", "g", "b")]
    alpha = max(0, min(1, _number(value.get("a"), 1) * _number(opacity, 1)))
    if alpha >= 1:
        return "#" + "".join(f"{channel:02x}" for channel in channels)
    return f"rgba({channels[0]}, {channels[1]}, {channels[2]}, {alpha:.3f})"


def _children(node: dict) -> list[dict]:
    children = node.get("children", [])
    if not isinstance(children, list) or any(not isinstance(child, dict) for child in children):
        raise ValueError("Figma 节点 children 必须是对象数组")
    return children


def _roots(payload: dict) -> list[dict]:
    if isinstance(payload.get("document"), dict):
        return [payload["document"]]
    if "nodes" in payload:
        if not isinstance(payload["nodes"], dict):
            raise ValueError("Figma nodes 必须是对象映射")
        return [entry["document"] for entry in payload["nodes"].values() if isinstance(entry, dict) and isinstance(entry.get("document"), dict)]
    if "type" in payload:
        return [payload]
    raise ValueError("需要 Figma /files 响应、/nodes 响应或单个设计节点")


def _walk(nodes: list[dict], depth: int = 0):
    # Selection has a separate search budget because a file can contain many pages.
    stack = [(node, depth) for node in reversed(nodes)]
    searched = 0
    while stack:
        node, level = stack.pop()
        searched += 1
        if searched > 50000 or level > 200:
            raise ValueError("Figma 文件过大，请通过 node_id 或 /nodes 导入局部设计")
        yield node
        stack.extend((child, level + 1) for child in reversed(_children(node)))


def normalize_design(payload: dict, node_id: str | None = None) -> dict:
    """Return a normalized, JSON-serializable design or raise ``ValueError``.

    The supported tree has at most 500 visible nodes and 40 levels (root level 0).
    DOCUMENT/CANVAS wrappers are removed. An explicit node id always wins over
    automatic first-frame selection. Figma URL ids such as ``12-34`` are accepted.
    """
    if not isinstance(payload, dict):
        raise ValueError("设计输入必须是 JSON 对象")
    warnings: list[str] = []
    roots = _roots(payload)
    if not roots:
        raise ValueError("Figma 响应中没有可用节点，请检查 node_id 和访问权限")
    selected: dict | None = None
    if node_id:
        lookup = str(node_id).replace("-", ":")
        selected = next((node for node in _walk(roots) if str(node.get("id")) in {str(node_id), lookup}), None)
        if selected is None:
            raise ValueError(f"未找到 Figma 节点 {node_id}")
    else:
        selected = roots[0]
        if len(roots) > 1:
            warnings.append(f"响应包含 {len(roots)} 个节点，默认仅导入第一个；请指定 node_id 选择其他节点。")
    if selected.get("visible") is False:
        raise ValueError("选中的设计节点已隐藏")
    while selected.get("type") in {"DOCUMENT", "CANVAS"}:
        candidates = [node for node in _children(selected) if node.get("visible") is not False]
        if not candidates:
            raise ValueError("选中的页面没有可见 Frame")
        preferred = [node for node in candidates if node.get("type") in {"FRAME", "COMPONENT", "INSTANCE", "CANVAS", "SECTION"}]
        if len(candidates) > 1:
            warnings.append(f"{selected.get('name', selected.get('type'))} 包含多个页面或 Frame，默认仅导入第一个；请指定 node_id。")
        selected = (preferred or candidates)[0]

    ids: set[str] = set()
    colors: set[str] = set()
    fonts: set[str] = set()
    stats = {"node_count": 0, "text_count": 0, "placeholder_count": 0, "hidden_count": 0, "max_depth": 0}

    def convert(node: dict, parent: dict | None, depth: int) -> dict:
        if depth > MAX_DEPTH:
            raise ValueError(f"设计层级超过 {MAX_DEPTH}，请拆分 Frame")
        stats["node_count"] += 1
        if stats["node_count"] > MAX_NODES:
            raise ValueError(f"设计节点超过 {MAX_NODES}，请缩小导入范围")
        stats["max_depth"] = max(stats["max_depth"], depth)
        ident = str(node.get("id") or f"generated-{stats['node_count']}")
        if ident in ids:
            raise ValueError(f"重复节点 ID：{ident}")
        ids.add(ident)
        kind = str(node.get("type", "UNKNOWN"))
        result: dict[str, Any] = {"id": ident, "name": str(node.get("name", kind)), "type": kind, "style": {"boxSizing": "border-box", "position": "relative", "minWidth": "0"}, "children": []}
        style = result["style"]
        box = node.get("absoluteBoundingBox") or node.get("size") or {}
        if not isinstance(box, dict):
            box = {}
        width = _number(box.get("width", box.get("x") if "absoluteBoundingBox" not in node else None))
        height = _number(box.get("height", box.get("y") if "absoluteBoundingBox" not in node else None))
        mode = node.get("layoutMode")
        auto = mode in {"HORIZONTAL", "VERTICAL"}
        sizing_x, sizing_y = node.get("layoutSizingHorizontal"), node.get("layoutSizingVertical")
        parent_auto = parent is not None and parent.get("layoutMode") in {"HORIZONTAL", "VERTICAL"}
        if parent is None:
            style.update({"width": "100%", "maxWidth": _px(width) if width else "1200px", "margin": "0 auto"})
            if height:
                style["minHeight"] = _px(height)
        elif parent_auto and (sizing_x == "FILL" or node.get("layoutAlign") == "STRETCH"):
            style["alignSelf"] = "stretch"
            if parent.get("layoutMode") == "HORIZONTAL":
                style.update({"flex": "1 1 0", "minWidth": "0"})
            else:
                style["width"] = "100%"
        elif width and sizing_x != "HUG":
            style.update({"width": _px(width), "maxWidth": "100%"})
            if parent_auto:
                style["flexShrink"] = "0"
        if parent is not None and height and sizing_y != "HUG" and kind != "TEXT":
            style["height"] = _px(height)
        if parent_auto and (_number(node.get("layoutGrow")) > 0 or sizing_y == "FILL" and parent.get("layoutMode") == "VERTICAL"):
            style["flexGrow"] = "1"
        if parent and (not parent_auto or node.get("layoutPositioning") == "ABSOLUTE"):
            parent_box = parent.get("absoluteBoundingBox") or {}
            style.update({"position": "absolute", "left": _px(_number(box.get("x")) - _number(parent_box.get("x")), -10000), "top": _px(_number(box.get("y")) - _number(parent_box.get("y")), -10000)})
        if auto:
            style.update({"display": "flex", "flexDirection": "row" if mode == "HORIZONTAL" else "column", "gap": _px(node.get("itemSpacing")), "paddingTop": _px(node.get("paddingTop")), "paddingRight": _px(node.get("paddingRight")), "paddingBottom": _px(node.get("paddingBottom")), "paddingLeft": _px(node.get("paddingLeft"))})
            align = {"MIN": "flex-start", "MAX": "flex-end", "CENTER": "center", "SPACE_BETWEEN": "space-between", "BASELINE": "baseline"}
            style["justifyContent"] = align.get(node.get("primaryAxisAlignItems"), "flex-start")
            style["alignItems"] = align.get(node.get("counterAxisAlignItems"), "flex-start")
            if node.get("layoutWrap") == "WRAP":
                style["flexWrap"] = "wrap"
                if node.get("counterAxisSpacing") is not None:
                    style["rowGap"] = _px(node["counterAxisSpacing"])
            # Legacy Figma responses only expose sizing mode on auto-layout axes.
            if node.get("primaryAxisSizingMode") == "AUTO" and sizing_y is None and mode == "VERTICAL" and parent is not None:
                style.pop("height", None)
            if node.get("counterAxisSizingMode") == "AUTO" and sizing_y is None and mode == "HORIZONTAL" and parent is not None:
                style.pop("height", None)
        if kind == "TEXT":
            stats["text_count"] += 1
            result["text"] = str(node.get("characters", ""))
            text_style = node.get("style") if isinstance(node.get("style"), dict) else {}
            font = str(text_style.get("fontFamily", "Inter"))
            font = re.sub(r"[^\w\s,\-]", "", font, flags=re.UNICODE)[:100] or "Inter"
            fonts.add(font)
            style.update({"margin": "0", "whiteSpace": "pre-wrap", "overflowWrap": "anywhere", "fontFamily": f'"{font}", "PingFang SC", "Microsoft YaHei", sans-serif', "fontSize": _px(text_style.get("fontSize", 16)), "fontWeight": str(int(max(100, min(900, _number(text_style.get("fontWeight"), 400))))), "lineHeight": _px(text_style["lineHeightPx"]) if text_style.get("lineHeightPx") else "1.5"})
            if text_style.get("italic"):
                style["fontStyle"] = "italic"
            style["textAlign"] = {"LEFT": "left", "CENTER": "center", "RIGHT": "right", "JUSTIFIED": "justify"}.get(text_style.get("textAlignHorizontal"), "left")
            if text_style.get("letterSpacing"):
                style["letterSpacing"] = _px(text_style["letterSpacing"], -100)
            if node.get("characterStyleOverrides") or node.get("styleOverrideTable"):
                warnings.append(f"{ident}：富文本混合样式暂使用主文本样式，请人工核对。")
        placeholders: list[str] = []
        if kind not in SUPPORTED:
            placeholders.append(f"{kind} 图形待替换")
        fills = [fill for fill in node.get("fills", []) if isinstance(fill, dict) and fill.get("visible") is not False] if isinstance(node.get("fills", []), list) else []
        if len(fills) > 1:
            warnings.append(f"{ident}：多重填充暂仅保留一个纯色层，其余填充需人工核对。")
        for fill in fills:
            fill_type = fill.get("type", "SOLID")
            if fill_type == "SOLID":
                color = _color(fill.get("color"), fill.get("opacity", 1))
                if color:
                    style["color" if kind == "TEXT" else "backgroundColor"] = color
                    colors.add(color)
            elif fill_type == "IMAGE":
                placeholders.append("图片资源待接入")
            else:
                placeholders.append(f"{fill_type} 填充待还原")
        strokes = node.get("strokes") or []
        if isinstance(strokes, list):
            stroke = next((s for s in strokes if isinstance(s, dict) and s.get("visible") is not False), None)
            if stroke:
                color = _color(stroke.get("color"), stroke.get("opacity", 1))
                if stroke.get("type", "SOLID") != "SOLID":
                    placeholders.append("非纯色描边待还原")
                elif color:
                    style["border"] = f"{_px(node.get('strokeWeight', 1))} solid {color}"
                    colors.add(color)
        if kind == "ELLIPSE":
            style["borderRadius"] = "50%"
        elif node.get("rectangleCornerRadii"):
            radii = node["rectangleCornerRadii"]
            if isinstance(radii, list) and len(radii) == 4:
                style["borderRadius"] = " ".join(_px(radius) for radius in radii)
        elif node.get("cornerRadius") is not None:
            style["borderRadius"] = _px(node["cornerRadius"])
        shadows = []
        for effect in node.get("effects", []) if isinstance(node.get("effects", []), list) else []:
            if not isinstance(effect, dict) or effect.get("visible") is False:
                continue
            if effect.get("type") in {"DROP_SHADOW", "INNER_SHADOW"}:
                offset = effect.get("offset") or {}
                color = _color(effect.get("color")) or "rgba(0, 0, 0, 0.100)"
                shadows.append(f"{'inset ' if effect['type'] == 'INNER_SHADOW' else ''}{_px(offset.get('x'), -10000)} {_px(offset.get('y'), -10000)} {_px(effect.get('radius'))} {_px(effect.get('spread'), -10000)} {color}")
            else:
                warnings.append(f"{ident}：暂未还原 {effect.get('type', '未知')} 效果。")
        if shadows:
            style["boxShadow"] = ", ".join(shadows)
        if node.get("opacity") is not None:
            style["opacity"] = f"{max(0, min(1, _number(node['opacity'], 1))):g}"
        if node.get("clipsContent"):
            style["overflow"] = "hidden"
        if node.get("rotation"):
            warnings.append(f"{ident}：旋转节点暂按轴对齐布局呈现。")
        if placeholders:
            result["placeholder"] = " · ".join(dict.fromkeys(placeholders))
            stats["placeholder_count"] += 1
            warnings.append(f"{ident}（{result['name']}）：{result['placeholder']}。")
            style.setdefault("minHeight", "56px")
            style.setdefault("backgroundColor", "#f1f3f7")
        for child in _children(node):
            if child.get("visible") is False:
                stats["hidden_count"] += 1
            else:
                result["children"].append(convert(child, node, depth + 1))
        if result["children"] and not auto and not height:
            warnings.append(f"{ident}：自由布局容器缺少高度，使用最小占位高度，请人工核对。")
            style.setdefault("minHeight", "160px")
        return result

    root = convert(selected, None, 0)
    return {"name": str(selected.get("name", payload.get("name", "Figma D2C 页面"))), "root": root, "tokens": {"colors": sorted(colors), "fonts": sorted(fonts)}, "warnings": warnings, "stats": stats}
