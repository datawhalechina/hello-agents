"""pytest 公共夹具：FakeLLM、配置与样例请求。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import Settings  # noqa: E402
from src.models import StoryRequest  # noqa: E402

LONG_DRAFT = (
    "雨从傍晚开始下，便利店的玻璃门被风推得轻轻作响。林岚把最后一箱牛奶码上货架，"
    "抬头看见一个浑身湿透的老人站在门口，手里攥着一张被雨水泡皱的地址条。\n\n"
    "老人说他要找二十三年前在这里上夜班的女儿。林岚没有立刻回答，她给他倒了杯热水，"
    "把地址条摊在收银台上烘干，字迹一点点浮出来，竟是她母亲的名字。\n\n"
    "凌晨三点，雨停了。林岚关掉半排灯，陪老人坐在窗边等天亮。她第一次听他说起"
    "那些被家人刻意避开的往事，也第一次明白母亲为何总在雨夜多煮一碗面。"
) * 2

LONG_DRAFT_2 = (
    "雨声敲在便利店的遮阳棚上，像有人用指节一下一下叩门。林岚把临期的饭团挑出来，"
    "看见老人推门进来，雨水顺着他的袖口滴成一条细线。\n\n"
    "他掏出一张地址条，说想找二十三年未见的女儿。林岚把纸条压在收银台的灯下，"
    "看清那行褪色的字，手停在半空——那是母亲年轻时住过的街道。\n\n"
    "她拨通母亲的电话，把听筒递给老人，自己走到货架尽头整理饮料。等她回来时，"
    "老人正对着电话反复说“我到了”，而窗外第一班公交车正碾过积水。\n\n"
    "天亮前，母亲撑着伞赶来。林岚给两个人各煮了一碗面，热气模糊了玻璃，"
    "也模糊了她终于拼完整的家事。"
)


def build_review(
    *,
    approved: bool,
    overall: int,
    relevance: int,
    instructions: list[str] | None = None,
) -> str:
    """构造一段合法的审稿 JSON 字符串。"""
    if instructions is None:
        instructions = [] if approved else ["补充与用户需求直接相关的情节"]
    payload = {
        "approved": approved,
        "overall_score": overall,
        "scores": {
            "relevance": relevance,
            "completeness": overall,
            "genre_format": overall,
            "style": overall,
        },
        "issues": [],
        "revision_instructions": instructions,
        "summary": "稿件整体与需求基本相符，个别细节仍需调整以提升相关性。",
    }
    return json.dumps(payload, ensure_ascii=False)


class FakeLLM:
    """按顺序返回预设文本的假 LLM，记录调用参数。"""

    def __init__(self, responses: list[str] | None = None, error: Exception | None = None):
        self.responses = list(responses or [])
        self.error = error
        self.model = "fake-model"
        self.provider = "openai"
        self.calls: list[tuple[list[dict[str, str]], dict[str, object]]] = []

    def invoke(self, messages, **kwargs):
        self.calls.append((list(messages), dict(kwargs)))
        if self.error is not None:
            raise self.error
        if not self.responses:
            content = ""
        elif len(self.responses) == 1:
            content = self.responses[0]
        else:
            content = self.responses.pop(0)
        return SimpleNamespace(
            content=content,
            usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
            latency_ms=12,
        )


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """指向临时目录、带假 LLM 配置的运行配置。"""
    return Settings(
        llm_model_id="fake-model",
        llm_api_key="test-key",
        llm_base_url="http://127.0.0.1:9/v1",
        output_dir=tmp_path / "outputs",
        cleanup_keep_runs=10,
        approve_score=80,
        min_relevance_score=80,
    )


@pytest.fixture
def novel_request() -> StoryRequest:
    """一条 200 字目标长度的小说请求。"""
    return StoryRequest(
        prompt="写一个雨夜便利店的故事，主角是夜班店员，结尾要有和解。",
        genre="novel",
        style="温暖克制",
        target_length=200,
        max_rounds=2,
    )
