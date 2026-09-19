from pydantic import BaseModel
from typing import Optional, List, Dict
from enum import Enum
from datetime import datetime


class LearningPath(str, Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    FULLSTACK = "fullstack"


class ModuleStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    LOCKED = "locked"


class UserLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class LearningModule(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    order: int
    lessons: List["LearningLesson"]
    status: ModuleStatus = ModuleStatus.NOT_STARTED
    progress: float = 0.0  # 0-100


class LearningLesson(BaseModel):
    id: str
    title: str
    description: str
    type: str  # "theory", "practice", "quiz", "project"
    duration_minutes: int
    is_completed: bool = False
    content_markdown: Optional[str] = None  # Markdown格式的课程内容


class LearningPathData(BaseModel):
    path: LearningPath
    title: str
    description: str
    icon: str
    modules: List[LearningModule]
    total_lessons: int = 0
    completed_lessons: int = 0
    progress: float = 0.0


class AssessmentResult(BaseModel):
    """水平检测结果"""
    user_id: str = "default"
    path_type: str  # LearningPath value
    total_questions: int
    correct_count: int
    score: float  # 0-100
    level: UserLevel
    category_scores: Dict[str, float]  # 各分类得分 {"html_css": 80, "javascript": 60, ...}
    recommended_start_module: str  # 推荐开始的模块ID
    completed_at: datetime
    is_current: bool = True  # 是否为当前有效结果


class UserProgress(BaseModel):
    user_id: str = "default"
    current_path: Optional[LearningPath] = None
    completed_modules: List[str] = []
    completed_lessons: List[str] = []
    current_module: Optional[str] = None
    current_lesson: Optional[str] = None
    started_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    total_study_minutes: int = 0
    assessments: List[AssessmentResult] = []  # 测试结果历史
    skill_levels: Dict[str, float] = {}  # 各分类水平 0-100
    learning_plan: Optional[str] = None  # AI生成的个性化学习计划
    last_session: Optional[dict] = None  # 用户最近的会话数据


class CodeSubmission(BaseModel):
    """代码提交记录"""
    id: str
    user_id: str = "default"
    code: str
    language: str = "python"
    output: str = ""
    error: str = ""
    success: bool = True
    exit_code: int = 0
    lesson_id: Optional[str] = None
    feedback: str = ""
    created_at: datetime


class CoachRecommendation(BaseModel):
    type: str  # "next_lesson", "review", "practice", "challenge"
    title: str
    description: str
    module_id: Optional[str] = None
    lesson_id: Optional[str] = None
    priority: int = 1  # 1-5


class GamificationProfile(BaseModel):
    """游戏化个人档案"""
    user_id: str = "default"
    total_xp: int = 0
    level: int = 1
    streak: int = 0  # 连续学习天数
    last_active_date: str = ""  # "YYYY-MM-DD"
    badges: List[str] = []  # 已获得的徽章ID列表
    xp_log: List[dict] = []  # XP变动记录 [{amount, reason, timestamp}]


class CoachResponse(BaseModel):
    greeting: str
    recommendations: List[CoachRecommendation]
    encouragement: str
    stats: dict
    learning_plan: Optional[str] = None  # AI生成的个性化学习计划


# ===== 水平检测相关模型 =====

class AssessmentQuestion(BaseModel):
    """检测题目"""
    id: str
    category: str  # "html_css", "javascript", "python", "vue", "system_design"
    difficulty: int  # 1-5
    content: str
    question_type: str = "choice"  # "choice" | "code_output" | "code_fill" | "bug_fix"
    code_snippet: Optional[str] = None  # 代码片段（用于代码类题目）
    options: List[str]  # 选择题选项
    correct_answer: str  # "A", "B", "C", "D"
    explanation: str


class AssessmentStartRequest(BaseModel):
    """开始检测请求"""
    path_type: str  # LearningPath value
    user_id: str = "default"


class AssessmentAnswerRequest(BaseModel):
    """提交答案请求"""
    session_id: str
    question_id: str
    answer: str  # "A", "B", "C", "D"
    path_type: str
    user_id: str = "default"


class AssessmentCompleteRequest(BaseModel):
    """完成检测请求"""
    session_id: str
    path_type: str
    user_id: str = "default"


class AssessmentStartResponse(BaseModel):
    """开始检测响应"""
    session_id: str
    question: AssessmentQuestion
    current_index: int
    total_questions: int


class AssessmentAnswerResponse(BaseModel):
    """提交答案响应"""
    is_correct: bool
    correct_answer: str
    explanation: str
    next_question: Optional[AssessmentQuestion]
    current_index: int
    total_questions: int
    is_completed: bool
