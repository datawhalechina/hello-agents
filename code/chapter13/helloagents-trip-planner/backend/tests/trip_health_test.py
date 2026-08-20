"""旅行规划健康检查的离线单元测试。"""

import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


class StubAPIRouter:
    """提供路由装饰器所需的最小 FastAPI 接口。"""

    def __init__(self, **kwargs):
        self.options = kwargs

    @staticmethod
    def _route_decorator(*args, **kwargs):
        del args, kwargs

        def decorator(function):
            return function

        return decorator

    get = _route_decorator
    post = _route_decorator


class StubHTTPException(Exception):
    """保留路由异常转换所需的状态码和详情。"""

    def __init__(self, status_code, detail):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def load_trip_route():
    """在不安装 FastAPI、Pydantic 或 hello-agents 时加载路由。"""
    fastapi = types.ModuleType("fastapi")
    fastapi.APIRouter = StubAPIRouter
    fastapi.HTTPException = StubHTTPException

    schemas = types.ModuleType("app.models.schemas")
    schemas.TripRequest = type("TripRequest", (), {})
    schemas.TripPlanResponse = type("TripPlanResponse", (), {})
    schemas.ErrorResponse = type("ErrorResponse", (), {})

    trip_planner_agent = types.ModuleType("app.agents.trip_planner_agent")

    def unpatched_agent_factory():
        raise AssertionError("测试必须替换旅行规划 Agent 工厂")

    trip_planner_agent.get_trip_planner_agent = unpatched_agent_factory

    with patch.dict(
        sys.modules,
        {
            "fastapi": fastapi,
            "app.models.schemas": schemas,
            "app.agents.trip_planner_agent": trip_planner_agent,
        },
    ):
        return importlib.import_module("app.api.routes.trip")


trip = load_trip_route()


class StubAgent:
    """只提供健康检查需要的本地工具清单。"""

    def __init__(self, tools):
        self._tools = tools

    def list_tools(self):
        return list(self._tools)


class StubMultiAgentTripPlanner:
    """不初始化 LLM 或 MCP 服务的多智能体替身。"""

    def __init__(self):
        self.attraction_agent = StubAgent(["amap_search", "amap_weather"])
        self.weather_agent = StubAgent(["amap_weather"])
        self.hotel_agent = StubAgent(["amap_search", "amap_hotel"])
        self.planner_agent = StubAgent([])


class TripHealthCheckTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_check_reports_multi_agent_tools_without_external_calls(self):
        planner = StubMultiAgentTripPlanner()

        with patch.object(
            trip,
            "get_trip_planner_agent",
            return_value=planner,
        ) as get_agent:
            response = await trip.health_check()

        self.assertEqual(
            response,
            {
                "status": "healthy",
                "service": "trip-planner",
                "agent_name": "StubMultiAgentTripPlanner",
                "tools_count": 3,
            },
        )
        get_agent.assert_called_once_with()

    async def test_health_check_keeps_503_for_initialization_errors(self):
        with patch.object(
            trip,
            "get_trip_planner_agent",
            side_effect=RuntimeError("initialization failed"),
        ):
            with self.assertRaises(StubHTTPException) as raised:
                await trip.health_check()

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(
            raised.exception.detail,
            "服务不可用: initialization failed",
        )


if __name__ == "__main__":
    unittest.main()
