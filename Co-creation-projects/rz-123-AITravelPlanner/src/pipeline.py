"""
流水线编排：需求解析 → 调研 → 规划 → 预算 → 校验（可返工一次）→ 报告。

为什么不用「自由对话」让智能体自己商量：
  顺序流水线的每一步输入输出都是显式的，出问题能定位到具体环节；
  校验环节用评分阈值决定是否返工，避免无限循环。
"""

from __future__ import annotations

import json                            # 解析模型返回的 JSON
import re                              # 从自然语言里兜底提取天数/人数/预算
from datetime import date, timedelta    # 生成行程日期（不写死固定日期）
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from .agents import build_agents        # 5 个智能体的工厂
from .tools import BudgetCalculatorTool, build_tools

# 校验分数低于该值就触发一次返工（最多一次，防止死循环）
REVIEW_PASS_SCORE = 7
# 支持的演示城市，用于需求解析失败时兜底
KNOWN_CITIES = ["杭州", "成都", "西安"]


def parse_json(text: Optional[str]) -> Dict[str, Any]:
    """从模型输出中提取 JSON；失败返回空字典，由调用方兜底"""
    if not text:
        return {}
    cleaned = text.strip()
    # 去掉模型可能加上的 ```json ... ``` 包裹
    cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError:
        # 常见问题：尾逗号。做一次最小修复后再试
        try:
            return json.loads(re.sub(r",\s*([}\]])", r"\1", cleaned[start:end + 1]))
        except json.JSONDecodeError:
            return {}


def _tool_json(tool: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """调用工具并把结果转成字典（兼容 ToolResponse 与纯字符串两种返回）"""
    resp = tool.run(params)
    text = getattr(resp, "text", resp)      # ToolResponse 取 text；纯字符串直接用
    return json.loads(text)


def fallback_requirement(user_input: str) -> Dict[str, Any]:
    """模型解析失败时的正则兜底，保证流水线还能继续跑"""
    def pick(pattern: str, default: int) -> int:
        match = re.search(pattern, user_input)
        return int(match.group(1)) if match else default

    # 城市优先取已知城市；否则从「拉萨 2 天」这类句式里截取，不强行改成杭州
    city_in_known = next((c for c in KNOWN_CITIES if c in user_input), None)
    city_match = re.search(r"([\u4e00-\u9fa5]{2,4}?)\s*\d+\s*天", user_input)
    city = city_in_known or (city_match.group(1) if city_match else "杭州")
    interests = [k for k in ["美食", "博物馆", "景点", "自然"] if k in user_input]

    return {
        "city": city,
        "days": pick(r"(\d+)\s*天", 3),
        "people": pick(r"(\d+)\s*人", 2),
        "budget": pick(r"预算\s*(\d+)", 3000),
        "interests": interests or ["景点"],
    }


def fallback_plan(req: Dict[str, Any], attractions: List[dict]) -> List[dict]:
    """规划失败时，把景点按顺序平均分配到每天"""
    days = max(int(req.get("days") or 3), 1)
    per_day = max(1, min(3, (len(attractions) + days - 1) // days))
    plan = []

    for i in range(days):
        chunk = attractions[i * per_day:(i + 1) * per_day]
        names = [a.get("name", "") for a in chunk]
        plan.append({
            "day": i + 1,
            "date": "",
            # 用列表拼接而非固定三个坑位，景点不足时不会出现空环节
            "morning": names[0] if names else "自由活动",
            "afternoon": names[1] if len(names) > 1 else "自由活动",
            "evening": names[2] if len(names) > 2 else "自由活动",
            "tips": "由兜底规则生成",
        })
    return plan


def fallback_budget(req: Dict[str, Any], attractions: List[dict]) -> Dict[str, Any]:
    """预算 Agent 失败时，直接调用同一个工具计算"""
    tool = BudgetCalculatorTool()
    tickets = sum(float(a.get("cost") or 0) for a in attractions) * int(req.get("people") or 1)
    return _tool_json(tool, {
        "days": req.get("days", 3),
        "people": req.get("people", 2),
        "transport": 500,
        "hotel_per_night": 400,
        "food_per_day": 150,
        "tickets": tickets,
    })


def _research(req: Dict[str, Any], fallback_tools: List[Any]) -> Dict[str, Any]:
    """工具直连调研：作为 Agent 调研失败时的兜底，同时保证数据可复现"""
    search, weather = fallback_tools

    # 先拿全城景点，再按兴趣把匹配项排到前面。
    # 为什么不在工具里直接按关键词过滤：只命中「美食」会让其余几天无景点可排。
    all_spots = _tool_json(search, {"city": req["city"], "keyword": ""})["attractions"]
    keywords = req.get("interests") or []

    def matched(spot: dict) -> bool:
        text = spot.get("name", "") + spot.get("type", "") + spot.get("desc", "")
        return any(kw in text for kw in keywords)

    ordered: List[dict] = []
    for spot in [s for s in all_spots if matched(s)] + all_spots:
        if spot["name"] not in {x["name"] for x in ordered}:
            ordered.append(spot)

    days = int(req.get("days") or 3)
    # 从明天开始生成连续日期，避免写死某一天导致报告过期
    start = date.today() + timedelta(days=1)
    forecasts = [
        _tool_json(weather, {
            "city": req["city"],
            "date": str(start + timedelta(days=i)),
        })
        for i in range(days)
    ]
    return {"attractions": ordered, "weather": forecasts}


def run_pipeline(user_input: str, llm=None, verbose: bool = True) -> Dict[str, Any]:
    """执行完整流水线，返回结构化结果与 Markdown 报告"""
    load_dotenv()
    tools = build_tools()

    # llm 允许外部注入（测试时可传假对象，不必消耗真实 Token）
    if llm is None:
        from hello_agents import HelloAgentsLLM
        llm = HelloAgentsLLM()
    agents = build_agents(llm, tools)

    # 第 1 步：需求解析（失败则正则兜底）
    req = parse_json(agents["requirement"].run(user_input)) or fallback_requirement(user_input)

    # 第 2 步：调研；Agent 没返回景点就用工具直连，避免被模型编造数据带偏
    research = parse_json(agents["research"].run(
        f"用户需求：{json.dumps(req, ensure_ascii=False)}。请查询景点和天气。"
    ))
    if not research.get("attractions"):
        research = _research(req, [tools[0], tools[1]])

    # 第 3 步：规划（失败则平均分配兜底）
    plan_raw = parse_json(agents["planner"].run(
        f"需求：{json.dumps(req, ensure_ascii=False)}\n"
        f"候选景点：{json.dumps(research['attractions'], ensure_ascii=False)}\n"
        f"天气：{json.dumps(research['weather'], ensure_ascii=False)}"
    ))
    plan = plan_raw.get("days") or fallback_plan(req, research["attractions"])

    # 第 4 步：预算（Agent 调工具；失败则同样用工具直接算）
    budget = parse_json(agents["budget"].run(
        f"需求：{json.dumps(req, ensure_ascii=False)}\n"
        f"景点：{json.dumps(research['attractions'], ensure_ascii=False)}"
    )) or fallback_budget(req, research["attractions"])

    # 第 5 步：校验；不达标且还没返工时，让规划 Agent 带着问题重排一次
    review = parse_json(agents["review"].run(
        f"用户需求：{json.dumps(req, ensure_ascii=False)}\n"
        f"行程：{json.dumps(plan, ensure_ascii=False)}\n"
        f"预算：{json.dumps(budget, ensure_ascii=False)}"
    )) or {"score": 7, "issues": [], "suggestions": []}

    if int(review.get("score") or 0) < REVIEW_PASS_SCORE:
        repaired = parse_json(agents["planner"].run(
            f"上一版行程问题：{json.dumps(review.get('issues', []), ensure_ascii=False)}。"
            f"请据此重排，需求：{json.dumps(req, ensure_ascii=False)}，"
            f"候选景点：{json.dumps(research['attractions'], ensure_ascii=False)}"
        ))
        if repaired.get("days"):
            plan = repaired["days"]
            budget = parse_json(agents["budget"].run(
                f"需求：{json.dumps(req, ensure_ascii=False)}，"
                f"重排后行程：{json.dumps(plan, ensure_ascii=False)}"
            )) or budget
            review["revised"] = True

    if verbose:
        print(f"[完成] {req['city']} {req['days']} 天，预计总预算 {budget.get('total', '?')} 元")

    return {
        "requirement": req,
        "weather": research["weather"],
        "attractions": research["attractions"],
        "plan": plan,
        "budget": budget,
        "review": review,
        "report": build_report(req, research["weather"], plan, budget, review),
    }


def build_report(req: Dict[str, Any], weather: List[dict], plan: List[dict],
                 budget: Dict[str, Any], review: Dict[str, Any]) -> str:
    """把结构化结果拼成可直接阅读的 Markdown 报告"""
    lines = [
        f"# {req['city']} {req['days']} 日行程",
        "",
        f"- 出行人数：{req['people']} 人",
        f"- 预算上限：{req['budget']} 元",
        f"- 偏好：{'、'.join(req.get('interests') or []) or '无特别偏好'}",
        f"- 预计总花费：{budget.get('total', 0)} 元（人均 {budget.get('per_person', 0)} 元）",
        "",
        "## 每日安排",
    ]

    for item in plan:
        lines += [
            f"### Day {item.get('day')}　{item.get('date', '')}",
            f"- 上午：{item.get('morning', '')}",
            f"- 下午：{item.get('afternoon', '')}",
            f"- 晚上：{item.get('evening', '')}",
        ]
        if item.get("tips"):
            lines.append(f"- 提示：{item['tips']}")
        lines.append("")

    lines += ["## 天气", ""]
    for w in weather:
        lines.append(
            f"- {w.get('date', '')}：{w.get('condition', '')}，"
            f"{w.get('temp_low', '')}~{w.get('temp_high', '')}℃，{w.get('tip', '')}"
        )

    lines += ["", "## 预算明细", ""]
    for key, label in [("transport", "交通"), ("hotel", "住宿"),
                       ("food", "餐饮"), ("tickets", "门票")]:
        lines.append(f"- {label}：{budget.get(key, 0)} 元")
    lines.append(f"- **合计：{budget.get('total', 0)} 元**")

    lines += ["", "## 质检结果", "", f"评分：{review.get('score', '?')}/10"]
    for issue in review.get("issues") or []:
        lines.append(f"- 问题：{issue}")
    for tip in review.get("suggestions") or []:
        lines.append(f"- 建议：{tip}")

    return "\n".join(lines)
