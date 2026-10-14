"""心语倾诉助理。

安全检查在模型之前完成。通过检查的内容才会进入 SimpleAgent，
并按 user_id 写入本地专属记忆。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from src.memory.user_agent_store import UserAgentStore, validate_user_id
from src.safety.guardrails import GuardResult, check_message
from src.utils.paths import data_dir, project_root
from src.utils.summary import write_session_summary

SYSTEM_PROMPT = """你是「心语」，面向学生的倾诉助理。你不是心理医生、咨询师或医疗机构。

工作方式：
1. 先倾听和共情，不说教，也不急着讲大道理。
2. 帮对方整理三件事：此刻的感受、担心被误解的点、可以对父母或老师尝试的一种说法。
3. 语气稳一点、短一点，一次只往前推一小步。
4. 下方若有专属记忆，用它理解这个人，不要主动复述敏感细节。

边界：
- 不做诊断，不开药，不提供治疗方案。
- 不提供违法、暴力或色情内容。
- 若对方流露自伤或伤人风险，停止闲聊，请对方联系 12356、120 或 110，以及身边可信的成年人。
- 不鼓励隐瞒可能危及安全的情况。
"""

_PLACEHOLDER_KEYS = {"", "your-api-key", "your-api-key-here"}
_NO_LLM_REPLY = (
    "这句话已经通过安全检查，并写入了你的专属记忆。"
    "当前没有可用的 LLM API 密钥，所以我还不能生成倾听回复。"
    "请在项目目录配置 .env 后重新运行。"
)


class ConfideAgent:
    """单个使用者的倾诉助理。"""

    def __init__(
        self,
        user_id: str,
        store: UserAgentStore | None = None,
        llm=None,
    ):
        self.user_id = validate_user_id(user_id)
        self.store = store or UserAgentStore()
        self.llm = llm
        self._agent = None
        self._memory_tool = None

    def chat(self, message: str) -> str:
        """倾听一轮。被护栏拦住时不调用大模型。"""
        guard = check_message(message)
        if not guard.allowed:
            if guard.category != "empty":
                self.store.append_turn(self.user_id, message, guard.message, guard.category)
            return guard.message

        reply = self._reply(message)
        self.store.append_turn(self.user_id, message, reply, "ok")
        self._remember_working(message, reply)
        return reply

    def profile(self) -> dict:
        return self.store.load(self.user_id)

    def write_summary(self, filename: str = "session_summary.md") -> str:
        return write_session_summary(self.profile(), filename)

    def _reply(self, message: str) -> str:
        if not _llm_ready() and self.llm is None:
            return _NO_LLM_REPLY
        agent = self._ensure_agent()
        memory_context = self.store.context_for_prompt(self.user_id)
        prompt = (
            f"{memory_context}\n\n"
            "请根据上面的专属记忆（如果有）回应当前这句倾诉。\n"
            f"同学说：{message.strip()}"
        )
        return str(agent.run(prompt)).strip()

    def _ensure_agent(self):
        if self._agent is not None:
            return self._agent
        load_project_env()
        from hello_agents import HelloAgentsLLM, SimpleAgent

        llm = self.llm or HelloAgentsLLM()
        self._agent = SimpleAgent(
            name=f"心语-{self.user_id}",
            llm=llm,
            system_prompt=SYSTEM_PROMPT,
            enable_tool_calling=False,
        )
        self._attach_working_memory()
        return self._agent

    def _attach_working_memory(self) -> None:
        """当次会话的工作记忆。失败时仍保留本地 JSON 档案。"""
        if self._memory_tool is not None:
            return
        try:
            from hello_agents.tools import MemoryTool

            self._memory_tool = MemoryTool(
                user_id=self.user_id,
                memory_types=["working"],
            )
        except Exception:
            self._memory_tool = None

    def _remember_working(self, message: str, reply: str) -> None:
        if self._memory_tool is None:
            return
        try:
            self._memory_tool.run({
                "action": "add",
                "content": f"同学说：{message.strip()}\n心语回应：{reply.strip()}",
                "memory_type": "working",
                "importance": 0.6,
            })
        except Exception:
            return


def create_confide_agent(user_id: str | None = None, llm=None) -> ConfideAgent:
    """按 README 示例创建专属助理。"""
    load_project_env()
    resolved = user_id or os.getenv("DEFAULT_USER_ID") or "demo_student_001"
    return ConfideAgent(user_id=resolved, llm=llm)


def load_project_env() -> None:
    env_path = project_root() / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def replay_samples(sample_path: Path | None = None, memory_root: Path | None = None) -> dict:
    """回放 data/sample_dialogues.json。安全用例不进入模型。"""
    path = sample_path or (data_dir() / "sample_dialogues.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    store = UserAgentStore(root=memory_root)
    demo_ids = {item["user_id"] for item in payload.get("dialogues", [])}
    demo_ids.update(item.get("user_id", "safety_demo") for item in payload.get("safety_cases", []))
    for user_id in demo_ids:
        profile_path = store.path_for(user_id)
        if profile_path.exists():
            profile_path.unlink()
    agents: dict[str, ConfideAgent] = {}
    transcripts = []

    for case in payload.get("safety_cases", []):
        text = case["text"]
        result: GuardResult = check_message(text)
        transcripts.append({
            "kind": "safety",
            "text": text,
            "category": result.category,
            "expected": case.get("expect"),
            "passed": result.category == case.get("expect"),
        })
        if result.category != "ok":
            user_id = case.get("user_id", "safety_demo")
            if user_id not in agents:
                agents[user_id] = ConfideAgent(user_id, store=store)
            agents[user_id].store.append_turn(user_id, text, result.message, result.category)

    for dialogue in payload.get("dialogues", []):
        user_id = dialogue["user_id"]
        agent = agents.get(user_id) or ConfideAgent(user_id, store=store)
        agents[user_id] = agent
        for turn in dialogue.get("turns", []):
            reply = agent.chat(turn)
            transcripts.append({
                "kind": "dialogue",
                "user_id": user_id,
                "user": turn,
                "assistant": reply,
            })

    summaries = {user_id: agent.profile() for user_id, agent in agents.items()}
    return {"transcripts": transcripts, "profiles": summaries}


def _llm_ready() -> bool:
    load_project_env()
    key = (os.getenv("LLM_API_KEY") or "").strip()
    return key not in _PLACEHOLDER_KEYS and "your-api-key" not in key
