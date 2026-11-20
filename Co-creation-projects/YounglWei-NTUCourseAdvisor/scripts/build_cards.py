"""构建课程卡片：原始 jsonl → data/course_cards.jsonl。

用法：.venv/Scripts/python.exe scripts/build_cards.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.cards import build_all  # noqa: E402
from src.config import COURSE_CARDS_PATH, DATA_DIR  # noqa: E402


def main():
    cards, stats = build_all(DATA_DIR)

    with open(COURSE_CARDS_PATH, "w", encoding="utf-8") as f:
        for card in cards:
            f.write(json.dumps(card, ensure_ascii=False) + "\n")

    print(f"==> 写出 {COURSE_CARDS_PATH}（{stats['total']} 张卡）")
    for key, value in stats.items():
        print(f"    {key}: {value}")

    # 质量护栏：无简介的卡要点名（影响检索质量）
    if stats["missing_description"]:
        missing = [c["course_code"] for c in cards if not c.get("description")]
        print(f"    [WARN] 无 description 的课程：{', '.join(missing)}")


if __name__ == "__main__":
    main()
