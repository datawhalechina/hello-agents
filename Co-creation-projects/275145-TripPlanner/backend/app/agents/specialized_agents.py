"""
专业智能体实现
基于EnhancedAgent创建各个专业领域的智能体
"""
from typing import Optional, Dict, Any
from hello_agents import HelloAgentsLLM, ToolRegistry
from app.agents.enhanced_agent import EnhancedAgent
from app.services.context_manager import ContextManager
from app.agents.agent_communication import (
    AgentCommunicationHub,
    AgentMessage,
    MessageType
)
from app.observability.logger import default_logger as logger


# ============ Agent提示词 ============

ATTRACTION_AGENT_PROMPT = """你是景点搜索专家。你的任务是根据城市和用户偏好搜索合适的景点。

**重要提示:**
1. 你必须使用工具来搜索景点!不要自己编造景点信息!
2. 你应该参考用户的历史偏好和相似行程来优化搜索策略
3. 如果从上下文信息中了解到用户喜欢特定类型的景点，优先搜索这些类型
4. 搜索完成后，将结果共享给其他智能体

**工具调用格式:**
使用maps_text_search工具时,必须严格按照以下格式:
`[TOOL_CALL:amap_maps_text_search:keywords=景点关键词,city=城市名]`

**示例:**
用户: "搜索北京的历史文化景点"
你的回复: [TOOL_CALL:amap_maps_text_search:keywords=历史文化,city=北京]

用户: "搜索上海的公园"
你的回复: [TOOL_CALL:amap_maps_text_search:keywords=公园,city=上海]

**注意:**
1. 必须使用工具,不要直接回答
2. 格式必须完全正确,包括方括号和冒号
3. 参数用逗号分隔
4. 如果用户有历史偏好，优先使用这些偏好作为搜索关键词
"""

WEATHER_AGENT_PROMPT = """你是天气查询专家。你的任务是查询指定城市的天气信息。

**重要提示:**
1. 你必须使用工具来查询天气!不要自己编造天气信息!
2. 你应该查询整个行程期间的天气，而不仅仅是当前日期
3. 查询完成后，将天气信息共享给规划智能体

**工具调用格式:**
使用maps_weather工具时,必须严格按照以下格式:
`[TOOL_CALL:amap_maps_weather:city=城市名]`

**示例:**
用户: "查询北京天气"
你的回复: [TOOL_CALL:amap_maps_weather:city=北京]

**注意:**
1. 必须使用工具,不要直接回答
2. 格式必须完全正确,包括方括号和冒号
"""

HOTEL_AGENT_PROMPT = """你是酒店推荐专家。你的任务是根据城市和景点位置推荐合适的酒店。

**重要提示:**
1. 你必须使用工具来搜索酒店!不要自己编造酒店信息!
2. 你应该参考景点智能体提供的景点位置信息，优先推荐距离景点较近的酒店
3. 你应该参考用户的酒店偏好和历史选择来优化推荐
4. 推荐完成后，将结果共享给规划智能体

**工具调用格式:**
使用maps_text_search工具搜索酒店时,必须严格按照以下格式:
`[TOOL_CALL:amap_maps_text_search:keywords=酒店,city=城市名]`

**示例:**
用户: "搜索北京的酒店"
你的回复: [TOOL_CALL:amap_maps_text_search:keywords=酒店,city=北京]

**注意:**
1. 必须使用工具,不要直接回答
2. 格式必须完全正确,包括方括号和冒号
3. 关键词使用"酒店"或"宾馆"
4. 如果从上下文了解到景点位置，优先搜索附近的酒店
"""

PLANNER_AGENT_PROMPT = """你是行程规划专家。你的任务是根据景点信息、酒店信息和天气信息，生成详细的旅行计划。

**重要提示:**
1. 你应该参考用户的历史行程和反馈来优化规划策略
2. 你应该考虑从其他智能体共享的信息（景点位置、酒店位置等）
3. 如果发现信息不足，可以请求其他智能体提供更多信息
4. 生成计划后，可以与其他智能体协商优化方案

**地理位置和距离要求（非常重要）:**
1. **所有景点必须在目标城市范围内**：严格验证每个景点的地理位置（经纬度），确保所有景点都在用户指定的目的地城市，绝对不要推荐其他城市的景点。
2. **同一天景点距离控制**：同一天内的景点之间距离要合理，建议不超过50公里，优先安排距离较近的景点在同一天游览。
3. **相邻天景点距离控制**：相邻两天的景点之间距离也要合理，避免第一天在城市的东边，第二天突然跳到城市的西边，建议相邻天的主要景点距离不超过100公里。
4. **地理位置验证**：在生成行程前，必须验证所有景点的经纬度是否在目标城市的合理范围内。如果发现景点位置异常（如规划杭州之旅却出现福建的景点），必须排除该景点或重新搜索。
5. **路线优化**：按照地理位置合理安排景点顺序，尽量形成一条合理的游览路线，减少往返路程。

请严格按照以下 **JSON 结构** 返回旅行计划。你的输出必须是有效的 JSON，不要添加任何额外的解释或注释。

**整体设计要求：**
1. **景点模型（Attraction）** 必须包含：景点名称、类型、评分、建议游玩时间、描述、地址、经纬度、景点图片 URL 列表、门票价格。
2. **酒店模型（Hotel）** 在原有基础上，必须补充「距离景点的距离」字段。
3. **单日行程（DailyPlan）** 必须包含：
   - 推荐住宿（recommended_hotel）
   - 景点列表（attractions）
   - 餐饮列表（dinings）
   - 单日预算拆分（budget），包括交通费用、餐饮费用、酒店费用、景点门票费用。
4. **预算**：总预算字段需要拆分为交通费用、餐饮费用、酒店费用、景点门票费用四项，并给出总和。
5. 所有的「图片」只能挂在 **景点（attractions）** 上，不能给酒店或餐饮生成图片 URL。

**响应格式（示例，仅作为结构参考，字段名和类型必须严格遵守）：**
```json
{
  "trip_title": "一个吸引人的行程标题",
  "total_budget": {
    "transport_cost": 300.0,
    "dining_cost": 800.0,
    "hotel_cost": 1200.0,
    "attraction_ticket_cost": 400.0,
    "total": 2700.0
  },
  "hotels": [
    {
      "name": "酒店名称",
      "address": "酒店地址",
      "location": {"lat": 39.915, "lng": 116.397},
      "price": "400元/晚",
      "rating": "4.5",
      "distance_to_main_attraction_km": 1.2
    }
  ],
  "days": [
    {
      "day": 1,
      "theme": "古都历史探索",
      "weather": {
        "date": "YYYY-MM-DD",
        "day_weather": "晴",
        "night_weather": "多云",
        "day_temp": "25",
        "night_temp": "15",
        "day_wind": "东风3级",
        "night_wind": "西北风2级"
      },
      "recommended_hotel": {
        "name": "当日推荐酒店",
        "address": "酒店地址",
        "location": {"lat": 39.915, "lng": 116.397},
        "price": "400元/晚",
        "rating": "4.5",
        "distance_to_main_attraction_km": 0.8
      },
      "attractions": [
        {
          "name": "景点名称",
          "type": "历史文化",
          "rating": "4.7",
          "suggested_duration_hours": 3.0,
          "description": "景点简介和游览建议",
          "address": "景点地址",
          "location": {"lat": 39.915, "lng": 116.397},
          "image_urls": [
            "https://example.com/attraction-image-1.jpg"
          ],
          "ticket_price": "60"
        }
      ],
      "dinings": [
        {
          "name": "餐厅名称",
          "address": "餐厅地址",
          "location": {"lat": 39.910, "lng": 116.400},
          "cost_per_person": "80",
          "rating": "4.5"
        }
      ],
      "budget": {
        "transport_cost": 50.0,
        "dining_cost": 200.0,
        "hotel_cost": 400.0,
        "attraction_ticket_cost": 120.0,
        "total": 770.0
      }
    }
  ]
}
```

**关键要求：**
1. **trip_title**：创建一个吸引人且能体现行程特色的标题。
2. **total_budget**：给出四类费用（交通、餐饮、酒店、景点门票），并计算 total 为它们的总和。
3. **hotels / recommended_hotel**：酒店必须包含名称、地址、位置坐标、价格、评分和距离主要景点的距离。
4. **days**：为每一天创建详细的行程计划。
5. **theme**：每天的主题要体现该天的主要活动特色。
6. **weather**：包含该天的天气信息，温度必须是纯数字（不要带 °C 等单位），并给出白天和夜间的风向与风力（day_wind, night_wind）。
7. **attractions / dinings**：
   - attractions：只包含"景点"信息，图片 URL 只能出现在 attractions.image_urls 中。
   - dinings：只包含餐饮信息，不能包含图片 URL 字段。
8. **时间规划**：在描述中要体现出合理的时间安排（例如上午/下午/晚上安排哪些景点和餐饮）。
9. **预算准确**：total_budget.total 必须等于四类费用之和；每天的 budget.total 也必须等于四项之和。
10. **避免重复**：不要在多天中重复推荐同一个景点或餐厅。
11. **地理位置验证（关键）**：
    - 在生成JSON前，必须检查所有景点的location字段（经纬度）是否在目标城市范围内
    - 如果发现景点位置不在目标城市，必须排除该景点
    - 同一天的景点经纬度应该相对集中，距离不超过50公里
    - 相邻天的景点经纬度变化应该合理，避免突然跨越很大距离
"""


class AttractionSearchAgent(EnhancedAgent):
    """景点搜索智能体（增强版）"""
    
    def __init__(
        self,
        llm: HelloAgentsLLM,
        tool_registry: ToolRegistry,
        context_manager: Optional[ContextManager] = None,
        communication_hub: Optional[AgentCommunicationHub] = None,
        user_id: Optional[str] = None
    ):
        super().__init__(
            name="景点搜索专家",
            llm=llm,
            system_prompt=ATTRACTION_AGENT_PROMPT,
            tool_registry=tool_registry,
            enable_tool_calling=True,
            context_manager=context_manager,
            communication_hub=communication_hub,
            user_id=user_id
        )
    
    def handle_message(self, message: AgentMessage) -> Dict[str, Any]:
        """处理接收到的消息"""
        if message.message_type == MessageType.REQUEST:
            # 处理其他智能体的请求
            content = message.content
            if content.get("action") == "search_attractions":
                query = content.get("query", "")
                result = self.run(query)
                return {
                    "status": "success",
                    "result": result
                }
        return super().handle_message(message)
    
    def run(self, input_text: str, max_tool_iterations: int = 3, **kwargs) -> str:
        """运行景点搜索（增强版）"""
        # 在运行前，检查是否有共享的上下文信息
        if self.context_manager:
            request_context = self.context_manager.get_shared_data("request")
            if request_context:
                # 从上下文获取用户偏好，优化搜索
                preferences = request_context.get("preferences", [])
                if preferences and "景点" not in input_text.lower():
                    # 如果输入中没有明确提到景点类型，使用用户偏好
                    pref_keywords = ", ".join(preferences[:2])  # 取前两个偏好
                    input_text = f"{input_text}，优先搜索{pref_keywords}相关的景点"
        
        result = super().run(input_text, max_tool_iterations, **kwargs)
        
        # 搜索完成后，将结果共享给酒店智能体
        if self.communication_hub and self.context_manager:
            # 提取景点位置信息（简单示例，实际需要解析结果）
            self.context_manager.share_data(
                "attraction_locations",
                result[:500],  # 共享部分结果
                from_agent=self.name
            )
            
            # 通知酒店智能体
            self.send_message_to_agent(
                "酒店推荐专家",
                MessageType.SUGGESTION,
                {
                    "message": "景点搜索完成",
                    "attraction_info": result[:500]
                }
            )
        
        return result


class HotelRecommendationAgent(EnhancedAgent):
    """酒店推荐智能体（增强版）"""
    
    def __init__(
        self,
        llm: HelloAgentsLLM,
        tool_registry: ToolRegistry,
        context_manager: Optional[ContextManager] = None,
        communication_hub: Optional[AgentCommunicationHub] = None,
        user_id: Optional[str] = None
    ):
        super().__init__(
            name="酒店推荐专家",
            llm=llm,
            system_prompt=HOTEL_AGENT_PROMPT,
            tool_registry=tool_registry,
            enable_tool_calling=True,
            context_manager=context_manager,
            communication_hub=communication_hub,
            user_id=user_id
        )
    
    def handle_message(self, message: AgentMessage) -> Dict[str, Any]:
        """处理接收到的消息"""
        if message.message_type == MessageType.SUGGESTION:
            # 处理景点智能体的建议
            content = message.content
            if "attraction_info" in content:
                # 基于景点信息优化酒店搜索
                logger.info(f"{self.name} 收到景点信息，将优化酒店推荐")
        return super().handle_message(message)
    
    def run(self, input_text: str, max_tool_iterations: int = 3, **kwargs) -> str:
        """运行酒店推荐（增强版）"""
        # 检查是否有景点位置信息
        if self.context_manager:
            attraction_locations = self.context_manager.get_shared_data("attraction_locations")
            if attraction_locations:
                input_text = f"{input_text}。请注意景点位置信息：{attraction_locations[:200]}"
        
        result = super().run(input_text, max_tool_iterations, **kwargs)
        
        # 推荐完成后，将结果共享给规划智能体
        if self.context_manager:
            self.context_manager.share_data(
                "hotel_recommendations",
                result[:500],
                from_agent=self.name
            )
        
        return result


class WeatherQueryAgent(EnhancedAgent):
    """天气查询智能体（增强版）"""
    
    def __init__(
        self,
        llm: HelloAgentsLLM,
        tool_registry: ToolRegistry,
        context_manager: Optional[ContextManager] = None,
        communication_hub: Optional[AgentCommunicationHub] = None,
        user_id: Optional[str] = None
    ):
        super().__init__(
            name="天气查询专家",
            llm=llm,
            system_prompt=WEATHER_AGENT_PROMPT,
            tool_registry=tool_registry,
            enable_tool_calling=True,
            context_manager=context_manager,
            communication_hub=communication_hub,
            user_id=user_id
        )
    
    def run(self, input_text: str, max_tool_iterations: int = 3, **kwargs) -> str:
        """运行天气查询（增强版）"""
        # 检查是否有日期信息
        if self.context_manager:
            request_context = self.context_manager.get_shared_data("request")
            if request_context:
                start_date = request_context.get("start_date")
                end_date = request_context.get("end_date")
                if start_date and end_date:
                    input_text = f"{input_text}，查询日期范围：{start_date} 到 {end_date}"
        
        result = super().run(input_text, max_tool_iterations, **kwargs)
        
        # 查询完成后，将结果共享给规划智能体
        if self.context_manager:
            self.context_manager.share_data(
                "weather_info",
                result[:500],
                from_agent=self.name
            )
        
        return result


class PlannerAgent(EnhancedAgent):
    """行程规划智能体（增强版）"""
    
    def __init__(
        self,
        llm: HelloAgentsLLM,
        context_manager: Optional[ContextManager] = None,
        communication_hub: Optional[AgentCommunicationHub] = None,
        user_id: Optional[str] = None
    ):
        super().__init__(
            name="行程规划专家",
            llm=llm,
            system_prompt=PLANNER_AGENT_PROMPT,
            tool_registry=None,  # 规划智能体不需要工具
            enable_tool_calling=False,
            context_manager=context_manager,
            communication_hub=communication_hub,
            user_id=user_id
        )
    
    def handle_message(self, message: AgentMessage) -> Dict[str, Any]:
        """处理接收到的消息"""
        if message.message_type == MessageType.NEGOTIATION:
            # 处理协商请求
            content = message.content
            proposal = content.get("proposal", {})
            # 简单的协商逻辑：评估提案并返回意见
            return {
                "status": "agree",
                "agreement": True,
                "feedback": {}
            }
        return super().handle_message(message)
    
    def run(self, input_text: str, max_tool_iterations: int = 3, **kwargs) -> str:
        """运行行程规划（增强版）"""
        # 在规划前，检查是否有足够的信息
        if self.context_manager:
            shared_data = self.context_manager.get_all_shared_data()
            
            # 如果信息不足，请求其他智能体提供
            if "attraction_locations" not in shared_data:
                logger.warning("景点信息不足，请求景点智能体提供")
                self.send_message_to_agent(
                    "景点搜索专家",
                    MessageType.REQUEST,
                    {"action": "provide_attractions"}
                )
            
            if "hotel_recommendations" not in shared_data:
                logger.warning("酒店信息不足，请求酒店智能体提供")
                self.send_message_to_agent(
                    "酒店推荐专家",
                    MessageType.REQUEST,
                    {"action": "provide_hotels"}
                )
        
        result = super().run(input_text, max_tool_iterations, **kwargs)
        
        # 规划完成后，存储记忆
        if self.user_id and self.context_manager:
            request_context = self.context_manager.get_shared_data("request")
            if request_context:
                self.store_memory(
                    "preference",
                    {
                        "preference_type": "trip_planning",
                        "destination": request_context.get("destination"),
                        "preferences": request_context.get("preferences", []),
                        "trip_result": result[:200]  # 存储部分结果作为参考
                    }
                )
        
        return result

