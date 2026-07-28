"""
游戏化服务 - XP、等级、徽章、连击系统
"""
from datetime import date, datetime
from typing import List, Optional, Dict, Tuple
from ..models.learning import GamificationProfile
from .data_store import data_store

# ========== 配置 ==========
XP_PER_LEVEL = 100

# 徽章定义
BADGE_DEFINITIONS: Dict[str, dict] = {
    "first_lesson": {
        "id": "first_lesson",
        "name": "第一步",
        "description": "完成第一节课",
        "icon": "🌱",
        "condition": "完成1节课",
    },
    "ten_lessons": {
        "id": "ten_lessons",
        "name": "勤学苦练",
        "description": "累计完成10节课",
        "icon": "📚",
        "condition": "完成10节课",
    },
    "twenty_lessons": {
        "id": "twenty_lessons",
        "name": "学富五车",
        "description": "累计完成20节课",
        "icon": "🧠",
        "condition": "完成20节课",
    },
    "first_assessment": {
        "id": "first_assessment",
        "name": "自我认知",
        "description": "完成第一次水平检测",
        "icon": "📊",
        "condition": "完成1次测试",
    },
    "perfect_score": {
        "id": "perfect_score",
        "name": "完美主义者",
        "description": "水平检测获得满分",
        "icon": "💯",
        "condition": "测试得分100",
    },
    "speed_demon": {
        "id": "speed_demon",
        "name": "神速",
        "description": "同一天完成5节课",
        "icon": "⚡",
        "condition": "单日5节课",
    },
    "first_path": {
        "id": "first_path",
        "name": "选择方向",
        "description": "选择一条学习路径",
        "icon": "🛤️",
        "condition": "选择路径",
    },
    "all_modules": {
        "id": "all_modules",
        "name": "开拓者",
        "description": "完成一个路径的所有模块",
        "icon": "🏆",
        "condition": "完成全部模块",
    },
    "week_streak": {
        "id": "week_streak",
        "name": "坚持不懈",
        "description": "连续学习7天",
        "icon": "🔥",
        "condition": "连续7天",
    },
    "month_streak": {
        "id": "month_streak",
        "name": "铁杆学员",
        "description": "连续学习30天",
        "icon": "💎",
        "condition": "连续30天",
    },
}


class GamificationService:
    """游戏化服务"""

    def get_profile(self, user_id: str) -> GamificationProfile:
        """获取用户游戏化档案"""
        profile = data_store.get_gamification(user_id)
        if not profile:
            profile = GamificationProfile(user_id=user_id)
            data_store.save_gamification(profile)
        return profile

    def award_xp(self, user_id: str, amount: int, reason: str) -> GamificationProfile:
        """给用户增加XP"""
        profile = self.get_profile(user_id)
        profile.total_xp += amount
        profile.level = max(1, profile.total_xp // XP_PER_LEVEL + 1)

        if len(profile.xp_log) > 500:
            profile.xp_log = profile.xp_log[-500:]
        profile.xp_log.append({
            "amount": amount,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })

        # 更新连击
        today = date.today().isoformat()
        if profile.last_active_date == today:
            pass  # 今天已经活跃过
        elif profile.last_active_date == _yesterday():
            profile.streak += 1
        else:
            profile.streak = 1
        profile.last_active_date = today

        # 检查新徽章
        new_badges = self._check_new_badges(profile, user_id)
        data_store.save_gamification(profile)
        return profile, new_badges

    def _check_new_badges(self, profile: GamificationProfile, user_id: str) -> List[dict]:
        """检查是否有新徽章获得"""
        progress = data_store.get_user_progress(user_id)
        if not progress:
            return []

        earned = set(profile.badges)
        new_badges = []

        # 按条件检查
        checks = [
            ("first_lesson", lambda: len(progress.completed_lessons) >= 1),
            ("ten_lessons", lambda: len(progress.completed_lessons) >= 10),
            ("twenty_lessons", lambda: len(progress.completed_lessons) >= 20),
            ("first_assessment", lambda: len(data_store.get_user_assessments(user_id)) >= 1),
            ("first_path", lambda: progress.current_path is not None),
            ("all_modules", lambda: progress.current_path is not None and
             _all_modules_completed(progress)),
            ("week_streak", lambda: profile.streak >= 7),
            ("month_streak", lambda: profile.streak >= 30),
            ("speed_demon", lambda: False),  # 由外部触发
            ("perfect_score", lambda: False),  # 由外部触发
        ]

        for badge_id, check_fn in checks:
            if badge_id not in earned and check_fn():
                badge = dict(BADGE_DEFINITIONS[badge_id])
                badge["awarded_at"] = datetime.now().isoformat()
                profile.badges.append(badge_id)
                new_badges.append(badge)

        return new_badges

    def check_perfect_score(self, user_id: str):
        """检查是否获得完美得分徽章"""
        profile = self.get_profile(user_id)
        if "perfect_score" in profile.badges:
            return
        assessments = data_store.get_user_assessments(user_id)
        if any(a.score >= 100 for a in assessments):
            profile.badges.append("perfect_score")
            data_store.save_gamification(profile)

    def check_speed_demon(self, user_id: str):
        """检查单日5课成就"""
        profile = self.get_profile(user_id)
        if "speed_demon" in profile.badges:
            return
        progress = data_store.get_user_progress(user_id)
        if not progress:
            return
        # 完成5节课即授予
        if len(progress.completed_lessons) >= 5:
            profile.badges.append("speed_demon")
            data_store.save_gamification(profile)


def _yesterday() -> str:
    from datetime import timedelta
    return (date.today() - timedelta(days=1)).isoformat()


def _all_modules_completed(progress) -> bool:
    """检查一个路径的所有模块是否完成"""
    if not progress.current_path:
        return False
    from .learning_content import get_learning_path
    path_data = get_learning_path(progress.current_path)
    if not path_data:
        return False
    return all(m.id in progress.completed_modules for m in path_data.modules)


# 全局单例
_gamification_service: Optional[GamificationService] = None


def get_gamification_service() -> GamificationService:
    global _gamification_service
    if _gamification_service is None:
        _gamification_service = GamificationService()
    return _gamification_service
