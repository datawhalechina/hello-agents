# -*- coding: utf-8 -*-
"""
高德开放平台 REST API 轻量客户端（DatePlannerAgent 数据层）。

特性：
- 仅依赖 requests（可选），无 SDK 依赖；
- 双后端兜底：requests -> urllib（均为进程内 HTTP 客户端，Key 不会暴露到
  系统进程列表/命令行，避免被监控或诊断日志读取），网络异常自动重试；
- 所有返回均为高德原始 JSON，缺失字段由上层标注“需要确认”，不编造；
- 异常信息中的 Key 自动脱敏。

用法：
    from date_planner.amap_client import AMapClient
    client = AMapClient()          # 自动读环境变量 AMAP_KEY 或 .env 文件
    pois = client.text_search("西餐厅", city="北京")
"""
import json
import os
import time
import urllib.parse
import urllib.request

BASE = "https://restapi.amap.com/v3"


def load_key():
    """从环境变量 AMAP_KEY 或项目根 .env 文件读取 Key。"""
    key = os.environ.get("AMAP_KEY", "").strip()
    if key:
        return key
    # 从 .env 文件读取（兼容 `AMAP_KEY=xxx` 或 `AMAP_KEY = xxx`）
    for base in (os.path.dirname(os.path.dirname(os.path.abspath(__file__))), os.getcwd()):
        env_path = os.path.join(base, ".env")
        if os.path.exists(env_path):
            try:
                for line in open(env_path, encoding="utf-8"):
                    line = line.strip()
                    if line.startswith("AMAP_KEY"):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if key:
                            return key
            except Exception:
                pass
    return ""


def _redact(text, secret):
    """把文本中的 Key 替换为 ***，避免异常/日志泄露。"""
    if not secret or not text:
        return text
    return str(text).replace(secret, "***")


def _http_get(url, tries=3, timeout=15, secret=None):
    """GET 请求：requests -> urllib 双后端，带重试；异常信息自动脱敏。"""
    last_err = None
    for _ in range(tries):
        # 1) requests
        try:
            import requests  # noqa: WPS433
            r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last_err = e
        # 2) urllib（部分环境 SSL 报 UNEXPECTED_EOF，作为中间层尝试）
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(1)
    raise RuntimeError(f"高德 API 请求失败（{tries} 次尝试后放弃）: {_redact(last_err, secret)}")


class AMapClient:
    """高德 Web 服务 API 客户端。"""

    def __init__(self, key=None):
        self.key = key or load_key()
        if not self.key:
            raise ValueError(
                "未找到高德 Key：请设置环境变量 AMAP_KEY，或在项目根目录创建 .env 写入 AMAP_KEY=xxx"
            )

    def _get(self, path, params):
        params = {k: v for k, v in params.items() if v not in (None, "")}
        params["key"] = self.key
        params["output"] = "json"
        url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
        return _http_get(url, secret=self.key)

    # ---------- 搜索 ----------
    def text_search(self, keywords, city="", offset=10, page=1):
        """关键词搜索：keywords + city。返回 POI 列表。"""
        d = self._get("place/text", {"keywords": keywords, "city": city,
                                     "offset": offset, "page": page,
                                     "citylimit": "true" if city else "false"})
        return d.get("pois", []) if d.get("status") == "1" else []

    def around_search(self, location, keywords="", radius=1000, offset=10):
        """周边搜索：location='经度,纬度' + radius(米) + keywords。"""
        d = self._get("place/around", {"location": location, "keywords": keywords,
                                       "radius": radius, "offset": offset, "sortrule": "distance"})
        return d.get("pois", []) if d.get("status") == "1" else []

    def detail(self, poi_id):
        """POI 详情：address / tel / business_area / type / location。"""
        d = self._get("place/detail", {"id": poi_id})
        pois = d.get("pois", []) if d.get("status") == "1" else []
        return pois[0] if pois else {}

    # ---------- 坐标/距离 ----------
    def geo(self, address, city=""):
        """地址 -> 经纬度。返回 (lng, lat) 或 None。"""
        d = self._get("geocode/geo", {"address": address, "city": city})
        geos = d.get("geocodes", []) if d.get("status") == "1" else []
        if geos and geos[0].get("location"):
            lng, lat = geos[0]["location"].split(",")
            return lng, lat
        return None

    def regeocode(self, location):
        """经纬度 -> 地址。"""
        d = self._get("regeocode/regeo", {"location": location})
        return d.get("regeocode", {}) if d.get("status") == "1" else {}

    def distance(self, origins, destination, type_="1"):
        """距离测量。type: 1驾车 / 2骑行 / 3步行。返回 {'km':..,'min':..} 或 None。
        origins 支持多组（用 | 分隔），本封装只取第一组。"""
        d = self._get("distance", {"origins": origins, "destination": destination, "type": type_})
        results = d.get("results", []) if d.get("status") == "1" else []
        if results:
            r0 = results[0]
            return {"km": round(int(r0.get("distance", 0)) / 1000.0, 1),
                    "min": int(r0.get("duration", 0)) // 60}
        return None

    # ---------- 天气 ----------
    def weather(self, city, extensions="all"):
        """天气。city 可为 adcode 或城市名。返回 forecast 列表。"""
        d = self._get("weather/weatherInfo", {"city": city, "extensions": extensions})
        if d.get("status") == "1":
            return d.get("forecasts", [{}])[0].get("casts", [])
        return []


def pretty_poi(p, index=""):
    """把高德 POI 转成可读文本（缺字段标“需要确认”）。"""
    biz = p.get("biz_ext", {}) or {}
    return (f"{index} {p.get('name', '需要确认')} | 地址:{p.get('address') or '需要确认'} "
            f"| 电话:{p.get('tel') or '需要确认'} | 人均:{biz.get('cost') or '需要确认'} "
            f"| 评分:{p.get('rating') or '需要确认'} | 坐标:{p.get('location') or '需要确认'}")
