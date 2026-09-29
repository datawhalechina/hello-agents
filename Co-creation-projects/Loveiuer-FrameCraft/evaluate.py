"""Reproducible offline evaluation; does not call a model or invent visual scores."""

from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

from d2c.pipeline import run_pipeline

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="评估结构保持和可报告的能力边界，不测量像素还原度")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/evaluation.json")
    args = parser.parse_args()
    cases = {
        "auto_layout_sample": json.loads((ROOT / "data/sample-design.json").read_text()),
        "absolute_layout": {
            "id": "9:1", "type": "FRAME", "name": "固定布局",
            "absoluteBoundingBox": {"x": 100, "y": 80, "width": 400, "height": 200},
            "children": [{"id": "9:2", "type": "TEXT", "characters": "坐标来自父画板", "absoluteBoundingBox": {"x": 124, "y": 104, "width": 200, "height": 24}}],
        },
        "unsupported_artwork": {
            "id": "8:1", "type": "FRAME", "name": "未支持素材",
            "layoutMode": "VERTICAL", "children": [
                {"id": "8:2", "type": "VECTOR", "name": "复杂矢量"},
                {"id": "8:3", "type": "RECTANGLE", "fills": [{"type": "IMAGE", "imageRef": "fixture-only"}]},
            ],
        },
    }
    outcomes = []
    for name, payload in cases.items():
        started = time.perf_counter()
        result = run_pipeline(payload, mode="demo")
        outcomes.append({
            "case": name, "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            "stats": result["design"]["stats"], "review": result["review"],
            "metrics": result["metrics"], "warnings": result["design"]["warnings"],
        })
    report = {
        "recorded_at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
        "mode": "demo", "cases": outcomes,
        "visual_fidelity": {"status": "not_measured", "reason": "未取得 Figma 基准渲染图，结构覆盖不能替代像素或人工视觉测量。"},
        "live_figma": {"status": "not_tested", "reason": "离线评估不使用 Figma Token。"},
        "live_llm": {"status": "not_tested", "reason": "离线评估不调用模型。"},
        "react_build": {"status": "not_run", "command": "cd outputs/<run> && npm install && npm run build"},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已评估 {len(outcomes)} 个用例：{args.output}")


if __name__ == "__main__":
    main()
