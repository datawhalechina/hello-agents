"""多智能体旅行规划系统"""

import json
from typing import Dict, Any, List
from hello_agents import SimpleAgent
from .mcp_tool import MCPTool
from ..services.llm_service import get_llm
from ..services.amap_service import get_amap_service
from ..models.schemas import TripRequest, TripPlan, DayPlan, Attraction, Meal, WeatherInfo, Location, Hotel, TransportSegment
from ..config import get_settings

# ============ Agent提示词 ============

ATTRACTION_AGENT_PROMPT = """你是景点搜索专家。你的任务是根据城市和用户偏好搜索合适的景点。

**重要提示:**
你必须使用工具来搜索景点!不要自己编造景点信息!

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
"""

WEATHER_AGENT_PROMPT = """你是天气查询专家。你的任务是查询指定城市的天气信息。

**重要提示:**
你必须使用工具来查询天气!不要自己编造天气信息!

**工具调用格式:**
使用maps_weather工具时,必须严格按照以下格式:
`[TOOL_CALL:amap_maps_weather:city=城市名]`

**示例:**
用户: "查询北京天气"
你的回复: [TOOL_CALL:amap_maps_weather:city=北京]

用户: "上海的天气怎么样"
你的回复: [TOOL_CALL:amap_maps_weather:city=上海]

**注意:**
1. 必须使用工具,不要直接回答
2. 格式必须完全正确,包括方括号和冒号
"""

HOTEL_AGENT_PROMPT = """你是酒店推荐专家。你的任务是根据城市和景点位置推荐合适的酒店。

**重要提示:**
你必须使用工具来搜索酒店!不要自己编造酒店信息!

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
"""

PLANNER_AGENT_PROMPT = """你是行程规划专家。你的任务是根据景点信息、天气信息和出行人群,生成个性化的旅行计划。

请严格按照以下JSON格式返回旅行计划(**transportation_details字段由系统自动填充,你无需生成,但必须保证attractions和hotel的address字段真实准确**):
```json
{
  "city": "城市名称",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "description": "第1天行程概述",
      "transportation": "交通方式概览",
      "accommodation": "住宿类型",
      "hotel": {
        "name": "酒店名称",
        "address": "酒店地址",
        "location": {"longitude": 116.397128, "latitude": 39.916527},
        "price_range": "300-500元",
        "rating": "4.5",
        "distance": "距离景点2公里",
        "type": "经济型酒店",
        "estimated_cost": 400
      },
      "attractions": [
        {
          "name": "景点名称",
          "address": "详细地址",
          "location": {"longitude": 116.397128, "latitude": 39.916527},
          "visit_duration": 120,
          "description": "景点详细描述",
          "category": "景点类别",
          "ticket_price": 60
        }
      ],
      "meals": [
        {"type": "breakfast", "name": "早餐推荐", "description": "早餐描述", "estimated_cost": 30},
        {"type": "lunch", "name": "午餐推荐", "description": "午餐描述", "estimated_cost": 50},
        {"type": "dinner", "name": "晚餐推荐", "description": "晚餐描述", "estimated_cost": 80}
      ]
    }
  ],
  "weather_info": [
    {
      "date": "YYYY-MM-DD",
      "day_weather": "晴",
      "night_weather": "多云",
      "day_temp": 25,
      "night_temp": 15,
      "wind_direction": "南风",
      "wind_power": "1-3级"
    }
  ],
  "overall_suggestions": "总体建议",
  "budget": {
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }
}
```

**出行人群定制指南:**
根据不同的出行人群,调整行程安排风格:

- **独自旅行**: 推荐经济型住宿(青旅/青舍),安排社交友好型活动,景点紧凑高效,推荐当地特色小吃,控制预算
- **情侣夫妻**: 安排浪漫景点(日落观景台、情侣步道),推荐氛围好的餐厅,选择舒适型以上酒店,安排双人体验活动
- **朋友结伴**: 安排集体互动性强的活动,推荐娱乐项目,住宿可选多人间或民宿,餐饮推荐适合聚会的场所
- **家庭亲子**: 安排儿童友好的景点(科技馆、动物园、主题乐园),节奏要宽松,餐饮选择适合孩子的餐厅,住宿推荐家庭房
- **公司团建**: 安排团队协作活动,推荐大型场地,兼顾会议讨论空间与休闲娱乐,住宿可选度假型酒店
- **老年旅行**: 行程节奏舒缓,景点平坦少爬坡,步行距离短,推荐养生餐饮,住宿选择舒适型电梯房
- **研学旅行**: 安排博物馆、科技馆、历史文化遗址等教育性景点,每个景点预留充足学习时间,可安排讲解服务

**重要提示:**
1. weather_info数组必须包含每一天的天气信息
2. 温度必须是纯数字(不要带°C等单位)
3. 每天安排2-3个景点
4. 考虑景点之间的距离和游览时间
5. 每天必须包含早中晚三餐
6. 提供实用的旅行建议
7. 行程安排必须符合用户选择的"出行人群"类型
8. **必须包含预算信息**:
   - 景点门票价格(ticket_price)
   - 餐饮预估费用(estimated_cost)
   - 酒店预估费用(estimated_cost)
   - 预算汇总(budget)包含各项总费用
"""


class MultiAgentTripPlanner:
    """多智能体旅行规划系统"""

    def __init__(self):
        """初始化多智能体系统"""
        print("🔄 开始初始化多智能体旅行规划系统...")

        try:
            settings = get_settings()
            self.llm = get_llm()

            # 创建共享的MCP工具(只创建一次)
            print("  - 创建共享MCP工具...")
            self.amap_tool = MCPTool(
                name="amap",
                description="高德地图服务",
                server_command=["uvx", "amap-mcp-server"],
                env={"AMAP_MAPS_API_KEY": settings.amap_api_key},
                auto_expand=True
            )

            # 创建景点搜索Agent
            print("  - 创建景点搜索Agent...")
            self.attraction_agent = SimpleAgent(
                name="景点搜索专家",
                llm=self.llm,
                system_prompt=ATTRACTION_AGENT_PROMPT
            )
            self.attraction_agent.add_tool(self.amap_tool)

            # 创建天气查询Agent
            print("  - 创建天气查询Agent...")
            self.weather_agent = SimpleAgent(
                name="天气查询专家",
                llm=self.llm,
                system_prompt=WEATHER_AGENT_PROMPT
            )
            self.weather_agent.add_tool(self.amap_tool)

            # 创建酒店推荐Agent
            print("  - 创建酒店推荐Agent...")
            self.hotel_agent = SimpleAgent(
                name="酒店推荐专家",
                llm=self.llm,
                system_prompt=HOTEL_AGENT_PROMPT
            )
            self.hotel_agent.add_tool(self.amap_tool)

            # 创建行程规划Agent(不需要工具)
            print("  - 创建行程规划Agent...")
            self.planner_agent = SimpleAgent(
                name="行程规划专家",
                llm=self.llm,
                system_prompt=PLANNER_AGENT_PROMPT
            )

            print(f"✅ 多智能体系统初始化成功")
            print(f"   景点搜索Agent: {len(self.attraction_agent.list_tools())} 个工具")
            print(f"   天气查询Agent: {len(self.weather_agent.list_tools())} 个工具")
            print(f"   酒店推荐Agent: {len(self.hotel_agent.list_tools())} 个工具")

        except Exception as e:
            print(f"❌ 多智能体系统初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def plan_trip(self, request: TripRequest) -> TripPlan:
        """
        使用多智能体协作生成旅行计划

        Args:
            request: 旅行请求

        Returns:
            旅行计划
        """
        try:
            print(f"\n{'='*60}")
            print(f"🚀 开始多智能体协作规划旅行...")
            print(f"目的地: {request.city}")
            print(f"日期: {request.start_date} 至 {request.end_date}")
            print(f"天数: {request.travel_days}天")
            print(f"偏好: {', '.join(request.preferences) if request.preferences else '无'}")
            print(f"出行人群: {request.traveler_group if request.traveler_group else '未指定'}")
            print(f"{'='*60}\n")

            # 步骤1: 景点搜索Agent搜索景点
            print("📍 步骤1: 搜索景点...")
            attraction_query = self._build_attraction_query(request)
            attraction_response = self.attraction_agent.run(attraction_query)
            print(f"景点搜索结果: {attraction_response[:200]}...\n")

            # 步骤2: 天气查询Agent查询天气
            print("🌤️  步骤2: 查询天气...")
            weather_query = f"请查询{request.city}的天气信息"
            weather_response = self.weather_agent.run(weather_query)
            print(f"天气查询结果: {weather_response[:200]}...\n")

            # 步骤3: 酒店推荐Agent搜索酒店
            print("🏨 步骤3: 搜索酒店...")
            hotel_query = f"请搜索{request.city}的{request.accommodation}酒店"
            hotel_response = self.hotel_agent.run(hotel_query)
            print(f"酒店搜索结果: {hotel_response[:200]}...\n")

            # 步骤4: 行程规划Agent整合信息生成计划
            print("📋 步骤4: 生成行程计划...")
            planner_query = self._build_planner_query(request, attraction_response, weather_response, hotel_response)
            planner_response = self.planner_agent.run(planner_query)
            print(f"行程规划结果: {planner_response[:300]}...\n")

            # 解析最终计划
            trip_plan = self._parse_response(planner_response, request)

            # 步骤5: 调用高德地图MCP获取真实交通路线数据
            print("🚗 步骤5: 获取真实交通路线数据...")
            trip_plan = self._enrich_with_real_routes(trip_plan, request)
            print(f"交通路线获取完成\n")

            print(f"{'='*60}")
            print(f"✅ 旅行计划生成完成!")
            print(f"{'='*60}\n")

            return trip_plan

        except Exception as e:
            print(f"❌ 生成旅行计划失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_plan(request)
    
    def _build_attraction_query(self, request: TripRequest) -> str:
        """构建景点搜索查询 - 直接包含工具调用"""
        keywords = []
        if request.preferences:
            # 如果用户有明确的偏好,使用偏好标签作为关键词
            keywords = request.preferences
        else:
            keywords = "景点"

        # 根据出行人群调整搜索关键词
        group_keywords = {
            "独自旅行": "景点",
            "情侣夫妻": "浪漫景点",
            "朋友结伴": "热门景点",
            "家庭亲子": "亲子景点",
            "公司团建": "景点",
            "老年旅行": "公园",
            "研学旅行": "博物馆"
        }
        if request.traveler_group and request.traveler_group in group_keywords:
            # 如果用户没有明确偏好,使用人群推荐的关键词
            if not request.preferences:
                keywords = group_keywords[request.traveler_group]

        # 直接返回工具调用格式
        query = f"请使用amap_maps_text_search工具搜索{request.city}与{keywords}相关的景点。\n[TOOL_CALL:amap_maps_text_search:keywords={keywords},city={request.city}]"
        return query

    def _build_planner_query(self, request: TripRequest, attractions: str, weather: str, hotels: str = "") -> str:
        """构建行程规划查询"""
        # 出行人群定制指导
        group_guidance = {
            "独自旅行": "该用户是独自旅行:\n- 推荐经济型住宿(青旅/青舍),安排社交友好型活动\n- 景点紧凑高效,推荐当地特色小吃\n- 控制预算,推荐性价比高的选择",
            "情侣夫妻": "该用户是情侣/夫妻出行:\n- 安排浪漫景点(日落观景台、情侣步道等)\n- 推荐氛围好的餐厅,选择舒适型以上酒店\n- 安排双人体验活动,注重私密性和舒适度",
            "朋友结伴": "该用户是朋友结伴出行:\n- 安排集体互动性强的活动,推荐娱乐项目\n- 住宿可选多人间或民宿\n- 餐饮推荐适合聚会的场所,推荐热闹区域",
            "家庭亲子": "该用户是家庭亲子出行(有儿童):\n- 安排儿童友好的景点(科技馆、动物园、主题乐园)\n- 行程节奏要宽松,避免安排过满\n- 餐饮选择适合孩子的餐厅,住宿推荐家庭房",
            "公司团建": "该用户是公司团建:\n- 安排团队协作活动,推荐大型场地\n- 兼顾会议讨论空间与休闲娱乐\n- 住宿可选度假型酒店,推荐集体用餐",
            "老年旅行": "该用户是老年旅行:\n- 行程节奏舒缓,景点平坦少爬坡\n- 步行距离短,每个景点预留充足休息时间\n- 推荐养生餐饮,住宿选择舒适型电梯房",
            "研学旅行": "该用户是研学旅行:\n- 安排博物馆、科技馆、历史文化遗址等教育性景点\n- 每个景点预留充足学习时间\n- 可安排讲解服务,注重知识性"
        }

        traveler_note = ""
        if request.traveler_group and request.traveler_group in group_guidance:
            traveler_note = f"\n**出行人群:** {request.traveler_group}\n{group_guidance[request.traveler_group]}\n"

        query = f"""请根据以下信息生成{request.city}的{request.travel_days}天旅行计划:

**基本信息:**
- 城市: {request.city}
- 日期: {request.start_date} 至 {request.end_date}
- 天数: {request.travel_days}天
- 交通方式: {request.transportation}
- 住宿: {request.accommodation}
- 偏好: {', '.join(request.preferences) if request.preferences else '无'}
{traveler_note}
**景点信息:**
{attractions}

**天气信息:**
{weather}

**酒店信息:**
{hotels}

**要求:**
1. 每天安排2-3个景点
2. 每天必须包含早中晚三餐
3. 每天推荐一个具体的酒店(从酒店信息中选择)
3. 考虑景点之间的距离和交通方式(仅填写transportation概览字段即可)
4. 返回完整的JSON格式数据
5. 景点的经纬度坐标和地址(address)要真实准确
6. 行程安排必须充分考虑"出行人群"的特点
"""
        if request.free_text_input:
            query += f"\n**额外要求:** {request.free_text_input}"

        return query

    def _enrich_with_real_routes(self, plan: TripPlan, request: TripRequest) -> TripPlan:
        """调用高德地图MCP获取真实交通数据,填充transportation_details"""
        try:
            amap = get_amap_service()
            city = request.city

            # 用户交通方式 → MCP route_type 映射
            route_type_map = {
                "公共交通": "transit",
                "自驾": "driving",
                "步行": "walking",
                "混合": "transit",  # 默认用公共交通
            }
            route_type = route_type_map.get(request.transportation, "transit")
            type_label = {
                "transit": "公共交通",
                "driving": "自驾",
                "walking": "步行",
            }

            for day in plan.days:
                details = []
                waypoints = []  # (name, address)

                # 起点: 酒店(如果有地址)
                if day.hotel and day.hotel.address:
                    waypoints.append((day.hotel.name, day.hotel.address))
                elif day.hotel and day.hotel.location:
                    waypoints.append((day.hotel.name, f"{city}市"))
                else:
                    waypoints.append(("酒店", f"{city}市区"))

                # 中间点: 景点
                for attr in day.attractions:
                    addr = attr.address or f"{city}市"
                    waypoints.append((attr.name, addr))

                # 终点: 回酒店(如果酒店在起点后有地址)
                if day.hotel and day.hotel.address and len(waypoints) > 1:
                    waypoints.append((day.hotel.name, day.hotel.address))

                # 逐个分段调MCP(带降级重试)
                total_duration = 0
                total_distance = 0
                had_fallback = False
                for i in range(len(waypoints) - 1):
                    from_name, from_addr = waypoints[i]
                    to_name, to_addr = waypoints[i + 1]

                    # 按优先级尝试路线类型
                    route_types_to_try = [route_type]
                    if route_type == "transit":
                        route_types_to_try = ["transit", "driving"]
                    elif route_type == "driving":
                        route_types_to_try = ["driving", "transit"]

                    segments = []
                    attempted_types = []
                    success_type = None
                    for try_route_type in route_types_to_try:
                        attempted_types.append(try_route_type)
                        segments = amap.get_route_via_http(
                            origin_address=from_addr,
                            destination_address=to_addr,
                            origin_name=from_name,
                            destination_name=to_name,
                            origin_city=city,
                            destination_city=city,
                            route_type=try_route_type
                        )
                        if segments:
                            success_type = try_route_type
                            break

                    is_fallback = success_type and success_type != route_type

                    if segments:
                        for seg in segments:
                            seg_from = from_name if not details else seg.get("from_name", from_name)
                            seg_to = to_name if i == len(waypoints) - 2 else seg.get("to_name", to_name)
                            seg["from_name"] = seg_from
                            seg["to_name"] = seg_to

                            # 处理回退: 用户选公交但用了驾车数据
                            if is_fallback:
                                had_fallback = True
                                seg["type"] = type_label.get(route_type, "公共交通")
                                seg["route_detail"] = (seg.get("route_detail", "") + " · 驾车参考").strip(" ·")
                                if "驾车" not in seg.get("instruction", ""):
                                    seg["instruction"] += "（驾车参考路线）"

                            details.append(seg)
                            total_duration += seg.get("duration", 0)
                            total_distance += seg.get("distance", 0)
                    else:
                        # 所有API都失败,尝试LLM估计路线
                        llm_segments = self._estimate_routes_with_llm(
                            from_name=from_name,
                            to_name=to_name,
                            city=city,
                            route_type_label=type_label.get(route_type, "公共交通")
                        )
                        if llm_segments:
                            for seg in llm_segments:
                                seg["from_name"] = from_name
                                seg["to_name"] = to_name
                                details.append(seg)
                                total_duration += seg.get("duration", 0)
                                total_distance += seg.get("distance", 0)
                        else:
                            # LLM也失败,生成占位段
                            road_type_cn = type_label.get(route_type, "公共交通")
                            details.append({
                                "type": road_type_cn,
                                "instruction": f"从{from_name}前往{to_name}",
                                "from_name": from_name,
                                "to_name": to_name,
                                "departure_time": "08:00",
                                "duration": 30,
                                "distance": 2000,
                                "route_detail": "路线规划暂不可用",
                            })
                            total_duration += 30
                        total_distance += 2000

                # 回填详细交通数据到DayPlan(dict -> TransportSegment)
                day.transportation_details = [
                    TransportSegment(**seg) for seg in details
                ]

                # 更新概要transportation字段
                if total_duration > 0:
                    road_type_cn = type_label.get(route_type, "公共交通")
                    dist_km = round(total_distance / 1000, 1)
                    fallback_note = "（部分路段为驾车参考）" if had_fallback else ""
                    day.transportation = f"{road_type_cn} · 共{dist_km}公里 · 约{total_duration}分钟{fallback_note}"

                print(f"  ✅ 第{day.day_index + 1}天交通: {len(details)}段, {day.transportation}")

        except Exception as e:
            print(f"⚠️ 获取真实路线数据失败: {e}")

        return plan

    def _estimate_routes_with_llm(
        self,
        from_name: str,
        to_name: str,
        city: str,
        route_type_label: str = "公共交通"
    ) -> List[Dict]:
        """当高德API路线获取失败时,用LLM估计交通路线"""
        prompt = f"""请估计从"{from_name}"到"{to_name}"（位于{city}）的{route_type_label}路线。

根据你对{city}的了解，生成合理的路线分段信息。只返回JSON数组，不要其他文字：
[
  {{
    "type": "步行/公交/地铁",
    "instruction": "具体乘坐指引（如'乘坐1路公交车从火车站到市中心'）",
    "from_name": "起点站名或地点",
    "to_name": "终点站名或地点",
    "duration": 15,
    "distance": 2000,
    "route_detail": "线路详情（如'经过5站'或'约2公里'）"
  }}
]

要求：
1. type取值 "步行"/"公交"/"地铁"，可组合多个分段
2. duration单位分钟，distance单位米，数值要合理
3. 根据{city}实际公交/地铁线路命名习惯来写
4. 仅返回JSON数组，不要markdown标记"""
        try:
            from hello_agents import SimpleAgent
            estimator = SimpleAgent(
                name="route_estimator",
                llm=self.llm,
                system_prompt="你是城市交通专家，根据起点终点和城市信息合理估计路线。只返回JSON。"
            )
            response = estimator.run(prompt)

            # 提取JSON
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            import re
            match = re.search(r'\[.*?\]', json_str, re.DOTALL)
            if match:
                data = json.loads(match.group())
                if isinstance(data, list):
                    print(f"  ✅ LLM路线估计成功: {len(data)}段")
                    return data
        except Exception as e:
            print(f"  ⚠️ LLM路线估计失败: {e}")
        return []

    def _parse_response(self, response: str, request: TripRequest) -> TripPlan:
        """
        解析Agent响应
        
        Args:
            response: Agent响应文本
            request: 原始请求
            
        Returns:
            旅行计划
        """
        try:
            # 尝试从响应中提取JSON
            # 查找JSON代码块
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "{" in response and "}" in response:
                # 直接查找JSON对象
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            else:
                raise ValueError("响应中未找到JSON数据")
            
            # 解析JSON
            data = json.loads(json_str)
            
            # 转换为TripPlan对象
            trip_plan = TripPlan(**data)
            
            return trip_plan
            
        except Exception as e:
            print(f"⚠️  解析响应失败: {str(e)}")
            print(f"   将使用备用方案生成计划")
            return self._create_fallback_plan(request)
    
    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        """创建备用计划(当Agent失败时)"""
        from datetime import datetime, timedelta

        # 解析日期
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")

        # 出行人群描述
        group_desc = {
            "独自旅行": "适合独自旅行者",
            "情侣夫妻": "适合情侣/夫妻浪漫之旅",
            "朋友结伴": "适合朋友结伴游玩",
            "家庭亲子": "适合家庭亲子活动",
            "公司团建": "适合公司团建活动",
            "老年旅行": "适合老年休闲之旅",
            "研学旅行": "适合研学教育之旅"
        }
        traveler_desc = group_desc.get(request.traveler_group, "")

        # 创建每日行程
        days = []
        for i in range(request.travel_days):
            current_date = start_date + timedelta(days=i)

            group_note = f"({traveler_desc}) " if traveler_desc else ""
            day_plan = DayPlan(
                date=current_date.strftime("%Y-%m-%d"),
                day_index=i,
                description=f"第{i+1}天行程{group_note}- 探索{request.city}",
                transportation=request.transportation,
                accommodation=request.accommodation,
                attractions=[
                    Attraction(
                        name=f"{request.city}景点{j+1}",
                        address=f"{request.city}市",
                        location=Location(longitude=116.4 + i*0.01 + j*0.005, latitude=39.9 + i*0.01 + j*0.005),
                        visit_duration=120,
                        description=f"这是{request.city}的著名景点",
                        category="景点"
                    )
                    for j in range(2)
                ],
                meals=[
                    Meal(type="breakfast", name=f"第{i+1}天早餐", description="当地特色早餐"),
                    Meal(type="lunch", name=f"第{i+1}天午餐", description="午餐推荐"),
                    Meal(type="dinner", name=f"第{i+1}天晚餐", description="晚餐推荐")
                ]
            )
            days.append(day_plan)
        
        return TripPlan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=days,
            weather_info=[],
            overall_suggestions=f"这是为您规划的{request.city}{request.travel_days}日游行程{'(适合' + traveler_desc + ')' if traveler_desc else ''}。建议提前查看各景点的开放时间。"
        )


# 全局多智能体系统实例
_multi_agent_planner = None


def get_trip_planner_agent() -> MultiAgentTripPlanner:
    """获取多智能体旅行规划系统实例(单例模式)"""
    global _multi_agent_planner

    if _multi_agent_planner is None:
        _multi_agent_planner = MultiAgentTripPlanner()

    return _multi_agent_planner

