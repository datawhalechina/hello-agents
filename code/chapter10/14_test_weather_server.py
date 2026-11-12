#!/usr/bin/env python3
"""测试天气查询 MCP 服务器"""

import asyncio
import json
import os
import sys
from hello_agents.protocols import MCPClient


async def test_weather_server():
    server_script = os.path.join(os.path.dirname(__file__), "14_weather_mcp_server.py")
    client = MCPClient([sys.executable, server_script])

    try:
        async with client:
            # 测试1: 获取服务器信息
            info = json.loads(await client.call_tool("get_server_info", {}))
            print(f"服务器: {info['name']} v{info['version']}")

            # 测试2: 列出支持的城市
            cities = json.loads(await client.call_tool("list_supported_cities", {}))
            print(f"支持城市: {cities['count']} 个")

            # 测试3、4: 查询北京和深圳天气，保留每个城市的失败信息
            failed_cities = []
            for city in ("北京", "深圳"):
                weather = json.loads(await client.call_tool("get_weather", {"city": city}))
                if "error" in weather:
                    failed_cities.append(city)
                    print(f"❌ {city}天气查询失败: {weather['error']}")
                else:
                    print(f"{city}天气: {weather['temperature']}°C, {weather['condition']}")

            if failed_cities:
                print(f"\n❌ 天气查询测试失败: {', '.join(failed_cities)}")
            else:
                print("\n✅ 所有测试完成！")

    except Exception as e:
        print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    asyncio.run(test_weather_server())
