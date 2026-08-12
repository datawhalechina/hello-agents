from typing import List


class PlanConverter:
    @staticmethod
    def _sanitize_lines(text: str) -> List[str]:
        raw_lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in raw_lines if line]
        return lines

    @staticmethod
    def to_mermaid(text: str, direction: str = "TD") -> str:
        lines = PlanConverter._sanitize_lines(text)
        if not lines:
            return f"flowchart {direction}\n    A[空计划]"

        # 支持单行 "A -> B -> C" 快捷输入
        if len(lines) == 1 and "->" in lines[0]:
            segments = [seg.strip() for seg in lines[0].split("->") if seg.strip()]
            lines = segments

        nodes = []
        edges = []

        for idx, label in enumerate(lines):
            node_id = f"N{idx + 1}"
            safe_label = label.replace('"', "'")
            nodes.append(f"    {node_id}[\"{safe_label}\"]")
            if idx > 0:
                prev_id = f"N{idx}"
                edges.append(f"    {prev_id} --> {node_id}")

        body = "\n".join(nodes + edges)
        return f"flowchart {direction}\n{body}"
