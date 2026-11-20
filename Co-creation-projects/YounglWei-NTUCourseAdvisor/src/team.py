"""D3 三 Agent 协作：Planner → Retrieval → Reviewer（Reflection ≤3 轮）。

框架协作机制核实结论（hello-agents 1.0.1 源码，2026-10-23）：
- 框架没有 AgentTeam 类；真实多 Agent 协作 = Python 编排层组合多个 Agent 实例，
  通过拼 prompt 传递上下文（PlanSolveAgent 的 step_prompt / ReflectionAgent 的
  reflection prompt 即此模式）。本模块采用同一模式，不自造框架不存在的 API。
- Agent 间无消息总线：Planner 计划、Retrieval 结果、Reviewer 意见均由编排层
  显式拼进下一阶段的 prompt，全程可溯源、可测试。

三 Agent 分工（02-提示词设计.md 毛坯迭代为正稿）：
- Planner：身份理解（LLM 结合用户原话 + 完整对话历史 + 库覆盖事实输出
  assumed_identity）+ 计划生成（function calling，实现模式对齐框架 Planner 类）
- Retrieval：ReActAgent 按计划执行 rag_search + 4 个校验工具，产出草稿
  （只重组工具返回，三板斧继承 D2 v12）
- Reviewer：SimpleAgent 四项审查（来源覆盖/查不到明说/学位规则校验引用/
  身份一致性），PASS 放行 / FAIL 打回（引用草稿原句），≤3 轮

确定性护栏（D2 教训"代码管必须"）：
- 身份理解由 Planner 输出，代码只做过滤（层次未知反问 / 库外项目 grounding /
  单课属性查询忽略身份），不替模型判定身份
- "推荐类检索步需要 level 但身份未确认" → 编排层拦截反问，不靠模型自觉
- ExactCodeGuard / CourseRAGTool.level 过滤（D2 已落地）继续生效
"""

import json

from hello_agents.agents import ReActAgent, SimpleAgent
from hello_agents.core.config import Config
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.retrieval import HybridSearch, RAGStore
from hello_agents.tools import ToolRegistry

from src.agent import CourseRAGTool, ExactCodeGuard
from src.config import (DATA_DIR, EMBEDDING_MODEL, RAG_DB_PATH,
                        ZHIPU_API_KEY, ZHIPU_BASE_URL, ZHIPU_MODEL)
from src.guards import (_CODE_RE, _RECOMMEND_WORDS, _clean_answer,
                        _has_synthesis, _identity_ask,
                        _only_empty_field_complaint, _programme_known,
                        _sanitize_sources, _scope_notice, mechanical_review)
from src.identity import (IdentityResult, claimed_programme, explicit_level,
                          programme_code, programme_mentioned)
from src.prompts import (PLANNER_PROMPT, PLAN_TOOL_SCHEMA, RETRIEVAL_PROMPT,
                         REVIEWER_PROMPT)
from src.vector_store import VectorSearchBackend, make_zhipu_provider
from src.validators import DegreeAuditTool, _cards

# 拆分说明（2026-10-25）：提示词与 plan schema 在 prompts.py，
# 机械审查/来源验真/字段核对/覆盖文案在 guards.py；本文件负责计划生成与编排。

# ---------------------------------------------------------------------------
# 计划生成（实现模式对齐框架 agents/plan_solve_agent.py 的 Planner 类：
# function calling 强制结构化输出 → 解析校验）
# ---------------------------------------------------------------------------

def _coverage_facts() -> str:
    """课程库覆盖事实（注入 Planner，避免模型凭记忆猜项目归属）。"""
    cards = _cards()
    ug = sum(1 for c in cards.values() if c.get("level") == "undergraduate")
    grad: dict[str, int] = {}
    for c in cards.values():
        if c.get("level") == "graduate":
            key = c.get("programme") or "未标注项目"
            grad[key] = grad.get(key, 0) + 1
    lines = [f"- 本科课程：{ug} 门，仅覆盖 CCDS（计算机与数据科学学院）"
             f"的 5 个专业：CSC 计算机科学 / CE 计算机工程 / DSAI 数据科学与人工智能 / "
             f"AISC 人工智能与社会 / COMP 计算；**其他学院（工程、商科、人文等）未收录**"]
    for name, n in sorted(grad.items()):
        lines.append(f"- 研究生课程：{name}，{n} 门")
    return "\n".join(lines)


def generate_plan(llm: HelloAgentsLLM, question: str,
                  history_text: str = "") -> tuple[list[dict], dict]:
    """Planner：LLM 从原话 + 历史 + 库覆盖事实生成计划与身份理解。

    出路 1（2026-10-24）：不再由代码替模型判断身份——代码只提供事实
    （库里有什么），身份理解与项目归属由模型在 assumed_identity 里说明；
    代码后续只做"需要身份但不确定 → 反问"这一道过滤。
    """
    messages = [
        {"role": "system", "content": PLANNER_PROMPT},
        {"role": "user",
         "content": f"课程库实际覆盖：\n{_coverage_facts()}\n\n"
                    f"对话历史（最近几轮，供理解上下文）：\n{history_text or '（无）'}\n\n"
                    f"用户本轮原话：{question}\n"
                    f"请调用 generate_plan 工具提交 steps 与 assumed_identity。"},
    ]
    response = llm.invoke_with_tools(
        messages=messages, tools=[PLAN_TOOL_SCHEMA], tool_choice="auto")
    if len(response.tool_calls or []) != 1 or \
            response.tool_calls[0].name != "generate_plan":
        raise ValueError("模型未返回 generate_plan 请求")
    args = json.loads(response.tool_calls[0].arguments)
    steps = args.get("steps") if isinstance(args, dict) else None
    if not isinstance(steps, list) or not steps or any(
            not isinstance(s, dict) or not isinstance(s.get("action"), str)
            for s in steps):
        raise ValueError("计划必须是非空步骤列表")
    assumed = args.get("assumed_identity") or {}
    if not isinstance(assumed, dict):
        assumed = {}
    return _augment_steps(question, _sanitize_steps(steps)), assumed


def _sanitize_steps(steps: list[dict]) -> list[dict]:
    """代码层计划清洗（提示词规则模型遵守不稳定，D2 教训：确定性规则下沉代码）。

    规则：query 含具体课程码的 search 步，level 强制置空——点名查课 = 属性查询，
    应按卡片 Level 字段如实回答（如"SC4000 是本科课"），level 过滤会把
    不符身份的课卡滤掉导致"未查到"式假阴性（D2 基线 8 回归中实证的退化）。
    ExactCodeGuard 保证课码精确命中，置空 level 无幻觉风险。
    """
    for s in steps:
        if (s.get("action") == "search" and s.get("query")
                and _CODE_RE.search(s["query"])):
            if s.get("level"):
                s["level"] = ""
    return steps


def _augment_steps(question: str, steps: list[dict]) -> list[dict]:
    """代码层计划补全：用户点名的课码若未被任何 search/audit 步覆盖，
    自动前置一步无 level 过滤的课码检索。

    动机（基线 8 回归实证）：Planner 可能把"SC4000 是研究生课吗"的 query
    写成不含课码的"is it a graduate course"，且误标 level 过滤，导致
    该课被滤成"未查到"假阴性。代码层兜底确保点名的课必被检索。
    """
    q_codes = list(dict.fromkeys(_CODE_RE.findall(question)))
    if not q_codes:
        return steps
    covered = set()
    for s in steps:
        if s.get("action") == "search":
            covered.update(_CODE_RE.findall(s.get("query", "")))
        elif s.get("action") == "audit":
            covered.update(_CODE_RE.findall(" ".join(s.get("course_codes") or [])))
    missing = [c for c in q_codes if c not in covered]
    if missing and any(s.get("action") == "search" for s in steps):
        return [{"action": "search", "query": " ".join(missing), "level": "",
                 "note": "代码层补全：用户点名的课程码检索（不过滤）"}] + steps
    return steps


# ---------------------------------------------------------------------------
# 三 Agent 编排
# ---------------------------------------------------------------------------

class CourseAdvisorTeam:
    """三 Agent 协作入口（编排层组合，框架 PlanSolve/Reflection 同款模式）。

    会话状态：identity（身份缓存，跨问题保持）；pending（身份反问挂起的问题）。
    """

    def __init__(self, max_review_rounds: int = 3, retrieval_max_steps: int = 8,
                 verbose: bool = True):
        self.verbose = verbose
        self.max_review_rounds = max_review_rounds
        # 会话状态（出路 1：用对话历史承载上下文，不再用挂起态字段）
        self.identity: IdentityResult | None = None
        self.assumed_identity: dict = {}
        self.history: list[dict] = []

        # LLM（三 Agent 共享同一模型实例）
        self.llm = HelloAgentsLLM(
            model=ZHIPU_MODEL, api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL,
            temperature=0.2)

        # 检索栈（同 D2 build_agent）
        store = RAGStore(str(RAG_DB_PATH))
        provider = make_zhipu_provider(EMBEDDING_MODEL, ZHIPU_API_KEY, ZHIPU_BASE_URL)
        vector_backend = VectorSearchBackend(
            store, provider, cache_path=DATA_DIR / f"vector_index_{EMBEDDING_MODEL}.json")
        hybrid = ExactCodeGuard(HybridSearch([store, vector_backend]))

        # Retrieval Agent：ReActAgent + RAG 工具 + 校验工具
        # D4.2：免费档 glm-4-flash 偶发长响应，Q06 两次触发框架默认 120s
        # 单次 LLM 时限；提高到 240s，避免内容正确的回答被基础设施时限截断。
        agent_config = Config(llm_async_timeout=240, tool_async_timeout=60)
        registry = ToolRegistry()
        registry.register_tool(CourseRAGTool(store, search_backend=hybrid))
        registry.register_tool(DegreeAuditTool())
        self.retrieval = ReActAgent(
            name="retrieval", llm=self.llm, tool_registry=registry,
            system_prompt=RETRIEVAL_PROMPT, max_steps=retrieval_max_steps,
            config=agent_config)

        # Reviewer Agent：无业务工具，纯 LLM 审查
        self.reviewer = SimpleAgent(
            name="reviewer", llm=self.llm, system_prompt=REVIEWER_PROMPT,
            config=agent_config)

    # ---------------- 生命周期 ----------------

    def reset(self):
        """清空会话状态（新会话用）。"""
        self.identity = None
        self.assumed_identity = {}
        self.history.clear()
        self._clear_agent_history()

    def _clear_agent_history(self):
        """清空 Retrieval/Reviewer 的内部历史。

        跨轮上下文由 self.history 显式拼进 prompt；内部 history_manager 若跨轮
        累积，会把上一轮的工具调用/审查意见重复带进本轮，造成上下文膨胀。
        """
        self.retrieval.history_manager.clear()
        self.reviewer.history_manager.clear()

    def _log(self, tag: str, msg: str):
        if self.verbose:
            print(f"  [{tag}] {msg}")

    # ---------------- 主流程 ----------------

    def run(self, user_input: str) -> str:
        """处理一条用户输入：完整对话历史 + 原话透传给 Planner，代码不改写身份。

        出路 1（2026-10-24）：取消挂起态窄解析、身份声明改写、计划补 level 等
        改写型护栏——它们把用户已表达的信息截断（"我是CS本科"只留下"本科"）。
        身份由模型结合原话与库覆盖事理解读，代码只做"检索需要身份但模型不确定
        → 反问"这一道过滤。
        """
        self._clear_agent_history()
        history_text = self._history_text()
        try:
            steps, assumed = generate_plan(self.llm, user_input, history_text)
        except Exception as exc:
            self._log("Planner", f"计划生成失败（{type(exc).__name__}: {exc}），"
                                  f"退化为直接检索")
            steps, assumed = [{"action": "search", "query": user_input, "level": ""}], {}

        level = (assumed.get("level") or "").strip()
        programme = (assumed.get("programme") or "").strip()
        confidence = (assumed.get("confidence") or "none").strip()
        has_code = bool(_CODE_RE.search(user_input))
        has_audit = any(s.get("action") == "audit" for s in steps)

        # 事后校验①：模型把库外项目说成"确定身份"属臆断（实测把 SPML 判成
        # "本科生 certain"）。若用户原话也没明说层次 → **层次一并清空**
        # （模型猜的层次不采信），让下方护栏走反问。
        if programme and not _programme_known(programme) \
                and not explicit_level(user_input):
            confidence = "uncertain"
            level = ""

        # 事后校验①b（D4 Q14）：模型可能把库外专业自行映射成库内项目
        # （实测“机械工程专业”→ programme=CCA, certain）。代码只做 grounding
        # 过滤：模型说的项目必须能在用户原话（当前轮有新声明时只看当前轮，
        # 否则允许历史）里找到证据；找不到就视为臆断，转覆盖说明/反问。
        if programme and _programme_known(programme):
            claimed_now = claimed_programme(user_input)
            probe = claimed_now or (user_input + "\n" + history_text)
            if not programme_mentioned(probe, programme):
                if claimed_now and not _programme_known(claimed_now):
                    programme = claimed_now  # 用用户原话进入覆盖说明
                else:
                    programme = ""
                confidence = "uncertain"
                if not explicit_level(user_input):
                    level = ""
                self._log("Planner", f"身份 grounding 失败：模型项目不在用户原话里，"
                                      f"转 programme={programme or '-'}")

        # 事后校验②：**单课属性查询**（无 audit 步）不需要身份。忽略模型的项目
        # 理解，避免把课码前缀当项目（实测 "EE6407 几 AU" 被解读成"本科生 · EE"）。
        # D4 Q10 修正：audit/推荐类即使含课码也要保留身份（专选/AU 校验需要 CCA）。
        if has_code and not has_audit:
            level, programme, confidence = "", "", "none"

        self.assumed_identity = {"level": level, "programme": programme,
                                 "confidence": confidence}
        # 仅在模型自认确定（且通过校验）时构造身份对象，供 Reviewer 身份一致性审查
        self.identity = (IdentityResult(status="confirmed", level=level,
                                        programme=programme or None)
                         if confidence == "certain" and level else None)

        self._log("Planner", "计划：" + " | ".join(
            f"{s['action']}:{s.get('query') or s.get('audit_kind') or ''}"
            f"{('/' + s['level']) if s.get('level') else ''}" for s in steps))
        self._log("Planner", f"身份理解：level={level or '-'} "
                             f"programme={programme or '-'} confidence={confidence}")

        # 唯一代码护栏（过滤，非改写）：需要身份但连层次都不知道 → 反问。
        # 已知层次（哪怕项目不在库内）就放行检索——项目缺失由模型在回答里说明，
        # 避免"我是CS本科"这种表述被反问打断（信息不丢，只做必要澄清）。
        # 不再用挂起态字段：反问文本进对话历史，用户下一句回答时 Planner 看得到。
        is_list = (not has_code
                   and any(w in user_input.lower() for w in _RECOMMEND_WORDS))
        needs_identity = (
            any(s.get("action") == "search" and s.get("level") for s in steps)
            or is_list)
        if needs_identity and not level and confidence != "certain":
            answer = _identity_ask(programme)
            self._remember(user_input, answer)
            self._log("Planner", "身份不确定且检索需要身份，反问用户")
            return answer

        # 方案 C 明确边界（2026-10-24 用户拍板）：用户明确提到一个库外专业时，
        # 直接说明覆盖范围，不检索——避免拿 CCDS 的课冒充"机械工程专业的课"。
        # 含课码的属性查询豁免（问单门课不需要专业归属）。
        if programme and not has_code and not _programme_known(programme):
            answer = _scope_notice(programme)
            self._remember(user_input, answer)
            self._log("Planner", f"库外专业「{programme}」→ 说明覆盖边界（不检索）")
            return answer

        # 专业过滤兜底：把模型已理解的项目名映射成标准代码，补进未标注的 search 步。
        # 这是**传递已理解的信息**给工具，不是改写用户表达（与已删除的"补 level"不同：
        # 那条是代码替模型决定过滤条件，这条是把 assumed_identity 落到检索参数）。
        p_code = programme_code(programme)
        if p_code and not has_code:
            for s in steps:
                if s.get("action") == "search" and not s.get("programme"):
                    s["programme"] = p_code
                    self._log("Planner", f"计划补 programme={p_code}（按已理解的专业过滤）")

        try:
            answer = self._identity_banner() + self._pipeline(
                user_input, steps, history_text)
        except Exception as exc:
            name = type(exc).__name__
            if "Timeout" in name:
                answer = ("本次响应超时（模型长时间未返回）。请重试，或把问题拆小一些："
                          "例如先问单门课程属性，再问选课组合。")
                self._log("Team", f"LLM 超时：{name}")
            else:
                answer = (f"本次处理失败（{name}）。请重试；若反复出现，"
                          f"请检查 API key/网络，或把问题拆小。")
                self._log("Team", f"处理异常：{name}: {exc}")
        self._remember(user_input, answer)
        return answer

    # ---------------- 对话历史（承载上下文，替代挂起态字段） ----------------

    def _history_text(self, limit: int = 6) -> str:
        if not self.history:
            return ""
        lines = []
        for turn in self.history[-limit:]:
            role = "用户" if turn["role"] == "user" else "助手"
            content = turn["content"]
            # 用户原话不截断（信息流红线）；只压缩助手长回答，避免上下文膨胀
            if role == "助手" and len(content) > 400:
                content = content[:400] + "…（截断）"
            lines.append(f"{role}：{content}")
        return "\n".join(lines)

    def _remember(self, user_input: str, answer: str):
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": answer})
        if len(self.history) > 12:
            self.history = self.history[-12:]

    # ---------------- 检索 + Reflection ----------------

    def _identity_banner(self) -> str:
        """身份回显：显示**模型自己理解到**的身份，便于用户立刻纠正。

        用户反馈"看不出匹配的是哪个项目"——身份理解原本只写进日志。
        这里不改写模型判断，只是把它已经做出的理解显式呈现。
        """
        a = self.assumed_identity or {}
        level = (a.get("level") or "").strip()
        programme = (a.get("programme") or "").strip()
        if not level and not programme:
            return ""
        lv = {"graduate": "研究生", "undergraduate": "本科生"}.get(level, "")
        who = " · ".join(x for x in (lv, programme) if x)
        if programme and not _programme_known(programme):
            who += "（库内未收录该项目）"
        return f"已理解身份：{who}（本次按此检索）\n\n"

    def _polish_draft(self, question: str, plan_text: str, draft: str) -> str:
        """单轮草稿精炼：溯源声明 + 组合逻辑总述结构。

        归因修正（2026-10-23 A/B 判别实验）：glm-4-flash 在干净单轮上下文 +
        聚焦任务下能产出高质量组合逻辑，但 ReAct 循环内同类指令不遵循
        ——是信息流设计压制（工具调用汇报模式 + 历史堆叠），非模型上限。
        本方法把实验 B 结构搬进编排层：初稿（唯一事实来源）→ 单轮成文，
        事实保真由 Reviewer 双轨审查兜底。

        三轮联调实证：整篇"重组/撰写"任务下 flash 把注意力全放在保真上，
        总述（创作部分）被稀释而不写——故 prompt 聚焦"总述是唯一要写的部分，
        其余照抄整理"；另加代码护栏：推荐类总述缺失时重试 1 次（代码管必须）。
        """
        def _invoke() -> str:
            resp = self.llm.invoke(messages=[
                {"role": "system", "content": RETRIEVAL_PROMPT},
                {"role": "user", "content":
                    f"用户问题：{question}\n执行计划：\n{plan_text}\n\n"
                    f"已核实的资料（你的唯一事实来源）：\n{draft}\n\n"
                    f"输出最终草稿，其中只有一段需要你写，其余全是整理：\n"
                    f"1. 第一句溯源声明（照写）：「（课程信息全部来自 NTU 官方课程库，"
                    f"未使用模型自身知识，来源见文末）」\n"
                    f"2. 【唯一需要你写的部分】组合逻辑总述段：为什么是这几门、怎么安排——"
                    f"各门定位与搭配（如\"EE6406 打机器学习基础，EE6407 以进化计算视角进阶，"
                    f"EE6497 补深度学习方向，三者互补不重叠\"；资料含类别时点明谁计入专选、"
                    f"谁算通选）。这是从资料推出的判断，不算新增事实。属性查询类问题跳过本段。\n"
                    f"3. 逐门课程要点：整理自资料，不改动事实\n"
                    f"4. 来源清单：保留资料全部来源\n"
                    f"不得引入资料没有的课程信息，不得丢失资料中的课程与来源。"}])
            return resp.content

        out = _invoke()
        # 代码护栏：推荐类问题总述缺失（概率性）→ 重试 1 次
        if (any(w in question.lower() for w in _RECOMMEND_WORDS)
                and not _has_synthesis(out)):
            self._log("Polish", "总述缺失，重试一次")
            out = _invoke()
        return out

    def _pipeline(self, question: str, steps: list[dict],
                  history_text: str = "") -> str:
        """Retrieval 产出草稿 → Reviewer 审查（≤max_review_rounds 轮）。"""
        # 问题原话直接透传（不改写）；对话历史一并交给 Retrieval，
        # 让"我是CS本科"这类上下文对检索阶段也可见。
        id_desc = f"level={self.identity.level}" if self.identity else "未确认"
        plan_text = self._format_steps(steps)

        # Retrieval：初稿
        draft = self.retrieval.run(
            f"对话历史：\n{history_text or '（无）'}\n\n"
            f"用户本轮原话：{question}\n身份理解：{id_desc}\n执行计划：\n{plan_text}\n"
            f"请按计划执行工具调用，然后输出面向用户的草稿答案（含来源清单）。")
        self._log("Retrieval", "草稿完成")

        # 初稿精炼：干净单轮重组（溯源声明 + 组合逻辑总述）。
        # A/B 判别实验结论：ReAct 循环内模型不遵循结构指令（信息流压制），
        # 同模型在干净单轮上下文下能写出组合逻辑——精炼放在循环外（设计说明见 _polish_draft）。
        # 事实保真由随后的 Reviewer 双轨审查兜底（polish 丢失课程/来源会被机械审查抓回）。
        # 校验类（计划含 audit 步）跳过：校验报告（规则引用+工具返回原文）是终态结构，
        # 推荐类 polish 模板会污染它（全量回归场景 11 实证：占位符字面量混入 +
        # 3 轮来源覆盖 FAIL 耗尽）。
        if not any(s.get("action") == "audit" for s in steps):
            draft = self._polish_draft(question, plan_text, draft)
            self._log("Retrieval", "草稿精炼完成（单轮重组）")

        # 来源兜底（D4 Q11/Q12）：模型会编造看似合理的域名，3 轮审查仍不改；
        # 放行前用代码把非白名单 URL 替换为对应课卡片的官方 source_url。
        draft = _sanitize_sources(draft)

        # Reviewer：Reflection 循环 ≤ N 轮（机械审查 + LLM 审查双轨，任一 FAIL 即 FAIL）
        id_desc = f"level={self.identity.level}" if self.identity else "未确认"
        for round_no in range(1, self.max_review_rounds + 1):
            draft = _sanitize_sources(draft)  # 修订轮可能重新编造 URL，每轮兜底
            mech_issues = mechanical_review(question, self.identity, draft, steps)
            review = self.reviewer.run(
                f"用户问题：{question}\n用户身份：{id_desc}\n待审草稿：\n{draft}")
            llm_pass = review.strip().upper().startswith("PASS")
            if (not llm_pass and not mech_issues
                    and _only_empty_field_complaint(review, draft)):
                self._log("Reviewer", "LLM 审查把“未列出”误判为缺失，"
                                      "机械审查无问题，代码按正确行为放行")
                llm_pass = True
            if not mech_issues and llm_pass:
                self._log("Reviewer", f"第 {round_no} 轮 PASS（机械+LLM 双通过），放行")
                return _sanitize_sources(_clean_answer(draft))
            combined = ""
            if mech_issues:
                combined += "【代码机械审查】\n" + "\n".join(
                    f"{i}. {issue}" for i, issue in enumerate(mech_issues, 1)) + "\n"
            if not llm_pass:
                combined += "【LLM 审查】\n" + review
            self._log("Reviewer", f"第 {round_no} 轮 FAIL"
                      f"（机械 {len(mech_issues)} 项 / LLM {'FAIL' if not llm_pass else 'PASS'}），打回修改")
            if round_no < self.max_review_rounds:
                draft = self.retrieval.run(
                    f"原执行计划：\n{plan_text}\n上一版草稿：\n{draft}\n\n"
                    f"审查意见（逐条落实：缺数据的先补工具检索再改写；"
                    f"机械审查问题优先修复）：\n{combined}\n\n"
                    f"直接输出修订后的完整草稿正文（末尾来源清单以'来源：'单行开头），"
                    f"不要任何引语或说明。")
                self._log("Retrieval", f"第 {round_no} 轮修订完成")
            else:
                review = combined
        # 轮次耗尽仍 FAIL：放行但如实标注（不静默放过，符合"查不到明说"哲学）
        self._log("Reviewer", "轮次耗尽，放行并附审查标注")
        final = (_clean_answer(draft) + "\n\n---\n[审查标注] 经 "
                 f"{self.max_review_rounds} 轮审查仍未完全通过，遗留问题：\n{review}")
        # 审查标注里可能带原始编造 URL，一并清理，确保最终回答不出现假来源
        return _sanitize_sources(final)

    @staticmethod
    def _format_steps(steps: list[dict]) -> str:
        lines = []
        for i, s in enumerate(steps, 1):
            if s.get("action") == "search":
                lv = f"，level={s['level']}" if s.get("level") else "（不过滤）"
                pg = f"，programme={s['programme']}" if s.get("programme") else ""
                lines.append(f"{i}. [检索] rag_search(query=\"{s.get('query', '')}\"{lv}{pg})")
            elif s.get("action") == "audit":
                codes = ", ".join(s.get("course_codes") or [])
                lines.append(f"{i}. [校验] {s.get('audit_kind')}({codes})")
            else:
                lines.append(f"{i}. [无需工具]")
        return "\n".join(lines)


if __name__ == "__main__":
    # 冒烟 1（无 LLM）：计划格式化 + 机械审查（坏草稿必须被抓）
    demo = [
        {"action": "search", "query": "machine learning", "level": "graduate"},
        {"action": "audit", "audit_kind": "au", "course_codes": ["EE6203", "EE6008"]},
        {"action": "none"},
    ]
    print("=== _format_steps 冒烟 ===")
    print(CourseAdvisorTeam._format_steps(demo))

    bad = ("EE6203 是 3 AU 的研究生课，讲计算机控制系统，没有先修要求，"
           "和 SC1003 不冲突。")
    good = ("EE6203 是 3 AU 的研究生课（MSc Computer Control & Automation 专选），"
            "内容包括离散时间系统建模与数字控制器设计。\n来源：\n"
            "- EE6203 COMPUTER CONTROL SYSTEMS — "
            "https://www.ntu.edu.sg/education/graduate-programme/"
            "master-of-science-in-computer-control-automation")
    print("\n=== 机械审查冒烟（无 LLM，确定性） ===")
    from src.identity import IdentityResult
    ident = IdentityResult("confirmed", level="graduate")
    rec_steps = [{"action": "search", "query": "x", "level": "graduate"}]
    for label, draft in [("坏草稿(无来源+虚构冲突结论+混本科课SC1003)", bad),
                         ("好草稿(带来源)", good)]:
        issues = mechanical_review("EE6203 是什么课？", ident, draft, rec_steps)
        print(f"[{label}] → {len(issues)} 项问题")
        for it in issues:
            print("  -", it)

    # 冒烟 2（LLM）：Reviewer LLM 审查（语义项 ②）行为观察
    print("\n=== Reviewer LLM 冒烟（需智谱 key） ===")
    team = CourseAdvisorTeam(verbose=True)
    ctx = "用户问题：EE6203 是什么课？\n用户身份：level=graduate\n待审草稿：\n{}"
    for label, draft in [("坏草稿", bad), ("好草稿", good)]:
        out = team.reviewer.run(ctx.format(draft))
        verdict = "PASS" if out.strip().upper().startswith("PASS") else "FAIL"
        print(f"\n[{label}] → LLM 判定 {verdict}\n{out[:300]}")
