"""
AutoModeAgent - 全自动模式 Agent
自动串联三轮，无用户输入，SSE 流式输出
"""
import json
import asyncio
from typing import Dict, Any, AsyncGenerator
from hello_agents.agents.tool_aware_agent import ToolAwareSimpleAgent
from .prompts import (
    AUTO_MODE_SYSTEM_PROMPT,
    AUTO_MODE_USER_PROMPT
)
from config import get_llm, tool_listener


class AutoModeAgent:
    """全自动模式 Agent - 自动串联三轮，SSE 流式输出"""
    
    def __init__(self):
        """初始化 AutoModeAgent"""
        self.llm = get_llm()
        self.agent = ToolAwareSimpleAgent(
            name="AutoMode",
            system_prompt=AUTO_MODE_SYSTEM_PROMPT,
            llm=self.llm,
            tool_call_listener=tool_listener
        )

    def run_auto_mode(self, seed_sentence: str) -> Dict[str, Any]:
        """
        执行全自动模式，生成三阶段扩写结果
        
        Args:
            seed_sentence: 种子句
            
        Returns:
            Dict[str, Any]: 完整扩写结果，包含：
                - stage1: 阶段一结果（question, expanded）
                - stage2: 阶段二结果（question, expanded）
                - stage3: 阶段三结果（question, expanded）
                - polished: 最终满分润色版本
                - structure_analysis: 语法结构分析
        """
        # 构建用户提示词
        user_prompt = AUTO_MODE_USER_PROMPT.format(
            seed_sentence=seed_sentence
        )
        
        # 调用 LLM
        response = self.agent.run(user_prompt)
        
        # 解析 JSON 响应
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError as e:
            # 如果解析失败，返回默认响应
            return {
                "stage1": {
                    "question": "请为这个句子增加一些细节",
                    "expanded": seed_sentence
                },
                "stage2": {
                    "question": "请为这个句子增加时间或地点信息",
                    "expanded": seed_sentence
                },
                "stage3": {
                    "question": "请为这个句子增加定语从句或状语从句",
                    "expanded": seed_sentence
                },
                "polished": seed_sentence,
                "structure_analysis": [
                    "自动模式生成失败，使用原始句子"
                ]
            }
    
    def _parse_stream_content(self, buffer: str) -> Dict[str, Any]:
        """
        解析流式内容，提取当前已完成的部分
        
        Args:
            buffer: 当前已收集的完整文本
            
        Returns:
            Dict[str, Any]: 解析结果，包含已完成的部分
        """
        result = {}
        
        # 定义分隔符和对应的键
        delimiters = [
            ("===STAGE1_QUESTION===", "stage1_question"),
            ("===STAGE1_EXPANDED===", "stage1_expanded"),
            ("===STAGE2_QUESTION===", "stage2_question"),
            ("===STAGE2_EXPANDED===", "stage2_expanded"),
            ("===STAGE3_QUESTION===", "stage3_question"),
            ("===STAGE3_EXPANDED===", "stage3_expanded"),
            ("===POLISHED===", "polished"),
            ("===ANALYSIS===", "analysis"),
            ("===END===", "end"),
        ]
        
        # 查找每个分隔符的位置
        positions = {}
        for delimiter, key in delimiters:
            pos = buffer.find(delimiter)
            if pos != -1:
                positions[key] = pos
        
        # 提取内容
        if "stage1_question" in positions and "stage1_expanded" in positions:
            result["stage1"] = {
                "question": buffer[positions["stage1_question"] + len("===STAGE1_QUESTION==="):positions["stage1_expanded"]].strip()
            }
        
        if "stage1_expanded" in positions and "stage2_question" in positions:
            if "stage1" not in result:
                result["stage1"] = {}
            result["stage1"]["expanded"] = buffer[positions["stage1_expanded"] + len("===STAGE1_EXPANDED==="):positions["stage2_question"]].strip()
        
        if "stage2_question" in positions and "stage2_expanded" in positions:
            result["stage2"] = {
                "question": buffer[positions["stage2_question"] + len("===STAGE2_QUESTION==="):positions["stage2_expanded"]].strip()
            }
        
        if "stage2_expanded" in positions and "stage3_question" in positions:
            if "stage2" not in result:
                result["stage2"] = {}
            result["stage2"]["expanded"] = buffer[positions["stage2_expanded"] + len("===STAGE2_EXPANDED==="):positions["stage3_question"]].strip()
        
        if "stage3_question" in positions and "stage3_expanded" in positions:
            result["stage3"] = {
                "question": buffer[positions["stage3_question"] + len("===STAGE3_QUESTION==="):positions["stage3_expanded"]].strip()
            }
        
        if "stage3_expanded" in positions and "polished" in positions:
            if "stage3" not in result:
                result["stage3"] = {}
            result["stage3"]["expanded"] = buffer[positions["stage3_expanded"] + len("===STAGE3_EXPANDED==="):positions["polished"]].strip()
        
        if "polished" in positions and "analysis" in positions:
            result["polished"] = buffer[positions["polished"] + len("===POLISHED==="):positions["analysis"]].strip()
        
        if "analysis" in positions and "end" in positions:
            analysis_text = buffer[positions["analysis"] + len("===ANALYSIS==="):positions["end"]].strip()
            result["structure_analysis"] = [line.strip() for line in analysis_text.split('\n') if line.strip()]
        
        return result
    
    async def run_auto_mode_stream(self, seed_sentence: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行全自动模式，流式输出结果（用于 SSE）
        
        Args:
            seed_sentence: 种子句
            
        Yields:
            Dict[str, Any]: 流式输出的事件，包含：
                - type: 事件类型 (stage1/stage2/stage3/polished/analysis/done/progress)
                - data: 事件数据
        """
        # 构建用户提示词
        user_prompt = AUTO_MODE_USER_PROMPT.format(
            seed_sentence=seed_sentence
        )
        
        # 调用 LLM 使用 stream_run（同步方法）
        response_buffer = []
        
        # 记录已经发送过的部分，避免重复发送
        sent_parts = set()
        
        for chunk in self.agent.stream_run(user_prompt):
            response_buffer.append(chunk)
            full_response = ''.join(response_buffer)
            
            # 解析当前内容
            parsed = self._parse_stream_content(full_response)
            
            # 检查是否有新的完整部分可以发送
            if "stage1" in parsed and "question" in parsed["stage1"] and "stage1_question" not in sent_parts:
                yield {"type": "stage1", "data": {"question": parsed["stage1"]["question"]}}
                sent_parts.add("stage1_question")
            
            if "stage1" in parsed and "expanded" in parsed["stage1"] and "stage1_expanded" not in sent_parts:
                yield {"type": "stage1", "data": {"expanded": parsed["stage1"]["expanded"]}}
                sent_parts.add("stage1_expanded")
            
            if "stage2" in parsed and "question" in parsed["stage2"] and "stage2_question" not in sent_parts:
                yield {"type": "stage2", "data": {"question": parsed["stage2"]["question"]}}
                sent_parts.add("stage2_question")
            
            if "stage2" in parsed and "expanded" in parsed["stage2"] and "stage2_expanded" not in sent_parts:
                yield {"type": "stage2", "data": {"expanded": parsed["stage2"]["expanded"]}}
                sent_parts.add("stage2_expanded")
            
            if "stage3" in parsed and "question" in parsed["stage3"] and "stage3_question" not in sent_parts:
                yield {"type": "stage3", "data": {"question": parsed["stage3"]["question"]}}
                sent_parts.add("stage3_question")
            
            if "stage3" in parsed and "expanded" in parsed["stage3"] and "stage3_expanded" not in sent_parts:
                yield {"type": "stage3", "data": {"expanded": parsed["stage3"]["expanded"]}}
                sent_parts.add("stage3_expanded")
            
            if "polished" in parsed and "polished" not in sent_parts:
                yield {"type": "polished", "data": {"sentence": parsed["polished"]}}
                sent_parts.add("polished")
            
            if "structure_analysis" in parsed and "analysis" not in sent_parts:
                yield {"type": "analysis", "data": {"items": parsed["structure_analysis"]}}
                sent_parts.add("analysis")
            
            # 发送进度更新
            yield {"type": "progress", "data": {"message": "正在生成...", "partial": full_response}}
            
            # 暂停一下以确保异步性
            await asyncio.sleep(0.01)
        
        # 所有块都接收完后，进行最终解析
        full_response = ''.join(response_buffer)
        final_parsed = self._parse_stream_content(full_response)
        
        # 检查是否有未发送的部分
        if "stage1" in final_parsed:
            if "question" in final_parsed["stage1"] and "stage1_question" not in sent_parts:
                yield {"type": "stage1", "data": {"question": final_parsed["stage1"]["question"]}}
            if "expanded" in final_parsed["stage1"] and "stage1_expanded" not in sent_parts:
                yield {"type": "stage1", "data": {"expanded": final_parsed["stage1"]["expanded"]}}
        
        if "stage2" in final_parsed:
            if "question" in final_parsed["stage2"] and "stage2_question" not in sent_parts:
                yield {"type": "stage2", "data": {"question": final_parsed["stage2"]["question"]}}
            if "expanded" in final_parsed["stage2"] and "stage2_expanded" not in sent_parts:
                yield {"type": "stage2", "data": {"expanded": final_parsed["stage2"]["expanded"]}}
        
        if "stage3" in final_parsed:
            if "question" in final_parsed["stage3"] and "stage3_question" not in sent_parts:
                yield {"type": "stage3", "data": {"question": final_parsed["stage3"]["question"]}}
            if "expanded" in final_parsed["stage3"] and "stage3_expanded" not in sent_parts:
                yield {"type": "stage3", "data": {"expanded": final_parsed["stage3"]["expanded"]}}
        
        if "polished" in final_parsed and "polished" not in sent_parts:
            yield {"type": "polished", "data": {"sentence": final_parsed["polished"]}}
        
        if "structure_analysis" in final_parsed and "analysis" not in sent_parts:
            yield {"type": "analysis", "data": {"items": final_parsed["structure_analysis"]}}
        
        # 发送完成事件，包含完整数据
        complete_data = {
            "stage1": final_parsed.get("stage1", {
                "question": "请为这个句子增加一些细节",
                "expanded": seed_sentence
            }),
            "stage2": final_parsed.get("stage2", {
                "question": "请为这个句子增加时间或地点信息",
                "expanded": seed_sentence
            }),
            "stage3": final_parsed.get("stage3", {
                "question": "请为这个句子增加定语从句或状语从句",
                "expanded": seed_sentence
            }),
            "polished": final_parsed.get("polished", seed_sentence),
            "structure_analysis": final_parsed.get("structure_analysis", [
                "自动模式生成"
            ])
        }
        yield {"type": "done", "data": complete_data}
    
    def generate_session_state(self, seed_sentence: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据自动模式结果生成会话状态
        
        Args:
            seed_sentence: 种子句
            result: 自动模式结果
            
        Returns:
            Dict[str, Any]: 会话状态数据
        """
        # 构建轮次记录
        rounds = [
            {
                "stage": "stage1",
                "question": result["stage1"]["question"],
                "user_answer": result["stage1"]["expanded"],
                "evaluation": "自动模式生成，语法正确",
                "expanded_sentence": result["stage1"]["expanded"]
            },
            {
                "stage": "stage2",
                "question": result["stage2"]["question"],
                "user_answer": result["stage2"]["expanded"],
                "evaluation": "自动模式生成，语法正确",
                "expanded_sentence": result["stage2"]["expanded"]
            },
            {
                "stage": "stage3",
                "question": result["stage3"]["question"],
                "user_answer": result["stage3"]["expanded"],
                "evaluation": "自动模式生成，语法正确",
                "expanded_sentence": result["stage3"]["expanded"]
            }
        ]
        
        return {
            "seed_sentence": seed_sentence,
            "current_stage": "done",
            "rounds": rounds,
            "final_polished": result["polished"],
            "structure_analysis": result["structure_analysis"]
        }


# 创建全局实例（单例模式）
_auto_mode_instance = None


def get_auto_mode() -> AutoModeAgent:
    """
    获取全局 AutoModeAgent 实例（单例模式）
    
    Returns:
        AutoModeAgent: AutoModeAgent 实例
    """
    global _auto_mode_instance
    if _auto_mode_instance is None:
        _auto_mode_instance = AutoModeAgent()
    return _auto_mode_instance


def reset_auto_mode():
    """重置 AutoModeAgent 实例（用于测试）"""
    global _auto_mode_instance
    _auto_mode_instance = None
