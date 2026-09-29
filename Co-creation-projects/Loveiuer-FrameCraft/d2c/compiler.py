"""Deterministic React + CSS compiler for normalized Figma trees.

The optional LLM plan contains data only. No generated JavaScript, HTML, CSS,
imports, or event handlers from a model are evaluated or inserted verbatim.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from typing import Any

TAGS = {"div", "section", "header", "footer", "nav", "main", "article", "aside", "h1", "h2", "h3", "p", "span", "button"}
TEXT_TAGS = {"h1", "h2", "h3", "p", "span", "button"}
CONTAINER_TAGS = TAGS - {"h1", "h2", "h3", "p", "span"}
STYLE_KEYS = {"boxSizing", "position", "minWidth", "width", "maxWidth", "height", "minHeight", "maxHeight", "margin", "alignSelf", "flex", "flexGrow", "flexShrink", "left", "top", "display", "flexDirection", "gap", "rowGap", "paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "justifyContent", "alignItems", "flexWrap", "whiteSpace", "overflowWrap", "fontFamily", "fontSize", "fontWeight", "fontStyle", "lineHeight", "textAlign", "letterSpacing", "color", "backgroundColor", "border", "borderRadius", "boxShadow", "opacity", "overflow"}
BUTTON_TITLE = "演示按钮，业务交互待接入"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _css_name(key: str) -> str:
    return re.sub(r"[A-Z]", lambda match: "-" + match[0].lower(), key)


def _css_value(value: Any) -> str:
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise ValueError("CSS 值必须是字符串或数字")
    value = str(value)
    if len(value) > 1000 or re.search(r"[{};<>\\@]|url\s*\(|expression\s*\(|/\*", value, re.I):
        raise ValueError("检测到不安全的 CSS 值")
    return value


def compile_project(design: dict, plan: dict | None = None) -> dict[str, str]:
    """Compile a normalized design, validating every structural plan decision.

    ``manifest.json`` contains one entry per Figma node. The static preview uses
    the same tree, tags and style sheet as React, but needs no JavaScript runtime.
    """
    if not isinstance(design, dict) or not isinstance(design.get("root"), dict):
        raise ValueError("缺少 normalized design.root")
    nodes: dict[str, dict] = {}

    def collect(node: dict, depth: int = 0):
        if depth > 40 or len(nodes) >= 500:
            raise ValueError("设计超过编译器的节点或深度限制")
        if not isinstance(node, dict) or not isinstance(node.get("id"), str) or not node["id"]:
            raise ValueError("设计节点必须有非空字符串 ID")
        if node["id"] in nodes:
            raise ValueError(f"重复节点 ID：{node['id']}")
        nodes[node["id"]] = node
        children = node.get("children", [])
        if not isinstance(children, list):
            raise ValueError("设计节点 children 必须是数组")
        for child in children:
            collect(child, depth + 1)

    collect(design["root"])
    plan = plan if plan is not None else {"components": [], "notes": []}
    if not isinstance(plan, dict) or not isinstance(plan.get("components", []), list):
        raise ValueError("组件计划必须包含 components 数组")
    if len(plan.get("components", [])) > 40:
        raise ValueError("组件计划最多允许 40 个组件")
    if not isinstance(plan.get("notes", []), list) or any(not isinstance(note, str) for note in plan.get("notes", [])):
        raise ValueError("组件计划 notes 必须是字符串数组")
    components: dict[str, dict] = {}
    names: set[str] = {"App", "React", "Fragment", "StrictMode"}
    for component in plan.get("components", []):
        if not isinstance(component, dict):
            raise ValueError("组件计划中的每一项必须是对象")
        ident, name, tag = component.get("node_id"), component.get("name"), component.get("tag")
        if not isinstance(ident, str) or ident not in nodes:
            raise ValueError(f"组件计划引用了不存在的节点：{ident}")
        if ident in components:
            raise ValueError(f"组件计划重复引用节点：{ident}")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Z][A-Za-z0-9]{0,63}", name) or name in names:
            raise ValueError(f"组件名称不合法或重复：{name}")
        if tag not in TAGS:
            raise ValueError(f"不允许的语义标签：{tag}")
        allowed = TEXT_TAGS if nodes[ident].get("type") == "TEXT" and not nodes[ident].get("children") else CONTAINER_TAGS
        if tag not in allowed:
            raise ValueError(f"节点 {ident} 不支持标签 {tag}，请匹配文本或容器语义")
        names.add(name)
        components[ident] = {"node_id": ident, "name": name, "tag": tag}

    classes = {ident: "figma-" + hashlib.sha256(ident.encode()).hexdigest()[:12] for ident in nodes}

    def tag_for(node: dict) -> str:
        if node["id"] in components:
            return components[node["id"]]["tag"]
        return "p" if node.get("type") == "TEXT" else "div"

    effective_tags: dict[str, str] = {}

    def check_buttons(node: dict, inside: bool = False):
        button = tag_for(node) == "button"
        if inside and button:
            raise ValueError("按钮不能嵌套按钮")
        if inside and tag_for(node) not in {"div", "span", "p"}:
            raise ValueError("按钮内容不允许嵌套结构化语义标签")
        effective_tags[node["id"]] = "span" if inside and tag_for(node) in {"div", "p"} else tag_for(node)
        for child in node.get("children", []):
            check_buttons(child, inside or button)

    check_buttons(design["root"])
    css = [
        ':root { font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif; color: #17253c; background: #edf1f6; font-synthesis: none; text-rendering: optimizeLegibility; -webkit-font-smoothing: antialiased; }',
        '* { box-sizing: border-box; }',
        'body { margin: 0; padding: 0; }',
        'button { font: inherit; color: inherit; text-align: inherit; appearance: none; border: 0; }',
        'button:disabled { opacity: 1; cursor: not-allowed; }',
        '.d2c-placeholder { display: flex; align-items: center; justify-content: center; min-height: 48px; width: 100%; padding: 12px; border: 1px dashed #a8b5c8; border-radius: 8px; color: #65758e; background: #f1f3f7; font: 12px/1.5 sans-serif; text-align: center; }',
    ]
    for ident, node in nodes.items():
        styles = node.get("style", {})
        if not isinstance(styles, dict):
            raise ValueError("节点 style 必须是对象")
        declarations = []
        for key, value in styles.items():
            if key not in STYLE_KEYS:
                raise ValueError(f"不支持的 CSS 属性：{key}")
            declarations.append(f"  {_css_name(key)}: {_css_value(value)};")
        css.append(f".{classes[ident]} {{\n" + "\n".join(declarations) + "\n}")
    # A conservative adaptation applies only to auto-layout rows. Absolute-layout
    # artboards remain fixed internally; the README explicitly calls this out.
    rows = [node for node in nodes.values() if node.get("style", {}).get("display") == "flex" and node.get("style", {}).get("flexDirection") == "row" and len(node.get("children", [])) > 1]
    if rows:
        selectors = ", ".join("." + classes[node["id"]] for node in rows)
        rules = [selectors + " { flex-wrap: wrap; }"]
        flexible = [child for node in rows for child in node.get("children", []) if child.get("style", {}).get("flex") == "1 1 0"]
        if flexible:
            # Figma FILL uses a zero basis at desktop widths. A nonzero mobile
            # basis lets wrapping happen before text becomes one character wide.
            rules.append(", ".join("." + classes[node["id"]] for node in flexible) + " { min-width: min(100%, 120px); flex-basis: 120px; }")
        # Only larger, multi-child rows need their fixed height released. Small
        # visual primitives (progress tracks, badges, avatars) keep their sizing.
        large_fixed = [node for node in rows if re.fullmatch(r"\d+(?:\.\d+)?px", str(node.get("style", {}).get("height", ""))) and float(node["style"]["height"][:-2]) >= 80]
        if large_fixed:
            rules.append(", ".join("." + classes[node["id"]] for node in large_fixed) + " { height: auto; }")
        css.append("@media (max-width: 720px) {\n  " + "\n  ".join(rules) + "\n}")
    stylesheet = "\n\n".join(css) + "\n"

    def render(node: dict, jsx: bool, own_component: str | None = None, inside_button: bool = False) -> str:
        ident = node["id"]
        if jsx and ident in components and ident != own_component:
            return f"<{components[ident]['name']} />"
        # Resolve tags across the entire tree before component extraction so a
        # separately declared child component retains its button ancestry.
        tag = effective_tags[ident]
        if jsx:
            attrs = f"className={{{_json(classes[ident])}}} data-node-id={{{_json(ident)}}}"
        else:
            attrs = f'class="{classes[ident]}" data-node-id="{html.escape(ident, quote=True)}"'
        if tag == "button":
            attrs += f' type="button" disabled title="{BUTTON_TITLE}"'
        parts = []
        if "text" in node:
            parts.append("{" + _json(str(node["text"])) + "}" if jsx else html.escape(str(node["text"])))
        if node.get("placeholder"):
            placeholder = str(node["placeholder"])
            contents = "{" + _json(placeholder) + "}" if jsx else html.escape(placeholder)
            parts.append(f'<span {"className" if jsx else "class"}="d2c-placeholder" role="img" aria-label={"{" + _json(placeholder) + "}" if jsx else chr(34) + html.escape(placeholder, quote=True) + chr(34)}>{contents}</span>')
        parts.extend(render(child, jsx, own_component, inside_button or tag == "button") for child in node.get("children", []))
        return f"<{tag} {attrs}>" + "\n".join(parts) + f"</{tag}>"

    definitions = []
    for ident, component in components.items():
        definitions.append(f"function {component['name']}() {{\n  return (\n    {render(nodes[ident], True, ident)}\n  );\n}}")
    definitions.append("export default function App() {\n  return (\n    " + render(design["root"], True) + "\n  );\n}")
    app = 'import "./styles.css";\n\n' + "\n\n".join(definitions) + "\n"
    name = str(design.get("name", "Figma D2C 页面"))
    title = html.escape(name)
    static = "<!doctype html>\n<html lang=\"zh-CN\"><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>" + title + "</title><style>\n" + stylesheet + "</style></head><body>\n" + render(design["root"], False) + "\n</body></html>\n"
    manifest = {"version": 1, "name": name, "root_node_id": design["root"]["id"], "nodes": [{"id": ident, "name": node.get("name", ""), "type": node.get("type", ""), "className": classes[ident], "component": components.get(ident, {}).get("name"), "tag": effective_tags[ident]} for ident, node in nodes.items()], "tokens": design.get("tokens", {}), "warnings": design.get("warnings", []), "plan": plan, "limitations": ["仅生成展示层，按钮禁用，业务交互待接入。", "窄屏仅对 Auto Layout 行启用换行；自由布局与复杂断点需要人工调整。", "图片、向量与渐变以可见占位提示，未进行像素级截图评测。"]}
    package = {"name": "figma-d2c-output", "private": True, "version": "1.0.0", "type": "module", "scripts": {"dev": "vite --host 127.0.0.1", "build": "tsc -b && vite build", "preview": "vite preview --host 127.0.0.1"}, "dependencies": {"react": "^18.3.1", "react-dom": "^18.3.1"}, "devDependencies": {"@types/react": "^18.3.18", "@types/react-dom": "^18.3.5", "@vitejs/plugin-react": "^4.3.4", "typescript": "~5.7.3", "vite": "^6.1.0"}}
    return {
        "package.json": json.dumps(package, ensure_ascii=False, indent=2) + "\n",
        "index.html": '<!doctype html>\n<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>' + title + '</title></head><body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>\n',
        "src/App.tsx": app,
        "src/main.tsx": 'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport App from "./App";\n\nReactDOM.createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);\n',
        "src/styles.css": stylesheet,
        "vite.config.ts": 'import { defineConfig } from "vite";\nimport react from "@vitejs/plugin-react";\n\nexport default defineConfig({ plugins: [react()] });\n',
        "tsconfig.json": json.dumps({"compilerOptions": {"target": "ES2020", "useDefineForClassFields": True, "lib": ["ES2020", "DOM", "DOM.Iterable"], "module": "ESNext", "skipLibCheck": True, "moduleResolution": "Bundler", "allowImportingTsExtensions": True, "resolveJsonModule": True, "isolatedModules": True, "noEmit": True, "jsx": "react-jsx", "strict": True}, "include": ["src", "vite.config.ts"]}, indent=2) + "\n",
        "preview.html": static,
        "manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        "README.md": "# Figma D2C 生成页面\n\n运行环境：Node.js 20.19+ 与 npm。\n\n```bash\nnpm install\nnpm run dev\nnpm run build\n```\n\n`preview.html` 可直接打开，不依赖 npm 或 JavaScript。React 与静态预览共享同一结构和样式。\n`manifest.json` 记录 Figma 节点、CSS 类与 React 组件的映射。\n\n## 范围与限制\n\n- 输出为展示层，按钮被禁用并注明业务交互待接入。\n- 窄屏仅对 Auto Layout 行启用换行；这不等同于完整的响应式设计。自由布局、复杂断点与溢出需人工验收。\n- 图片、向量与渐变显示明确占位。字体依赖设备环境，未打包商业字体。\n- 请根据 manifest.json 中的 warnings 核对未还原部分；当前生成结果未进行像素级截图评测。\n",
    }
