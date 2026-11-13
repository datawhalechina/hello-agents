"""Build reviewable project documentation and bounded local PNG design diagrams."""
from __future__ import annotations

import base64
import hashlib
import io
import math
import os
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont

from .workspace import Conflict, MAX_FILE


ANALYSIS_SKILL = "analyze-project-zh"
OUTPUT_PATHS = (
    "项目说明.md", "docs/diagrams/README.md", "docs/diagrams/architecture.png",
    "docs/diagrams/workflow.png", "docs/diagrams/sequence.png",
)
ANALYSIS_INSTRUCTIONS = """你正在为用户导入的整个项目生成中文项目说明与设计图，交付位置固定为：
项目说明.md、docs/diagrams/README.md，以及同目录 architecture.png、workflow.png、sequence.png。
参考结构包括：项目概述、已有功能、技术栈、目录结构、模块职责与架构、安装、配置、运行、使用示例、验证方式、当前边界与后续计划。
按实际项目选择适用内容，所有事实、路径、命令和调用关系以真实文件与工具观察为依据；没有依据就注明未知或待核对。
先检查完整文件清单及现有 README、依赖、入口、配置样例和关键模块，再提出说明与图的结构。
不得把参考项目的 Electron、菲比、作者、许可证、测试结果或功能照搬到目标项目。不得伪造截图、运行成功、测试通过或已完成的功能。
仅静态阅读，不执行目标代码、测试、构建或安装依赖；不修改源代码和配置，不读取密钥。
通过 submit_action 提交 action=propose_documentation，args 仅包含 overview、diagrams；文件版本由客户端管理。
overview 为项目说明.md 的 Markdown 正文；客户端会追加三图的正确相对链接，不要引用不存在的截图或文档。
diagrams 必须包含 architecture、workflow、sequence 三个结构化图。架构/流程图给 title、description、nodes、edges；
节点含唯一 id、label，可选 level(0到8)、kind(process或decision)，最多14节点、24边；每条边的from/to必须引用已有节点。
时序图给 title、description、participants、messages，最多7参与者、20消息；参与者唯一id/label，消息from/to/label，可选dashed布尔值。
id使用字母开头的英文字母、数字、下划线或连字符（最多40字符），标签使用简短中文，图的description解释实际流程并标出计划能力。
PNG由客户端本地绘制，无需模型生成图片、SVG、base64或运行绘图代码。提交后由客户端校验并自动应用，必须以真实工具结果确认写入。
存在版本冲突时保留原文件并停止自动应用；只有全部五个交付文件实际应用后，才能报告项目解析交付完成。
"""
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PIXELS = 10_000_000
MAX_EXISTING_PNG = 8 * 1024 * 1024
COLORS = {"background": "#f6f9ff", "ink": "#173759", "muted": "#506b88",
          "line": "#557dac", "fill": "#e7f0ff", "border": "#5686bf", "gold": "#fff3d3"}


def _object(value, required, optional=(), name="对象"):
    if not isinstance(value, dict) or not set(required) <= value.keys() or not value.keys() <= set(required) | set(optional):
        raise ValueError(f"{name} 必须包含 {list(required)}，且不能包含未知字段。")
    return value


def _text(value, name, maximum=80, *, empty=False):
    if (not isinstance(value, str) or len(value) > maximum or (not empty and not value.strip())
            or any(ord(char) < 32 and char not in "\n\t" for char in value)):
        raise ValueError(f"{name} 必须为{'0' if empty else '1'}–{maximum}字符的文本。")
    return value.strip()


def _id(value):
    value = _text(value, "节点 id", 40)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,39}", value):
        raise ValueError("图 id 须以英文字母开头，仅使用字母、数字、下划线或连字符。")
    return value


def _font(size):
    override = os.getenv("CODE_ASSISTANT_FONT_PATH")
    candidates = ([override] if override else []) + [
        "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", "/System/Library/Fonts/PingFang.ttc",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                pass
    raise ValueError("未找到中文绘图字体。请安装微软雅黑/Noto Sans CJK，或设置 CODE_ASSISTANT_FONT_PATH 指向中文字体文件。")


def _wrap(draw, text, font, width):
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for char in paragraph:
            if current and draw.textlength(current + char, font=font) > width:
                lines.append(current)
                current = char
            else:
                current += char
        lines.append(current)
    return lines


def _label(draw, text, center, width=260, font=None, fill=None, background=False, max_height=None):
    font = font or _font(24)
    lines = _wrap(draw, text, font, width)
    while max_height and len(lines) * (font.size + 7) > max_height and font.size > 8:
        font = _font(font.size - 1)
        lines = _wrap(draw, text, font, width)
    height = len(lines) * (font.size + 7)
    x, y = center
    if background:
        draw.rounded_rectangle((x - width / 2 - 5, y - height / 2 - 3, x + width / 2 + 5, y + height / 2 + 3),
                               radius=5, fill=COLORS["background"])
    for index, line in enumerate(lines):
        draw.text((x - draw.textlength(line, font=font) / 2, y - height / 2 + index * (font.size + 7)),
                  line, font=font, fill=fill or COLORS["ink"])


def _arrow(draw, points, *, dashed=False):
    for start, end in zip(points, points[1:]):
        if dashed:
            distance = math.dist(start, end)
            for offset in range(0, int(distance), 15):
                ratios = (offset / max(distance, 1), min(offset + 8, distance) / max(distance, 1))
                segment = [(start[0] + (end[0] - start[0]) * r, start[1] + (end[1] - start[1]) * r) for r in ratios]
                draw.line(segment, fill=COLORS["line"], width=3)
        else:
            draw.line([start, end], fill=COLORS["line"], width=3)
    tip, previous = points[-1], points[-2]
    angle = math.atan2(tip[1] - previous[1], tip[0] - previous[0])
    draw.polygon([tip, (tip[0] - 14 * math.cos(angle - .4), tip[1] - 14 * math.sin(angle - .4)),
                  (tip[0] - 14 * math.cos(angle + .4), tip[1] - 14 * math.sin(angle + .4))], fill=COLORS["line"])


def _png(image):
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=True)
    raw = stream.getvalue()
    if len(raw) > MAX_FILE:
        stream = io.BytesIO()
        image.convert("P", palette=Image.Palette.ADAPTIVE, colors=128).save(stream, format="PNG", optimize=True)
        raw = stream.getvalue()
    if len(raw) > MAX_FILE:
        raise ValueError("图表 PNG 超过 256 KB，请减少节点、消息或标签。")
    return raw


def _graph(spec):
    _object(spec, ("title", "description", "nodes", "edges"), name="架构/流程图")
    title = _text(spec["title"], "图标题", 80)
    _text(spec["description"], "图说明", 2500)
    if not isinstance(spec["nodes"], list) or not 1 <= len(spec["nodes"]) <= 14:
        raise ValueError("架构/流程图须包含1–14个节点。")
    if not isinstance(spec["edges"], list) or not 0 <= len(spec["edges"]) <= 24:
        raise ValueError("架构/流程图最多24条边。")
    nodes, names = [], set()
    for item in spec["nodes"]:
        _object(item, ("id", "label"), ("level", "kind"), "图节点")
        name = _id(item["id"])
        if name in names:
            raise ValueError("图节点 id 重复。")
        names.add(name)
        level = item.get("level")
        if level is not None and (type(level) is not int or not 0 <= level <= 8):
            raise ValueError("节点 level 必须为0–8的整数。")
        kind = item.get("kind", "process")
        if kind not in {"process", "decision"}:
            raise ValueError("节点 kind 仅支持process或decision。")
        nodes.append({"id": name, "label": _text(item["label"], "节点标签", 80), "level": level, "kind": kind})
    edges = []
    for item in spec["edges"]:
        _object(item, ("from", "to"), ("label",), "图连线")
        source, target = _id(item["from"]), _id(item["to"])
        if source not in names or target not in names:
            raise ValueError("图连线引用不存在的节点。")
        edges.append({"from": source, "to": target, "label": _text(item.get("label", ""), "连线标签", 50, empty=True)})
    # Infer a bounded level for unspecified nodes; cycles get a stable fallback.
    levels = {node["id"]: node["level"] for node in nodes if node["level"] is not None}
    roots = names - {edge["to"] for edge in edges}
    for name in roots:
        levels.setdefault(name, 0)
    for _ in nodes:
        changed = False
        for edge in edges:
            if edge["from"] in levels and edge["to"] not in levels:
                levels[edge["to"]] = min(8, levels[edge["from"]] + 1)
                changed = True
        if not changed:
            break
    groups = {}
    for node in nodes:
        groups.setdefault(levels.get(node["id"], 0), []).append(node)
    rows = []
    for _, group in sorted(groups.items()):
        rows.extend(group[start:start + 3] for start in range(0, len(group), 3))
    width, height = 1440, max(430, 170 + len(rows) * 180)
    if height > 2600:
        raise ValueError("图表层级超过安全画布范围。")
    image = Image.new("RGB", (width, height), COLORS["background"])
    draw = ImageDraw.Draw(image)
    _label(draw, title, (width / 2, 55), width=1260, font=_font(34))
    positions = {}
    for row_index, row in enumerate(rows):
        spacing = width / (len(row) + 1)
        for col, node in enumerate(row):
            positions[node["id"]] = (int(spacing * (col + 1)), 180 + row_index * 180)
    for index, edge in enumerate(edges):
        sx, sy = positions[edge["from"]]
        tx, ty = positions[edge["to"]]
        if edge["from"] == edge["to"]:
            bottom = 67 if next(node for node in nodes if node["id"] == edge["from"])["kind"] == "decision" else 57
            points = [(sx + 166, sy), (sx + 195, sy), (sx + 195, sy + 85),
                      (sx, sy + 85), (sx, sy + bottom)]
            label = (sx + 245, sy + 40)
        elif sy < ty:
            mid = (sy + ty) / 2
            points = [(sx, sy + 55), (sx, mid), (tx, mid), (tx, ty - 55)]
            label = ((sx + tx) / 2, mid - 16)
        elif sy == ty and sx != tx:
            direction = 1 if sx < tx else -1
            points = [(sx + 155 * direction, sy), (tx - 155 * direction, ty)]
            label = ((sx + tx) / 2, sy - 21)
        else:
            lane = 45 + (index % 4) * 16
            points = [(sx - 155, sy), (lane, sy), (lane, ty), (tx - 155, ty)]
            label = (max(130, min(sx, tx) - 210), (sy + ty) / 2)
        _arrow(draw, points)
        if edge["label"]:
            _label(draw, edge["label"], label, 200, _font(18), background=True, max_height=54)
    for node in nodes:
        x, y = positions[node["id"]]
        if node["kind"] == "decision":
            draw.polygon([(x, y - 67), (x + 166, y), (x, y + 67), (x - 166, y)],
                         fill=COLORS["gold"], outline=COLORS["border"], width=3)
            label_width = 230
        else:
            draw.rounded_rectangle((x - 155, y - 57, x + 155, y + 57), radius=15,
                                   fill=COLORS["fill"], outline=COLORS["border"], width=3)
            label_width = 280
        _label(draw, node["label"], (x, y), label_width, _font(23),
               max_height=85 if node["kind"] == "decision" else 98)
    return _png(image)


def _sequence(spec):
    _object(spec, ("title", "description", "participants", "messages"), name="时序图")
    title = _text(spec["title"], "图标题", 80)
    _text(spec["description"], "图说明", 2500)
    if not isinstance(spec["participants"], list) or not 1 <= len(spec["participants"]) <= 7:
        raise ValueError("时序图须包含1–7个参与者。")
    if not isinstance(spec["messages"], list) or not 1 <= len(spec["messages"]) <= 20:
        raise ValueError("时序图须包含1–20条消息。")
    actors = {}
    for item in spec["participants"]:
        _object(item, ("id", "label"), name="时序参与者")
        name = _id(item["id"])
        if name in actors:
            raise ValueError("时序参与者 id 重复。")
        actors[name] = _text(item["label"], "参与者标签", 50)
    messages = []
    for item in spec["messages"]:
        _object(item, ("from", "to", "label"), ("dashed",), "时序消息")
        source, target = _id(item["from"]), _id(item["to"])
        if source not in actors or target not in actors:
            raise ValueError("时序消息引用不存在的参与者。")
        dashed = item.get("dashed", False)
        if type(dashed) is not bool:
            raise ValueError("时序消息 dashed 必须为布尔值。")
        messages.append((source, target, _text(item["label"], "消息标签", 100), dashed))
    width, height = max(1080, len(actors) * 230 + 100), 220 + len(messages) * 92
    image = Image.new("RGB", (width, height), COLORS["background"])
    draw = ImageDraw.Draw(image)
    _label(draw, title, (width / 2, 50), width=width - 100, font=_font(34))
    positions = {name: 90 + index * (width - 180) / max(1, len(actors) - 1) for index, name in enumerate(actors)}
    for name, label in actors.items():
        x = positions[name]
        if len(actors) == 1:
            x = positions[name] = width / 2
        _arrow(draw, [(x, 175), (x, height - 35)], dashed=True)
        draw.rounded_rectangle((x - 85, 105, x + 85, 175), radius=12,
                               fill=COLORS["fill"], outline=COLORS["border"], width=3)
        _label(draw, label, (x, 140), 155, _font(22), max_height=60)
    for index, (source, target, label, dashed) in enumerate(messages):
        sx, tx, y = positions[source], positions[target], 230 + index * 92
        if source == target:
            direction = -1 if sx + 210 > width else 1
            points = [(sx, y), (sx + direction * 100, y),
                      (sx + direction * 100, y + 30), (sx, y + 30)]
            center = (sx + direction * 105, y - 18)
        else:
            points = [(sx, y), (tx, y)]
            center = ((sx + tx) / 2, y - 27)
        _arrow(draw, points, dashed=dashed)
        _label(draw, label, center, min(700, max(200, abs(tx - sx) - 20)), _font(20),
               background=True, max_height=64)
    return _png(image)


def _output_bytes(workspace, relative):
    path = workspace.path(relative)
    if path.relative_to(workspace.root).as_posix().casefold() != relative.casefold():
        raise ValueError("交付目录不能通过链接指向其他项目文件。")
    if not path.exists():
        return None
    limit = MAX_EXISTING_PNG if relative.endswith(".png") else MAX_FILE
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError(f"{relative} 不是可处理的文件或超过既有文件备份上限。")
    raw = path.read_bytes()
    if relative.endswith(".png"):
        if not raw.startswith(PNG_SIGNATURE):
            raise ValueError(f"{relative} 已存在但不是PNG图片，不能自动覆盖。")
        try:
            with Image.open(io.BytesIO(raw)) as image:
                if image.format != "PNG" or image.width * image.height > MAX_PIXELS:
                    raise ValueError(f"{relative} 图片尺寸超过安全范围。")
                image.verify()
        except (OSError, SyntaxError) as exc:
            raise ValueError(f"{relative} 不是有效PNG图片。") from exc
    else:
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"{relative} 不是UTF-8文档，不能自动覆盖。") from exc
        if b"\x00" in raw:
            raise ValueError(f"{relative} 不是可处理的文本文档。")
    return raw


def analysis_baselines(workspace) -> dict[str, str]:
    return {path: "missing" if (raw := _output_bytes(workspace, path)) is None else hashlib.sha256(raw).hexdigest()
            for path in OUTPUT_PATHS}


def build_analysis_bundle(workspace, overview: str, diagrams: dict, base_hashes: dict) -> list[dict]:
    """Render proposed artifacts only; creation and overwrite remain reviewable."""
    overview = _text(overview, "项目说明", 22_000)
    _object(diagrams, ("architecture", "workflow", "sequence"), name="设计图集合")
    if (not isinstance(base_hashes, dict) or set(base_hashes) != set(OUTPUT_PATHS)
            or any(not isinstance(value, str) for value in base_hashes.values())):
        raise ValueError("base_hashes 必须显式提供全部五个交付路径的真实基线。")
    current = analysis_baselines(workspace)
    if current != base_hashes:
        changed = [path for path in OUTPUT_PATHS if current[path] != base_hashes[path]]
        raise Conflict("交付文件已变化，请重新获取基线后生成：" + "、".join(changed))
    rendered = {"architecture": _graph(diagrams["architecture"]), "workflow": _graph(diagrams["workflow"]),
                "sequence": _sequence(diagrams["sequence"])}
    links = ("\n\n## 项目设计图\n\n"
             "[设计图说明](docs/diagrams/README.md)\n\n"
             "### 系统架构图\n\n![系统架构图](docs/diagrams/architecture.png)\n\n"
             "### 任务流程图\n\n![任务流程图](docs/diagrams/workflow.png)\n\n"
             "### 交互时序图\n\n![交互时序图](docs/diagrams/sequence.png)\n")
    overview = overview.rstrip() + links
    descriptions = ["# 项目设计图", "[返回项目说明](../../项目说明.md)"]
    for key in ("architecture", "workflow", "sequence"):
        spec = diagrams[key]
        descriptions.append(f"## {spec['title'].strip()}\n\n{spec['description'].strip()}\n\n![{key}]({key}.png)")
    texts = {OUTPUT_PATHS[0]: overview, OUTPUT_PATHS[1]: "\n\n".join(descriptions) + "\n"}
    if any(len(content) > 24_000 or len(content.encode("utf-8")) > MAX_FILE for content in texts.values()):
        raise ValueError("说明文档超过编辑大小上限，请精简后重新提交。")
    changes = [{"path": path, "base_hash": current[path], "content": content} for path, content in texts.items()]
    changes.extend({"path": f"docs/diagrams/{key}.png", "base_hash": current[f"docs/diagrams/{key}.png"],
                    "content": base64.b64encode(raw).decode("ascii"), "encoding": "base64", "mime_type": "image/png"}
                   for key, raw in rendered.items())
    return changes
