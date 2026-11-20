"""D1 冒烟：智谱 embedding 接口连通性、维度、中英语义。

用 OpenAI 兼容客户端直连智谱 /api/paas/v4/embeddings，
验证 OpenAIEmbeddingProvider 可用性（后者走同一 client.embeddings.create）。

用法：.venv/Scripts/python.exe scripts/smoke_embedding.py
"""

import math
from pathlib import Path
import sys

from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import ZHIPU_API_KEY, ZHIPU_BASE_URL  # noqa: E402


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb)


def main():
    load_dotenv()
    client = OpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL)

    texts = [
        "Discrete-time system modelling and analysis. State-space design methods.",  # EE6203 风格英文
        "数字控制与自动化",  # 中文查询
        "Introduction to biomolecular engineering",  # CB1131 英文
    ]
    for model in ("embedding-3", "embedding-2"):
        try:
            resp = client.embeddings.create(model=model, input=texts)
        except Exception as exc:  # noqa: BLE001
            print(f"[{model}] 调用失败：{type(exc).__name__}: {exc}")
            continue

        vectors = [item.embedding for item in sorted(resp.data, key=lambda r: r.index)]
        dim = len(vectors[0])
        print(f"[{model}] OK：{len(vectors)} 条向量，维度 {dim}")

        # 中英语义健全性：EE6203 英文 与 中文"数字控制" 的相似度，
        # 应明显高于其与 CB1131 英文的相似度
        s_zh = cosine(vectors[0], vectors[1])
        s_other = cosine(vectors[0], vectors[2])
        verdict = "通过" if s_zh > s_other else "异常"
        print(f"    sim(EE6203英文, 中文'数字控制') = {s_zh:.4f}")
        print(f"    sim(EE6203英文, CB1131英文)   = {s_other:.4f}")
        print(f"    中英语义判别：{verdict}")


if __name__ == "__main__":
    main()
