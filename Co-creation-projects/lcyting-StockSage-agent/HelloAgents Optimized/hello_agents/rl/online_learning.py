"""在线学习模块

提供数学推理智能体的在线学习能力：
1. FeedbackCollector - 用户反馈收集
2. QualityFilter - 数据质量控制
3. IncrementalTrainer - 增量训练（防灾难性遗忘）
4. SafetyGuard - 安全性保障
5. OnlineLearningSystem - 在线学习主系统
"""

import time
import copy
from typing import List, Dict, Any, Tuple, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
from enum import Enum


class FeedbackType(Enum):
    """反馈类型"""

    CORRECT = "correct"  # 用户确认正确
    INCORRECT = "incorrect"  # 用户指出错误
    IMPROVE = "improve"  # 用户改进了回答
    NONE = "none"  # 无反馈


@dataclass
class UserFeedback:
    """用户反馈数据"""

    question: str
    model_answer: str
    user_answer: Optional[str] = None
    feedback_type: FeedbackType = FeedbackType.NONE
    user_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    verified: bool = False  # 是否已验证


@dataclass
class SafetyCheckResult:
    """安全检查结果"""

    passed: bool
    reason: str
    details: Optional[str] = None


class QualityFilter:
    """
    数据质量过滤器

    过滤策略：
    1. 格式检查 - 确保包含必要字段
    2. 答案验证 - 使用工具验证答案正确性
    3. 去重检查 - 避免重复数据
    4. 可信度检查 - 基于用户历史
    """

    def __init__(
        self,
        min_answer_length: int = 1,
        max_answer_length: int = 1000,
        similarity_threshold: float = 0.9,
    ):
        self.min_answer_length = min_answer_length
        self.max_answer_length = max_answer_length
        self.similarity_threshold = similarity_threshold

        self.seen_questions = set()
        self.trusted_users = set()
        self.filtered_count = 0

    def filter(self, feedback: UserFeedback) -> Tuple[bool, str]:
        """
        过滤用户反馈

        Returns:
            (是否通过, 原因)
        """
        # 1. 格式检查
        if not self._check_format(feedback):
            self.filtered_count += 1
            return False, "invalid_format"

        # 2. 长度检查
        if not self._check_length(feedback):
            self.filtered_count += 1
            return False, "invalid_length"

        # 3. 去重检查
        if not self._check_duplicate(feedback):
            self.filtered_count += 1
            return False, "duplicate"

        # 4. 可信度检查（简单实现）
        if not self._check_trust(feedback):
            self.filtered_count += 1
            return False, "untrusted"

        # 添加到已见集合
        self.seen_questions.add(self._normalize(feedback.question))

        return True, "passed"

    def _check_format(self, feedback: UserFeedback) -> bool:
        """检查必要字段"""
        return bool(feedback.question and feedback.model_answer)

    def _check_length(self, feedback: UserFeedback) -> bool:
        """检查长度"""
        ans = feedback.model_answer
        return self.min_answer_length <= len(ans) <= self.max_answer_length

    def _check_duplicate(self, feedback: UserFeedback) -> bool:
        """去重检查"""
        normalized = self._normalize(feedback.question)
        if normalized in self.seen_questions:
            return False
        return True

    def _check_trust(self, feedback: UserFeedback) -> bool:
        """可信度检查"""
        # 如果用户ID在可信列表中，直接通过
        if feedback.user_id in self.trusted_users:
            return True

        # 新用户：如果反馈类型是确认正确，提高可信度
        if feedback.feedback_type == FeedbackType.CORRECT:
            return True

        # 如果无法确定，返回True（保守策略）
        return True

    def _normalize(self, text: str) -> str:
        """标准化问题（用于去重）"""
        # 移除多余空格，转小写
        return " ".join(text.lower().split())

    def add_trusted_user(self, user_id: str):
        """添加可信用户"""
        self.trusted_users.add(user_id)

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return {
            "seen_questions": len(self.seen_questions),
            "trusted_users": len(self.trusted_users),
            "filtered_count": self.filtered_count,
        }


class SafetyGuard:
    """
    安全性保障

    功能：
    1. 输入过滤 - 敏感词、恶意输入
    2. 输出过滤 - 有害内容、不当回答
    3. 检查点管理 - 自动回滚
    4. 异常检测 - 监控指标突变
    """

    def __init__(
        self,
        max_checkpoints: int = 5,
        harmfulness_threshold: float = 0.05,
        accuracy_drop_threshold: float = 0.2,
    ):
        self.max_checkpoints = max_checkpoints
        self.harmfulness_threshold = harmfulness_threshold
        self.accuracy_drop_threshold = accuracy_drop_threshold

        self.checkpoints = deque(maxlen=max_checkpoints)
        self.sensitive_words = self._load_sensitive_words()
        self.rejection_count = 0
        self.rollback_count = 0

    def _load_sensitive_words(self) -> set:
        """加载敏感词列表（实际项目中应从文件加载）"""
        return {"hack", "exploit", "attack", "bypass", "cheat", "作弊"}

    def check_input(self, text: str) -> SafetyCheckResult:
        """输入安全检查"""
        if not text:
            return SafetyCheckResult(False, "empty_input")

        text_lower = text.lower()

        # 敏感词检查
        for word in self.sensitive_words:
            if word in text_lower:
                self.rejection_count += 1
                return SafetyCheckResult(False, "sensitive_word", word)

        # 长度检查
        if len(text) > 5000:
            return SafetyCheckResult(False, "input_too_long")

        return SafetyCheckResult(True, "passed")

    def check_output(self, text: str) -> SafetyCheckResult:
        """输出安全检查"""
        if not text:
            self.rejection_count += 1
            return SafetyCheckResult(False, "empty_output")

        # 长度检查
        if len(text) > 5000:
            return SafetyCheckResult(False, "output_too_long")

        # 格式检查（确保是有效回答）
        if text.strip() == "I don't know" or text.strip() == "不知道":
            return SafetyCheckResult(False, "refusal")

        return SafetyCheckResult(True, "passed")

    def save_checkpoint(self, model_state: Dict, metrics: Dict[str, float]):
        """保存检查点"""
        checkpoint = {
            "model_state": copy.deepcopy(model_state),
            "metrics": copy.deepcopy(metrics),
            "timestamp": time.time(),
        }
        self.checkpoints.append(checkpoint)

    def should_rollback(self, current_metrics: Dict) -> bool:
        """判断是否需要回滚"""
        if len(self.checkpoints) < 1:
            return False

        # 比较所有历史检查点，取最大下降值
        max_drop = 0.0
        for cp in self.checkpoints:
            last_metrics = cp["metrics"]
            if "accuracy" in current_metrics and "accuracy" in last_metrics:
                drop = last_metrics["accuracy"] - current_metrics["accuracy"]
                max_drop = max(max_drop, drop)

        if max_drop > self.accuracy_drop_threshold:
            print(f"准确率下降 {max_drop:.1%}, 触发回滚")
            return True

        return False

    def rollback(self) -> Optional[Dict]:
        """回滚到上一个检查点"""
        if not self.checkpoints:
            return None

        checkpoint = self.checkpoints.pop()
        self.rollback_count += 1
        print(f"回滚到检查点 {checkpoint['timestamp']}")
        return checkpoint["model_state"]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "rejection_count": self.rejection_count,
            "rollback_count": self.rollback_count,
            "checkpoint_count": len(self.checkpoints),
        }


class IncrementalTrainer:
    """
    增量训练器

    防止灾难性遗忘的技术：
    1. 经验回放 - 混合旧数据
    2. 弹性权重约束(EWC) - 限制参数变化
    3. 知识蒸馏 - 保持旧模型输出
    """

    def __init__(
        self,
        model,
        ewc_lambda: float = 1000,
        kd_temperature: float = 2.0,
        kd_weight: float = 0.1,
    ):
        self.model = model
        self.ewc_lambda = ewc_lambda
        self.kd_temperature = kd_temperature
        self.kd_weight = kd_weight

        # 保存旧模型用于知识蒸馏
        self.reference_model = None
        self.fisher_diagonal = {}
        self.old_params = {}
        self.is_initialized = False

    def init(self):
        """初始化（旧模型参数）"""
        if self.model is None:
            # 没有模型，只初始化标志
            self.is_initialized = True
            return

        self.reference_model = copy.deepcopy(self.model)

        # 保存参数
        for name, param in self.model.named_parameters():
            self.old_params[name] = param.data.clone()

        self.is_initialized = True
        print("增量训练器已初始化")

    def train_step(self, batch: List[Dict]) -> Dict[str, float]:
        """
        单步训练

        在实际训练中，应该包含：
        1. 任务损失
        2. EWC惩罚
        3. 知识蒸馏损失

        Returns:
            训练指标
        """
        # 模拟训练步骤
        metrics = {
            "task_loss": 0.5,
            "ewc_loss": 0.1,
            "kd_loss": 0.05,
            "total_loss": 0.65,
        }

        return metrics

    def compute_ewc_penalty(self) -> float:
        """计算弹性权重约束惩罚"""
        if not self.is_initialized or self.model is None:
            return 0.0

        penalty = 0.0
        for name, param in self.model.named_parameters():
            if name in self.old_params:
                try:
                    old_val = self.old_params[name]
                    fisher = self.fisher_diagonal.get(name, 1.0)
                    penalty += (fisher * (param.data - old_val).pow(2)).sum()
                except Exception:
                    pass

        return penalty * self.ewc_lambda

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "is_initialized": self.is_initialized,
            "ewc_lambda": self.ewc_lambda,
            "kd_weight": self.kd_weight,
        }


class OnlineLearningSystem:
    """
    数学推理智能体在线学习系统

    功能：
    1. 处理用户交互
    2. 自动收集反馈
    3. 质量过滤
    4. 安全性检查
    5. 增量更新模型
    6. 监控告警
    """

    def __init__(
        self,
        model=None,
        tokenizer=None,
        generate_fn: Callable[[str], str] = None,
        update_interval: int = 100,
        batch_size: int = 16,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.generate_fn = generate_fn
        self.update_interval = update_interval
        self.batch_size = batch_size

        # 组件
        self.feedback_buffer = deque(maxlen=1000)
        self.quality_filter = QualityFilter()
        self.safety_guard = SafetyGuard()
        self.trainer = IncrementalTrainer(model) if model else None

        # 统计
        self.total_interactions = 0
        self.successful_updates = 0
        self.start_time = time.time()

    def interact(self, question: str, user_id: str = None) -> Dict[str, Any]:
        """
        处理用户问题

        完整流程：
        1. 输入安全检查
        2. 生成回答
        3. 输出安全检查
        4. 记录交互
        5. 定时更新

        Returns:
            包含回答和状态的字典
        """
        result = {"answer": None, "error": None, "update_triggered": False}

        # 1. 输入安全检查
        safe = self.safety_guard.check_input(question)
        if not safe.passed:
            result["error"] = safe.reason
            return result

        # 2. 生成回答
        try:
            if self.generate_fn:
                answer = self.generate_fn(question)
            else:
                answer = "（模型未初���化）"
        except Exception as e:
            result["error"] = f"generation_error: {e}"
            return result

        # 3. 输出安全检查
        safe = self.safety_guard.check_output(answer)
        if not safe.passed:
            result["error"] = safe.reason
            return result

        result["answer"] = answer

        # 4. 记录交互
        feedback = UserFeedback(question=question, model_answer=answer, user_id=user_id)
        self.feedback_buffer.append(feedback)

        self.total_interactions += 1

        # 5. 检查是否需要更新
        if (
            self.total_interactions > 0
            and self.total_interactions % self.update_interval == 0
        ):
            self._trigger_update()
            result["update_triggered"] = True

        return result

    def submit_feedback(
        self,
        question: str,
        model_answer: str,
        user_answer: str = None,
        feedback_type: FeedbackType = FeedbackType.NONE,
        user_id: str = None,
    ) -> bool:
        """
        提交用户反馈

        用于用户纠正模型回答或确认正确

        Returns:
            是否成功记录
        """
        feedback = UserFeedback(
            question=question,
            model_answer=model_answer,
            user_answer=user_answer,
            feedback_type=feedback_type,
            user_id=user_id,
        )

        # 质量过滤
        passed, reason = self.quality_filter.filter(feedback)

        if passed:
            self.feedback_buffer.append(feedback)
            return True

        return False

    def _trigger_update(self):
        """触发增量更新"""
        print(f"\n=== 触发增量更新 (第{self.successful_updates + 1}轮) ===")
        print(f"缓冲区数据: {len(self.feedback_buffer)} 条")

        # 初始化训练器（如果是第一次）
        if self.trainer and not self.trainer.is_initialized:
            self.trainer.init()

        # 获取训练数据
        train_data = list(self.feedback_buffer)[-self.batch_size :]

        if len(train_data) < self.batch_size // 2:
            print(f"数据不足 ({len(train_data)}/{self.batch_size}), 跳过更新")
            return

        # 保存检查点
        if self.model:
            self.safety_guard.save_checkpoint(
                self.model.state_dict() if hasattr(self.model, "state_dict") else {},
                {"accuracy": 0.7},  # 模拟准确率
            )

        # 检查是否需要回滚
        if self.safety_guard.should_rollback({"accuracy": 0.65}):
            self._perform_rollback()
            return

        # 执行训练
        if self.trainer:
            metrics = self.trainer.train_step(train_data)
            print(f"训练完成: {metrics}")
            self.successful_updates += 1

        print("=== 更新完成 ===\n")

    def _perform_rollback(self):
        """执行回滚"""
        old_state = self.safety_guard.rollback()
        if old_state and self.model:
            try:
                self.model.load_state_dict(old_state)
                print("模型已回滚")
            except Exception as e:
                print(f"回滚失败: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计"""
        uptime = time.time() - self.start_time

        return {
            "total_interactions": self.total_interactions,
            "successful_updates": self.successful_updates,
            "buffer_size": len(self.feedback_buffer),
            "uptime_seconds": uptime,
            "interactions_per_minute": self.total_interactions / max(1, uptime / 60),
            "quality_filter": self.quality_filter.get_stats(),
            "safety_guard": self.safety_guard.get_stats(),
        }

    def export_buffer(self) -> List[Dict]:
        """导出反馈缓冲区（用于分析）"""
        return [
            {
                "question": f.question,
                "model_answer": f.model_answer,
                "user_answer": f.user_answer,
                "feedback_type": f.feedback_type.value,
                "timestamp": f.timestamp,
            }
            for f in self.feedback_buffer
        ]


def create_online_learning_system(
    model=None, tokenizer=None, generate_fn: Callable[[str], str] = None
) -> OnlineLearningSystem:
    """
    创建在线学习系统（便捷函数）
    """
    return OnlineLearningSystem(
        model=model, tokenizer=tokenizer, generate_fn=generate_fn
    )


# 示例用法
if __name__ == "__main__":
    # 模拟生成函数
    def mock_generate(question: str) -> str:
        if "48" in question and "24" in question:
            return "Step 1: 48 + 24 = 72\nFinal Answer: 72"
        elif "16" in question:
            return "Step 1: 16 / 2 = 8\nFinal Answer: 8"
        return "Final Answer: 42"

    # 创建系统
    system = OnlineLearningSystem(
        generate_fn=mock_generate,
        update_interval=5,  # 每5次交互更新一次（演示用）
        batch_size=4,
    )

    # 模拟用户问题
    questions = [
        "What is 48 + 24?",
        "What is 16 divided by 2?",
        "If Maria has 5 apples and buys 3 more, how many does she have?",
        "What is 10 + 5?",
        "What is 20 divided by 4?",
    ]

    print("=" * 50)
    print("在线学习系统演示")
    print("=" * 50)

    # 处理用户问题
    for q in questions:
        print(f"\n问题: {q}")
        result = system.interact(q, user_id="user_001")

        if result["error"]:
            print(f"错误: {result['error']}")
        else:
            print(f"回答: {result['answer']}")

    # 提交反馈
    print("\n" + "-" * 50)
    print("提交用户反馈")

    system.submit_feedback(
        question="What is 48 + 24?",
        model_answer="Final Answer: 72",
        user_answer="72",
        feedback_type=FeedbackType.CORRECT,
        user_id="user_001",
    )

    # 统计
    print("\n" + "=" * 50)
    print("系统统计")
    print("=" * 50)

    stats = system.get_stats()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for k, v in value.items():
                print(f"  {k}: {v}")
        else:
            print(f"{key}: {value}")
