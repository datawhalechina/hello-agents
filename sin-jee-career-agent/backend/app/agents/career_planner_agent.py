"""多智能体求职规划系统

"""

import json
from typing import Optional
from hello_agents import SimpleAgent
from hello_agents.tools import MCPTool
from ..services.llm_service import get_llm
from ..models.schemas import CareerRequest, CareerPlan, JobTask, CareerBudget
from ..config import get_settings

# ============ Agent 提示词 ============

JOB_SEARCH_AGENT_PROMPT = """你是职位搜索专家。你的任务是根据用户的求职需求搜索真实招聘信息。

**重要:**
你必须使用工具来搜索职位信息！不要自己编造职位！

**工具调用格式:**
`[TOOL_CALL:brave_web_search:query=搜索关键词]`

**搜索策略（请逐一搜索以下关键词）:**
1. 先搜索: "{role} {city} 招聘"
2. 再搜索: "{role} {city} {industry} 招聘"
3. 最后搜索: "{role} {preferences} 招聘"

**结果整理要求:**
请从搜索结果中整理出5-10个最匹配的职位，每个职位包含:
- 职位名称
- 公司名称
- 薪资范围
- 核心要求（3-5条）
- 招聘来源（BOSS直聘/猎聘/拉勾等）
- 招聘链接（如果有）

**注意:**
1. 必须使用工具搜索，不要编造信息
2. 格式必须完全正确，包括方括号和冒号
3. 优先使用BOSS直聘、猎聘、拉勾等平台的结果
"""

COMPANY_RESEARCH_AGENT_PROMPT = """你是公司研究专家。你的任务是研究目标公司背景，为求职者提供决策信息。

**重要:**
你必须使用工具来搜索公司信息！

**工具调用格式:**
`[TOOL_CALL:brave_web_search:query=搜索关键词]`

**搜索策略:**
1. 先搜索: "{company_name} 公司介绍 规模 业务"
2. 再搜索: "{company_name} 工作体验 员工评价"
3. 最后搜索: "{company_name} 融资 发展前景"

**信息整理要求:**
对每家公司整理出:
- 公司名称、行业、规模、总部
- 主营业务简介
- 公司文化/氛围
- 融资阶段/发展前景
- 优势（3条）
- 潜在风险（2条）
- 综合评分（1-5分）

**注意:**
1. 必须使用工具搜索
2. 积极正面的同时保持客观，指出潜在风险
"""

SALARY_AGENT_PROMPT = """你是薪资研究专家。你的任务是查询目标职位在目标城市的真实薪资水平。

**重要:**
你必须先使用工具搜索真实薪资数据，再用自己的知识补充！

**工具调用格式:**
`[TOOL_CALL:brave_web_search:query=搜索关键词]`

**搜索策略:**
1. 先搜索: "{role} {city} 薪资 2024 2025"
2. 再搜索: "{role} {experience_level} 薪资水平"

**信息整理要求:**
整理出:
- 目标职位的薪资范围（最低-最高）
- 平均薪资
- 不同经验级别的薪资差异
- 数据来源（标注可信度）
- 薪资谈判建议

**注意:**
1. 必须先搜索再整理
2. 标注数据来源和可信度
"""

CAREER_PLAN_AGENT_PROMPT = """你是求职策略规划专家。你的任务是整合职位信息、公司信息和薪资信息，生成一份完整的求职策略报告。

请严格按照以下JSON格式返回求职计划:
```json
{
  "target_role": "目标职位",
  "city": "目标城市",
  "start_date": "YYYY-MM-DD",
  "target_days": 7,
  "jobs": [
    {
      "title": "职位名称",
      "company": "公司名称",
      "location": "工作地点",
      "salary_range": "薪资范围",
      "description": "职位描述",
      "requirements": ["要求1", "要求2", "要求3"],
      "url": "招聘链接",
      "source": "招聘来源",
      "posted_date": "发布日期",
      "employment_type": "全职"
    }
  ],
  "companies": [
    {
      "name": "公司名称",
      "industry": "行业",
      "size": "规模",
      "headquarters": "总部",
      "description": "简介",
      "culture": "文化氛围",
      "funding_stage": "融资阶段",
      "rating": 4.2,
      "pros": ["优势1", "优势2"],
      "cons": ["风险1"]
    }
  ],
  "salary_info": [
    {
      "role": "职位",
      "city": "城市",
      "experience_level": "经验级别",
      "avg_salary": "平均薪资",
      "salary_range_low": 15000,
      "salary_range_high": 25000,
      "source": "数据来源",
      "confidence": "medium"
    }
  ],
  "daily_tasks": [
    {
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "description": "当日任务概述",
      "tasks": ["具体任务1", "具体任务2"],
      "target_companies": ["目标公司1"],
      "target_jobs": ["目标职位1"],
      "preparation_tips": "今日准备提示"
    }
  ],
  "resume_tips": "简历优化建议",
  "interview_prep": "面试准备清单",
  "overall_strategy": "总体求职策略",
  "budget": {
    "transportation": 200,
    "printing": 50,
    "training": 500,
    "others": 200,
    "total": 950
  }
}
```

**规划要求:**
1. 每天安排3-5个具体求职任务（投递简历、准备面试、学习技能等）
2. 简历优化建议要针对目标职位的关键要求
3. 面试准备清单覆盖：技术面试、行为面试、项目展示
4. 总体策略要包含时间线和优先级排序
5. 预算按求职城市实际开销估算
6. 根据用户偏好（大厂/创业公司等）调整推荐权重
7. 薪资数据中的数字为纯数字（不带单位）
"""


class CareerPlannerAgent:
    """多智能体求职规划系统"""

    def __init__(self):
        print("[INIT] 开始初始化多智能体求职规划系统...")

        try:
            settings = get_settings()
            self.llm = get_llm()
            self.has_brave_search = bool(settings.brave_search_api_key)

            if self.has_brave_search:
                print("  - 创建Brave Search MCP工具...")
                self.search_tool = MCPTool(
                    name="brave_search",
                    description="Brave网页搜索服务",
                    server_command=["npx", "-y", "@anthropic/mcp-server-brave-search"],
                    env={"BRAVE_SEARCH_API_KEY": settings.brave_search_api_key},
                    auto_expand=True
                )
                search_tool_desc = "Brave Search MCP"
            else:
                print("  - 未配置Brave Search Key，Agent将使用LLM内置知识")

            # 创建职位搜索Agent
            print("  - 创建职位搜索Agent...")
            self.job_search_agent = SimpleAgent(
                name="职位搜索专家",
                llm=self.llm,
                system_prompt=JOB_SEARCH_AGENT_PROMPT
            )
            if self.has_brave_search:
                self.job_search_agent.add_tool(self.search_tool)

            # 创建公司研究Agent
            print("  - 创建公司研究Agent...")
            self.company_research_agent = SimpleAgent(
                name="公司研究专家",
                llm=self.llm,
                system_prompt=COMPANY_RESEARCH_AGENT_PROMPT
            )
            if self.has_brave_search:
                self.company_research_agent.add_tool(self.search_tool)

            # 创建薪资研究Agent
            print("  - 创建薪资研究Agent...")
            self.salary_agent = SimpleAgent(
                name="薪资研究专家",
                llm=self.llm,
                system_prompt=SALARY_AGENT_PROMPT
            )
            if self.has_brave_search:
                self.salary_agent.add_tool(self.search_tool)

            # 创建求职规划Agent（不需要工具，纯LLM整合）
            print("  - 创建求职规划Agent...")
            self.career_plan_agent = SimpleAgent(
                name="求职策略规划专家",
                llm=self.llm,
                system_prompt=CAREER_PLAN_AGENT_PROMPT
            )

            status = "[SEARCH] Brave Search" if self.has_brave_search else "[BRAIN] LLM内置知识"
            print(f"[OK] 多智能体求职规划系统初始化成功 (搜索模式: {status})")

        except Exception as e:
            print(f"[FAIL] 多智能体系统初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def plan_career(self, request: CareerRequest) -> CareerPlan:
        """
        使用多智能体协作生成求职计划

        Args:
            request: 求职请求

        Returns:
            求职计划
        """
        try:
            print(f"\n{'='*60}")
            print(f"[START] 开始多智能体协作规划求职...")
            print(f"目标职位: {request.target_role}")
            print(f"城市: {request.city}")
            print(f"周期: {request.target_days}天")
            print(f"偏好: {', '.join(request.preferences) if request.preferences else '无'}")
            print(f"{'='*60}\n")

            # 步骤1: 搜索职位
            print("[JOB] 步骤1: 搜索职位...")
            job_query = self._build_job_search_query(request)
            job_response = self.job_search_agent.run(job_query)
            print(f"职位搜索结果: {job_response[:200]}...\n")

            # 步骤2: 研究公司
            print("[COMP] 步骤2: 研究公司...")
            company_query = self._build_company_research_query(request, job_response)
            company_response = self.company_research_agent.run(company_query)
            print(f"公司研究结果: {company_response[:200]}...\n")

            # 步骤3: 查询薪资
            print("[SAL] 步骤3: 查询薪资...")
            salary_query = self._build_salary_query(request)
            salary_response = self.salary_agent.run(salary_query)
            print(f"薪资查询结果: {salary_response[:200]}...\n")

            # 步骤4: 整合生成求职计划
            print("[PLAN] 步骤4: 生成求职策略...")
            planner_query = self._build_career_plan_query(
                request, job_response, company_response, salary_response
            )
            planner_response = self.career_plan_agent.run(planner_query)
            print(f"求职规划结果: {planner_response[:300]}...\n")

            # 解析JSON
            career_plan = self._parse_response(planner_response, request)

            print(f"{'='*60}")
            print(f"[OK] 求职计划生成完成!")
            print(f"{'='*60}\n")

            return career_plan

        except Exception as e:
            print(f"[FAIL] 生成求职计划失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_plan(request)

    def _build_job_search_query(self, request: CareerRequest) -> str:
        """构建职位搜索查询"""
        pref = request.preferences[0] if request.preferences else "高薪"
        query = (
            f"请使用brave_web_search工具搜索{request.city}的{request.target_role}职位。\n"
            f"[TOOL_CALL:brave_web_search:query={request.target_role} {request.city} {request.industry} 招聘]\n"
            f"搜索后请再补充搜索: [TOOL_CALL:brave_web_search:query={request.target_role} {pref} 招聘 {request.city}]"
        )
        if request.free_text_input:
            query += f"\n额外偏好: {request.free_text_input}"
        return query

    def _build_company_research_query(self, request: CareerRequest, job_response: str) -> str:
        """构建公司研究查询 — 从职位结果中提取公司名"""
        query = (
            f"请根据以下职位搜索结果，研究其中提到的公司的详细信息。\n\n"
            f"**职位搜索结果:**\n{job_response[:2000]}\n\n"
            f"**用户偏好:** {', '.join(request.preferences) if request.preferences else '大厂优先'}\n"
            f"**目标行业:** {request.industry}\n\n"
            f"请使用brave_web_search工具逐一搜索关键公司的背景信息。"
        )
        return query

    def _build_salary_query(self, request: CareerRequest) -> str:
        """构建薪资查询"""
        query = (
            f"请使用brave_web_search工具查询{request.target_role}在{request.city}的薪资水平。\n"
            f"[TOOL_CALL:brave_web_search:query={request.target_role} {request.city} 薪资 2025]\n"
            f"用户经验级别: {request.experience_level}，期望薪资: {request.salary_expectation}"
        )
        return query

    def _build_career_plan_query(
        self,
        request: CareerRequest,
        job_response: str,
        company_response: str,
        salary_response: str,
    ) -> str:
        """构建求职规划整合查询"""
        query = f"""请根据以下信息生成{request.city}的{request.target_role}求职规划:

**基本信息:**
- 目标职位: {request.target_role}
- 目标城市: {request.city}
- 开始日期: {request.start_date}
- 求职周期: {request.target_days}天
- 经验级别: {request.experience_level}
- 薪资期望: {request.salary_expectation}
- 目标行业: {request.industry}
- 偏好: {', '.join(request.preferences) if request.preferences else '无'}
- 额外要求: {request.free_text_input}

**职位搜索结果:**
{job_response[:3000]}

**公司研究结果:**
{company_response[:3000]}

**薪资数据:**
{salary_response[:2000]}

**要求:**
1. 每天安排3-5个具体求职任务
2. 简历优化建议要针对职位要求
3. 面试准备覆盖技术和行为面试
4. 根据偏好（大厂/创业公司）调整推荐
5. 返回完整JSON格式
"""
        return query

    def _parse_response(self, response: str, request: CareerRequest) -> CareerPlan:
        """解析Agent响应中的JSON"""
        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            else:
                raise ValueError("响应中未找到JSON数据")

            data = json.loads(json_str)
            return CareerPlan(**data)

        except Exception as e:
            print(f"[WARN]  解析响应失败: {str(e)}，使用备用方案")
            return self._create_fallback_plan(request)

    def _create_fallback_plan(self, request: CareerRequest) -> CareerPlan:
        """创建备用计划（当Agent失败时）"""
        from datetime import datetime, timedelta

        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")

        daily_tasks = []
        task_templates = [
            ["更新简历，针对目标职位优化关键词", "在BOSS直聘搜索目标职位"],
            ["研究3家目标公司", "准备技术面试常见问题"],
            ["投递5份简历", "整理项目经验，准备项目展示"],
            ["刷LeetCode/算法题", "整理行为面试STAR案例"],
            ["跟进已投递公司", "准备薪资谈判要点"],
            ["模拟面试练习", "扩展人脉，联系目标公司员工"],
            ["复盘本周求职进展", "制定下周求职计划"],
        ]

        for i in range(min(request.target_days, len(task_templates))):
            current_date = start_date + timedelta(days=i)
            daily_tasks.append(JobTask(
                date=current_date.strftime("%Y-%m-%d"),
                day_index=i,
                description=f"第{i+1}天求职任务",
                tasks=task_templates[i],
                target_companies=[],
                target_jobs=[],
                preparation_tips="记得保持积极心态，每次面试后及时总结复盘"
            ))

        return CareerPlan(
            target_role=request.target_role,
            city=request.city,
            start_date=request.start_date,
            target_days=request.target_days,
            jobs=[],
            companies=[],
            salary_info=[],
            daily_tasks=daily_tasks,
            resume_tips=(
                f"1. 根据{request.target_role}的JD中的关键词优化简历"
                f"2. 量化项目成果，使用数据说明影响力"
                f"3. 突出与{request.industry}行业相关的经验"
            ),
            interview_prep=(
                "技术面试准备：数据结构与算法、系统设计、编程语言基础\n"
                "行为面试准备：准备STAR案例（情境-任务-行动-结果）\n"
                "项目展示：整理2-3个核心项目，能够清晰介绍技术选型和业务价值"
            ),
            overall_strategy=(
                f"针对{request.city}的{request.target_role}岗位，建议采用以下策略：\n"
                "第1-3天：简历优化+公司调研，确定10家目标公司\n"
                "第3-5天：集中投递+准备面试\n"
                "第5-7天：面试+跟进+复盘调整"
            ),
            budget=CareerBudget(
                transportation=200,
                printing=50,
                training=500,
                others=200,
                total=950
            )
        )


# 全局单例
_career_planner: Optional[CareerPlannerAgent] = None


def get_career_planner() -> CareerPlannerAgent:
    """获取求职规划Agent实例（单例模式）"""
    global _career_planner
    if _career_planner is None:
        _career_planner = CareerPlannerAgent()
    return _career_planner
