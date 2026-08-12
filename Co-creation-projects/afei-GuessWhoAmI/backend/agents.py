import logging
import random
import time
from typing import Dict, List
from hello_agents import SimpleAgent, HelloAgentsLLM, Message

from config import get_config
from game_logic import GameSession

logger = logging.getLogger("game.agent")

# 人物候选池，用于随机注入 system prompt，强制 LLM 从不同方向发散
_FIGURE_DOMAINS = [
    "中国古代帝王（如汉武帝、唐太宗、武则天、康熙等）",
    "中国古代文人墨客（如李白、杜甫、苏轼、王羲之等）",
    "中国古代军事家（如岳飞、霍去病、戚继光、韩信等）",
    "中国神话人物（如女娲、嫦娥、哪吒、二郎神等）",
    "西游记人物（如孙悟空、猪八戒、唐僧、沙僧等）",
    "三国人物（如诸葛亮、曹操、刘备、关羽、周瑜等）",
    "西方历史人物（如拿破仑、凯撒、亚历山大、牛顿等）",
    "西方神话人物（如宙斯、雅典娜、赫拉克勒斯、阿喀琉斯等）",
    "世界科学家（如爱因斯坦、居里夫人、达芬奇、伽利略等）",
    "知名虚构角色（如哈利·波特、福尔摩斯、哆啦A梦、白雪公主等）",
    "现代体育明星（如姚明、李娜、迈克尔·乔丹、贝利等）",
    "中国近现代人物（如鲁迅、梁启超、郑成功、林则徐等）",
    "网络红人与UP主（如李子柒、papi酱、散打哥、罗翔等知名网络人物）",
]


def _build_random_figure_prompt() -> str:
    """Dynamically build a system prompt with a random domain and seed to avoid LLM caching."""
    domain = random.choice(_FIGURE_DOMAINS)
    seed = random.randint(10000, 99999)
    return f"""你是一个随机知名人物生成器。随机种子：{seed}
本次请从【{domain}】这个方向随机选择一个人物。
要求：
1. 必须是大众熟知、有足够信息可供猜测的人物
2. 必须是人物（真实或虚构），不要选建筑、动植物、自然景观等物体
3. 输出格式严格如下（两行，不要多余内容）：
名称：<人物名称>
简介：<一句话概括其性格特点与主要成就，50字以内>
4. 每次必须随机选择，不要总是选同一个"""

_HINT_SYSTEM_PROMPT = """你是一位博学的助手。
根据提供的搜索资料，生成3条适合猜谜游戏的提示。
要求：
1. 每条提示单独一行，格式为：提示N：<内容>
2. 提示由模糊到具体，第1条最模糊，第3条最具体
3. 不能直接说出答案的名称
4. 只输出3行提示，不要其他内容"""

_SEMANTIC_MATCH_PROMPT = """你是一位知识渊博的助手。请判断以下两个名称是否指代同一个人物或事物。
只需回答 "是" 或 "否"，不要输出任何其他内容。
名称A：{guess}
名称B：{actual}"""

_ROLEPLAY_SYSTEM_PROMPT = """你正在参与一个猜谜游戏，扮演一个神秘人物（代号：【谜底】）。

## 人物背景（仅供你参考，不可直接透露）：
{bio}

## 对话规则：
1. 以该人物的第一人称身份回答，语气、措辞符合其性格特点与所处时代/背景
2. 用户会通过提问来猜测你的身份，**必须直接针对用户的问题给出明确回应**（如"是的"/"不是"/"确实如此"等），不能回避或答非所问
3. 在给出明确回应的基础上，可以用符合人物身份的语气补充一句，增加趣味性
4. 每次回答要简短（1-2句话），不要长篇大论
5. 回答内容要基于该人物真实的生平、性格、成就，不要编造
6. **严禁在任何情况下说出该人物的名称**（包括姓名、字号、封号、外号等一切称谓）
7. 如果用户的问题与该人物完全无关，可以用符合人物身份的方式婉转说明"""


class HistoricalFigureAgent:
    """GuessWhoAmI game Agent wrapper"""

    def __init__(self, game_session: GameSession):
        """
        Initialize Agent: use LLM to randomly generate a subject (person/object/landmark etc.)
        with brief intro, then use TavilySearchTool to pre-generate 3 hints, finally create
        role-play Agent.

        Args:
            game_session: game session object to store current subject info
        """
        self.game_session = game_session
        config = get_config()

        logger.info(f"[AGENT] Initializing LLM: model={config.LLM_MODEL_ID} base_url={config.LLM_BASE_URL}")

        self._llm = HelloAgentsLLM(
            model=config.LLM_MODEL_ID,
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
            timeout=config.LLM_TIMEOUT,
            provider="modelscope"
        )
        self._config = config

        # Register search tool
        self._search_tool = None
        if config.TAVILY_API_KEY:
            from tools.tavily_search_tool import TavilySearchTool
            self._search_tool = TavilySearchTool(api_key=config.TAVILY_API_KEY)
            logger.info("[AGENT] TavilySearchTool registered")
        else:
            logger.warning("[AGENT] TAVILY_API_KEY not set, search tool disabled")

        # Register Wikipedia image tool (no API key required)
        from tools.search_image_tool import SearchImageTool
        self._image_tool = SearchImageTool()
        logger.info("[AGENT] SearchImageTool (Wikipedia) registered")

        # Step 1: LLM generates subject name + brief intro
        figure = self._generate_figure()
        self.game_session.current_figure = figure
        logger.info(f"[AGENT] Subject loaded: {figure}")

        # Step 2: pre-generate 3 hints via tavily search
        hints = self._generate_hints(figure["name"])
        self.game_session.hints = hints
        logger.info(f"[AGENT] Hints pre-generated: {hints}")

        # Step 3: create role-play Agent
        self.agent = self._create_roleplay_agent()

    # ── Subject generation ────────────────────────────────────────────────────

    def _generate_figure(self) -> Dict[str, str]:
        """Use LLM to randomly generate a subject (person/object/landmark) with brief intro."""
        try:
            system_prompt = _build_random_figure_prompt()
            ts = int(time.time() * 1000)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请随机给我一个（时间戳：{ts}，随机数：{random.randint(1, 9999)}）"},
            ]
            raw = self._llm.invoke(messages).strip()
            logger.info(f"[AGENT] LLM generated subject raw: {raw!r}")
            return self._parse_figure(raw)
        except Exception as e:
            logger.error(f"[AGENT] Failed to generate subject via LLM: {e}", exc_info=True)
            return self._fallback_figure()

    def _parse_figure(self, raw: str) -> Dict[str, str]:
        """Parse LLM output into {name, bio} dict."""
        name = ""
        bio = ""
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("名称：") or line.startswith("名称:") or line.startswith("姓名：") or line.startswith("姓名:"):
                name = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif line.startswith("简介：") or line.startswith("简介:"):
                bio = line.split("：", 1)[-1].split(":", 1)[-1].strip()
        if not name:
            logger.warning("[AGENT] Failed to parse subject name, using fallback")
            return self._fallback_figure()
        return {"name": name, "bio": bio}

    def _fallback_figure(self) -> Dict[str, str]:
        """Return a minimal fallback person when LLM fails."""
        persons = [
            ("孔子", "春秋时期思想家、教育家，儒家学派创始人，性格温和而坚定，一生致力于礼乐仁义"),
            ("孙悟空", "《西游记》中的神话英雄，天性顽皮好斗、嫉恶如仇，七十二变，大闹天宫"),
            ("武则天", "中国历史上唯一的女皇帝，铁腕治国，心思缜密，开创武周政权"),
            ("诸葛亮", "三国时期蜀汉丞相，足智多谋、鞠躬尽瘁，以隆中对和空城计闻名"),
            ("哈利·波特", "《哈利·波特》系列中的魔法师主角，勇敢善良，最终击败伏地魔"),
        ]
        name, bio = random.choice(persons)
        return {"name": name, "bio": bio}

    # ── Hint generation ───────────────────────────────────────────────────────

    def _generate_hints(self, name: str) -> List[str]:
        """Use TavilySearchTool to search subject info, then LLM generates 3 hints."""
        if not self._search_tool:
            return self._fallback_hints(name)

        try:
            search_results = self._search_tool.run(
                {"query": f"{name} 简介 特点 介绍"}
            )
            logger.info(f"[AGENT] Search results for hints, length: {len(search_results)} chars")

            messages = [
                {"role": "system", "content": _HINT_SYSTEM_PROMPT},
                {"role": "user", "content": f"答案：{name}\n\n搜索资料：\n{search_results}\n\n请生成3条提示："},
            ]
            raw = self._llm.invoke(messages).strip()
            logger.info(f"[AGENT] LLM hint raw output: {raw!r}")
            return self._parse_hints(raw, name)

        except Exception as e:
            logger.error(f"[AGENT] Hint generation failed: {e}", exc_info=True)
            return self._fallback_hints(name)

    def _parse_hints(self, raw: str, name: str) -> List[str]:
        """Parse LLM hint output into a list of 3 hint strings."""
        hints = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            # Remove prefix like "提示1：" / "提示1:" / "1." etc.
            import re
            cleaned = re.sub(r'^(提示\d[：:]\s*|\d+[\.、]\s*)', '', line).strip()
            if cleaned:
                hints.append(cleaned)
        # Ensure exactly 3 hints
        if len(hints) >= 3:
            return hints[:3]
        # Pad with fallback if not enough
        fallback = self._fallback_hints(name)
        hints.extend(fallback[len(hints):])
        return hints[:3]

    def _fallback_hints(self, name: str) -> List[str]:
        """Return fallback hints when search/LLM fails."""
        return [
            "这是一个广为人知的事物",
            "它在各自的领域中具有重要地位或影响力",
            "它的名字在国内外都有很高的知名度",
        ]

    # ── Role-play Agent ───────────────────────────────────────────────────────

    def _create_roleplay_agent(self) -> SimpleAgent:
        """Create the role-play SimpleAgent (no tools, conversation only)"""
        system_prompt = self._create_system_prompt()
        agent = SimpleAgent(
            name="guess_who_agent",
            llm=self._llm,
            system_prompt=system_prompt,
            enable_tool_calling=False,
        )
        subject_name = self.game_session.current_figure.get("name", "未知")
        logger.info(f"[AGENT] Role-play agent created | subject={subject_name}")
        return agent

    def _create_system_prompt(self) -> str:
        """Create dynamic system prompt based on current subject"""
        figure = self.game_session.current_figure
        return _ROLEPLAY_SYSTEM_PROMPT.format(
            bio=figure["bio"],
        )

    # ── Guess ─────────────────────────────────────────────────────────────────

    def make_guess(self, guess_name: str) -> Dict:
        """Process a guess: semantic match via self._llm, then delegate to game_session.
        If correct, fetch figure portrait via SearchImageTool (Wikipedia).
        """
        result = self.game_session.make_guess(
            guess_name,
            semantic_match_fn=self._semantic_match
        )

        # If guessed correctly, fetch portrait images via Wikipedia
        if result.get("correct") and self._image_tool:
            figure_name = self.game_session.current_figure.get("name", guess_name)
            logger.info(f"[AGENT] Fetching portrait images for {figure_name!r}")
            photos = self._image_tool.search_photos(figure_name, per_page=3)
            result["portrait_images"] = photos
            logger.info(f"[AGENT] Portrait images fetched: {len(photos)} results")

        return result

    def _semantic_match(self, guess: str, actual: str) -> bool:
        """Use LLM to semantically judge whether guess and actual refer to the same subject."""
        try:
            prompt = _SEMANTIC_MATCH_PROMPT.format(guess=guess.strip(), actual=actual)
            result = self._llm.invoke([{"role": "user", "content": prompt}]).strip()
            logger.info(f"[AGENT] Semantic match | guess={guess!r} actual={actual!r} llm_answer={result!r}")
            return result.startswith("是")
        except Exception as e:
            logger.error(f"[AGENT] Semantic match failed: {e}", exc_info=True)
            return False

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
            return "抱歉，我现在有些恍惚，请再问一次吧。"

    def get_conversation_history(self) -> List[Message]:
        """Get full conversation history"""
        return self.agent.get_history()

    def reset_conversation(self):
        """Reset conversation history and reload subject"""
        self.agent.clear_history()
        # Reload a new subject
        figure = self._generate_figure()
        self.game_session.current_figure = figure
        # Re-generate hints
        hints = self._generate_hints(figure["name"])
        self.game_session.hints = hints
        # Rebuild system prompt
        system_prompt = self._create_system_prompt()
        self.agent.system_prompt = system_prompt
        logger.info("[AGENT] Conversation reset and new subject loaded")


# ── Utility functions ─────────────────────────────────────────────────────────

def check_guess(guess: str, actual_name: str) -> bool:
    """
    Check if user guess is correct

    Args:
        guess: user guessed name
        actual_name: actual subject name

    Returns:
        bool: whether guess is correct
    """
    return guess.strip().lower() == actual_name.lower()


def provide_hint(figure: Dict, hints: List[str], hint_index: int = 0) -> str:
    """
    Provide hint about the subject

    Args:
        figure: subject info dict
        hints: pre-generated hint list
        hint_index: which hint to return (0-based)

    Returns:
        str: hint message
    """
    if hints and hint_index < len(hints):
        return hints[hint_index]
    return "这是一个广为人知的事物"