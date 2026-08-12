import re


def extract_mermaid(text: str) -> str:
    if not text:
        return ""

    fenced = re.findall(r"```(?:mermaid)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    if fenced:
        return fenced[0].strip()

    return text.strip()


def extract_optimized_text(text: str) -> str:
    if not text:
        return ""

    marker_start = "【优化后规范描述】"
    marker_start_alt = "【优化后描述】"
    marker_code = "【Mermaid 流程图代码】"

    if marker_start in text and marker_code in text:
        return text.split(marker_start, 1)[1].split(marker_code, 1)[0].strip()

    if marker_start_alt in text and marker_code in text:
        return text.split(marker_start_alt, 1)[1].split(marker_code, 1)[0].strip()

    fenced_removed = re.sub(r"```(?:mermaid)?[\s\S]*?```", "", text, flags=re.IGNORECASE).strip()
    fenced_removed = fenced_removed.replace(marker_start, "").replace(marker_start_alt, "").strip()
    fenced_removed = fenced_removed.replace(marker_code, "").strip()
    return fenced_removed


def prune_complexity(code: str, mode: str) -> str:
    if mode == "standard":
        return code

    lines = [ln.rstrip() for ln in code.splitlines() if ln.strip()]
    if not lines:
        return code

    head = lines[0]
    body = lines[1:]

    max_lines = 12 if mode == "standard" else 11
    if len(body) > max_lines:
        body = body[:max_lines]

    return "\n".join([head] + body)


def apply_direction(code: str, direction: str) -> str:
    normalized = "LR" if str(direction).upper() == "LR" else "TD"
    if not code:
        return code

    lines = code.splitlines()
    if not lines:
        return code

    first_idx = None
    for idx, line in enumerate(lines):
        if line.strip():
            first_idx = idx
            break

    if first_idx is None:
        return code

    first_line = lines[first_idx].strip()
    if re.match(r"^(flowchart|graph)\s+(TD|LR|TB|BT|RL)\b", first_line, flags=re.IGNORECASE):
        lines[first_idx] = re.sub(
            r"^(flowchart|graph)\s+(TD|LR|TB|BT|RL)\b",
            rf"\1 {normalized}",
            lines[first_idx],
            flags=re.IGNORECASE,
        )
        return "\n".join(lines)

    if re.match(r"^(flowchart|graph)\b", first_line, flags=re.IGNORECASE):
        lines[first_idx] = re.sub(
            r"^(flowchart|graph)\b",
            rf"\1 {normalized}",
            lines[first_idx],
            flags=re.IGNORECASE,
        )
        return "\n".join(lines)

    return f"flowchart {normalized}\n{code}"
