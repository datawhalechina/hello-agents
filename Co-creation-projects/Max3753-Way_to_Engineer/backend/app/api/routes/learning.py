from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ...models.learning import (
    LearningPath, UserProgress, LearningPathData, CoachResponse,
    CoachRecommendation, ModuleStatus
)
from ...services.learning_content import get_learning_path, get_all_paths, find_next_lesson
from ...services.data_store import data_store
from ...services.gamification_service import get_gamification_service

router = APIRouter(prefix="/api/learning", tags=["learning"])


def get_user_progress(user_id: str = "default") -> UserProgress:
    """获取用户进度，使用data_store持久化"""
    progress = data_store.get_user_progress(user_id)
    if not progress:
        progress = UserProgress(
            user_id=user_id,
            started_at=datetime.now(),
            last_activity_at=datetime.now()
        )
        data_store.save_user_progress(progress)
    return progress


def save_user_progress(progress: UserProgress):
    """保存用户进度"""
    progress.last_activity_at = datetime.now()
    data_store.save_user_progress(progress)


@router.get("/paths")
async def list_learning_paths(user_id: str = Query("default")):
    """获取所有学习路径概览"""
    paths = get_all_paths()
    return {
        "paths": [
            {
                "path": p.path.value,
                "title": p.title,
                "description": p.description,
                "icon": p.icon,
                "total_modules": len(p.modules),
                "total_lessons": sum(len(m.lessons) for m in p.modules)
            }
            for p in paths
        ]
    }


@router.get("/paths/{path_type}")
async def get_learning_path_detail(path_type: LearningPath, user_id: str = Query("default")):
    """获取指定学习路径详情"""
    path_data = get_learning_path(path_type)
    progress = get_user_progress(user_id)
    
    # 根据用户进度更新模块状态
    for module in path_data.modules:
        module_progress = calculate_module_progress(module.id, progress)
        module.progress = module_progress
        
        if module_progress >= 100:
            module.status = ModuleStatus.COMPLETED
        elif module_progress > 0:
            module.status = ModuleStatus.IN_PROGRESS
        elif is_module_unlocked(module.order, progress):
            module.status = ModuleStatus.NOT_STARTED
        else:
            module.status = ModuleStatus.LOCKED
    
    # 计算总进度
    total_lessons = sum(len(m.lessons) for m in path_data.modules)
    completed_lessons = sum(
        len([l for l in m.lessons if l.id in progress.completed_lessons])
        for m in path_data.modules
    )
    path_data.total_lessons = total_lessons
    path_data.completed_lessons = completed_lessons
    path_data.progress = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
    
    return path_data


@router.get("/progress")
async def get_progress(user_id: str = Query("default")):
    """获取用户学习进度"""
    progress = get_user_progress(user_id)
    return progress


@router.post("/select-path/{path_type}")
async def select_learning_path(path_type: LearningPath, user_id: str = Query("default")):
    """选择学习路径"""
    progress = get_user_progress(user_id)
    progress.current_path = path_type
    
    # 获取路径数据，设置第一个模块为当前
    path_data = get_learning_path(path_type)
    if path_data.modules:
        progress.current_module = path_data.modules[0].id
    
    save_user_progress(progress)
    return {"message": f"已选择{path_type.value}路径", "progress": progress}


@router.post("/complete-lesson/{lesson_id}")
async def complete_lesson(lesson_id: str, user_id: str = Query("default")):
    """标记课程完成"""
    progress = get_user_progress(user_id)
    is_new = False
    
    if lesson_id not in progress.completed_lessons:
        progress.completed_lessons.append(lesson_id)
        is_new = True
    
    # 检查是否完成整个模块
    path_data = get_learning_path(progress.current_path) if progress.current_path else None
    if path_data:
        for module in path_data.modules:
            lesson_ids = [l.id for l in module.lessons]
            if lesson_id in lesson_ids:
                if all(lid in progress.completed_lessons for lid in lesson_ids):
                    if module.id not in progress.completed_modules:
                        progress.completed_modules.append(module.id)
                break
    
    save_user_progress(progress)
    
    # 发放XP奖励
    xp_awarded = 0
    new_badges = []
    if is_new:
        svc = get_gamification_service()
        # 基础XP：每节课10XP
        xp_awarded = 10
        profile, new_badges = svc.award_xp(user_id, xp_awarded, f"完成课程: {lesson_id}")
    
    # 查找下一课程（用于前端自动跳转）
    next_lesson = None
    if progress.current_path and is_new:
        next_lesson = find_next_lesson(
            path_type=progress.current_path.value,
            current_lesson_id=lesson_id,
            completed_lessons=progress.completed_lessons,
        )
    
    return {
        "message": "课程已标记完成",
        "progress": progress,
        "xp_awarded": xp_awarded,
        "new_badges": new_badges,
        "next_lesson": next_lesson,
    }


def calculate_module_progress(module_id: str, progress: UserProgress) -> float:
    """计算模块进度"""
    path_data = get_learning_path(progress.current_path) if progress.current_path else None
    if not path_data:
        return 0.0
    
    for module in path_data.modules:
        if module.id == module_id:
            total = len(module.lessons)
            if total == 0:
                return 0.0
            completed = sum(1 for l in module.lessons if l.id in progress.completed_lessons)
            return (completed / total) * 100
    
    return 0.0


def is_module_unlocked(module_order: int, progress: UserProgress) -> bool:
    """检查模块是否解锁"""
    if module_order <= 1:
        return True
    
    path_data = get_learning_path(progress.current_path) if progress.current_path else None
    if not path_data:
        return False
    
    # 找到前一个模块
    prev_module = None
    for m in path_data.modules:
        if m.order == module_order - 1:
            prev_module = m
            break
    
    if prev_module:
        return prev_module.id in progress.completed_modules
    
    return False


@router.get("/coach")
async def get_coach_recommendations(user_id: str = Query("default")):
    """获取学习教练推荐"""
    progress = get_user_progress(user_id)
    
    if not progress.current_path:
        return CoachResponse(
            greeting="👋 你好！我是你的学习教练。",
            recommendations=[
                CoachRecommendation(
                    type="select_path",
                    title="选择学习路径",
                    description="首先选择一个学习路径开始你的学习之旅",
                    priority=5
                )
            ],
            encouragement="每个人都有自己的学习节奏，加油！",
            stats={"total_study_minutes": 0, "completed_lessons": 0},
            learning_plan=progress.learning_plan  # 如果有AI生成的计划则带上
        )
    
    path_data = get_learning_path(progress.current_path)
    recommendations = []
    
    # 找到下一个未完成的课程
    next_lesson = None
    next_module = None
    for module in path_data.modules:
        if module.id in progress.completed_modules:
            continue
        for lesson in module.lessons:
            if lesson.id not in progress.completed_lessons:
                next_lesson = lesson
                next_module = module
                break
        if next_lesson:
            break
    
    if next_lesson and next_module:
        recommendations.append(
            CoachRecommendation(
                type="next_lesson",
                title=f"继续学习: {next_lesson.title}",
                description=f"来自 {next_module.title} 模块",
                module_id=next_module.id,
                lesson_id=next_lesson.id,
                priority=5
            )
        )
    
    # 如果有完成的模块，建议复习
    if progress.completed_modules:
        recommendations.append(
            CoachRecommendation(
                type="review",
                title="复习已完成内容",
                description="巩固已学知识，加深理解",
                priority=3
            )
        )
    
    # 生成鼓励语
    completed_count = len(progress.completed_lessons)
    if completed_count == 0:
        encouragement = "🌱 刚开始学习，每一步都是进步！"
    elif completed_count < 5:
        encouragement = "💪 开了个好头，继续努力！"
    elif completed_count < 15:
        encouragement = "🚀 学习势头很好，保持下去！"
    else:
        encouragement = "🌟 你已经学了很多，快要成为专家了！"
    
    return CoachResponse(
        greeting=f"👋 你好！你正在学习 {path_data.title}。",
        recommendations=recommendations,
        encouragement=encouragement,
        stats={
            "total_study_minutes": progress.total_study_minutes,
            "completed_lessons": completed_count,
            "completed_modules": len(progress.completed_modules),
            "current_path": progress.current_path.value if progress.current_path else None
        },
        learning_plan=progress.learning_plan
    )


@router.post("/ai-plan")
async def save_ai_plan(data: dict, user_id: str = Query("default")):
    """保存AI生成的个性化学习计划"""
    plan_text = data.get("plan_text", "")
    progress = get_user_progress(user_id)
    progress.learning_plan = plan_text
    save_user_progress(progress)
    return {"message": "学习计划已保存"}


class SessionUpdate(BaseModel):
    lesson_id: Optional[str] = None
    module_id: Optional[str] = None
    lesson_title: Optional[str] = None
    module_title: Optional[str] = None
    path_type: Optional[str] = None
    last_reply_summary: Optional[str] = None


@router.get("/session")
async def get_session(user_id: str = Query("default")):
    """获取用户最近的会话数据"""
    progress = get_user_progress(user_id)
    return {"session": progress.last_session or None}


@router.post("/session")
async def save_session(update: SessionUpdate, user_id: str = Query("default"), clear: bool = Query(False)):
    """保存/更新用户会话数据。clear=true 则清除会话"""
    progress = get_user_progress(user_id)
    if clear:
        progress.last_session = None
        save_user_progress(progress)
        return {"message": "ok", "session": None}
    if progress.last_session is None:
        progress.last_session = {}
    update_data = update.model_dump(exclude_unset=True)
    progress.last_session.update(update_data)
    save_user_progress(progress)
    return {"message": "ok", "session": progress.last_session}
