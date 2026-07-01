import requests

def get_weather(city:str) -> str:
    """
    通过调用wttr.in API查询真实的天气信息
    """
    url = f"https://wttr.in/{city}?format=j1"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        current_conditions = data['current_condition'][0]
        weather_desc = current_conditions['weatherDesc'][0]['value']
        temp_c = current_conditions['temp_C']

        return f"{city}当前天气:{weather_desc}，气温{temp_c}摄氏度"

    except requests.exceptions.RequestException as e:
        return f"错误:查询天气时遇到网络问题 - {e}"
    except (KeyError, IndexError) as e:
        return f"错误:解析天气数据失败，可能是城市名称无效 - {e}"

import os
from tavily import TavilyClient
from dotenv import load_dotenv
def get_attraction(city:str, weather:str) -> str:
    load_dotenv()
    """
    根据城市和天气，使用Tavily Search API搜素并返回优化后的景点
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "错误：未配置'TAVILY_API_KEY'环境变量"

    tavily = TavilyClient(api_key=api_key)
    query = f"'{city}' 在 '{weather}'天气下最值得去的地方以及推荐理由"

    try:
        response = tavily.search(query=query, search_depth="basic", include_answer=True)
        if response.get("answer"):
            return response["answer"]

        formatted_results = []
        for result in response.get("results", []):
            formatted_results.append(f"- {result['title']}: {result['content']}")

        if not formatted_results:
            return "抱歉，没有找到相关的旅游景点推荐。"

        return "根据搜索，为您找到以下信息:\n" + "\n".join(formatted_results)

    except Exception as e:
        return f"错误:执行Tavily搜索时出现问题 - {e}"

available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction
}

from openai import OpenAI



if __name__ == '__main__':
    print(get_weather("nanchong"))
    print(get_attraction("nanchong", get_weather("nanchong")))