"""
五个智能体的定义。

为什么每个智能体都要求「只输出 JSON」：
  流水线靠上一步的输出驱动下一步。自然语言段落无法稳定解析，
  固定成 JSON 后，任何一步出错都能立刻发现并兜底。
"""

from __future__ import annotations

from typing import Dict, List

from hello_agents import HelloAgentsLLM, SimpleAgent
from hello_agents.tools import Tool

# 统一的 JSON 输出约束，减少模型加解释性前后缀的概率
_JSON_ONLY = "只输出一个 JSON 对象，不要输出解释、不要加 Markdown 代码块。"


def build_agents(llm: HelloAgentsLLM, tools: List[Tool]) -> Dict[str, SimpleAgent]:
    """创建 5 个智能体；工具只挂给真正需要它的角色"""

    # 工具按名字分配：调研 Agent 查景点天气，预算 Agent 算钱
    tool_map = {t.name: t for t in tools}

    requirement_agent = SimpleAgent(
        name="需求解析Agent",
        llm=llm,
        system_prompt=(
            "你是旅行需求解析专家。从用户的话里提取：城市 city、天数 days、"
            "人数 people、预算 budget、偏好 interests（字符串数组）。"
            "金额单位是元；缺失的字段用合理默认值（days=3, people=2, "
            "budget=3000, interests=[]）。"
            '输出格式：{"city":"杭州","days":3,"people":2,"budget":3000,'
            '"interests":["美食","博物馆"]}。' + _JSON_ONLY
        ),
    )

    research_agent = SimpleAgent(
        name="目的地调研Agent",
        llm=llm,
        system_prompt=(
            "你是目的地调研专家。必须先调用 search_attractions 查询候选景点，"
            "再调用 get_weather 查询行程期间的天气，然后汇总。"
            "候选景点不少于 5 个（工具返回不足时以实际数量为准），必须全部来自工具结果，"
            "不得自己补充或改写景点名称。"
            '输出格式：{"attractions":[{"name":"","type":"","duration":0,'
            '"cost":0,"area":"","desc":""}],"weather":[{"date":"","condition":"",'
            '"temp_low":0,"temp_high":0,"tip":""}]}。禁止编造工具没有返回的景点。'
            + _JSON_ONLY
        ),
    )
    research_agent.add_tool(tool_map["search_attractions"])
    research_agent.add_tool(tool_map["get_weather"])

    planner_agent = SimpleAgent(
        name="行程规划Agent",
        llm=llm,
        system_prompt=(
            "你是行程规划专家。根据候选景点、天气和天数，把景点分配到每一天的"
            "上午、下午、晚上。硬性约束："
            "1) 每天景点总游玩时长不超过 8 小时；"
            "2) 一天最多 3 个景点；"
            "3) 每天尽量安排 2~3 个具体景点，候选足够时不要留空档；"
            "4) 雨天优先安排博物馆等室内项目。"
            '输出格式：{"days":[{"day":1,"date":"","morning":"","afternoon":"",'
            '"evening":"","tips":""}]}。' + _JSON_ONLY
        ),
    )

    budget_agent = SimpleAgent(
        name="预算测算Agent",
        llm=llm,
        system_prompt=(
            "你是旅行预算专家。必须调用 calc_budget 工具完成计算，不要自己心算。"
            "参数估算规则：transport 用每人 300~800 元（按城市远近取合理值），"
            "hotel_per_night 用 300~600 元，food_per_day 用 100~200 元，"
            "tickets 等于所选景点门票之和乘以人数。"
            '输出格式：{"transport":0,"hotel":0,"food":0,"tickets":0,'
            '"total":0,"per_person":0}。' + _JSON_ONLY
        ),
    )
    budget_agent.add_tool(tool_map["calc_budget"])

    review_agent = SimpleAgent(
        name="方案校验Agent",
        llm=llm,
        system_prompt=(
            "你是行程质检员。检查三件事："
            "1) 每天是否超过 8 小时或 3 个景点；"
            "2) 预算是否超出用户预算；"
            "3) 雨天是否安排了户外项目。"
            "给 0~10 分（10 分最好）。"
            '输出格式：{"score":8,"issues":["..."],"suggestions":["..."]}。'
            + _JSON_ONLY
        ),
    )

    return {
        "requirement": requirement_agent,
        "research": research_agent,
        "planner": planner_agent,
        "budget": budget_agent,
        "review": review_agent,
    }
