"""Offline tests: python -m unittest discover -s code/chapter10 -p test_weather_demo_reporting.py -v"""

import contextlib
import importlib.util
import io
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class WeatherDemoReportingTests(unittest.IsolatedAsyncioTestCase):
    async def run_demo(self, responses, connection_error=None):
        class FakeClient:
            async def __aenter__(self):
                if connection_error:
                    raise connection_error
                return self

            async def __aexit__(self, *args):
                return False

            async def call_tool(self, name, arguments):
                if name == "get_server_info":
                    return json.dumps({"name": "Fake Weather", "version": "1"})
                if name == "list_supported_cities":
                    return json.dumps({"count": 12})
                return json.dumps(responses[arguments["city"]])

        protocols = types.ModuleType("hello_agents.protocols")
        protocols.MCPClient = Mock(return_value=FakeClient())
        framework = types.ModuleType("hello_agents")
        framework.protocols = protocols
        spec = importlib.util.spec_from_file_location(
            "weather_demo", Path(__file__).with_name("14_test_weather_server.py")
        )
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"hello_agents": framework, "hello_agents.protocols": protocols}):
            spec.loader.exec_module(module)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            await module.test_weather_server()
        return output.getvalue(), protocols.MCPClient

    async def test_successful_queries(self):
        weather = {"temperature": 20, "condition": "Sunny"}
        output, _ = await self.run_demo({"北京": weather, "深圳": weather})
        self.assertIn("北京天气: 20°C", output)
        self.assertIn("深圳天气: 20°C", output)
        self.assertIn("✅ 所有测试完成", output)
        self.assertNotIn("失败", output)

    async def test_one_failed_query(self):
        output, _ = await self.run_demo({
            "北京": {"error": "mock timeout"},
            "深圳": {"temperature": 25, "condition": "Sunny"},
        })
        self.assertIn("北京天气查询失败: mock timeout", output)
        self.assertIn("深圳天气: 25°C", output)
        self.assertIn("天气查询测试失败: 北京", output)
        self.assertNotIn("✅ 所有测试完成", output)

    async def test_both_queries_fail(self):
        output, _ = await self.run_demo({"北京": {"error": "first"}, "深圳": {"error": "second"}})
        self.assertIn("北京天气查询失败: first", output)
        self.assertIn("深圳天气查询失败: second", output)
        self.assertIn("天气查询测试失败: 北京, 深圳", output)
        self.assertNotIn("✅ 所有测试完成", output)

    async def test_current_interpreter(self):
        weather = {"temperature": 20, "condition": "Sunny"}
        _, factory = await self.run_demo({"北京": weather, "深圳": weather})
        command = factory.call_args.args[0]
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(Path(command[1]).name, "14_weather_mcp_server.py")

    async def test_connection_failure_is_reported(self):
        output, _ = await self.run_demo({}, RuntimeError("mock connection failure"))
        self.assertIn("测试失败: mock connection failure", output)
        self.assertNotIn("✅ 所有测试完成", output)


if __name__ == "__main__":
    unittest.main()
