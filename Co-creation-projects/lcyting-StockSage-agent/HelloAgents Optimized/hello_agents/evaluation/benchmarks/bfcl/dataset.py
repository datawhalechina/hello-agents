"""
BFCL 数据集加载模块

负责加载 Berkeley Function Calling Leaderboard 数据集
支持从BFCL官方数据目录加载，包括测试数据和ground truth
"""

from typing import List, Dict, Any, Optional, Union
import json
from pathlib import Path


class BFCLDataset:
    """BFCL 数据集加载器

    支持从BFCL官方数据目录加载数据集，包括测试数据和ground truth。

    数据集类别（BFCL v4）:
    - simple_python: 简单Python函数调用
    - simple_java: 简单Java函数调用
    - simple_javascript: 简单JavaScript函数调用
    - multiple: 多函数调用
    - parallel: 并行函数调用
    - parallel_multiple: 并行多函数调用
    - irrelevance: 无关检测
    - live_simple: 用户贡献的简单函数调用
    - live_multiple: 用户贡献的多函数调用
    - live_parallel: 用户贡献的并行函数调用
    - multi_turn_base: 多轮对话基础
    - multi_turn_miss_func: 多轮对话缺失函数
    - multi_turn_miss_param: 多轮对话缺失参数
    - multi_turn_long_context: 多轮对话长上下文

    Attributes:
        bfcl_data_dir: BFCL官方数据目录路径
        category: 评估类别
        data: 加载的测试数据列表
        ground_truth: ground truth字典，key为样本id
    """

    # BFCL v4 数据集的标准类别映射
    CATEGORY_MAPPING = {
        "simple_python": "BFCL_v4_simple_python",
        "simple_java": "BFCL_v4_simple_java",
        "simple_javascript": "BFCL_v4_simple_javascript",
        "multiple": "BFCL_v4_multiple",
        "parallel": "BFCL_v4_parallel",
        "parallel_multiple": "BFCL_v4_parallel_multiple",
        "irrelevance": "BFCL_v4_irrelevance",
        "live_simple": "BFCL_v4_live_simple",
        "live_multiple": "BFCL_v4_live_multiple",
        "live_parallel": "BFCL_v4_live_parallel",
        "live_parallel_multiple": "BFCL_v4_live_parallel_multiple",
        "live_irrelevance": "BFCL_v4_live_irrelevance",
        "live_relevance": "BFCL_v4_live_relevance",
        "multi_turn_base": "BFCL_v4_multi_turn_base",
        "multi_turn_miss_func": "BFCL_v4_multi_turn_miss_func",
        "multi_turn_miss_param": "BFCL_v4_multi_turn_miss_param",
        "multi_turn_long_context": "BFCL_v4_multi_turn_long_context",
        "memory": "BFCL_v4_memory",
        "web_search": "BFCL_v4_web_search",
    }

    def __init__(
        self,
        bfcl_data_dir: Union[
            str, Path
        ] = "./temp_gorilla/berkeley-function-call-leaderboard/bfcl_eval/data",
        category: Optional[str] = None,
    ):
        """初始化 BFCL 数据集加载器

        Args:
            bfcl_data_dir: BFCL官方数据目录路径（包含BFCL_v4_*.json文件）
            category: 评估类别，如'simple_python', 'multiple'等
        """
        self.bfcl_data_dir = Path(bfcl_data_dir)
        self.category = category
        self.data = []
        self.ground_truth = {}

        # 验证数据目录
        if not self.bfcl_data_dir.exists():
            print(f"   ⚠️ BFCL数据目录不存在: {self.bfcl_data_dir}")
            print("   请确保已克隆BFCL仓库到正确位置")

        # 验证possible_answer目录
        self.answer_dir = self.bfcl_data_dir / "possible_answer"
        if not self.answer_dir.exists():
            print(f"   ⚠️ Ground truth目录不存在: {self.answer_dir}")

    def load(self) -> List[Dict[str, Any]]:
        """加载数据集（包括测试数据和ground truth）

        Returns:
            数据集列表，每个元素包含问题、函数定义、ground truth等
        """
        if not self.bfcl_data_dir.exists():
            print("   ⚠️ 数据目录不存在，无法加载数据")
            return []

        # 确定要加载的文件
        if self.category:
            # 加载指定类别
            filename = self.CATEGORY_MAPPING.get(self.category)
            if not filename:
                print(f"   ⚠️ 未知类别: {self.category}")
                print(f"   支持的类别: {list(self.CATEGORY_MAPPING.keys())}")
                return []

            self.data = self._load_category(filename)
        else:
            # 加载所有类别（不推荐，数据量大）
            print("   ⚠️ 未指定类别，将加载simple_python作为示例")
            self.data = self._load_category(self.CATEGORY_MAPPING["simple_python"])

        print("✅ BFCL数据集加载完成")
        print(f"   数据目录: {self.bfcl_data_dir}")
        print(f"   类别: {self.category or 'simple_python'}")
        print(f"   样本数: {len(self.data)}")
        print(f"   Ground truth数: {len(self.ground_truth)}")

        return self.data

    def _load_category(self, filename: str) -> List[Dict[str, Any]]:
        """加载指定类别的数据（包括测试数据和ground truth）

        Args:
            filename: 文件名（不含.json后缀），如'BFCL_v4_simple_python'

        Returns:
            测试数据列表
        """
        # 加载测试数据
        test_file = self.bfcl_data_dir / f"{filename}.json"
        if not test_file.exists():
            print(f"   ⚠️ 测试数据文件不存在: {test_file}")
            return []

        test_data = self._load_jsonl_file(test_file)
        print(f"   ✓ 加载测试数据: {test_file.name} ({len(test_data)} 样本)")

        # 加载ground truth
        gt_file = self.answer_dir / f"{filename}.json"
        if gt_file.exists():
            gt_data = self._load_jsonl_file(gt_file)
            # 构建ground truth字典
            for item in gt_data:
                item_id = item.get("id")
                if item_id:
                    self.ground_truth[item_id] = item.get("ground_truth", [])
            print(f"   ✓ 加载ground truth: {gt_file.name} ({len(gt_data)} 样本)")
        else:
            print(f"   ⚠️ Ground truth文件不存在: {gt_file}")

        # 合并测试数据和ground truth
        for item in test_data:
            item_id = item.get("id")
            if item_id and item_id in self.ground_truth:
                item["ground_truth"] = self.ground_truth[item_id]

        return test_data

    def _load_jsonl_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """加载JSONL文件（每行一个JSON对象）

        Args:
            file_path: JSON/JSONL文件路径

        Returns:
            数据列表
        """
        data = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        item = json.loads(line)
                        data.append(item)
                    except json.JSONDecodeError as e:
                        print(f"   ⚠️ JSON解析失败: {e}")
                        continue
        return data

    def get_ground_truth(self, sample_id: str) -> List[Dict[str, Any]]:
        """获取指定样本的ground truth

        Args:
            sample_id: 样本ID

        Returns:
            Ground truth列表
        """
        return self.ground_truth.get(sample_id, [])

    def get_sample(self, index: int) -> Dict[str, Any]:
        """获取单个样本

        Args:
            index: 样本索引

        Returns:
            样本数据
        """
        if not self.data:
            self.load()
        return self.data[index] if index < len(self.data) else {}

    def get_available_categories(self) -> List[str]:
        """获取所有可用的类别

        Returns:
            类别列表
        """
        return list(self.CATEGORY_MAPPING.keys())

    def __len__(self) -> int:
        """返回数据集大小"""
        if not self.data:
            self.load()
        return len(self.data)

    def __iter__(self):
        """迭代器"""
        if not self.data:
            self.load()
        return iter(self.data)
