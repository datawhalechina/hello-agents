import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("game.logic")

_SEMANTIC_MATCH_PROMPT = """你是一位历史学家。请判断以下两个名称是否指代同一位历史人物。
只需回答 "是" 或 "否"，不要输出任何其他内容。
名称A：{guess}
名称B：{actual}"""

class GameSession:
    """游戏会话管理类"""
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # LLM instance for semantic guess matching (injected by HistoricalFigureAgent)
        self._llm = None

        # 游戏状态
        self.current_figure: Optional[Dict] = None
        self.questions_asked = 0
        self.hints_used = 0
        self.is_game_over = False
        self.is_correct = False
        self.guess_history: List[str] = []
        
        # 配置
        self.max_questions = 20
        self.max_hints = 3
        
        # 初始化游戏状态（current_figure 由 HistoricalFigureAgent 初始化时填充）
        self._reset_state()
    
    def _reset_state(self):
        """重置游戏状态（不加载人物，人物由 Agent 负责填充）"""
        self.current_figure = None
        self.questions_asked = 0
        self.hints_used = 0
        self.is_game_over = False
        self.is_correct = False
        self.guess_history = []
        self.updated_at = datetime.now()
    
    def ask_question(self) -> bool:
        """记录提问，返回是否还可以继续提问"""
        self.questions_asked += 1
        self.updated_at = datetime.now()
        
        if self.questions_asked >= self.max_questions:
            self.is_game_over = True
            return False
        return True
    
    def _semantic_match(self, guess: str, actual: str) -> bool:
        """Use LLM to semantically judge whether guess and actual refer to the same person."""
        if self._llm is None:
            return False
        try:
            prompt = _SEMANTIC_MATCH_PROMPT.format(guess=guess.strip(), actual=actual)
            messages = [
                {"role": "user", "content": prompt}
            ]
            result = self._llm.invoke(messages)
            answer = result.strip()
            logger.info(f"[LOGIC] Semantic match | guess={guess!r} actual={actual!r} llm_answer={answer!r}")
            return answer.startswith("是")
        except Exception as e:
            logger.error(f"[LOGIC] Semantic match failed: {e}", exc_info=True)
            return False

    def make_guess(self, guess_name: str) -> Dict[str, Any]:
        """进行猜测，返回猜测结果"""
        self.updated_at = datetime.now()
        self.guess_history.append(guess_name)

        actual_name = self.current_figure["name"]

        # First try exact match, then fall back to semantic match
        is_correct = guess_name.strip().lower() == actual_name.lower()
        if not is_correct:
            is_correct = self._semantic_match(guess_name, actual_name)
        
        if is_correct:
            self.is_correct = True
            self.is_game_over = True
            return {
                "correct": True,
                "message": "恭喜你猜对了！",
                "figure_info": self.current_figure
            }
        else:
            # 检查是否达到提问上限
            if self.questions_asked >= self.max_questions:
                self.is_game_over = True
                return {
                    "correct": False,
                    "message": "游戏结束！正确答案是：{}".format(self.current_figure["name"]),
                    "figure_info": self.current_figure
                }
            else:
                return {
                    "correct": False,
                    "message": "猜错了，请继续提问或猜测",
                    "remaining_questions": self.max_questions - self.questions_asked
                }
    
    def get_hint(self) -> Optional[Dict[str, Any]]:
        """获取提示"""
        if self.hints_used >= self.max_hints:
            return {
                "available": False,
                "message": "提示次数已用完"
            }
        
        self.hints_used += 1
        self.updated_at = datetime.now()
        
        # 根据提示次数提供不同级别的提示
        hint_level = self.hints_used
        hint_info = {
            "available": True,
            "hint_level": hint_level,
            "remaining_hints": self.max_hints - self.hints_used
        }
        
        if hint_level == 1:
            hint_info["hint"] = f"朝代/时代：{self.current_figure['dynasty']}"
        elif hint_level == 2:
            hint_info["hint"] = f"职业/身份：{self.current_figure['occupation']}"
        elif hint_level == 3:
            hint_info["hint"] = f"主要成就：{self.current_figure['achievements']}"
        
        return hint_info
    
    def get_game_status(self) -> Dict[str, Any]:
        """获取当前游戏状态"""
        return {
            "session_id": self.session_id,
            "questions_asked": self.questions_asked,
            "hints_used": self.hints_used,
            "remaining_questions": self.max_questions - self.questions_asked,
            "remaining_hints": self.max_hints - self.hints_used,
            "is_game_over": self.is_game_over,
            "is_correct": self.is_correct,
            "guess_history": self.guess_history
        }
    
    def reset_game(self):
        """重置游戏状态（人物由 Agent 重新搜索填充）"""
        self._reset_state()
    
    def get_figure_for_prompt(self) -> Dict[str, str]:
        """获取用于Agent提示的人物信息"""
        if not self.current_figure:
            return {}
        
        return {
            "name": self.current_figure["name"],
            "dynasty": self.current_figure["dynasty"],
            "occupation": self.current_figure["occupation"],
            "achievements": self.current_figure["achievements"],
            "characteristics": self.current_figure["characteristics"]
        }


class GameManager:
    """游戏会话管理器"""
    
    def __init__(self):
        self.active_sessions: Dict[str, GameSession] = {}
    
    def create_session(self) -> GameSession:
        """创建新游戏会话"""
        session = GameSession()
        self.active_sessions[session.session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[GameSession]:
        """获取游戏会话"""
        return self.active_sessions.get(session_id)
    
    def end_session(self, session_id: str):
        """结束游戏会话"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
    
    def cleanup_old_sessions(self, max_age_minutes: int = 60):
        """清理过期会话"""
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if (now - session.updated_at).total_seconds() > max_age_minutes * 60:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]


# 全局游戏管理器实例
game_manager = GameManager()