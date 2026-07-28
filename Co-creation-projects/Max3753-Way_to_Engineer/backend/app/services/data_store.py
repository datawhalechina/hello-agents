"""
JSON持久化存储服务
将用户进度和测试结果保存到本地JSON文件
"""
import json
import os
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from ..models.learning import (
    UserProgress, AssessmentResult, LearningPath, UserLevel, GamificationProfile,
    CodeSubmission
)

# 数据存储目录
DATA_DIR = Path(__file__).parent.parent.parent / "data"
USER_PROGRESS_FILE = DATA_DIR / "user_progress.json"
ASSESSMENTS_FILE = DATA_DIR / "assessments.json"
GAMIFICATION_FILE = DATA_DIR / "gamification.json"
SUBMISSIONS_FILE = DATA_DIR / "submissions.json"


class DataStore:
    """JSON文件存储服务"""

    def __init__(self):
        # 确保数据目录存在
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # 初始化进度存储
        self._progress: Dict[str, UserProgress] = {}
        self._load_progress()

        # 初始化测试结果存储
        self._assessments: Dict[str, List[AssessmentResult]] = {}
        self._load_assessments()

        # 初始化游戏化存储
        self._gamifications: Dict[str, GamificationProfile] = {}
        self._load_gamifications()

        # 初始化代码提交存储
        self._submissions: Dict[str, List[CodeSubmission]] = {}
        self._load_submissions()

    def _load_progress(self):
        """从文件加载用户进度"""
        if USER_PROGRESS_FILE.exists():
            try:
                with open(USER_PROGRESS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for user_id, progress_data in data.items():
                    # 处理 datetime 字段
                    for field in ["started_at", "last_activity_at"]:
                        if progress_data.get(field):
                            progress_data[field] = datetime.fromisoformat(
                                progress_data[field]
                            )
                    # 处理 assessments 中的 datetime
                    for assessment in progress_data.get("assessments", []):
                        if assessment.get("completed_at"):
                            assessment["completed_at"] = datetime.fromisoformat(
                                assessment["completed_at"]
                            )
                    self._progress[user_id] = UserProgress(**progress_data)
                print(f"[OK] 已加载 {len(self._progress)} 个用户进度")
            except Exception as e:
                print(f"[WARN] 加载用户进度失败: {e}")
                self._progress = {}

    def _save_progress(self):
        """保存用户进度到文件"""
        try:
            data = {}
            for user_id, progress in self._progress.items():
                progress_dict = progress.model_dump()
                # 处理 datetime 序列化
                for field in ["started_at", "last_activity_at"]:
                    if progress_dict.get(field):
                        progress_dict[field] = progress_dict[field].isoformat()
                for assessment in progress_dict.get("assessments", []):
                    if assessment.get("completed_at"):
                        assessment["completed_at"] = assessment["completed_at"].isoformat()
                data[user_id] = progress_dict

            with open(USER_PROGRESS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] 保存用户进度失败: {e}")

    def _load_assessments(self):
        """从文件加载测试结果"""
        if ASSESSMENTS_FILE.exists():
            try:
                with open(ASSESSMENTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for user_id, assessments_data in data.items():
                    self._assessments[user_id] = []
                    for assessment in assessments_data:
                        if assessment.get("completed_at"):
                            assessment["completed_at"] = datetime.fromisoformat(
                                assessment["completed_at"]
                            )
                        self._assessments[user_id].append(
                            AssessmentResult(**assessment)
                        )
                print(f"[OK] 已加载 {len(self._assessments)} 个用户测试记录")
            except Exception as e:
                print(f"[WARN] 加载测试记录失败: {e}")
                self._assessments = {}

    def _save_assessments(self):
        """保存测试结果到文件"""
        try:
            data = {}
            for user_id, assessments in self._assessments.items():
                data[user_id] = []
                for assessment in assessments:
                    assessment_dict = assessment.model_dump()
                    if assessment_dict.get("completed_at"):
                        assessment_dict["completed_at"] = (
                            assessment_dict["completed_at"].isoformat()
                        )
                    data[user_id].append(assessment_dict)

            with open(ASSESSMENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] 保存测试记录失败: {e}")

    # ==================== 游戏化存储 ====================

    def _load_gamifications(self):
        """从文件加载游戏化数据"""
        if GAMIFICATION_FILE.exists():
            try:
                with open(GAMIFICATION_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for user_id, profile_data in data.items():
                    self._gamifications[user_id] = GamificationProfile(**profile_data)
                print(f"[OK] 已加载 {len(self._gamifications)} 个游戏化档案")
            except Exception as e:
                print(f"[WARN] 加载游戏化数据失败: {e}")
                self._gamifications = {}

    def _save_gamifications(self):
        """保存游戏化数据到文件"""
        try:
            data = {}
            for user_id, profile in self._gamifications.items():
                data[user_id] = profile.model_dump()
            with open(GAMIFICATION_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] 保存游戏化数据失败: {e}")

    def get_gamification(self, user_id: str = "default") -> Optional[GamificationProfile]:
        """获取用户游戏化档案"""
        return self._gamifications.get(user_id)

    def save_gamification(self, profile: GamificationProfile):
        """保存用户游戏化档案"""
        self._gamifications[profile.user_id] = profile
        self._save_gamifications()

    # ==================== 用户进度 API ====================

    def get_user_progress(
        self, user_id: str = "default"
    ) -> Optional[UserProgress]:
        """获取用户进度"""
        return self._progress.get(user_id)

    def save_user_progress(self, progress: UserProgress):
        """保存用户进度"""
        self._progress[progress.user_id] = progress
        self._save_progress()

    def update_user_progress(
        self,
        user_id: str = "default",
        **kwargs
    ) -> UserProgress:
        """更新用户进度"""
        progress = self._progress.get(user_id)
        if not progress:
            progress = UserProgress(user_id=user_id)

        for key, value in kwargs.items():
            if hasattr(progress, key):
                setattr(progress, key, value)

        progress.last_activity_at = datetime.now()
        self._progress[user_id] = progress
        self._save_progress()
        return progress

    # ==================== 测试结果 API ====================

    def get_user_assessments(
        self, user_id: str = "default", path_type: str = None
    ) -> List[AssessmentResult]:
        """获取用户测试结果"""
        assessments = self._assessments.get(user_id, [])
        if path_type:
            assessments = [a for a in assessments if a.path_type == path_type]
        return assessments

    def get_current_assessment(
        self, user_id: str = "default", path_type: str = None
    ) -> Optional[AssessmentResult]:
        """获取用户当前有效的测试结果"""
        assessments = self.get_user_assessments(user_id, path_type)
        # 返回最新的有效结果
        for assessment in reversed(assessments):
            if assessment.is_current:
                return assessment
        return assessments[-1] if assessments else None

    def save_assessment(self, assessment: AssessmentResult):
        """保存测试结果"""
        user_id = assessment.user_id
        if user_id not in self._assessments:
            self._assessments[user_id] = []

        # 如果是"学习前重测"，将旧结果标记为非当前
        if assessment.is_current:
            for existing in self._assessments[user_id]:
                if existing.path_type == assessment.path_type:
                    existing.is_current = False

        self._assessments[user_id].append(assessment)
        self._save_assessments()
        self._save_user_assessment_to_progress(assessment)

    def _save_user_assessment_to_progress(self, assessment: AssessmentResult):
        """同步测试结果到用户进度"""
        progress = self._progress.get(assessment.user_id)
        if progress:
            progress.assessments = self.get_user_assessments(
                assessment.user_id, assessment.path_type
            )
            progress.skill_levels = assessment.category_scores
            self._save_progress()

    def has_assessment(
        self, user_id: str = "default", path_type: str = None
    ) -> bool:
        """检查用户是否已测试"""
        if path_type:
            return len(self.get_user_assessments(user_id, path_type)) > 0
        return len(self._assessments.get(user_id, [])) > 0

    # ==================== 代码提交流持久化 ====================

    def _load_submissions(self):
        """从文件加载代码提交记录"""
        if SUBMISSIONS_FILE.exists():
            try:
                with open(SUBMISSIONS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for user_id, submissions_data in data.items():
                    self._submissions[user_id] = []
                    for sub in submissions_data:
                        if sub.get("created_at"):
                            sub["created_at"] = datetime.fromisoformat(sub["created_at"])
                        self._submissions[user_id].append(CodeSubmission(**sub))
                print(f"[OK] 已加载 {sum(len(v) for v in self._submissions.values())} 条代码提交记录")
            except Exception as e:
                print(f"[WARN] 加载代码提交记录失败: {e}")
                self._submissions = {}

    def _save_submissions(self):
        """保存代码提交记录到文件"""
        try:
            data = {}
            for user_id, submissions in self._submissions.items():
                data[user_id] = []
                for sub in submissions:
                    sub_dict = sub.model_dump()
                    if sub_dict.get("created_at"):
                        sub_dict["created_at"] = sub_dict["created_at"].isoformat()
                    data[user_id].append(sub_dict)
            with open(SUBMISSIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] 保存代码提交记录失败: {e}")

    def save_submission(self, submission: CodeSubmission):
        """保存代码提交记录"""
        user_id = submission.user_id
        if user_id not in self._submissions:
            self._submissions[user_id] = []
        self._submissions[user_id].append(submission)
        self._save_submissions()

    def get_user_submissions(
        self, user_id: str = "default", limit: int = 20
    ) -> List[CodeSubmission]:
        """获取用户最近提交记录"""
        submissions = self._submissions.get(user_id, [])
        return sorted(submissions, key=lambda s: s.created_at, reverse=True)[:limit]


# 全局单例
data_store = DataStore()
