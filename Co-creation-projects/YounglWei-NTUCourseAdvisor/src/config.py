"""集中配置：.env 读取 + 路径常量。

所有脚本/模块统一从这里取配置，避免各处重复 load_dotenv。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根 = src/ 的上一级
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
EVAL_DIR = ROOT / "eval"

# .env 在项目根（已被 .gitignore 忽略）
load_dotenv(ROOT / ".env")

ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = os.environ.get("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
ZHIPU_MODEL = os.environ.get("ZHIPU_MODEL", "glm-4-flash")

# Embedding：智谱 OpenAI 兼容接口
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "embedding-3")

# RAG 持久化文件
RAG_DB_PATH = DATA_DIR / "rag.db"
VECTOR_INDEX_PATH = DATA_DIR / "vector_index.json"
COURSE_CARDS_PATH = DATA_DIR / "course_cards.jsonl"
