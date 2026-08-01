# -*- coding: utf-8 -*-
"""
HelloAgents 框架工具层：把高德数据能力封装为框架 Tool。

说明：
- 复用 date_planner.amap_client.AMapClient 作为数据层（Key 不落盘、异常脱敏）；
- 每个 Tool 继承 hello_agents.tools.base.Tool，实现 get_parameters / run；
- 返回统一 ToolResponse：success(text, data) / error(code, message)；
- 供上层 HelloAgentsLLM + ReActAgent 调用（见 demo_agent.py）。

用法：
    from date_planner.hello_tools import build_registry
    registry = build_registry()
    registry.list_tools()
"""
from typing import Any, Dict, List

from hello_agents.tools import Tool, ToolParameter, ToolResponse

from .amap_client import AMapClient, pretty_poi

__all__ = [
    "AMapTextSearchTool",
    "AMapDetailTool",
    "AMapDistanceTool",
    "AMapWeatherTool",
    "build_registry",
]


def _ensure_client(client):
    """工具调用前检查 client；未配置高德 Key 时返回错误响应。"""
    if client is None:
        return ToolResponse.error(
            code="NO_AMAP_KEY",
            message="未配置 AMAP_KEY：请在项目根 .env 或环境变量中设置高德 Web 服务 Key",
        )
    return None


class AMapTextSearchTool(Tool):
    """高德关键词搜索：按关键词 + 城市查找真实 POI（餐厅、活动、公园等）。"""

    def __init__(self, client: AMapClient = None):
        super().__init__(
            name="amap_text_search",
            description="按关键词和城市搜索真实地点（餐厅/展览/公园/咖啡/桌游等）。"
                        "返回候选列表：名称/地址/电话/人均/评分/坐标。",
        )
        self._client = client

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="keywords", type="string",
                          description="搜索关键词，如：西餐厅、桌游、猫咖", required=True),
            ToolParameter(name="city", type="string",
                          description="城市名，如：北京；可留空表示全国", required=False),
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        blocked = _ensure_client(self._client)
        if blocked:
            return blocked
        keywords = str(parameters.get("keywords", "")).strip()
        city = str(parameters.get("city", "")).strip()
        if not keywords:
            return ToolResponse.error(code="EMPTY_KEYWORDS", message="缺少 keywords 参数")
        try:
            pois = self._client.text_search(keywords, city=city)
        except Exception as e:  # noqa: BLE001
            return ToolResponse.error(code="AMAP_ERROR", message=str(e))
        if not pois:
            return ToolResponse.success(
                text=f"未找到「{keywords}」相关结果，请更换关键词或城市。", data={"count": 0},
            )
        lines = [pretty_poi(p, index=f"[{i}]") for i, p in enumerate(pois[:8], 1)]
        return ToolResponse.success(
            text="搜索结果（前{}条）：\n{}".format(min(len(pois), 8), "\n".join(lines)),
            data={"count": len(pois), "pois": pois[:8]},
        )


class AMapDetailTool(Tool):
    """POI 详情：地址 / 电话 / 营业时间 / 人均 / 评分。"""

    def __init__(self, client: AMapClient = None):
        super().__init__(
            name="amap_detail",
            description="查询某个地点(通过搜索得到的POI id)的详细信息：地址、电话、营业时间、人均、评分。",
        )
        self._client = client

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="poi_id", type="string",
                          description="POI id，来自 amap_text_search 返回结果", required=True),
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        blocked = _ensure_client(self._client)
        if blocked:
            return blocked
        poi_id = str(parameters.get("poi_id", "")).strip()
        if not poi_id:
            return ToolResponse.error(code="EMPTY_ID", message="缺少 poi_id 参数")
        try:
            d = self._client.detail(poi_id)
        except Exception as e:  # noqa: BLE001
            return ToolResponse.error(code="AMAP_ERROR", message=str(e))
        if not d:
            return ToolResponse.success(text="未查到该 POI 详情，请核实 poi_id。", data={})
        return ToolResponse.success(text=pretty_poi(d, index="[D]"), data={"poi": d})


class AMapDistanceTool(Tool):
    """两点之间距离与耗时：type=1驾车 / 2骑行 / 3步行。"""

    def __init__(self, client: AMapClient = None):
        super().__init__(
            name="amap_distance",
            description="计算两个坐标点之间的距离和预计耗时（驾车/骑行/步行），用于规划路线衔接。",
        )
        self._client = client

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="origins", type="string",
                          description="起点坐标，格式：经度,纬度", required=True),
            ToolParameter(name="destination", type="string",
                          description="终点坐标，格式：经度,纬度", required=True),
            ToolParameter(name="type", type="string",
                          description="1=驾车 2=骑行 3=步行（默认2）", required=False),
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        blocked = _ensure_client(self._client)
        if blocked:
            return blocked
        origins = str(parameters.get("origins", "")).strip()
        destination = str(parameters.get("destination", "")).strip()
        type_ = str(parameters.get("type", "2") or "2").strip()
        if not origins or not destination:
            return ToolResponse.error(code="EMPTY_COORD", message="缺少 origins 或 destination")
        try:
            r = self._client.distance(origins, destination, type_=type_)
        except Exception as e:  # noqa: BLE001
            return ToolResponse.error(code="AMAP_ERROR", message=str(e))
        if not r:
            return ToolResponse.success(text="距离计算失败，请核实坐标。", data={})
        return ToolResponse.success(
            text=f"距离 {r['km']} km，约 {r['min']} 分钟（type={type_}）", data=r,
        )


class AMapWeatherTool(Tool):
    """城市天气预报：当日/未来几天的天气、气温、风力。"""

    def __init__(self, client: AMapClient = None):
        super().__init__(
            name="amap_weather",
            description="查询指定城市的天气预报（未来几天）：天气、气温、风力，用于安排户外/室内活动。",
        )
        self._client = client

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="city", type="string",
                          description="城市名或adcode，如：北京", required=True),
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        blocked = _ensure_client(self._client)
        if blocked:
            return blocked
        city = str(parameters.get("city", "")).strip()
        if not city:
            return ToolResponse.error(code="EMPTY_CITY", message="缺少 city 参数")
        try:
            casts = self._client.weather(city)
        except Exception as e:  # noqa: BLE001
            return ToolResponse.error(code="AMAP_ERROR", message=str(e))
        if not casts:
            return ToolResponse.success(text="未获取到天气数据。", data={})
        lines = []
        for c in casts[:5]:
            lines.append(
                f"{c.get('date','')} {c.get('week','')} | {c.get('dayweather','?')}/"
                f"{c.get('nightweather','?')} | 白天{c.get('daytemp','?')}° "
                f"夜间{c.get('nighttemp','?')}° | {c.get('daywind','')}风{c.get('daypower','')}"
            )
        return ToolResponse.success(text="天气预报：\n" + "\n".join(lines), data={"casts": casts})


def build_registry(client: AMapClient = None):
    """创建 ToolRegistry 并注册全部高德工具（HelloAgents 框架用法）。

    未配置高德 Key 时仍可创建注册表（用于演示框架结构），
    工具调用时会返回 NO_AMAP_KEY 错误提示。
    """
    from hello_agents.tools import ToolRegistry

    if client is None:
        try:
            client = AMapClient()
        except ValueError:
            client = None
    registry = ToolRegistry()
    for tool in (
        AMapTextSearchTool(client),
        AMapDetailTool(client),
        AMapDistanceTool(client),
        AMapWeatherTool(client),
    ):
        registry.register_tool(tool)
    return registry
