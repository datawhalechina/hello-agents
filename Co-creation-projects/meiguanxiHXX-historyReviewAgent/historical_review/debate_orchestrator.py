"""多角色历史辩论编排：观点碰撞 → 终局综合（最可能事实 / 可疑点 / 阴谋论辨析）。"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from hello_agents import HelloAgentsLLM

from .config import create_llm
from .debate_prompts import (
    EVIDENCE_PREAMBLE,
    SUMMARIZER_FOR_ROUND2,
    SYSTEM_FOREIGN,
    SYSTEM_OFFICIAL,
    SYSTEM_POLITICAL,
    SYSTEM_SUSPICION,
    SYSTEM_SYNTHESIZER,
    SYSTEM_UNOFFICIAL,
    USER_ROUND1_TEMPLATE,
    USER_ROUND2_TEMPLATE,
    USER_SYNTHESIZER_TEMPLATE,
)
from .evidence_bundle import build_evidence_bundle


@dataclass(frozen=True)
class RoleSpec:
    key: str
    display_name: str
    system_prompt: str


ROLES: tuple[RoleSpec, ...] = (
    RoleSpec("official", "官修史书与王朝叙事", SYSTEM_OFFICIAL),
    RoleSpec("unofficial", "野史与边缘叙事", SYSTEM_UNOFFICIAL),
    RoleSpec("political", "政治语境与权力结构", SYSTEM_POLITICAL),
    RoleSpec("foreign", "域外与他者视角", SYSTEM_FOREIGN),
    RoleSpec("suspicion", "蹊跷与阴谋论辨析", SYSTEM_SUSPICION),
)

# 进度：议题 + 附录 + 五角色第一轮 + 秘书 + 五角色第二轮 + 终局（step 0..14 → 共 15 段）
TOTAL_STEPS = 15


def _excerpt(text: str, limit: int = 380) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def _invoke(llm: HelloAgentsLLM, system: str, user: str, *, temperature: float) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return (llm.invoke(messages, temperature=temperature) or "").strip()


def _summarize_round1_for_context(llm: HelloAgentsLLM, round1: dict[str, str]) -> str:
    body = "\n\n".join(f"### {r.display_name}\n{round1[r.key]}" for r in ROLES)
    return _invoke(
        llm,
        SUMMARIZER_FOR_ROUND2,
        body,
        temperature=0.15,
    )


def _yield_progress(step: int, message: str, **extra: Any) -> dict[str, Any]:
    return {
        "event": "progress",
        "step": step,
        "total": TOTAL_STEPS,
        "message": message,
        **extra,
    }


def iter_debate_events(
    topic: str,
    *,
    llm: HelloAgentsLLM | None = None,
    use_evidence_bundle: bool = True,
    debate_temperature: float = 0.72,
    synthesizer_temperature: float = 0.22,
    llm_api_key: str | None = None,
    llm_base_url: str | None = None,
    llm_model: str | None = None,
    llm_max_tokens: int | None = 4096,
    llm_timeout: int | None = None,
) -> Iterator[dict[str, Any]]:
    """
    逐步产出辩论过程事件，供 SSE / 日志展示。

    事件类型
    --------
    - progress: step, total, message
    - round1_start / round1_end: role, content（end）
    - digest_start / digest_end: content（end）
    - round2_start / round2_end: role, content（end）
    - synthesis_start / synthesis_end: content（end）
    - complete: markdown（全文）
    """
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("议题不能为空")

    if llm is None:
        llm = create_llm(
            api_key=llm_api_key,
            base_url=llm_base_url,
            model=llm_model,
            max_tokens=llm_max_tokens,
            timeout=llm_timeout,
            temperature=0.4,
        )

    step = 0

    yield _yield_progress(step, f"议题已接收：{topic[:80]}{'…' if len(topic) > 80 else ''}")
    step += 1

    evidence_block = ""
    if use_evidence_bundle:
        yield _yield_progress(step, "正在抓取维基与 DuckDuckGo 考据附录（可能需几十秒）…")
        evidence_block = EVIDENCE_PREAMBLE + "\n\n" + build_evidence_bundle(topic)
        yield {
            "event": "evidence_done",
            "step": step,
            "total": TOTAL_STEPS,
            "chars": len(evidence_block),
            "preview": evidence_block[:600] + ("…" if len(evidence_block) > 600 else ""),
        }
    else:
        yield _yield_progress(step, "已跳过网络附录，将仅依赖模型知识。")
        evidence_block = "（未启用网络附录；请完全依赖你的训练知识与逻辑。）"
    step += 1

    lines: list[str] = [
        "# 多角色历史辩论记录\n",
        f"## 议题\n{topic}\n",
    ]

    round1: dict[str, str] = {}
    for role in ROLES:
        yield {
            "event": "round1_start",
            "step": step,
            "total": TOTAL_STEPS,
            "role": role.display_name,
            "message": f"第一轮 · {role.display_name}：正在调用模型…",
        }
        user_msg = USER_ROUND1_TEMPLATE.format(topic=topic, evidence_block=evidence_block)
        out = _invoke(llm, role.system_prompt, user_msg, temperature=debate_temperature)
        round1[role.key] = out
        md_chunk = f"### 第一轮 · {role.display_name}\n\n{out}\n"
        lines.append(md_chunk)
        yield {
            "event": "round1_end",
            "step": step,
            "total": TOTAL_STEPS,
            "role": role.display_name,
            "content": out,
            "markdown_section": md_chunk,
        }
        step += 1

    yield {
        "event": "digest_start",
        "step": step,
        "total": TOTAL_STEPS,
        "message": "秘书：正在压缩第一轮五角色发言…",
    }
    digest = _summarize_round1_for_context(llm, round1)
    digest_md = f"### 秘书摘要（供第二轮引用）\n\n{digest}\n"
    lines.append(digest_md)
    yield {
        "event": "digest_end",
        "step": step,
        "total": TOTAL_STEPS,
        "content": digest,
        "markdown_section": digest_md,
    }
    step += 1

    round2: dict[str, str] = {}
    for role in ROLES:
        yield {
            "event": "round2_start",
            "step": step,
            "total": TOTAL_STEPS,
            "role": role.display_name,
            "message": f"第二轮观点碰撞 · {role.display_name}：正在调用模型…",
        }
        peer_bits = "\n".join(
            f"- **{r.display_name}**（摘录）：{_excerpt(round1[r.key], 420)}"
            for r in ROLES
            if r.key != role.key
        )
        user_msg = USER_ROUND2_TEMPLATE.format(
            topic=topic,
            other_summaries=digest + "\n\n**他角色第一轮摘录（供点名反驳）**：\n" + peer_bits,
            self_previous=_excerpt(round1[role.key], 520),
        )
        out = _invoke(llm, role.system_prompt, user_msg, temperature=debate_temperature)
        round2[role.key] = out
        md_chunk = f"### 第二轮 · 观点碰撞 · {role.display_name}\n\n{out}\n"
        lines.append(md_chunk)
        yield {
            "event": "round2_end",
            "step": step,
            "total": TOTAL_STEPS,
            "role": role.display_name,
            "content": out,
            "markdown_section": md_chunk,
        }
        step += 1

    yield {
        "event": "synthesis_start",
        "step": step,
        "total": TOTAL_STEPS,
        "message": "终局综合：正在生成「最可能事实 / 可疑点 / 阴谋论辨析」…",
    }
    full_transcript = "\n".join(lines)
    final_user = USER_SYNTHESIZER_TEMPLATE.format(topic=topic, full_transcript=full_transcript)
    verdict = _invoke(llm, SYSTEM_SYNTHESIZER, final_user, temperature=synthesizer_temperature)
    tail = "---\n\n# 终局综合\n\n" + verdict
    lines.append("---\n")
    lines.append("# 终局综合\n")
    lines.append(verdict)
    full_md = "\n".join(lines)

    yield {
        "event": "synthesis_end",
        "step": step,
        "total": TOTAL_STEPS,
        "content": verdict,
        "markdown_section": tail,
    }
    step += 1

    yield {
        "event": "complete",
        "step": step,
        "total": TOTAL_STEPS,
        "markdown": full_md,
        "message": "全部完成",
    }


def run_historical_debate(
    topic: str,
    *,
    llm: HelloAgentsLLM | None = None,
    use_evidence_bundle: bool = True,
    debate_temperature: float = 0.72,
    synthesizer_temperature: float = 0.22,
    llm_api_key: str | None = None,
    llm_base_url: str | None = None,
    llm_model: str | None = None,
    llm_max_tokens: int | None = 4096,
    llm_timeout: int | None = None,
) -> str:
    """执行两轮角色辩论 + 终局综合报告（无流式，供 CLI 等）。"""
    last: dict[str, Any] | None = None
    for ev in iter_debate_events(
        topic,
        llm=llm,
        use_evidence_bundle=use_evidence_bundle,
        debate_temperature=debate_temperature,
        synthesizer_temperature=synthesizer_temperature,
        llm_api_key=llm_api_key,
        llm_base_url=llm_base_url,
        llm_model=llm_model,
        llm_max_tokens=llm_max_tokens,
        llm_timeout=llm_timeout,
    ):
        last = ev
    if not last or last.get("event") != "complete":
        raise RuntimeError("辩论未正常结束")
    md = last.get("markdown")
    if not isinstance(md, str):
        raise RuntimeError("缺少完整 Markdown")
    return md


def debate_event_json(ev: dict[str, Any]) -> str:
    """序列化单条事件（SSE data 行）。"""
    return json.dumps(ev, ensure_ascii=False)
