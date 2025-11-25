import json
from typing import Dict, Any, List
from hello_agents import SimpleAgent

from ..models.schemas import FitnessRequest, TrainPlan
from ..services.llm_service import get_llm
from ..config import get_settings

# ========== Agent 提示词 ==========
PLANNER_AGENT_PROMPT = """你是健身规划专家，你的任务是根据客户的身高、体重和年龄，生成详细的健身计划。

请为以下用户生成个性化的健身计划：
- 年龄：{request.age}岁
- 身高：{request.height}cm
- 体重：{request.weight}kg

要求：
1. 包含训练计划（每周3-5天）
2. 包含营养建议
3. 包含注意事项
4. 用中文回复，格式美观

"""

class FitnessPlanner:

    def __init__(self):
        print("开始初始化智能体健身规划系统")

        try:
            settings = get_settings()
            self.llm = get_llm()

            print("创建健身规划Agent")
            self.planner_agent = SimpleAgent(
                name="健身规划专家",
                llm=self.llm,
                system_prompt=PLANNER_AGENT_PROMPT
            )

        except Exception as e:
            print(f"❌ 智能体系统初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def plan_train(self, request: FitnessRequest) -> List[TrainPlan]:
        try:
            print(f"\n{'=' * 60}")
            print(f"🚀 开始智能体规划训练...")
            print(f"身高：{request.height}")
            print(f"体重：{request.weight}")
            print(f"年龄：{request.age}")
            print(f"\n{'=' * 60}")

            print("制定训练计划中...")
            planner_query = self._build_planner_query(request)
            planner_response = self.planner_agent.run(planner_query)
            print(f"训练规划结果: {planner_response[:300]}...\n")

            # 解析响应为列表
            train_plan_list = self._parse_response(planner_response, request)

            # 确保返回 7 天列表，如果不足则用休息日填充
            full_plan = []
            for day in range(1, 8):
                day_plan = next((p for p in train_plan_list if p.get("day") == day), None)
                if day_plan:
                    # 转换为 TrainPlan 对象
                    full_plan.append(TrainPlan(**day_plan))
                else:
                    # 休息日占位
                    full_plan.append(TrainPlan(
                        day=day,
                        action="休息",
                        muscle=None,
                        group_num=None,
                        amount=None
                    ))

            print(f"{'=' * 60}")
            print(f"✅ 训练计划生成完成!")
            print(f"{'=' * 60}\n")

            return full_plan

        except Exception as e:
            print(f"❌ 生成训练计划失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_plan(request)

    def _build_planner_query(self, request: FitnessRequest) -> str:

        query = f"""
        你是一个健身训练计划生成器，只能返回 JSON 格式。

        请根据以下信息生成 **7 天训练计划**，并严格按下面的 JSON schema 输出：

        每条数据格式必须如下：
        {{
          "day": int,
          "action": str,
          "muscle": str,
          "group_num": int,
          "amount": int
        }}

        输出格式必须是一个 JSON 数组，例如：
        [
          {{ ... }},
          {{ ... }},
          ...
        ]

        用户信息：
        - 身高: {request.height}
        - 体重: {request.weight}
        - 年龄: {request.age}

        生成要求：
        1. 输出完整 7 天计划，每天 3~4 个动作（可拆成多条 JSON）
        2. 返回标准 JSON 数组
        3. 严禁输出解释、文字、标题，只能输出 JSON

        """
        return query

    def _parse_response(self, response: str, request: FitnessRequest) -> List[dict]:
        """
        解析 Agent 响应为字典列表，每个元素对应一天训练计划
        """
        try:
            import json

            # 提取 JSON 部分
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                # 尝试直接解析 JSON
                json_str = response.strip()

            data = json.loads(json_str)

            # 确保返回的是列表
            if isinstance(data, dict):
                return [data]
            elif isinstance(data, list):
                return data
            else:
                raise ValueError("Agent 返回数据格式不正确")

        except Exception as e:
            print(f"⚠️  解析响应失败: {str(e)}")
            print(f"   将使用备用方案生成计划")
            return [p.dict() for p in self._create_fallback_plan(request)]

    def _create_fallback_plan(self, request: FitnessRequest) -> List[TrainPlan]:
        """
        生成 7 天 fallback 计划
        """
        fallback = []
        for day in range(1, 8):
            if day % 2 == 0:
                fallback.append(TrainPlan(day=day, action="休息", muscle=None, group_num=None, amount=None))
            else:
                fallback.append(TrainPlan(day=day, action="深蹲", muscle="腿部", group_num=4, amount=12))
        return fallback


_fitness_planner = None

def get_fitness_planner_agent() -> FitnessPlanner:
    global _fitness_planner

    if _fitness_planner is None:
        _fitness_planner = FitnessPlanner()

    return _fitness_planner
