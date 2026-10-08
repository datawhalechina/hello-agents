import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import unittest

from d2c.compiler import compile_project
from d2c.design import normalize_design


def frame(ident="1:1", children=None, **kwargs):
    return {"id": ident, "type": "FRAME", "name": "Example", "absoluteBoundingBox": {"x": 100, "y": 50, "width": 800, "height": 600}, "children": children or [], **kwargs}


def label(ident="1:2", text="Hello"):
    return {"id": ident, "type": "TEXT", "name": "Title", "characters": text, "style": {"fontFamily": "Inter", "fontSize": 24, "fontWeight": 700}, "fills": [{"type": "SOLID", "color": {"r": 0.1, "g": 0.2, "b": 0.3}}]}


class NodeParser(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.nodes = {}
        self.scripts = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "data-node-id" in attrs:
            self.nodes[attrs["data-node-id"]] = (tag, attrs)
        if tag == "script":
            self.scripts.append(attrs)


class CompilerTests(unittest.TestCase):
    def test_file_and_nodes_selection(self):
        first, second = frame(), frame("2:1", [label("2:2")])
        payload = {"document": {"id": "0:0", "type": "DOCUMENT", "children": [{"id": "0:1", "type": "CANVAS", "children": [first, second]}]}}
        default = normalize_design(payload)
        self.assertEqual(default["root"]["id"], "1:1")
        self.assertTrue(any("多个" in warning for warning in default["warnings"]))
        self.assertEqual(normalize_design(payload, "2-1")["root"]["id"], "2:1")
        self.assertEqual(normalize_design({"nodes": {"2:1": {"document": second}}})["stats"]["text_count"], 1)
        with self.assertRaisesRegex(ValueError, "未找到"):
            normalize_design(payload, "unknown")

    def test_hidden_nodes_and_duplicate_ids(self):
        design = normalize_design(frame(children=[label(), {**label("1:3"), "visible": False}]))
        self.assertEqual(design["stats"]["node_count"], 2)
        self.assertEqual(design["stats"]["hidden_count"], 1)
        with self.assertRaisesRegex(ValueError, "重复"):
            normalize_design(frame(children=[label(), label()]))

    def test_node_and_depth_limits(self):
        with self.assertRaisesRegex(ValueError, "500"):
            normalize_design(frame(children=[label(f"n:{i}") for i in range(500)]))
        tree = label("leaf")
        for i in range(41):
            tree = frame(str(i), [tree])
        with self.assertRaisesRegex(ValueError, "40"):
            normalize_design(tree)

    def test_auto_layout_and_text_styles(self):
        tree = frame(children=[{**label(), "layoutSizingHorizontal": "FILL"}], layoutMode="HORIZONTAL", itemSpacing=16, paddingLeft=24, paddingTop=12, counterAxisAlignItems="CENTER", primaryAxisAlignItems="SPACE_BETWEEN")
        design = normalize_design(tree)
        style = design["root"]["style"]
        self.assertEqual((style["display"], style["flexDirection"], style["gap"]), ("flex", "row", "16px"))
        self.assertEqual(style["justifyContent"], "space-between")
        child = design["root"]["children"][0]
        self.assertEqual(child["style"]["flex"], "1 1 0")
        self.assertEqual(child["style"]["fontSize"], "24px")
        self.assertIn("#1a334c", design["tokens"]["colors"])

    def test_absolute_positions_are_relative_to_parent(self):
        child = frame("child")
        child["absoluteBoundingBox"].update({"x": 135, "y": 72, "width": 50, "height": 30})
        style = normalize_design(frame(children=[child]))["root"]["children"][0]["style"]
        self.assertEqual((style["position"], style["left"], style["top"]), ("absolute", "35px", "22px"))

    def test_artwork_remains_visible_as_placeholders(self):
        child = {"id": "vector", "name": "Illustration", "type": "VECTOR", "fills": [{"type": "IMAGE"}, {"type": "GRADIENT_LINEAR"}]}
        design = normalize_design(frame(children=[child]))
        self.assertEqual(design["stats"]["placeholder_count"], 1)
        self.assertTrue(design["warnings"])
        preview = compile_project(design)["preview.html"]
        for token in ["VECTOR", "图片资源待接入", "GRADIENT_LINEAR", "d2c-placeholder"]:
            self.assertIn(token, preview)

    def test_text_and_node_id_are_escaped(self):
        attack = '</script><img src=x onerror="alert(1)"> {danger}'
        tree = frame(children=[label('x" onclick="evil', attack)])
        files = compile_project(normalize_design(tree))
        self.assertIn("&lt;/script&gt;&lt;img", files["preview.html"])
        self.assertNotIn('<img src=x', files["preview.html"])
        self.assertIn(json.dumps(attack, ensure_ascii=False), files["src/App.tsx"])
        parsed = NodeParser(files["preview.html"])
        self.assertIn('x" onclick="evil', parsed.nodes)
        self.assertNotIn("onclick", parsed.nodes['x" onclick="evil'][1])
        self.assertEqual(parsed.scripts, [])

    def test_component_extraction_and_node_mapping(self):
        design = normalize_design(frame(children=[label()]))
        plan = {"components": [{"node_id": "1:1", "name": "Dashboard", "tag": "main"}, {"node_id": "1:2", "name": "PageTitle", "tag": "h1"}], "notes": []}
        files = compile_project(design, plan)
        self.assertIn("function Dashboard()", files["src/App.tsx"])
        self.assertIn("<PageTitle />", files["src/App.tsx"])
        self.assertIn("<Dashboard />", files["src/App.tsx"])
        self.assertEqual(NodeParser(files["preview.html"]).nodes["1:2"][0], "h1")
        manifest = json.loads(files["manifest.json"])
        self.assertEqual({node["id"] for node in manifest["nodes"]}, {"1:1", "1:2"})

    def test_invalid_component_plan_is_rejected(self):
        design = normalize_design(frame(children=[label()]))
        invalid = [
            {"node_id": "missing", "name": "Title", "tag": "h1"},
            {"node_id": "1:2", "name": "X);evil();//", "tag": "h1"},
            {"node_id": "1:2", "name": "App", "tag": "h1"},
            {"node_id": "1:2", "name": "Title", "tag": "script"},
            {"node_id": "1:1", "name": "Title", "tag": "p"},
        ]
        for item in invalid:
            with self.subTest(item=item), self.assertRaises(ValueError):
                compile_project(design, {"components": [item]})

    def test_buttons_are_disabled_and_extracted_children_are_phrasing(self):
        design = normalize_design(frame(children=[label()]))
        plan = {"components": [{"node_id": "1:1", "name": "ContinueButton", "tag": "button"}, {"node_id": "1:2", "name": "ButtonLabel", "tag": "p"}]}
        files = compile_project(design, plan)
        parser = NodeParser(files["preview.html"])
        self.assertEqual(parser.nodes["1:1"][0], "button")
        self.assertIn("disabled", parser.nodes["1:1"][1])
        self.assertEqual(parser.nodes["1:2"][0], "span")
        self.assertIn("function ButtonLabel() {\n  return (\n    <span", files["src/App.tsx"])
        self.assertNotIn("onClick", files["src/App.tsx"])
        plan["components"][1]["tag"] = "button"
        with self.assertRaisesRegex(ValueError, "嵌套"):
            compile_project(design, plan)

    def test_css_injection_is_rejected(self):
        design = normalize_design(frame())
        for value in ['red; } body {display:none', 'url(https://evil.test)', '</style><script>alert(1)</script>', 'u\\72l(x)']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                mutated = copy.deepcopy(design)
                mutated["root"]["style"]["backgroundColor"] = value
                compile_project(mutated)

    def test_sample_is_complete_and_compilation_is_deterministic(self):
        sample = Path(__file__).resolve().parents[1] / "data" / "sample-design.json"
        design = normalize_design(json.loads(sample.read_text()))
        first, second = compile_project(design), compile_project(design)
        self.assertEqual(first, second)
        self.assertEqual(design["stats"]["placeholder_count"], 0)
        self.assertGreater(design["stats"]["node_count"], 50)
        self.assertEqual(len(NodeParser(first["preview.html"]).nodes), design["stats"]["node_count"])
        for name in ["package.json", "src/App.tsx", "src/main.tsx", "src/styles.css", "vite.config.ts", "tsconfig.json", "preview.html", "manifest.json"]:
            self.assertIn(name, first)


if __name__ == "__main__":
    unittest.main()
