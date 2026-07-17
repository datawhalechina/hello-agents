from dotenv import load_dotenv
load_dotenv('D:/develop/Project/Hello-Agent/hello-agents/code/chapter6/Langgraph/.env')

import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_BASE_URL')
)

tools = [
    {
        'type': 'function',
        'function': {
            'name': 'get_weather',
            'description': '获取指定城市的天气',
            'parameters': {
                'type': 'object',
                'properties': {
                    'city': {'type': 'string', 'description': '城市名'},
                    'unit': {'type': 'string', 'description': '温度单位'}
                },
                'required': ['city']
            }
        }
    }
]

response = client.chat.completions.create(
    model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
    messages=[
        {'role': 'system', 'content': '你是一个天气助手'},
        {'role': 'user', 'content': '北京今天天气怎么样？'}
    ],
    tools=tools,
    tool_choice='auto'
)

choice = response.choices[0]
msg = choice.message

print('=== message 整体结构 ===')
print(f'role:        {msg.role}')
print(f'content:     {msg.content}')
print(f'tool_calls:  {msg.tool_calls}')

if msg.tool_calls:
    print()
    print('=== tool_calls[0] 详细结构 ===')
    tc = msg.tool_calls[0]
    print(f'type(tc):               {type(tc).__name__}')
    print(f'tc.id:                  {tc.id}')
    print(f'tc.type:                {tc.type}')
    print(f'tc.function:            {tc.function}')
    print(f'tc.function.name:       {tc.function.name}')
    print(f'tc.function.arguments:  {tc.function.arguments}')
    print(f'type(arguments):        {type(tc.function.arguments).__name__}')
