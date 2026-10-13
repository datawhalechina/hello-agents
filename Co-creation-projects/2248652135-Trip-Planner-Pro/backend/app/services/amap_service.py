"""高德地图MCP服务封装"""

import json
import re
from typing import List, Dict, Any, Optional
from ..agents.mcp_tool import MCPTool
from ..config import get_settings
from ..models.schemas import Location, POIInfo, WeatherInfo

# 全局MCP工具实例
_amap_mcp_tool = None


def get_amap_mcp_tool() -> MCPTool:
    """
    获取高德地图MCP工具实例(单例模式)

    Returns:
        MCPTool实例
    """
    global _amap_mcp_tool

    if _amap_mcp_tool is None:
        settings = get_settings()

        if not settings.amap_api_key:
            raise ValueError("高德地图API Key未配置,请在.env文件中设置AMAP_API_KEY")

        # 创建MCP工具
        _amap_mcp_tool = MCPTool(
            name="amap",
            description="高德地图服务,支持POI搜索、路线规划、天气查询等功能",
            server_command=["uvx", "amap-mcp-server"],
            env={"AMAP_MAPS_API_KEY": settings.amap_api_key},
            auto_expand=True  # 自动展开为独立工具
        )

        print(f"✅ 高德地图MCP工具初始化成功")
        print(f"   工具数量: {len(_amap_mcp_tool._available_tools)}")

        # 打印可用工具列表
        if _amap_mcp_tool._available_tools:
            print("   可用工具:")
            for tool in _amap_mcp_tool._available_tools[:5]:  # 只打印前5个
                print(f"     - {tool.get('name', 'unknown')}")
            if len(_amap_mcp_tool._available_tools) > 5:
                print(f"     ... 还有 {len(_amap_mcp_tool._available_tools) - 5} 个工具")

    return _amap_mcp_tool


class AmapService:
    """高德地图服务封装类"""

    def __init__(self):
        """初始化服务"""
        self.mcp_tool = get_amap_mcp_tool()

    def search_poi(self, keywords: str, city: str, citylimit: bool = True) -> List[POIInfo]:
        """
        搜索POI
        """
        try:
            result = self.mcp_tool.run({
                "action": "call_tool",
                "tool_name": "maps_text_search",
                "arguments": {
                    "keywords": keywords,
                    "city": city,
                    "citylimit": str(citylimit).lower()
                }
            })

            # 从 MCP 返回文本中提取 JSON
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if not json_match:
                return []

            data = json.loads(json_match.group())
            pois_data = data.get("pois", [])

            pois = []
            for p in pois_data:
                loc = None
                location_str = p.get("location", "")
                if location_str and isinstance(location_str, str) and "," in location_str:
                    try:
                        lng, lat = location_str.split(",")
                        loc = Location(longitude=float(lng), latitude=float(lat))
                    except (ValueError, TypeError):
                        pass

                pois.append(POIInfo(
                    id=p.get("id", ""),
                    name=p.get("name", ""),
                    type=p.get("typecode", p.get("type", "")),
                    address=p.get("address", ""),
                    location=loc or Location(longitude=116.4, latitude=39.9),
                    tel=p.get("tel")
                ))

            print(f"  ✅ POI搜索成功: {len(pois)} 条结果")
            return pois

        except Exception as e:
            print(f"❌ POI搜索失败: {str(e)}")
            return []

    def get_weather(self, city: str) -> List[WeatherInfo]:
        """
        查询天气
        """
        try:
            result = self.mcp_tool.run({
                "action": "call_tool",
                "tool_name": "maps_weather",
                "arguments": {
                    "city": city
                }
            })

            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if not json_match:
                return []

            data = json.loads(json_match.group())
            # 高德天气返回 forecast 格式
            forecasts = data.get("forecasts", [])

            weather_list = []
            for w in forecasts:
                weather_list.append(WeatherInfo(
                    date=w.get("date", ""),
                    day_weather=w.get("dayweather", ""),
                    night_weather=w.get("nightweather", ""),
                    day_temp=w.get("daytemp", w.get("daytemp_float", 0)),
                    night_temp=w.get("nighttemp", w.get("nighttemp_float", 0)),
                    wind_direction=w.get("daywind", ""),
                    wind_power=w.get("daypower", "")
                ))

            print(f"  ✅ 天气查询成功: {len(weather_list)} 条记录")
            return weather_list

        except Exception as e:
            print(f"❌ 天气查询失败: {str(e)}")
            return []

    def plan_route(
        self,
        origin_address: str,
        destination_address: str,
        origin_city: Optional[str] = None,
        destination_city: Optional[str] = None,
        route_type: str = "walking"
    ) -> Dict[str, Any]:
        """
        规划路线,调用高德地图MCP获取真实路线数据

        Args:
            origin_address: 起点地址
            destination_address: 终点地址
            origin_city: 起点城市
            destination_city: 终点城市
            route_type: 路线类型 (walking/driving/transit)

        Returns:
            路线信息字典,包含 distance(米)、duration(秒)、type、segments
        """
        try:
            tool_map = {
                "walking": "maps_direction_walking_by_address",
                "driving": "maps_direction_driving_by_address",
                "transit": "maps_direction_transit_integrated_by_address"
            }
            tool_name = tool_map.get(route_type, "maps_direction_walking_by_address")

            arguments = {
                "origin_address": origin_address,
                "destination_address": destination_address
            }
            if origin_city:
                arguments["origin_city"] = origin_city
            if destination_city:
                arguments["destination_city"] = destination_city

            result = self.mcp_tool.run({
                "action": "call_tool",
                "tool_name": tool_name,
                "arguments": arguments
            })

            parsed = self._parse_route_response(result, route_type)
            if not parsed:
                print(f"  ⚠️ 路线({route_type})返回空: {result[:150]}")
            else:
                print(f"  ✅ 路线({route_type})成功: {parsed.get('distance',0)}m, {parsed.get('duration',0)}s")
            return parsed

        except Exception as e:
            print(f"❌ 路线规划失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}

    def _parse_python_repr(self, text: str) -> Optional[Dict]:
        """amap-mcp-server 返回的是 Python repr(单引号),尝试解析"""
        import ast
        try:
            result = ast.literal_eval(text)
            if isinstance(result, dict):
                # 递归将键名统一为str
                return json.loads(json.dumps(result))
            return None
        except Exception:
            return None

    def _parse_route_response(self, result: str, route_type: str) -> Dict[str, Any]:
        """解析MCP路线返回结果为统一格式"""
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if not json_match:
            return {}

        raw_text = json_match.group()
        data = None
        # 先尝试标准 JSON
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            # 再尝试 Python repr (单引号)
            data = self._parse_python_repr(raw_text)

        if not data:
            print(f"  ⚠️ 无法解析路线返回数据, 前100字符: {raw_text[:100]}")
            return {}

        route = data.get("route", data)
        info = {"distance": 0, "duration": 0, "type": route_type, "segments": []}

        if route_type == "transit":
            transits = route.get("transits", [])
            if transits:
                transit = transits[0]
                info["duration"] = self._safe_int(
                    transit.get("cost", {}).get("duration", "0")
                )
                for seg in transit.get("segments", []):
                    info["segments"].extend(
                        self._parse_transit_segment(seg)
                    )
        else:
            paths = route.get("paths", [])
            if paths:
                path = paths[0]
                info["distance"] = self._safe_int(path.get("distance", "0"))
                info["duration"] = self._safe_int(path.get("duration", "0"))
                steps = path.get("steps", [])
                for step in steps:
                    info["segments"].append({
                        "instruction": step.get("instruction", ""),
                        "distance": self._safe_int(step.get("distance", "0")),
                        "duration": self._safe_int(step.get("duration", "0")),
                    })
                if not steps:
                    info["segments"].append({
                        "instruction": f"从起点到终点",
                        "distance": info["distance"],
                        "duration": info["duration"],
                    })

        return info

    def _parse_transit_segment(self, seg: Dict) -> List[Dict]:
        """解析公共交通的一个分段"""
        segments = []
        if "walking" in seg:
            walk = seg["walking"]
            instr = "步行"
            if walk.get("steps"):
                instr = walk["steps"][0].get("instruction", "步行")
            segments.append({
                "instruction": instr,
                "distance": self._safe_int(walk.get("distance", "0")),
                "duration": self._safe_int(walk.get("duration", "0")),
            })
        if "bus" in seg:
            bus = seg["bus"]
            buslines = bus.get("buslines", [])
            if buslines:
                bl = buslines[0]
                segments.append(self._make_vehicle_segment(bl, "公交"))
        if "subway" in seg:
            subway = seg["subway"]
            subwaylines = subway.get("subwaylines", [])
            if subwaylines:
                sl = subwaylines[0]
                segments.append(self._make_vehicle_segment(sl, "地铁"))
        return segments

    def _make_vehicle_segment(self, line: Dict, mode: str) -> Dict:
        """生成交通工具分段"""
        pass_num = line.get("pass_stop_num", "0")
        return {
            "instruction": f"乘坐{line.get('name', mode)}",
            "distance": self._safe_int(line.get("distance", "0")),
            "duration": self._safe_int(line.get("duration", "0")),
            "route_detail": f"经过{pass_num}站",
            "departure_stop": line.get("departure_stop", {}).get("name", ""),
            "arrival_stop": line.get("arrival_stop", {}).get("name", ""),
        }

    @staticmethod
    def _safe_int(value: Any) -> int:
        """安全转int"""
        if isinstance(value, (int, float)):
            return int(value)
        try:
            return int(float(str(value).replace(",", "")))
        except (ValueError, TypeError):
            return 0

    def get_route_segments(
        self,
        origin_address: str,
        destination_address: str,
        origin_name: str = "",
        destination_name: str = "",
        origin_city: Optional[str] = None,
        destination_city: Optional[str] = None,
        route_type: str = "transit"
    ) -> List[Dict]:
        """
        获取两点之间的交通分段信息,格式化为TransportSegment兼容的字典

        Args:
            origin_address: 起点地址
            destination_address: 终点地址
            origin_name: 起点名称(如酒店名/景点名)
            destination_name: 终点名称
            origin_city: 起点城市
            destination_city: 终点城市
            route_type: walking/driving/transit

        Returns:
            List[Dict], 每段包含 type/instruction/from_name/to_name/duration/distance/route_detail
        """
        raw = self.plan_route(
            origin_address=origin_address,
            destination_address=destination_address,
            origin_city=origin_city,
            destination_city=destination_city,
            route_type=route_type
        )
        if not raw:
            return []

        type_map = {
            "walking": "步行",
            "driving": "自驾",
            "transit": "公共交通",
        }
        segments = raw.get("segments", [])
        result = []
        base_minutes = 0

        if not segments and raw.get("distance", 0) > 0:
            total_dist = raw.get("distance", 0)
            total_dur = max(1, raw.get("duration", 0) // 60)
            hour = 8 + base_minutes // 60
            minute = base_minutes % 60

            route_type_cn = type_map.get(route_type, "公共交通")
            result.append({
                "type": route_type_cn,
                "instruction": f"从{origin_name or origin_address}前往{destination_name or destination_address}",
                "from_name": origin_name or origin_address,
                "to_name": destination_name or destination_address,
                "departure_time": f"{hour:02d}:{minute:02d}",
                "duration": total_dur,
                "distance": total_dist,
                "route_detail": f"总距离约{round(total_dist / 1000, 1)}公里" if total_dist >= 1000 else f"总距离{total_dist}米",
            })
        else:
            for seg in segments:
                dur_min = max(1, seg.get("duration", 0) // 60)
                dist = seg.get("distance", 0)
                current_minutes = base_minutes
                hour = 8 + current_minutes // 60
                minute = current_minutes % 60

                instruction = seg.get("instruction", "")
                route_detail = seg.get("route_detail", "")

                # 判断交通类型
                instr_lower = instruction.lower()
                if "步行" in instruction or route_type == "walking":
                    seg_type = "步行"
                elif "公交" in instruction or "bus" in instr_lower:
                    seg_type = "公交"
                elif "地铁" in instruction or "subway" in instr_lower:
                    seg_type = "地铁"
                elif route_type == "driving":
                    seg_type = "自驾"
                else:
                    seg_type = "公共交通"

                dep_stop = seg.get("departure_stop", "")
                arr_stop = seg.get("arrival_stop", "")
                full_instruction = instruction
                if dep_stop and arr_stop:
                    full_instruction = f"从{dep_stop}出发,{instruction}到{arr_stop}"

                # 起点/终点名称
                seg_from = origin_name
                if result:
                    seg_from = dep_stop or origin_name
                seg_to = destination_name
                if seg != segments[-1]:
                    seg_to = arr_stop or destination_name

                result.append({
                    "type": seg_type,
                    "instruction": full_instruction,
                    "from_name": seg_from,
                    "to_name": seg_to,
                    "departure_time": f"{hour:02d}:{minute:02d}",
                    "duration": dur_min,
                    "distance": dist,
                    "route_detail": route_detail or (f"约{dist}米" if dist else ""),
                })

                base_minutes += dur_min

        return result

    def get_route_via_http(
        self,
        origin_address: str,
        destination_address: str,
        origin_name: str = "",
        destination_name: str = "",
        origin_city: Optional[str] = None,
        destination_city: Optional[str] = None,
        route_type: str = "transit"
    ) -> List[Dict]:
        """
        通过高德HTTP API直接获取路线(绕过MCP子进程,更快更稳定)

        Returns:
            List[Dict], 同 get_route_segments 格式
        """
        import urllib.request, urllib.parse
        from ..config import get_settings

        settings = get_settings()
        if not settings.amap_api_key:
            return []

        city = origin_city or ""

        # origin/destination 先尝试地理编码
        origin_lng, origin_lat = self._geocode_sync(origin_address, city)
        dest_lng, dest_lat = self._geocode_sync(destination_address, city)
        if not origin_lng or not dest_lng:
            return []

        try:
            if route_type == "transit":
                params = urllib.parse.urlencode({
                    "key": settings.amap_api_key,
                    "origin": f"{origin_lng},{origin_lat}",
                    "destination": f"{dest_lng},{dest_lat}",
                    "city": city,
                    "cityd": city,
                }, encoding="utf-8")
                url = f"https://restapi.amap.com/v3/direction/transit/integrated?{params}"
            elif route_type == "walking":
                params = urllib.parse.urlencode({
                    "key": settings.amap_api_key,
                    "origin": f"{origin_lng},{origin_lat}",
                    "destination": f"{dest_lng},{dest_lat}",
                }, encoding="utf-8")
                url = f"https://restapi.amap.com/v3/direction/walking?{params}"
            elif route_type == "driving":
                params = urllib.parse.urlencode({
                    "key": settings.amap_api_key,
                    "origin": f"{origin_lng},{origin_lat}",
                    "destination": f"{dest_lng},{dest_lat}",
                    "city": city,
                }, encoding="utf-8")
                url = f"https://restapi.amap.com/v3/direction/driving?{params}"
            else:
                return []

            resp = urllib.request.urlopen(url, timeout=10)
            data = json.loads(resp.read().decode("utf-8"))

            if data.get("status") != "1":
                return []

            segments = []
            base_minutes = 0

            if route_type == "transit":
                route = data.get("route", {})
                transits = route.get("transits", [])
                if not transits:
                    return []
                transit = transits[0]
                total_dur = self._safe_int(transit.get("duration", "0"))
                total_dist = self._safe_int(transit.get("distance", "0"))

                # 预检: 如果只有步行段且总距离>500m,返回空让调用者降级
                has_vehicle = any("bus" in seg or "subway" in seg for seg in transit.get("segments", []))
                total_walk_dist = sum(
                    self._safe_int(seg["walking"].get("distance", "0"))
                    for seg in transit.get("segments", []) if "walking" in seg
                )
                if not has_vehicle and total_walk_dist > 500:
                    return []  # 全程步行且距离过长,触发调用方降级

                for seg in transit.get("segments", []):
                    dur_min = max(1, self._safe_int(seg.get("duration", "0")) // 60)
                    dist = self._safe_int(seg.get("distance", "0"))
                    hour = 8 + base_minutes // 60
                    minute = base_minutes % 60

                    if "walking" in seg:
                        walk = seg["walking"]
                        walk_dist = self._safe_int(walk.get("distance", "0"))
                        walk_dur = max(1, self._safe_int(walk.get("duration", "0")) // 60)
                        instruction = f"步行{walk_dist}米"
                        if walk_dist > 500 and has_vehicle:
                            instruction += "(步行距离较长,建议共享单车)"
                        elif walk_dist > 500:
                            instruction += "(距离较长,建议乘车)"
                        segments.append({
                            "type": "步行",
                            "instruction": instruction,
                            "from_name": origin_name if not segments else origin_name,
                            "to_name": destination_name,
                            "departure_time": f"{hour:02d}:{minute:02d}",
                            "duration": walk_dur,
                            "distance": walk_dist,
                            "route_detail": f"步行{walk_dist}米",
                        })
                    elif "bus" in seg:
                        for bl in seg["bus"].get("buslines", []):
                            dep_stop = bl.get("departure_stop", {}).get("name", "")
                            arr_stop = bl.get("arrival_stop", {}).get("name", "")
                            pass_num = bl.get("pass_stop_num", "0")
                            segments.append({
                                "type": "公交",
                                "instruction": f"乘坐{bl.get('name', '公交')}",
                                "from_name": f"{dep_stop}" if dep_stop else origin_name,
                                "to_name": f"{arr_stop}" if arr_stop else destination_name,
                                "departure_time": f"{hour:02d}:{minute:02d}",
                                "duration": max(1, self._safe_int(bl.get("duration", "0")) // 60),
                                "distance": self._safe_int(bl.get("distance", "0")),
                                "route_detail": f"{bl.get('name', '')}·经过{pass_num}站",
                            })
                    elif "subway" in seg:
                        for sl in seg["subway"].get("subwaylines", []):
                            dep_stop = sl.get("departure_stop", {}).get("name", "")
                            arr_stop = sl.get("arrival_stop", {}).get("name", "")
                            pass_num = sl.get("pass_stop_num", "0")
                            segments.append({
                                "type": "地铁",
                                "instruction": f"乘坐{sl.get('name', '地铁')}",
                                "from_name": f"{dep_stop}" if dep_stop else origin_name,
                                "to_name": f"{arr_stop}" if arr_stop else destination_name,
                                "departure_time": f"{hour:02d}:{minute:02d}",
                                "duration": max(1, self._safe_int(sl.get("duration", "0")) // 60),
                                "distance": self._safe_int(sl.get("distance", "0")),
                                "route_detail": f"{sl.get('name', '')}·经过{pass_num}站",
                            })
                    base_minutes += dur_min

                if not segments:
                    # 只有总数据,生成一个整体段
                    segments.append({
                        "type": "公共交通",
                        "instruction": f"从{origin_name or origin_address}到{destination_name or destination_address}",
                        "from_name": origin_name or origin_address,
                        "to_name": destination_name or destination_address,
                        "departure_time": "08:00",
                        "duration": max(1, total_dur // 60),
                        "distance": total_dist,
                        "route_detail": f"约{round(total_dist/1000,1)}公里",
                    })
            else:
                # walking/driving
                route = data.get("route", {})
                paths = route.get("paths", [])
                if paths:
                    path = paths[0]
                    total_dist = self._safe_int(path.get("distance", "0"))
                    total_dur = self._safe_int(path.get("duration", "0"))
                    road_type_cn = "步行" if route_type == "walking" else "自驾"
                    segments.append({
                        "type": road_type_cn,
                        "instruction": f"从{origin_name or origin_address}到{destination_name or destination_address}",
                        "from_name": origin_name or origin_address,
                        "to_name": destination_name or destination_address,
                        "departure_time": "08:00",
                        "duration": max(1, total_dur // 60),
                        "distance": total_dist,
                        "route_detail": f"约{round(total_dist/1000,1)}公里",
                    })

            return segments

        except Exception as e:
            print(f"  ⚠️ HTTP路线({route_type})失败: {e}")
            return []

    def _geocode_sync(self, address: str, city: str) -> tuple:
        """同步地理编码,返回 (lng, lat)"""
        import urllib.request, urllib.parse
        from ..config import get_settings

        try:
            params = urllib.parse.urlencode({
                "key": get_settings().amap_api_key,
                "address": address,
                "city": city,
            }, encoding="utf-8")
            url = f"https://restapi.amap.com/v3/geocode/geo?{params}"
            resp = urllib.request.urlopen(url, timeout=10)
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "1" and data.get("geocodes"):
                loc = data["geocodes"][0].get("location", "")
                if loc and "," in loc:
                    parts = loc.split(",")
                    return parts[0], parts[1]
        except Exception:
            pass
        return None, None

    def geocode(self, address: str, city: Optional[str] = None) -> Optional[Location]:
        """
        地理编码(地址转坐标)

        Args:
            address: 地址
            city: 城市

        Returns:
            经纬度坐标
        """
        try:
            arguments = {"address": address}
            if city:
                arguments["city"] = city

            result = self.mcp_tool.run({
                "action": "call_tool",
                "tool_name": "maps_geo",
                "arguments": arguments
            })

            print(f"地理编码结果: {result[:200]}...")

            # TODO: 解析实际的坐标数据
            return None

        except Exception as e:
            print(f"❌ 地理编码失败: {str(e)}")
            return None

    def get_poi_detail(self, poi_id: str) -> Dict[str, Any]:
        """
        获取POI详情

        Args:
            poi_id: POI ID

        Returns:
            POI详情信息
        """
        try:
            result = self.mcp_tool.run({
                "action": "call_tool",
                "tool_name": "maps_search_detail",
                "arguments": {
                    "id": poi_id
                }
            })

            print(f"POI详情结果: {result[:200]}...")

            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data

            return {"raw": result}

        except Exception as e:
            print(f"❌ 获取POI详情失败: {str(e)}")
            return {}


# 创建全局服务实例
_amap_service = None


def get_amap_service() -> AmapService:
    """获取高德地图服务实例(单例模式)"""
    global _amap_service

    if _amap_service is None:
        _amap_service = AmapService()

    return _amap_service
