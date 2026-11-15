"""本场面试内的只读工具。工具事件不保存简历或回答原文。"""

import json
import secrets
import time

from .prompts import DATA_RULES, INTERVIEW_PROMPT
from .store import uid


class InterviewTools:
    def __init__(self, engine, session):
        self.engine, self.session = engine, session
        self.events = []

    def topic(self, topic_id):
        for topic in self.session["topics"]:
            if topic["id"] == topic_id:
                return topic
        raise ValueError("未知主题，工具只能访问本场面试的主题。")

    def invoke(self, name, parameters):
        started = time.perf_counter()
        status = "success"
        try:
            if len(self.events) >= 6:
                raise ValueError("本轮工具调用预算已用尽。")
            if name == "read_scoring_rubric":
                result = self.session["rubric"]
            else:
                topic = self.topic(parameters.get("topic_id"))
                if name == "read_material_evidence":
                    snapshot = self.session["snapshot"]
                    result = {
                        "topic": topic["title"],
                        "claims": [
                            c
                            for c in snapshot["analysis"]["claims"]
                            if c["id"] in topic["claim_ids"]
                        ],
                        "requirements": [
                            r
                            for r in snapshot["analysis"]["requirements"]
                            if r["topic"] == topic["title"]
                        ],
                        "notice": "材料只是候选人自述，不证明实际技术正确性。",
                    }
                elif name == "read_topic_history":
                    result = [
                        {
                            "turn_id": t["id"],
                            "question": t["question"]["text"],
                            "answer": t["answer"],
                        }
                        for t in self.session["turns"]
                        if t["question"].get("topic_id") == topic["id"]
                    ]
                else:
                    raise ValueError("未知工具。")
            return json.dumps(result, ensure_ascii=False)
        except ValueError as exc:
            status = "error"
            return json.dumps({"error": str(exc)}, ensure_ascii=False)
        finally:
            event = {
                "id": uid(),
                "name": name,
                "topic_id": parameters.get("topic_id"),
                "status": status,
                "duration_ms": round((time.perf_counter() - started) * 1000),
            }
            self.events.append(event)
            if self.engine.store:
                self.engine.store.event(
                    self.session["workspace_id"],
                    {
                        **event,
                        "stage": "tool",
                        "mode": self.session["mode"],
                        "model": "本场只读工具",
                        "input_chars": len(json.dumps(parameters)),
                        "tokens": None,
                    },
                )


def native_decision(engine, session, schema):
    from hello_agents import FunctionCallAgent, ToolRegistry
    from hello_agents.tools.base import Tool, ToolParameter

    tools = InterviewTools(engine, session)

    class ReadTool(Tool):
        def get_parameters(self):
            return (
                []
                if self.name == "read_scoring_rubric"
                else [
                    ToolParameter(
                        name="topic_id",
                        type="string",
                        description="本场面试主题 ID",
                        required=True,
                    )
                ]
            )

        def run(self, parameters):
            return tools.invoke(self.name, parameters)

    registry = ToolRegistry()
    for name, description in [
        (
            "read_material_evidence",
            "读取指定主题关联的冻结简历主张与岗位要求，进入新主题前使用。",
        ),
        (
            "read_topic_history",
            "读取指定主题本场已问的问题和候选人原始回答，核查重复、缺口和矛盾。",
        ),
        (
            "read_scoring_rubric",
            "读取本场锁定的观察维度与评分锚点，不向面试者透露答案。",
        ),
    ]:
        registry.register_tool(ReadTool(name, description))
    agent = FunctionCallAgent(
        name="interview",
        llm=engine.make_llm(timeout=20),
        tool_registry=registry,
        system_prompt=DATA_RULES
        + "\n"
        + INTERVIEW_PROMPT
        + "\n最终输出 Schema："
        + json.dumps(schema.model_json_schema(), ensure_ascii=False),
        max_tool_iterations=2,
    )
    current = next(
        (t for t in session["topics"] if t["id"] == session["current_topic_id"]), None
    )
    context = {
        "topics": session["topics"],
        "current_topic_id": session["current_topic_id"],
        "latest_turn": session["turns"][-1] if session["turns"] else None,
        "remaining_turns": session["budget"]["total_turns"] - len(session["turns"]),
        "max_topic_turns": session["budget"]["max_topic_turns"],
        "allowed_actions": allowed_actions(session),
        "current_topic_turns": sum(
            t["question"]["topic_id"] == current["id"] for t in session["turns"]
        )
        if current
        else 0,
    }
    result = engine.structured_run(agent, context, schema)
    session["_step_tool_events"] = tools.events
    return result


def allowed_actions(session):
    if session["current_topic_id"] is None:
        return ["switch_topic"]
    can_switch = any(t["status"] == "unvisited" for t in session["topics"])
    actions = ["switch_topic" if can_switch else "finish"]
    count = sum(
        t["question"]["topic_id"] == session["current_topic_id"]
        for t in session["turns"]
    )
    if count < session["budget"]["max_topic_turns"]:
        actions.insert(0, "ask_followup")
    return actions


def probe_native_tools(engine):
    """用服务端随机值证明实际执行了原生工具，不读取用户材料。"""
    from hello_agents import FunctionCallAgent, ToolRegistry

    nonce = secrets.token_hex(12)
    called = []
    registry = ToolRegistry()

    def probe(_value):
        called.append(True)
        return nonce

    registry.register_function("get_probe_nonce", "读取服务端随机校验值。", probe)
    agent = FunctionCallAgent(
        name="native-probe",
        llm=engine.make_llm(timeout=15),
        tool_registry=registry,
        max_tool_iterations=1,
        system_prompt="必须调用 get_probe_nonce 获取随机值，然后仅原样返回该值。不要猜测。",
    )
    output = agent.run("请验证工具调用。")
    if not called or nonce not in output:
        raise ValueError("未观察到完整的原生工具调用与结果回传。")
    return {"supported": True, "message": "原生工具调用及结果回传通过。"}
