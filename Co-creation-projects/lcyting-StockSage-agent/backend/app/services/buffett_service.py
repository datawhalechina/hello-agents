"""
智能股票分析助手 — 巴菲特投资评估服务层

加载巴菲特投资思维参考文件，构建价值投资评估框架，
供API路由层和智能体层调用。
"""

import sys
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

# 确保skills路径可导入
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # backend/app/services -> project root
_AGENTS_DIR = _PROJECT_ROOT / "agents"
_BUFFETT_DIR = _PROJECT_ROOT / "skills" / "巴菲特投资思维" / "skills" / "buffett"

for p in [_AGENTS_DIR, str(_PROJECT_ROOT)]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agents.text_truncation import truncate_at_natural_boundary
from app.config import settings


# ====================================================================
# 巴菲特投资思维核心内容（从参考文件中提取的摘要）
# ====================================================================

BUFFETT_FRAMEWORK = {
    "quick_filter": {
        "name": "8问快速筛选",
        "questions": [
            "能力圈：能否用一段话解释这家公司如何赚钱？",
            "持久性：10年后这家公司是否还会存在且更具竞争力？",
            "护城河：竞争对手能否通过努力复制其核心优势？",
            "定价权：能否提价5-10%而不丢失大量客户？",
            "盈利质量：利润是否真正转化为现金（而非会计技巧）？",
            "债务安全：在行业最差情况下（营收-30%）能否存活？",
            "管理层诚信：管理层是否诚实面对问题而非掩盖？",
            "合理价格：当前价格与内在价值的差距是否足够大？",
        ],
        "rule": "2个\"否\"需要强有力理由；4个\"否\"直接放弃",
    },
    "moat_analysis": {
        "name": "护城河分析",
        "types": [
            "成本优势（成本领先，规模经济）",
            "转换成本（客户迁移成本高）",
            "网络效应（用户越多价值越大）",
            "无形资产（品牌、专利、特许经营权）",
            "高效规模（天然垄断，小市场大份额）",
        ],
        "judgment": "不仅看当前状态，更关键的是趋势（拓宽/稳定/变窄）",
    },
    "management_assessment": {
        "name": "管理层评估三维度",
        "dimensions": [
            "诚信度（自动否决项：发现不诚信直接放弃）",
            "资本配置能力（能否明智分配资本：再投资/收购/回购/分红）",
            "所有者心态（是否像主人一样思考，不乱花股东的钱）",
        ],
        "warning": "警惕制度迫力——优秀的管理层在制度压力下也可能做出不合理决策",
    },
    "financial_metrics": {
        "name": "财务指标",
        "metrics": [
            "所有者收益 = 净利润 + 折旧摊销 - 维护性资本支出 - 营运资金增加",
            "ROIC 10年平均目标 >15%",
            "现金转化率目标 >90%",
            "透视盈余（考虑被投资公司未分配利润）",
        ],
    },
    "valuation": {
        "name": "估值与安全边际",
        "methods": [
            "现金流折现法（DCF）",
            "盈利倍数法（合理PE区间）",
            "资产价值法（净资产重估）",
        ],
        "margin_of_safety": {
            "高确定性（宽护城河+可预测增长）": "20-30%",
            "一般优秀": "30-40%",
            "存在不确定因素": "40-50%",
            "无法可靠评估": "不投资",
        },
    },
    "risk_analysis": {
        "name": "风险分类",
        "categories": {
            "结构性风险": "护城河变窄、技术颠覆、监管打击",
            "财务风险": "过度杠杆、现金流造假、表外负债",
            "行为风险": "确认偏误、沉没成本、制度迫力",
        },
    },
    "sell_criteria": {
        "name": "卖出四条标准",
        "criteria": [
            "价格严重高估（远超内在价值）",
            "基本面护城河遭到破坏",
            "管理层出现诚信问题（立即卖出）",
            "发现显著更好的投资机会",
        ],
    },
}

# 综合评估框架说明
BUFFETT_FRAMEWORK_DESC = """
## 巴菲特价值投资评估框架

### 核心哲学
- **内在价值 > 市场价格 → 安全边际**：只购买价格明显低于内在价值的股票
- **护城河 > 一切**：持久的竞争优势是长期回报的根基
- **能力圈原则**：只投资自己能理解的业务
- **市场先生**：市场是为你服务的，不是指导你的
- **长期持有**：以10年的视角思考，而非下一季度的股价

### 评估流程
1. **快速筛选** — 8问检查（2分钟内完成）
2. **企业质量** — 护城河类型+趋势、管理层评估
3. **财务快照** — ROIC、现金转化率、所有者收益
4. **估值分析** — 内在价值区间、安全边际计算
5. **风险评估** — 结构性/财务/行为三类风险
6. **综合判断** — 买入/不买/持有/卖出 + 建议买入价
"""


def _mx_cell_to_str(v: Any) -> str:
    """妙想表格单元格转为可 JSON 序列化的字符串。"""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        if v != v:  # NaN
            return ""
    if isinstance(v, (str, int, float)):
        return str(v)
    return str(v)


def _first_table_row_key_values(block: Optional[dict], max_keys: int = 48) -> dict:
    """取 mx_data 风格结果中首张表首行，扁平为字符串字典（减小体积、避免不可序列化对象）。"""
    if not isinstance(block, dict) or not block.get("success"):
        return {"success": False, "fields": {}}
    tables = block.get("tables") or []
    fields: dict[str, str] = {}
    for t in tables[:1]:
        names: List[str] = list(t.get("fieldnames") or t.get("fieldNames") or [])
        rows = t.get("rows") or []
        if not rows:
            continue
        row = rows[0]
        if isinstance(row, dict):
            for k, v in list(row.items())[:max_keys]:
                fields[str(k)] = _mx_cell_to_str(v)
        elif isinstance(row, list) and names:
            for i, name in enumerate(names):
                if i >= max_keys:
                    break
                val = row[i] if i < len(row) else None
                fields[str(name)] = _mx_cell_to_str(val)
        break
    return {"success": True, "fields": fields}


def slim_evaluation_context_for_api(full: dict) -> dict:
    """HTTP 响应用：去掉巨型 tables，保留框架与行情/财务摘要。"""
    if not isinstance(full, dict):
        return {}
    return {
        "framework": full.get("framework"),
        "framework_description": full.get("framework_description"),
        "market_snapshot": _first_table_row_key_values(full.get("market_data")),
        "financial_snapshot": _first_table_row_key_values(full.get("financial_data")),
    }


def get_buffett_framework() -> dict:
    """获取巴菲特投资评估框架

    返回完整的巴菲特投资思维体系结构，包括：
    - 快速筛选清单
    - 护城河分析框架
    - 管理层评估维度
    - 财务指标模板
    - 估值与安全边际计算
    - 风险评估分类
    - 卖出标准

    Returns:
        {
            "success": True,
            "framework": {...},  # 完整的评估框架
            "description": str,  # 框架说明
        }
    """
    return {
        "success": True,
        "framework": BUFFETT_FRAMEWORK,
        "description": BUFFETT_FRAMEWORK_DESC,
    }


def evaluate_with_buffett(stock_code: str, stock_name: str = "", data_context: dict = None) -> dict:
    """使用巴菲特投资思维评估股票

    收集分析数据并构建巴菲特框架评估上下文，返回评估所需的数据包。

    Args:
        stock_code: 6位股票代码
        stock_name: 股票名称
        data_context: 已有的分析数据（可选），包含行情/财务/概况/舆情信息

    Returns:
        {
            "success": True/False,
            "stock_code": str,
            "stock_name": str,
            "evaluation_context": {
                "framework": dict,     # 巴菲特评估框架
                "market_data": dict,   # 行情数据
                "financial_data": dict,# 财务数据
                "profile_data": dict,  # 公司概况
                "sentiment_data": dict,# 舆情数据
            },
            "report_template": str,    # 评估报告模板
            "error": str or None
        }
    """
    result = {
        "success": False,
        "stock_code": stock_code,
        "stock_name": stock_name,
        "evaluation_context": {},
        "report_template": "",
        "error": None,
    }

    data_context = data_context or {}

    # 构建评估上下文
    context = {
        "framework": BUFFETT_FRAMEWORK,
        "framework_description": BUFFETT_FRAMEWORK_DESC,
        "market_data": data_context.get("market", {}),
        "financial_data": data_context.get("financial", {}),
        "profile_data": data_context.get("profile", {}),
        "sentiment_data": data_context.get("sentiment", {}),
    }

    result["success"] = True
    result["evaluation_context"] = context
    result["report_template"] = _build_buffett_report_template(stock_code, stock_name)

    return result


def _build_buffett_report_template(stock_code: str, stock_name: str) -> str:
    """生成巴菲特风格评估报告模板

    Args:
        stock_code: 6位股票代码
        stock_name: 股票名称

    Returns:
        Markdown格式的报告模板
    """
    name_display = stock_name or stock_code

    template = f"""
# 巴菲特价值投资评估报告

## 标的: {name_display} ({stock_code})

---

## 一、结论

[买入 / 不买 / 持续观察 / 持有 / 卖出] — 一句话核心理由

---

## 二、能力圈判断

[明确判断：在圈内 / 圈外 / 边界区域]
若在圈外：停止分析并诚实说明原因。

---

## 三、关键假设（3-5条）

[列出决策所依赖的核心假设，供日后验证]
1.
2.
3.
4.
5.

---

## 四、快速筛选（8问检查）

| # | 维度 | 结果 | 说明 |
|---|------|------|------|
| 1 | 能力圈 | [是/否] | |
| 2 | 持久性 | [是/否] | |
| 3 | 护城河 | [是/否] | |
| 4 | 定价权 | [是/否] | |
| 5 | 盈利质量 | [是/否] | |
| 6 | 债务安全 | [是/否] | |
| 7 | 管理层诚信 | [是/否] | |
| 8 | 合理价格 | [是/否] | |

---

## 五、企业质量分析

### 护城河
- **类型**: [成本优势/转换成本/网络效应/无形资产/高效规模]
- **强度**: [强/中/弱]
- **趋势**: [拓宽/稳定/变窄]

### 管理层
- **诚信度**: [评估]
- **资本配置能力**: [评估]
- **所有者心态**: [评估]

### 商业模式
- **类型**: [特许经营权型/商品型/混合型]

### 制度迫力预警
- [有/无] — [依据]

---

## 六、财务快照

| 指标 | 数值 | 评估 |
|------|------|------|
| ROIC (10年均值) | — | |
| 现金转化率 | — | |
| 债务安全性 | — | |
| 所有者收益估算 | — | |

---

## 七、估值分析

- **内在价值区间**: —
- **当前安全边际**: —% （确定性水平：高/中/低）
- **建议买入价**: —

---

## 八、卖出标准逐条检验

| # | 标准 | 判断 | 依据 |
|---|------|------|------|
| 1 | 价格严重高估？ | [是/否] | |
| 2 | 基本面护城河破坏？ | [是/否] | |
| 3 | 管理层诚信问题？ | [是/否] | |
| 4 | 有更好的机会？ | [是/否] | |

---

## 九、主要风险（最多3条）

1. **风险一**: [描述]
2. **风险二**: [描述]
3. **风险三**: [描述]

---

## 十、监控指标

### 每季度检查:
- [指标1]
- [指标2]

### 触发卖出信号:
- [信号1]
- [信号2]

---

## 十一、综合判断

[以巴菲特的视角和语气，直接给出决策建议和核心理由]

---

> ⚠️ 以上分析基于巴菲特价值投资理念框架，仅供参考，不构成投资建议。投资有风险，入市需谨慎。
"""
    return template


def _truncate_text(s: str, max_len: int) -> str:
    if not s:
        return ""
    if len(s) <= max_len:
        return s
    return truncate_at_natural_boundary(s, max_len, "\n\n…（内容过长已截断）")


def _ensure_hello_agents_path() -> None:
    _hello = _PROJECT_ROOT / "HelloAgents Optimized"
    if str(_hello) not in sys.path:
        sys.path.insert(0, str(_hello))


def make_buffett_llm_client():
    """构造用于巴菲特长文生成的 LLM 客户端（流式/非流式共用）。"""
    _ensure_hello_agents_path()
    from hello_agents.core.llm import HelloAgentsLLM

    buffett_llm_timeout = max(int(settings.LLM_TIMEOUT), 180)
    return HelloAgentsLLM(
        model=settings.LLM_MODEL_ID,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL or None,
        provider=os.getenv("LLM_PROVIDER", "auto"),
        temperature=0.35,
        max_tokens=6144,
        timeout=buffett_llm_timeout,
    )


def prepare_buffett_ai_messages(stock_code: str, stock_name: str = "") -> Dict[str, Any]:
    """聚合行情/财务/舆情并组装 LLM messages。

    Returns:
        成功: {"ok": True, "messages": [...], "name": str}
        失败: {"ok": False, "error": str}
    """
    if not settings.is_agent_ready():
        return {
            "ok": False,
            "error": "未配置有效的 LLM_API_KEY，无法一键生成 AI 评估报告",
        }

    code = (stock_code or "").strip()
    if len(code) < 4:
        return {"ok": False, "error": "请输入有效的股票代码"}

    try:
        from app.services.market_service import (
            get_stock_financial,
            get_stock_profile,
            get_stock_quote,
        )
        from app.services.news_service import analyze_sentiment
        from app.services.analysis_service import _extract_stock_name, _format_data_section

        quote_data = get_stock_quote(code)
        financial_data = get_stock_financial(code)
        profile_data = get_stock_profile(code)
        sentiment_data = analyze_sentiment(code)

        name = (stock_name or "").strip() or _extract_stock_name(profile_data) or code

        chunks = []
        if quote_data.get("success"):
            chunks.append("### 行情\n" + _format_data_section(quote_data))
        else:
            chunks.append(
                "### 行情\n获取失败: " + str(quote_data.get("error") or "未知错误")
            )

        if financial_data.get("success"):
            chunks.append("\n### 财务\n" + _format_data_section(financial_data))
        else:
            chunks.append(
                "\n### 财务\n获取失败: " + str(financial_data.get("error") or "未知错误")
            )

        if profile_data.get("success"):
            chunks.append("\n### 公司概况\n" + _format_data_section(profile_data))
        else:
            chunks.append(
                "\n### 公司概况\n获取失败: " + str(profile_data.get("error") or "未知错误")
            )

        if sentiment_data.get("success"):
            news_items = sentiment_data.get("news_items") or []
            report_items = sentiment_data.get("report_items") or []
            ann_items = sentiment_data.get("announce_items") or []
            chunks.append(
                f"\n### 舆情摘要\n新闻 {len(news_items)} / 研报 {len(report_items)} / 公告 {len(ann_items)}"
            )
            merged = (news_items + report_items + ann_items)[:12]
            for item in merged:
                title = item.get("title") or ""
                date = (item.get("date") or "").split()[0] if item.get("date") else ""
                chunks.append(f"- [{date}] {title}")
        else:
            chunks.append(
                "\n### 舆情\n获取失败: " + str(sentiment_data.get("error") or "未知错误")
            )

        data_bundle = _truncate_text("\n".join(chunks), 14000)
        framework_desc = _truncate_text(BUFFETT_FRAMEWORK_DESC.strip(), 5000)
        outline = _build_buffett_report_template(code, name)

        user_prompt = f"""请撰写完整的《巴菲特价值投资评估报告》（Markdown）。

标的：**{name}**（股票代码 {code}）

【须覆盖的报告结构与要点】
以下提纲中的章节结构与顺序必须体现在你的输出中（使用 ## / ### 标题）；每个章节需要实质性段落或列表，禁止只输出标题或空白占位。

{outline}

【价值投资框架参考】（按需引用，勿全文照搬）
{framework_desc}

【客观数据】（结论必须以此为依据，勿编造数据中不存在的精确数值）
{data_bundle}

写作要求：
1. 「结论」「综合判断」中必须明确：**买入 / 不买 / 持续观察 / 持有 / 卖出** 之一，并附简短理由。
2. 「快速筛选」按 8 个维度逐条给出判断与简要依据。
3. 估值与安全边际：若数据不足以定量，请定性说明并列出需补充的信息，勿捏造 PE/PB。
4. 文末单独一行：⚠️ 以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。
"""

        system = (
            "你是资深证券投资分析师，精通巴菲特与格雷厄姆的价值投资框架。"
            "你只输出 Markdown 正文，语气专业、审慎。"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ]
        return {"ok": True, "messages": messages, "name": name}

    except Exception as e:
        return {"ok": False, "error": str(e)}


def iter_buffett_ai_report_events(stock_code: str, stock_name: str = "") -> Iterator[Dict[str, Any]]:
    """供 NDJSON 流式响应：通过巴菲特评估Agent (ReflectionAgent) 生成报告。"""
    prep = prepare_buffett_ai_messages(stock_code, stock_name)
    if not prep.get("ok"):
        yield {"type": "error", "message": prep.get("error") or "准备失败"}
        return

    code = (stock_code or "").strip()
    name = prep.get("name") or code
    yield {"type": "meta", "stock_code": code, "stock_name": name}

    try:
        from agents.advisor_agent import evaluate_buffett_stream

        for event in evaluate_buffett_stream(
            stock_code=code,
            stock_name=name,
        ):
            yield event

        yield {"type": "done"}
    except Exception as e:
        yield {"type": "error", "message": str(e)}


def generate_buffett_ai_report(stock_code: str, stock_name: str = "") -> dict:
    """调用 LLM 生成填充后的巴菲特风格 Markdown 报告（同步阻塞，请在 asyncio.to_thread 中调用）。

    Returns:
        {"success": bool, "report_markdown": str | None, "error": str | None}
    """
    result: dict = {"success": False, "report_markdown": None, "error": None}

    prep = prepare_buffett_ai_messages(stock_code, stock_name)
    if not prep.get("ok"):
        result["error"] = prep.get("error") or "准备失败"
        return result

    try:
        llm = make_buffett_llm_client()
        md = llm.invoke(
            prep["messages"],
            max_tokens=6144,
            temperature=0.35,
        )
        md = (md or "").strip()
        if not md:
            result["error"] = "LLM 返回为空，请稍后重试"
            return result

        result["success"] = True
        result["report_markdown"] = md
        return result

    except Exception as e:
        result["error"] = str(e)
        return result


def load_buffett_reference(ref_name: str) -> Optional[str]:
    """加载指定的巴菲特参考文件内容

    Args:
        ref_name: 参考文件名，如 "03-business-moat"

    Returns:
        文件内容文本，若文件不存在返回 None
    """
    safe_name = ref_name.replace("..", "").replace("\\", "").replace("/", "")
    ref_path = _BUFFETT_DIR / "references" / f"{safe_name}.md"

    if not ref_path.exists():
        return None

    try:
        with open(ref_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None
