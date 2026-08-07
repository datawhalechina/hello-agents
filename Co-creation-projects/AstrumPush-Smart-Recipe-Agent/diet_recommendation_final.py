from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool
from dotenv import load_dotenv
import os
import json
from datetime import datetime

load_dotenv()
os.makedirs("recipes", exist_ok=True)


def parse_response(response):
    try:
        if "```json" in response:
            json_start = response.find("```json") + 7
            json_end = response.find("```", json_start)
            json_str = response[json_start:json_end].strip()
        elif "```" in response:
            json_start = response.find("```") + 3
            json_end = response.find("```", json_start)
            json_str = response[json_start:json_end].strip()
        elif "{" in response and "}" in response:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            json_str = response[json_start:json_end]
        else:
            raise ValueError("响应中未找到JSON数据")
        
        data = json.loads(json_str)
        return data
    except Exception as e:
        print(f"⚠️  解析响应失败: {str(e)}")
        return None


def write_content_to_file(content):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # 例: 20260428_143022
    filename = f"recipes/recipes_{timestamp}.md" 

    with open(filename, "w", encoding="utf-8") as wf:
        wf.write(content)

    print(f"✅ 菜谱已创建: {filename}")


web_search_tool = MCPTool(name="web_research", server_command=["npx", "-y", "@mzxrai/mcp-webresearch@latest"])


# ===================================== 菜谱搜索助手 =====================================
caipu_search_agent = SimpleAgent(
    name="caipu_search_agent",
    llm=HelloAgentsLLM(),
    system_prompt="""
你是菜谱搜索专家。你的任务是根据用户的需求和用户偏好搜索合适的菜谱。

**重要提示:**
你必须使用工具来搜索菜谱!不要自己编造菜谱信息!返回的内容至少包括菜名和菜谱链接!可以包括菜品特点,便于后续筛选!

**工具调用格式:**
使用visit_page工具时,必须严格按照以下格式:
`[TOOL_CALL:visit_page:url=https://www.xiangha.com/so/?q=caipu&s=菜谱]`
`[TOOL_CALL:visit_page:url=https://www.xiangha.com/so/?q=caipu&s=食材]`


**示例:**
用户: "搜索五花肉的做法"
你的回复: [TOOL_CALL:visit_page:url=https://www.xiangha.com/so/?q=caipu&s=五花肉]

用户: "搜索和鱼有关的菜谱"
你的回复: [TOOL_CALL:visit_page:url=https://www.xiangha.com/so/?q=caipu&s=鱼]

**注意:**
1. 必须使用工具,不要直接回答
2. 格式必须完全正确,包括方括号和冒号
3. 参数用逗号分隔
"""
)
caipu_search_agent.add_tool(web_search_tool)


def build_caipu_search_prompts(user_input):
    return f"调用visit_page工具, 用户需求: {user_input}"


# ===================================== 饮食专家助手 =====================================
caipu_select_agent = SimpleAgent(
    name="caipu_select_agent",
    llm=HelloAgentsLLM(),
    system_prompt="""
你是饮食专家。你的任务是根据用户需求和推荐的菜谱列表，为用户选择一个最合适的菜谱，并给出推荐理由。

**重要提示:**
你必须从推荐的菜谱列表中选择，不能凭空产生新的菜名和菜谱链接。

请严格按照以下JSON格式返回推荐菜谱:
```json
{
  "name": "红烧鲫鱼",
  "url": "https://www.xiangha.com/caipu/102880489.html",
  "reason": "**推荐理由：**
    - 🐟 **清蒸烹饪** - 最清淡的烹饪方式，少油少盐
    - 🔥 **适合降火** - 清蒸做法不辛辣、不油腻，不会加重上火症状
    - 💪 **营养丰富** - 石斑鱼富含优质蛋白，肉质细嫩鲜美
  "
}
```

如果没有合适的推荐结果，请返回空的json数据，格式如下：
```json
{

}
```
"""
)


def build_caipu_select_prompts(user_input, caipu_list):
    return f"用户需求: {user_input}，推荐的菜谱列表: {caipu_list}"


# ===================================== 网页内容提取助手 =====================================
output_agent = SimpleAgent(
    name="demand_analyzer",
    llm=HelloAgentsLLM(),
    system_prompt="""
你是网页内容提取专家。你的任务是根据用户选择的菜名和菜谱链接，返回最终完整的的菜谱。

**重要提示:**
你必须使用工具来获取菜谱信息!不要自己编造菜谱信息!

**工具调用格式:**
使用visit_page工具时,必须严格按照以下格式:
`[TOOL_CALL:visit_page:url=菜谱链接]`


**示例:**
用户: 菜名: 红烧鲫鱼，菜谱链接: https://www.xiangha.com/caipu/102880489.html
你的回复: [TOOL_CALL:visit_page:url=https://www.xiangha.com/caipu/102880489.html]

**注意:**
1. 必须使用工具,不要直接回答
2. 格式必须完全正确,包括方括号和冒号
3. 参数用逗号分隔
"""
)
output_agent.add_tool(web_search_tool)


def build_output_prompts(caipu_json):
    return f"菜名: {caipu_json['name']}, 菜谱链接: {caipu_json['url']}"


# ===================================== 完整流程 =====================================

user_input = input("请输入菜谱需求(例如：我想吃小龙虾) >>> ")

print("\n\n正在搜索菜谱...")
search_caipu_result = caipu_search_agent.run(build_caipu_search_prompts(user_input=user_input))
print(search_caipu_result)

print("\n\n正在筛选菜谱...")
caipu_select_result = caipu_select_agent.run(build_caipu_select_prompts(user_input=user_input, caipu_list=search_caipu_result))
print(caipu_select_result)

print("\n\n正在解析结果...")
caipu_select_json = parse_response(caipu_select_result)
print(caipu_select_json)

if caipu_select_json:
    print("\n\n正在生成菜谱...")
    output_result = output_agent.run(build_output_prompts(caipu_select_json))

    print("\n\n正在保存菜谱...")
    print(f"菜名: {caipu_select_json['name']}\n推荐理由: {caipu_select_json['reason']}")
    write_content_to_file(output_result)
else:
    print("\n\n未找到合适的菜谱")
