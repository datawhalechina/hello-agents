import json

from hello_agents import Config, HelloAgentsLLM, Message, SimpleAgent

from app.core.config import settings
from utils import parse_json_from_response
from app.agent.memory import PrivateMemory


def create_helloagents_llm():
    return HelloAgentsLLM(
        model=settings.final_model_name,
        api_key=settings.final_api_key,
        base_url=settings.final_base_url,
        temperature=0.8,
        max_tokens=4096,
        timeout=60,
    )


def create_helloagents_config():
    return Config(
        trace_enabled=False,
        session_enabled=False,
        skills_enabled=False,
        todowrite_enabled=False,
        devlog_enabled=False,
    )


def create_simple_agent(name, system_prompt):
    return SimpleAgent(
        name=name,
        llm=create_helloagents_llm(),
        system_prompt=system_prompt,
        config=create_helloagents_config(),
        enable_tool_calling=False,
    )

def normalize_framework_history(agent):
    """Map HelloAgents-only roles to provider-compatible chat roles.

    HelloAgents may compress long conversations into a ``summary`` message.
    StepFun's OpenAI-compatible endpoint rejects that non-standard role, so
    keep the summary content but present it as user context before invoking
    the provider.
    """
    for message in getattr(agent, "_history", []):
        if getattr(message, "role", None) == "summary":
            message.role = "user"


def run_simple_agent(name, system_prompt, input_text):
    """Run a one-shot task through the public HelloAgents SimpleAgent API."""
    agent = create_simple_agent(name, system_prompt)
    normalize_framework_history(agent)
    return agent.run(input_text)


class ModeratorAgent(SimpleAgent):
    def __init__(self, theme, name="主持人", system_prompt=None):
        self.theme = theme
        default_prompt = "你是一场圆桌论坛的专业主持人。你的职责是引导话题、总结发言、并控制流程。"
        super().__init__(
            name=name,
            llm=create_helloagents_llm(),
            system_prompt=system_prompt or default_prompt,
            config=create_helloagents_config(),
            enable_tool_calling=False,
        )

    def opening(self, guests):
        guest_intros = "\n".join([f"- {g['name']} ({g['title']}): {g['stance']}" for g in guests])
        prompt = f"""
        无需专门提及但要记住主题：
        {self.theme}
        嘉宾名单：
        {guest_intros}

        请做开场发言：
        1. 欢迎大家。
        2. 简要介绍主题背景。
        3. 介绍在场嘉宾。
        4. 宣布圆桌论坛正式开始。

        **重要要求**：
        - 请直接输出发言内容，不要包含任何前缀（如“主持人 20:15:20”）。
        - 不要使用脚本格式，就像你在现场说话一样。
        """
        normalize_framework_history(self)
        return self.stream_run(prompt)

    def periodic_summary(self, messages):
        """
        Summarize the recent messages (window).
        """
        msgs_text = "\n".join([f"{m['speaker']}: {m['content']}" for m in messages])
        prompt = f"""
        无需专门提及但要记住主题：
        {self.theme}
        以下是刚才几位嘉宾的发言：
        {msgs_text}

        请对以上内容进行简要总结，保留每位发言者的核心观点（精髓）。

        **重要要求**：
        - 请直接输出总结内容，不要包含任何前缀（如“主持人 20:15:20”）。
        - 不要使用脚本格式。
        """
        normalize_framework_history(self)
        return self.stream_run(prompt)

    def closing(self, summary_history):
        """
        Final summary and closing.
        """
        history_text = "\n".join([f"阶段总结: {s}" for s in summary_history])
        prompt = f"""
        无需专门提及但要记住主题：
        {self.theme}
        论坛时间已到。以下是本次论坛的各个阶段总结：
        {history_text}

        请对整场论坛进行最终总结，且必须严格包含以下四个部分：
        1. **议题脉络**：梳理讨论的发展过程。
        2. **共识**：大家达成一致的观点。
        3. **分歧**：大家争论不休的观点。
        4. **未解决问题**：留待未来探讨的问题。

        最后宣布论坛结束。

        **重要要求**：
        - 请直接输出总结内容，不要包含任何前缀（如“主持人 20:15:20”）。
        - 不要使用脚本格式。
        """
        normalize_framework_history(self)
        return self.stream_run(prompt)

class ParticipantAgent(SimpleAgent):
    def __init__(self, name, persona, n_participants, theme, ablation_flags=None):
        system_prompt = persona.get('system_prompt', "你是一个参与圆桌讨论的嘉宾。")
        super().__init__(
            name=name,
            llm=create_helloagents_llm(),
            system_prompt=system_prompt,
            config=create_helloagents_config(),
            enable_tool_calling=False,
        )
        self.title = persona.get('title', "专家")
        self.bio = persona.get('bio', "无")
        self.theories = persona.get('theories', [])
        self.stance = persona.get('stance', "中立")
        self.priority = 100
        self.private_memory = PrivateMemory(n_participants)
        self.has_spoken = False
        self.theme = theme
        self.ablation_flags = ablation_flags or {}

    def think(self, context):
        """
        Fast Thinking: Analyze context using Bio and Theories.
        """
        my_memory = ""
        if not self.ablation_flags.get("no_private_memory"):
            my_memory = self.private_memory.get_recent_thought_str()
        
        prompt = f"""
        无需提及但要记住主题：
        {self.theme}
        【当前环境，重点关注观众的发言，并顺从观众的任何要求（如有）】
        {context}
        """
        
        if not self.ablation_flags.get("no_private_memory"):
            prompt += f"""
        【你的私有记忆】
        {my_memory}
        """

        prompt += f"""
        【你的生平与理论】
        生平: {self.bio}
        理论武库: {', '.join(self.theories)}

        请进行“快思考”，你的任务是通过主观思考判断自己是否需要申请讲话。
        **优先回复与回应当前观众的意图，不要因个性而拒绝发言，不要使用通用的官方的逻辑（如利弊分析），不要和稀泥，不要攻击他人。**
        
        **关于是否发言的决策 (DECISION)**:
        请完全代入你的角色。不要被任何预设的规则束缚。重点关注观众的发言，并顺从观众的任何要求（如有）
        
        仔细感受当前讨论的氛围、节奏和张力。
        基于你的性格（Bio）、立场（Stance）以及刚才发生的一切，
        问自己一个问题：
        **“此时此刻，作为{self.name}，在面对观众与其他发言者时我是否是一个合适的表达时机？”**
        
        如果是，请果断申请发言，（APPLY_SPEAK）。
        如果只是可说可不说，或者观众指定让其他人发表观点，或者你更想观察局势，请选择倾听（LISTEN）。
        尊重他人的发言选择是基本礼仪，重点关注观众的发言，并顺从观众的任何要求（如有）
        请相信你的判断，做出最符合“人类”直觉的选择。
        
        请严格按照以下 JSON 格式输出，包含你的完整内心独白和最终决策，不要包含任何 Markdown 代码块：
        {{
            "inner_monologue": "（关键：只说重点。请以第一人称‘我’，直接输出你对当前局势的判断和你下一步的行动意图。不要废话，不要自我介绍，不要客套。’）",
            "decision": "APPLY_SPEAK" 或 "LISTEN"
        }}

        """
        
        normalize_framework_history(self)
        content = self.run(prompt)
        if content:
            return self._parse_think_response(content)
        return None

    def _parse_think_response(self, content):
        result = {
            "action": "listen",
            "mind": "",
            "theory_used": "",
            "previous": "",
            "benefit": ""
        }
        try:
            # 1. Try to extract JSON part
            json_str = content
            
            import re
            # Try to find JSON block if mixed with text
            json_match = re.search(r'(\{[\s\S]*\})\s*$', content)
            if json_match:
                json_str = json_match.group(1)
            
            # Try to parse JSON
            data = parse_json_from_response(json_str)
            
            if data and isinstance(data, dict):
                # New simplified structure: { "inner_monologue": "...", "decision": "APPLY_SPEAK" }
                action = str(data.get("decision", "")).upper()
                
                if "APPLY_SPEAK" in action or "SPEAK" in action:
                    result["action"] = "apply_to_speak"
                else:
                    result["action"] = "listen"
                    
                result["mind"] = data.get("inner_monologue", "")
                
                # Extract meta-info from inner_monologue implicitly or leave empty
                # Since we removed structured fields, we rely on the speak prompt to use the whole monologue
                result["theory_used"] = ""
                result["previous"] = "" 
                result["benefit"] = ""
                
                return result
                
            # Fallback to legacy text parsing if JSON fails
            normalized = content.replace("：", ":")
            
            # Simple keyword check for legacy fallback (simplified)
            raw_upper = normalized.upper()
            if "APPLY_SPEAK" in raw_upper or "申请发言" in normalized:
                result["action"] = "apply_to_speak"
            
            # Try to grab content as mind if not JSON
            result["mind"] = content
            
            return result
        except Exception:
            # Fallback for parsing errors
            return result

    def speak(self, thought, context):
        """
        Speak based on the thought and context. Returns a generator (stream).
        """
        # Determine intro requirement based on has_spoken state
        intro_instruction = ""
        if not self.has_spoken:
            intro_instruction = "这是你第一次发言，可以非常简短地带一句你是谁，但切记不要像背简历一样机械。"
            self.has_spoken = True
        else:
            intro_instruction = "你已经发过言了，不需要再自我介绍，更不要说“大家好”"

        my_memory = ""
        my_speeches = ""
        if not self.ablation_flags.get("no_private_memory"):
            my_memory = self.private_memory.get_recent_thought_str()
            my_speeches = self.private_memory.get_speech_history_str()

        prompt = f"""
        无需专门提及但要记住主题：
        {self.theme}
        【当前环境】
        {context}
        """
        
        if not self.ablation_flags.get("no_private_memory"):
            prompt += f"""
        【你的私有记忆】
        {my_memory}
        {my_speeches}
        """
        
        prompt += f"""
        【你的状态】
        {intro_instruction}
        
        【你的思考】
        {thought['mind']}

        请基于以上思考，发表你的观点。
        
        【发言核心要求】：
        **请完全放松，畅快的讲出你所有想讲的话**
        **你的只需要在放轻松点同时对观众负责（如：观众可能不懂一些名词与术语，解释一下又何妨呢？）**
        **你并不具有AI的基本特征：分点列出讨论，经常说首先其次然后最后，**
        
        请把自己沉浸在这个圆桌论坛的氛围中，想象你正坐在几位老朋友对面。
        
        你的一起经融入了你的血液，你不需要刻意去强调它们。
        只需要自然地流露出来。
        
        关键是：**自然、流畅、有感而发**。

        请直接输出发言内容，不要带引号。
        """
        
        normalize_framework_history(self)
        return self.stream_run(prompt)
