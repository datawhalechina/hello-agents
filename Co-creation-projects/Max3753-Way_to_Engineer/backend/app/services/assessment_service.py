"""
水平检测服务
使用AI实时生成测试题目，评估用户水平
"""
import json
import uuid
from typing import List, Optional, Dict
from datetime import datetime

from ..models.learning import (
    AssessmentQuestion, AssessmentResult, UserLevel, LearningPath
)
from .llm_service import get_llm
from .learning_content import get_learning_path
from .data_store import data_store


# 测试配置
TOTAL_QUESTIONS = 10


# 各路径的测试分类定义
PATH_CATEGORIES = {
    LearningPath.FRONTEND: {
        "html_css": "HTML/CSS基础",
        "javascript": "JavaScript核心",
        "vue": "Vue.js框架",
        "browser_apis": "浏览器API与DOM",
    },
    LearningPath.BACKEND: {
        "python": "Python基础",
        "api_design": "REST API设计",
        "database": "数据库操作",
        "system_design": "系统设计",
    },
    LearningPath.FULLSTACK: {
        "html_css": "HTML/CSS",
        "javascript": "JavaScript",
        "python": "Python",
        "vue": "Vue.js",
        "api_design": "API设计",
    },
}


def get_categories_for_path(path_type: str) -> Dict[str, str]:
    """获取指定路径的测试分类"""
    try:
        path = LearningPath(path_type)
        return PATH_CATEGORIES.get(path, PATH_CATEGORIES[LearningPath.FRONTEND])
    except ValueError:
        return PATH_CATEGORIES[LearningPath.FRONTEND]


def get_modules_for_path(path_type: str) -> List[Dict]:
    """获取指定路径的模块信息"""
    try:
        path = LearningPath(path_type)
        path_data = get_learning_path(path)
        return [
            {
                "id": m.id,
                "title": m.title,
                "description": m.description,
                "lessons": [l.title for l in m.lessons],
            }
            for m in path_data.modules
        ]
    except ValueError:
        return []


# ===== AI题目生成 =====


def generate_assessment_questions(path_type: str) -> List[AssessmentQuestion]:
    """使用AI生成测试题目"""
    categories = get_categories_for_path(path_type)
    modules = get_modules_for_path(path_type)

    categories_text = ", ".join([f"{k}({v})" for k, v in categories.items()])
    modules_text = json.dumps([m["title"] for m in modules], ensure_ascii=False)

    prompt = """请为"{path_type}"学习路径生成{total}道编程水平测试题。

测试分类：{categories}
涉及模块：{modules}

要求：
1. 混合4种题型：choice（选择题/知识题）、code_output（预测输出）、code_fill（代码填空）、bug_fix（找Bug）
2. 每道题包含：id（q1到q10）、category（分类key）、difficulty（难度1-5）、question_type（题型）、content（题目描述，用中文）、code_snippet（代码片段，选择题填null）、options（A/B/C/D选项，用中文）、correct_answer（正确答案字母）、explanation（解析，用中文）
3. 代码题必须包含5-15行的代码片段
4. 难度分布：简单30%、中等40%、困难30%
5. 每个分类至少2道题
6. 所有题目内容、选项、解析必须用中文输出

只输出JSON数组：
[
  {{"id":"q1","category":"html_css","difficulty":2,"question_type":"choice","content":"关于HTML语义化标签的说法，正确的是？","code_snippet":null,"options":["A. <div>是语义化标签","B. <header>表示页面头部区域","C. <span>是块级元素","D. <article>只能用于博客文章"],"correct_answer":"B","explanation":"<header>是HTML5语义化标签，表示页面或区块的头部区域。div是无语义容器，span是行内元素，article可用于任何独立内容。"}},
  {{"id":"q2","category":"javascript","difficulty":3,"question_type":"code_output","content":"以下代码的输出是什么？","code_snippet":"const arr = [1, 2, 3];\\nconst result = arr.map(x => x * 2).filter(x => x > 3);\\nconsole.log(result);","options":["A. [2, 4, 6]","B. [4, 6]","C. [2, 4]","D. [6]"],"correct_answer":"B","explanation":"map将每个元素乘2得到[2,4,6]，filter筛选大于3的元素得到[4,6]。"}}
]""".format(
        path_type=path_type,
        total=TOTAL_QUESTIONS,
        categories=categories_text,
        modules=modules_text,
    )

    try:
        llm = get_llm()
        messages = [{"role": "user", "content": prompt}]
        response = llm.invoke(messages)
        content = response if isinstance(response, str) else str(response)

        # 提取JSON
        start_idx = content.find("[")
        end_idx = content.rfind("]") + 1

        if start_idx == -1 or end_idx == 0:
            print("[ERROR] AI返回格式错误，无法解析题目")
            return _get_fallback_questions(path_type)

        questions_data = json.loads(content[start_idx:end_idx])

        questions = []
        for q in questions_data:
            questions.append(AssessmentQuestion(
                id=q["id"],
                category=q["category"],
                difficulty=q.get("difficulty", 3),
                content=q["content"],
                question_type=q.get("question_type", "choice"),
                code_snippet=q.get("code_snippet"),
                options=q["options"],
                correct_answer=q["correct_answer"],
                explanation=q["explanation"],
            ))

        print(f"[OK] AI生成了 {len(questions)} 道题目")
        return questions[:TOTAL_QUESTIONS]

    except Exception as e:
        print(f"[ERROR] AI生成题目失败: {e}")
        return _get_fallback_questions(path_type)


def _get_fallback_questions(path_type: str) -> List[AssessmentQuestion]:
    """备用题目（当AI生成失败时）"""
    categories = get_categories_for_path(path_type)
    cat_keys = list(categories.keys())

    fallback = []
    for i in range(TOTAL_QUESTIONS):
        cat = cat_keys[i % len(cat_keys)]
        fallback.append(AssessmentQuestion(
            id=f"q{i+1}",
            category=cat,
            difficulty=2,
            content=f"这是一道关于{categories[cat]}的测试题（备用题目）",
            question_type="choice",
            code_snippet=None,
            options=["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
            correct_answer="A",
            explanation="备用题目解析",
        ))
    return fallback


# ===== 评估会话管理 =====


class AssessmentSession:
    """评估会话"""

    def __init__(self, session_id: str, path_type: str, questions: List[AssessmentQuestion], user_id: str = "default"):
        self.session_id = session_id
        self.path_type = path_type
        self.user_id = user_id
        self.questions = questions
        self.answers: Dict[str, str] = {}  # question_id -> answer
        self.current_index = 0
        self.created_at = datetime.now()

    @property
    def is_completed(self) -> bool:
        return self.current_index >= len(self.questions)

    @property
    def total_questions(self) -> int:
        return len(self.questions)

    def get_current_question(self) -> Optional[AssessmentQuestion]:
        if self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    def submit_answer(self, question_id: str, answer: str) -> Dict:
        """提交答案"""
        question = self.questions[self.current_index]
        if question.id != question_id:
            return {"error": "题目ID不匹配"}

        self.answers[question_id] = answer
        is_correct = answer.upper() == question.correct_answer.upper()
        self.current_index += 1

        next_question = self.get_current_question()

        return {
            "is_correct": is_correct,
            "correct_answer": question.correct_answer,
            "explanation": question.explanation,
            "next_question": next_question.model_dump() if next_question else None,
            "current_index": self.current_index,
            "total_questions": self.total_questions,
            "is_completed": self.is_completed,
        }


# 会话存储
_sessions: Dict[str, AssessmentSession] = {}


def create_session(path_type: str, user_id: str = "default") -> AssessmentSession:
    """创建新的评估会话"""
    session_id = str(uuid.uuid4())[:8]
    questions = generate_assessment_questions(path_type)
    session = AssessmentSession(session_id, path_type, questions, user_id=user_id)
    _sessions[session_id] = session
    print(f"[INFO] 创建评估会话 {session_id}（用户: {user_id}），{len(questions)}道题")
    return session


def get_session(session_id: str) -> Optional[AssessmentSession]:
    """获取评估会话"""
    return _sessions.get(session_id)


def delete_session(session_id: str):
    """删除评估会话"""
    if session_id in _sessions:
        del _sessions[session_id]


# ===== 评分与结果 =====


def calculate_result(session: AssessmentSession, user_id: str = "default") -> AssessmentResult:
    """计算评估结果"""
    questions = session.questions
    answers = session.answers
    categories = get_categories_for_path(session.path_type)

    # 统计
    total = len(questions)
    correct = 0
    category_correct = {cat: 0 for cat in categories}
    category_total = {cat: 0 for cat in categories}

    for q in questions:
        user_answer = answers.get(q.id, "")
        is_correct = user_answer.upper() == q.correct_answer.upper()
        if is_correct:
            correct += 1
            if q.category in category_correct:
                category_correct[q.category] += 1
        if q.category in category_total:
            category_total[q.category] += 1

    # 总分
    score = (correct / total * 100) if total > 0 else 0

    # 各分类得分
    category_scores = {}
    for cat in categories:
        if category_total.get(cat, 0) > 0:
            category_scores[cat] = round(
                category_correct[cat] / category_total[cat] * 100, 1
            )
        else:
            category_scores[cat] = 0.0

    # 确定水平
    if score >= 80:
        level = UserLevel.ADVANCED
    elif score >= 50:
        level = UserLevel.INTERMEDIATE
    else:
        level = UserLevel.BEGINNER

    # 推荐开始模块
    recommended_module = _recommend_module(session.path_type, level, category_scores)

    return AssessmentResult(
        user_id=user_id,
        path_type=session.path_type,
        total_questions=total,
        correct_count=correct,
        score=round(score, 1),
        level=level,
        category_scores=category_scores,
        recommended_start_module=recommended_module,
        completed_at=datetime.now(),
        is_current=True,
    )


def _recommend_module(
    path_type: str, level: UserLevel, category_scores: Dict[str, float]
) -> str:
    """根据水平推荐开始模块"""
    try:
        path = LearningPath(path_type)
        path_data = get_learning_path(path)
        modules = sorted(path_data.modules, key=lambda m: m.order)

        if level == UserLevel.BEGINNER:
            return modules[0].id

        # 中级：检查各分类得分，跳过掌握较好的模块
        for module in modules:
            # 检查模块相关的分类得分
            module_cats = _get_module_categories(module.id)
            avg_score = sum(
                category_scores.get(cat, 0) for cat in module_cats
            ) / max(len(module_cats), 1)

            if avg_score < 70:
                return module.id

        return modules[0].id

    except Exception:
        return ""


def _get_module_categories(module_id: str) -> List[str]:
    """根据模块ID获取相关分类"""
    mapping = {
        "fe-html-css": ["html_css"],
        "fe-javascript": ["javascript"],
        "fe-vue": ["vue"],
        "fe-project": ["html_css", "javascript", "vue"],
        "be-python": ["python"],
        "be-api": ["api_design"],
        "be-system": ["system_design", "database"],
        "be-project": ["python", "api_design", "system_design"],
        "fs-web-basics": ["html_css", "javascript"],
        "fs-frontend": ["vue"],
        "fs-backend": ["python", "api_design"],
        "fs-fullstack": ["html_css", "javascript", "python", "vue", "api_design"],
    }
    return mapping.get(module_id, [])


# ===== 顶层API =====


def start_assessment(path_type: str, user_id: str = "default") -> Dict:
    """开始评估"""
    session = create_session(path_type, user_id=user_id)
    question = session.get_current_question()

    return {
        "session_id": session.session_id,
        "question": question.model_dump() if question else None,
        "current_index": session.current_index,
        "total_questions": session.total_questions,
    }


def submit_answer(session_id: str, question_id: str, answer: str, user_id: str = "default") -> Dict:
    """提交答案"""
    session = get_session(session_id)
    if not session:
        return {"error": "会话不存在或已过期"}

    result = session.submit_answer(question_id, answer)

    # 如果完成，计算结果
    if result.get("is_completed"):
        assessment_result = calculate_result(session, user_id=user_id)
        data_store.save_assessment(assessment_result)
        result["assessment_result"] = assessment_result
        # 发放XP奖励
        from .gamification_service import get_gamification_service
        svc = get_gamification_service()
        svc.award_xp(user_id, 20, f"完成水平检测: {session.path_type}")
        if assessment_result.score >= 100:
            svc.award_xp(user_id, 30, "满分通关奖励")
            svc.check_perfect_score(user_id)
        svc.check_speed_demon(user_id)

    return result


def complete_assessment(session_id: str, user_id: str = "default") -> Optional[AssessmentResult]:
    """强制完成评估（跳过剩余题目）"""
    session = get_session(session_id)
    if not session:
        return None

    result = calculate_result(session, user_id=user_id)
    data_store.save_assessment(result)
    delete_session(session_id)

    # 发放XP奖励
    from .gamification_service import get_gamification_service
    svc = get_gamification_service()
    svc.award_xp(user_id, 20, f"完成水平检测: {session.path_type}")
    if result.score >= 100:
        svc.award_xp(user_id, 30, "满分通关奖励")
        svc.check_perfect_score(user_id)
    # 检查速度徽章也在这里
    svc.check_speed_demon(user_id)

    return result
