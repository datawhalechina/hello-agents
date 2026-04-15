import json
import logging
import random
from typing import Dict, List, Optional
from hello_agents import SimpleAgent, HelloAgentsLLM, Message

from config import get_config
from game_logic import GameSession

logger = logging.getLogger("game.agent")

_RANDOM_FIGURE_SYSTEM_PROMPT = """你是一个随机人物生成器。
请随机生成一个中国历史人物或中国神话传说人物的名字。
要求：
1. 可以是历史上真实存在的人物（帝王将相、文人墨客、科学家、军事家等）
2. 也可以是神话传说中的人物（如孙悟空、哪吒、嫦娥、女娲、关羽等）
3. 只输出人物名字，不要输出任何其他内容
4. 每次必须随机选择，不要总是选同一个人"""

_DISTILL_SYSTEM_PROMPT = """你是一位历史学家助手。
当用户给你一段关于某历史人物的搜索结果时，请提炼出结构化信息。
请严格按照以下 JSON 格式输出，不要输出任何其他内容：
{
  "name": "人物姓名",
  "dynasty": "所属朝代或时代（如：唐朝、春秋时期、近代等）",
  "occupation": "主要职业或身份（如：诗人、皇帝、军事家等）",
  "achievements": "主要成就，一句话概括（50字以内）",
  "characteristics": "关键性格特征或历史特点，一句话概括（50字以内）"
}"""


class HistoricalFigureAgent:
    """Guess historical figure game Agent wrapper"""

    def __init__(self, game_session: GameSession):
        """
        Initialize Agent: randomly pick a figure, search for info via tool,
        distill structured profile, then create the role-play Agent.

        Args:
            game_session: game session object to store current figure info
        """
        self.game_session = game_session
        config = get_config()

        logger.info(f"[AGENT] Initializing LLM: model={config.LLM_MODEL_ID} base_url={config.LLM_BASE_URL}")

        self._llm = HelloAgentsLLM(
            model=config.LLM_MODEL_ID,
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
            provider="modelscope"
        )
        self._config = config

        # Register search tool on this agent
        self._search_tool = None
        if config.TAVILY_API_KEY:
            from tools.tavily_search_tool import TavilySearchTool
            self._search_tool = TavilySearchTool(api_key=config.TAVILY_API_KEY)
            logger.info("[AGENT] TavilySearchTool registered")
        else:
            logger.warning("[AGENT] TAVILY_API_KEY not set, search tool disabled")

        # Step 1: load figure profile via search tool
        figure = self._load_figure_via_search()
        self.game_session.current_figure = figure
        # Inject LLM into game_session for semantic guess matching
        self.game_session._llm = self._llm
        logger.info(f"[AGENT] Figure loaded: {figure}")

        # Step 2: create role-play Agent
        self.agent = self._create_roleplay_agent()

    # ── Figure loading ────────────────────────────────────────────────────────

    def _load_figure_via_search(self) -> Dict[str, str]:
        """
        Use LLM to randomly generate a figure name, call TavilySearchTool directly,
        then use LLM to distill a structured profile.
        """
        name = self._generate_random_figure_name()
        logger.info(f"[AGENT] Selected figure: {name}")

        if not self._search_tool:
            return self._fallback_figure(name)

        try:
            # Step 1: call search tool directly
            search_results = self._search_tool.run(
                {"query": f"{name} 历史人物 生平 成就 简介"}
            )
            logger.info(f"[AGENT] Search results length: {len(search_results)} chars")

            # Step 2: use LLM to distill structured profile
            prompt = (
                f'以下是关于"{name}"的搜索结果：\n\n{search_results}\n\n'
                f'请严格按照系统提示的 JSON 格式，输出关于"{name}"的结构化信息，不要输出任何其他内容。'
            )
            logger.info(f"[AGENT] LLM distillation prompt: {prompt}")
            messages = [
                {"role": "system", "content": _DISTILL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            raw = self._llm.invoke(messages)
            logger.info(f"[AGENT] LLM distillation raw output: {raw!r}")

            return self._parse_figure_json(raw, name)

        except Exception as e:
            logger.error(f"[AGENT] Figure search/distill failed: {e}", exc_info=True)
            return self._fallback_figure(name)

    def _generate_random_figure_name(self) -> str:
        """Use LLM to randomly generate a historical or mythological figure name."""
        try:
            import time
            # Add timestamp to ensure randomness each call
            messages = [
                {"role": "system", "content": _RANDOM_FIGURE_SYSTEM_PROMPT},
                {"role": "user", "content": f"请随机给我一个人物名字（当前时间戳：{int(time.time() * 1000)}）"},
            ]
            name = self._llm.invoke(messages).strip()
            # Clean up: take only the first line in case of extra output
            name = name.splitlines()[0].strip()
            logger.info(f"[AGENT] LLM generated figure name: {name!r}")
            return name
        except Exception as e:
            logger.error(f"[AGENT] Failed to generate figure name via LLM: {e}", exc_info=True)
            # Fallback to a hardcoded default
            fallback = random.choice(["孔子", "秦始皇", "李白", "武则天", "孙悟空", "嫦娥", "岳飞", "诸葛亮"])
            logger.warning(f"[AGENT] Using fallback figure: {fallback}")
            return fallback

    def _parse_figure_json(self, raw: str, name: str) -> Dict[str, str]:
        """Extract and parse JSON from LLM output, with fallback."""
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            try:
                data = json.loads(raw[start:end])
                required = {"name", "dynasty", "occupation", "achievements", "characteristics"}
                if required.issubset(data.keys()):
                    return data
            except json.JSONDecodeError:
                pass
        logger.warning(f"[AGENT] Failed to parse JSON for {name}, using fallback")
        return self._fallback_figure(name)

    def _fallback_figure(self, name: str) -> Dict[str, str]:
        """Return a minimal fallback profile when search/LLM fails."""
        return {
            "name": name,
            "dynasty": "中国历史",
            "occupation": "历史人物",
            "achievements": f"{name}是中国历史上的著名人物",
            "characteristics": "具体信息请通过对话探索",
        }

    # ── Role-play Agent ───────────────────────────────────────────────────────

    def _create_roleplay_agent(self) -> SimpleAgent:
        """Create the role-play SimpleAgent (no tools, conversation only)"""
        system_prompt = self._create_system_prompt()
        agent = SimpleAgent(
            name="historical_figure_agent",
            llm=self._llm,
            system_prompt=system_prompt,
            enable_tool_calling=False,
        )
        figure_name = self.game_session.current_figure.get("name", "未知")
        logger.info(f"[AGENT] Role-play agent created | figure={figure_name}")
        return agent

    def _create_system_prompt(self) -> str:
        """Create dynamic system prompt based on current figure"""
        figure = self.game_session.current_figure
        prompt = f"""
你是一位历史人物角色扮演Agent。当前你扮演的历史人物是：{figure['name']}。

## 人物背景信息：
- 朝代/时代：{figure['dynasty']}
- 职业/身份：{figure['occupation']}
- 主要成就：{figure['achievements']}
- 关键特征：{figure['characteristics']}

## 游戏规则：
1. 你将以{figure['name']}的身份与用户对话
2. 用户会通过提问来猜测你的身份
3. 你不能直接透露自己的姓名
4. 回答要符合该历史人物的真实信息和性格特点
5. **每次回答只能是"是"或"否"，不得包含任何其他内容**
6. 如果用户的问题无法用"是"或"否"回答，请回答"否"

请开始与用户对话，等待用户提问。
"""
        return prompt.strip()

    # ── Chat ──────────────────────────────────────────────────────────────────

    def chat(self, user_message: str) -> str:
        """
        Process user message and return Agent reply

        Args:
            user_message: user input message

        Returns:
            Agent reply content
        """
        try:
            logger.info(f"[AGENT] Calling LLM | user={user_message!r}")
            response = self.agent.run(user_message)
            logger.info(f"[AGENT] LLM response received | response={response!r}")

            # Update game state (increment question count)
            self.game_session.ask_question()

            return response
        except Exception as e:
            logger.error(f"[AGENT] LLM call failed: {e}", exc_info=True)
            return f"抱歉，处理消息时出现错误：{str(e)}"

    def get_conversation_history(self) -> List[Message]:
        """Get full conversation history"""
        return self.agent.get_history()

    def reset_conversation(self):
        """Reset conversation history and reload figure via search"""
        self.agent.clear_history()
        # Reload a new figure
        figure = self._load_figure_via_search()
        self.game_session.current_figure = figure
        # Rebuild system prompt
        system_prompt = self._create_system_prompt()
        self.agent.system_prompt = system_prompt
        logger.info("[AGENT] Conversation reset and new figure loaded")


# ── Utility functions ─────────────────────────────────────────────────────────

def check_guess(guess: str, actual_name: str) -> bool:
    """
    Check if user guess is correct

    Args:
        guess: user guessed figure name
        actual_name: actual figure name

    Returns:
        bool: whether guess is correct
    """
    return guess.strip().lower() == actual_name.lower()


def provide_hint(figure: Dict) -> str:
    """
    Provide hint about historical figure

    Args:
        figure: historical figure info dict

    Returns:
        str: hint message
    """
    hints = [
        f"这位人物生活在{figure['dynasty']}时期",
        f"TA的主要身份是{figure['occupation']}",
        f"TA的著名成就是：{figure['achievements']}",
        f"TA的一个显著特征是：{figure['characteristics']}",
    ]
    return hints[0]