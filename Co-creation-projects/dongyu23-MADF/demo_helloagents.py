"""Minimal end-to-end MADF discussion powered by HelloAgents."""

from app.agent.agent import ModeratorAgent, ParticipantAgent
from app.agent.memory import SharedMemory


def _consume(stream):
    return "".join(token for token in stream if token)


def run_demo(topic="人工智能应该如何参与公共决策？"):
    persona = {
        "name": "林衡",
        "title": "公共政策研究者",
        "bio": "长期研究技术治理、公共参与和算法问责。",
        "theories": ["审议民主", "算法问责", "风险治理"],
        "stance": "技术可以辅助决策，但不能替代公共责任。",
        "system_prompt": "你是公共政策研究者林衡，表达具体、审慎并回应他人。",
    }
    moderator = ModeratorAgent(topic)
    participant = ParticipantAgent(persona["name"], persona, 1, topic)
    memory = SharedMemory(1)

    opening = _consume(moderator.opening([persona]))
    memory.add_message(moderator.name, opening)

    context = memory.get_context_str() + "\n主持人点名请林衡发表观点。"
    thought = participant.think(context) or {"action": "apply_to_speak", "mind": "回应主持人的问题。"}
    speech = _consume(participant.speak(thought, context))
    memory.add_message(participant.name, speech)

    summary = _consume(moderator.periodic_summary(memory.get_messages_for_summary()))
    memory.add_summary(summary)
    closing = _consume(moderator.closing(memory.get_summaries()))

    return {
        "topic": topic,
        "opening": opening,
        "thought": thought,
        "speech": speech,
        "summary": summary,
        "closing": closing,
    }


if __name__ == "__main__":
    transcript = run_demo()
    for key in ("opening", "speech", "summary", "closing"):
        print(f"\n[{key}]\n{transcript[key]}")
