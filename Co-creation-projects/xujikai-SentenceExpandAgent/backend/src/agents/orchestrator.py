"""
OrchestratorAgent - 流程调度 Agent
阶段调度、更新 SessionState、决定 next stage、内部串联三个 Agent
"""
import json
from typing import Dict, Any
from hello_agents.agents.tool_aware_agent import ToolAwareSimpleAgent
from .prompts import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    ORCHESTRATOR_USER_PROMPT
)
from .interviewer import get_interviewer
from .evaluator import get_evaluator
from .polisher import get_polisher
from config import get_llm, tool_listener
from models.entities import SessionState, RoundRecord, AgentResponse, Stage

class OrchestratorAgent:
    """流程调度 Agent - 阶段调度、更新 SessionState、决定 next stage"""
    
    def __init__(self):
        """初始化 OrchestratorAgent"""
        self.llm = get_llm()
        self.agent = ToolAwareSimpleAgent(
            name="Orchestrator",
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            llm=self.llm,
            tool_call_listener=tool_listener
        )
        
        # 获取子 Agent 实例
        self.interviewer = get_interviewer()
        self.evaluator = get_evaluator()
        self.polisher = get_polisher()
    
    def decide_next_action(self, session_state: SessionState) -> Dict[str, Any]:
        """
        根据当前会话状态决定下一步动作
        
        Args:
            session_state: 当前会话状态
            
        Returns:
            Dict[str, Any]: 下一步动作，包含：
                - action: 动作类型 (interview/evaluate/polish)
                - stage: 阶段 (stage1/stage2/stage3)
        """
        # 构建用户提示词
        user_prompt = ORCHESTRATOR_USER_PROMPT.format(
            seed_sentence=session_state.seed_sentence,
            current_stage=session_state.current_stage,
            rounds_count=len(session_state.rounds),
            last_evaluated=self._is_last_round_evaluated(session_state)
        )
        
        # 调用 LLM
        response = self.agent.run(user_prompt)
        
        # 解析 JSON 响应
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError as e:
            # 如果解析失败，使用规则判断
            return self._decide_next_action_rule_based(session_state)
    
    def _is_last_round_evaluated(self, session_state: SessionState) -> bool:
        """
        判断最新一轮是否已有点评
        
        Args:
            session_state: 当前会话状态
            
        Returns:
            bool: 最新一轮是否已有点评
        """
        if not session_state.rounds:
            return False
        
        last_round = session_state.rounds[-1]
        return bool(last_round.evaluation)
    
    def _decide_next_action_rule_based(self, session_state: SessionState) -> Dict[str, Any]:
        """
        基于规则决定下一步动作（LLM 解析失败时的备用方案）
        
        Args:
            session_state: 当前会话状态
            
        Returns:
            Dict[str, Any]: 下一步动作
        """
        rounds_count = len(session_state.rounds)
        last_evaluated = self._is_last_round_evaluated(session_state)
        
        # 规则判断
        if rounds_count == 0:
            # 会话刚开始，进入 stage1
            return {"action": "interview", "stage": "stage1"}
        elif not last_evaluated:
            # 用户提交了句子但尚未点评
            return {"action": "evaluate"}
        elif session_state.current_stage == "stage1":
            # stage1 点评完成，进入 stage2
            return {"action": "interview", "stage": "stage2"}
        elif session_state.current_stage == "stage2":
            # stage2 点评完成，进入 stage3
            return {"action": "interview", "stage": "stage3"}
        elif session_state.current_stage == "stage3":
            # stage3 点评完成，进入 polish
            return {"action": "polish"}
        else:
            # 默认情况
            return {"action": "interview", "stage": "stage1"}
    
    def start_session(self, session_state: SessionState) -> AgentResponse:
        """
        开始会话，生成第一阶段提问
        
        Args:
            session_state: 会话状态
            
        Returns:
            AgentResponse: 智能体响应
        """
        # 生成提问
        interview_result = self.interviewer.ask(
            stage=session_state.current_stage,
            current_sentence=session_state.seed_sentence,
            rounds_history=""
        )
        
        # 构建响应
        return AgentResponse(
            session_id=session_state.session_id,
            stage=session_state.current_stage,
            question=interview_result["question"],
            evaluation=None,
            expanded_sentence=None,
            final_polished=None,
            is_done=False
        )
    
    def process_user_input(self, session_state: SessionState, 
                          user_sentence: str) -> AgentResponse:
        """
        处理用户输入，执行点评和可能的下一阶段提问
        
        Args:
            session_state: 会话状态
            user_sentence: 用户提交的句子
            
        Returns:
            AgentResponse: 智能体响应
        """
        # 获取当前阶段目标
        stage_goal = self.interviewer.get_stage_goal(session_state.current_stage)
        
        # 获取当前句子（种子句或上一轮的扩写结果）
        current_sentence = self._get_current_sentence(session_state)
        
        # 生成提问（用于点评上下文）
        interview_result = self.interviewer.ask(
            stage=session_state.current_stage,
            current_sentence=current_sentence,
            rounds_history=self._format_rounds_history(session_state)
        )
        
        # 执行语法点评
        evaluation_result = self.evaluator.evaluate(
            stage_goal=stage_goal,
            question=interview_result["question"],
            seed_sentence=session_state.seed_sentence,
            user_sentence=user_sentence
        )
        
        # 创建轮次记录
        round_record = RoundRecord(
            stage=session_state.current_stage,
            question=interview_result["question"],
            user_answer=user_sentence,
            evaluation=evaluation_result["comment"],
            expanded_sentence=evaluation_result["corrected_sentence"]
        )
        
        # 更新会话状态
        session_state.rounds.append(round_record)
        
        # 决定下一步动作
        next_action = self.decide_next_action(session_state)
        
        # 根据下一步动作构建响应
        if next_action["action"] == "interview":
            # 进入下一阶段
            next_stage = next_action["stage"]
            session_state.current_stage = next_stage
            
            # 生成下一阶段提问
            next_interview_result = self.interviewer.ask(
                stage=next_stage,
                current_sentence=evaluation_result["corrected_sentence"],
                rounds_history=self._format_rounds_history(session_state)
            )
            
            return AgentResponse(
                session_id=session_state.session_id,
                stage=next_stage,
                question=next_interview_result["question"],
                evaluation=evaluation_result["comment"],
                expanded_sentence=evaluation_result["corrected_sentence"],
                final_polished=None,
                is_done=False
            )
        elif next_action["action"] == "polish":
            # 进入润色阶段
            session_state.current_stage = "done"
            
            # 生成润色版本
            rounds_detail = self.polisher.format_rounds_detail(session_state.rounds)
            polish_result = self.polisher.polish(
                seed_sentence=session_state.seed_sentence,
                rounds_detail=rounds_detail
            )
            
            session_state.final_polished = polish_result["polished_sentence"]
            
            return AgentResponse(
                session_id=session_state.session_id,
                stage="done",
                question=None,
                evaluation=evaluation_result["comment"],
                expanded_sentence=evaluation_result["corrected_sentence"],
                final_polished=polish_result["polished_sentence"],
                is_done=True
            )
        else:
            # 默认情况（不应该发生）
            return AgentResponse(
                session_id=session_state.session_id,
                stage=session_state.current_stage,
                question=None,
                evaluation=evaluation_result["comment"],
                expanded_sentence=evaluation_result["corrected_sentence"],
                final_polished=None,
                is_done=False
            )
    
    def _get_current_sentence(self, session_state: SessionState) -> str:
        """
        获取当前句子（用于生成提问）
        
        Args:
            session_state: 会话状态
            
        Returns:
            str: 当前句子
        """
        if not session_state.rounds:
            return session_state.seed_sentence
        else:
            return session_state.rounds[-1].expanded_sentence
    
    def _format_rounds_history(self, session_state: SessionState) -> str:
        """
        格式化轮次历史为字符串
        
        Args:
            session_state: 会话状态
            
        Returns:
            str: 轮次历史字符串
        """
        if not session_state.rounds:
            return ""
        
        history_parts = []
        for i, round_record in enumerate(session_state.rounds, 1):
            stage_num = round_record.stage.replace("stage", "")
            history = f"阶段{stage_num}: {round_record.question} -> {round_record.expanded_sentence}"
            history_parts.append(history)
        
        return "\n".join(history_parts)


# 创建全局实例（单例模式）
_orchestrator_instance = None


def get_orchestrator() -> OrchestratorAgent:
    """
    获取全局 OrchestratorAgent 实例（单例模式）
    
    Returns:
        OrchestratorAgent: OrchestratorAgent 实例
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = OrchestratorAgent()
    return _orchestrator_instance


def reset_orchestrator():
    """重置 OrchestratorAgent 实例（用于测试）"""
    global _orchestrator_instance
    _orchestrator_instance = None
