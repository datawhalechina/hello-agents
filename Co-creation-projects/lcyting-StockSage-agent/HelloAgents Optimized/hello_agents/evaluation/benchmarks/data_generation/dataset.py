"""
AIME Dataset Loader

加载AIME数学题目数据集，支持：
- 从HuggingFace加载真题数据
- 加载生成的题目数据
- 数据格式统一化
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from huggingface_hub import snapshot_download


class AIDataset:
    """AIME数据集加载器"""

    def __init__(
        self,
        dataset_type: str = "generated",  # "generated" or "real"
        data_path: Optional[str] = None,
        year: Optional[int] = None,  # 用于真题数据，如2024, 2025
        cache_dir: Optional[str] = None,
    ):
        """
        初始化AIME数据集

        Args:
            dataset_type: 数据集类型，"generated"（生成的）或"real"（真题）
            data_path: 本地数据路径（用于generated类型）
            year: AIME年份（用于real类型），如2024, 2025
            cache_dir: 缓存目录
        """
        self.dataset_type = dataset_type
        self.data_path = data_path
        self.year = year
        self.cache_dir = cache_dir or os.path.expanduser("~/.cache/hello_agents/aime")

        self.problems: List[Dict[str, Any]] = []

    def load(self) -> List[Dict[str, Any]]:
        """
        加载数据集

        Returns:
            问题列表，每个问题包含：
            - problem_id: 问题ID
            - problem: 问题描述
            - answer: 答案
            - solution: 解答过程（可选）
            - difficulty: 难度（可选）
            - topic: 主题（可选）
        """
        if self.dataset_type == "generated":
            return self._load_generated_data()
        elif self.dataset_type == "real":
            return self._load_real_data()
        else:
            raise ValueError(f"Unknown dataset_type: {self.dataset_type}")

    def _load_generated_data(self) -> List[Dict[str, Any]]:
        """加载生成的数据"""
        if not self.data_path:
            raise ValueError("data_path is required for generated dataset")

        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Data file not found: {self.data_path}")

        print(f"📥 加载生成数据: {self.data_path}")

        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 统一数据格式
        problems = []
        for idx, item in enumerate(data):
            problem = {
                "problem_id": item.get("id", f"gen_{idx}"),
                "problem": item.get("problem", item.get("question", "")),
                "answer": item.get("answer", ""),
                "solution": item.get("solution", item.get("reasoning", "")),
                "difficulty": item.get("difficulty", None),
                "topic": item.get("topic", item.get("category", None)),
            }
            problems.append(problem)

        self.problems = problems
        print(f"✅ 加载了 {len(problems)} 个生成题目")
        return problems

    def _load_real_data(self) -> List[Dict[str, Any]]:
        """从HuggingFace加载AIME真题数据"""
        if not self.year:
            raise ValueError("year is required for real dataset")

        print(f"📥 从HuggingFace加载AIME {self.year}真题...")

        try:
            # 使用AIME 2025数据集
            repo_id = "math-ai/aime25"
            # 使用snapshot_download（JSONL格式）

            print(f"   使用数据集: {repo_id}")

            # 使用snapshot_download下载文件
            local_dir = snapshot_download(
                repo_id=repo_id, repo_type="dataset", cache_dir=self.cache_dir
            )

            # 查找JSONL数据文件
            data_files = list(Path(local_dir).glob("*.jsonl"))

            if not data_files:
                raise FileNotFoundError(f"No JSONL data file found in {repo_id}")

            data_file = data_files[0]
            print(f"   ✓ 找到数据文件: {data_file.name}")

            # 加载JSONL数据
            data = []
            with open(data_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data.append(json.loads(line))

            # 统一数据格式（AIME 2025使用小写字段名）
            problems = []
            for idx, item in enumerate(data):
                problem = {
                    "problem_id": item.get("id", f"aime_2025_{idx}"),
                    "problem": item.get("problem", ""),
                    "answer": item.get("answer", ""),
                    "solution": item.get("solution", ""),  # AIME 2025没有solution字段
                    "difficulty": item.get("difficulty", None),
                    "topic": item.get("topic", None),
                }
                problems.append(problem)

            self.problems = problems
            print(f"✅ 加载了 {len(problems)} 个AIME {self.year}真题")
            return problems

        except Exception as e:
            print(f"❌ 加载失败: {e}")
            print("提示: 请确保已安装huggingface_hub并配置HF_TOKEN")
            raise

    def get_problem(self, problem_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取问题"""
        for problem in self.problems:
            if problem["problem_id"] == problem_id:
                return problem
        return None

    def get_problems_by_topic(self, topic: str) -> List[Dict[str, Any]]:
        """根据主题获取问题"""
        return [p for p in self.problems if p.get("topic") == topic]

    def get_problems_by_difficulty(
        self, min_diff: int, max_diff: int
    ) -> List[Dict[str, Any]]:
        """根据难度范围获取问题"""
        return [
            p
            for p in self.problems
            if p.get("difficulty") and min_diff <= p["difficulty"] <= max_diff
        ]

    def __len__(self) -> int:
        """返回数据集大小"""
        return len(self.problems)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        """支持索引访问"""
        return self.problems[idx]
