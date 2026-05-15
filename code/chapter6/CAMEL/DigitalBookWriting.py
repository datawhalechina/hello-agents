from colorama import Fore
from camel.societies import RolePlaying
from camel.utils import print_text_animated
from camel.models import ModelFactory
from camel.types import ModelPlatformType
from dotenv import load_dotenv
import os

LLM_MODEL_ID="coding-glm-4.7-free"
LLM_API_KEY="sk-Yfh9jNQSWoNgoZAC23Cb8d1a924d43E286Cd81Dc17Fa0b89"
LLM_BASE_URL="https://aihubmix.com/v1"

#创建模型,在这里以Qwen为例,调用的百炼大模型平台API
model = ModelFactory.create(
    model_platform=ModelPlatformType.ZHIPU,
    model_type=LLM_MODEL_ID,
    url=LLM_BASE_URL,
    api_key=LLM_API_KEY
)

# 定义协作任务
task_prompt = """
创作一本关于"人类移民"的短篇电子书，目标读者是对科幻题材感兴趣的普通大众。
要求：
1. 内容科学严谨，基于实证研究
2. 语言通俗易懂，避免过多专业术语
3. 包含实用的改善建议和案例分析
4. 篇幅控制在8000-10000字
5. 结构清晰，包含引言、核心章节和总结
"""

print(Fore.YELLOW + f"协作任务:\n{task_prompt}\n")

# 初始化角色扮演会话
role_play_session = RolePlaying(
    assistant_role_name="量子力学学家", 
    user_role_name="作家", 
    task_prompt=task_prompt,
    model=model
)

print(Fore.CYAN + f"具体任务描述:\n{role_play_session.task_prompt}\n")

# 开始协作对话
chat_turn_limit, n = 30, 0
input_msg = role_play_session.init_chat()

while n < chat_turn_limit:
    n += 1
    assistant_response, user_response = role_play_session.step(input_msg)
    
    print_text_animated(Fore.BLUE + f"作家:\n\n{user_response.msg.content}\n")
    print_text_animated(Fore.GREEN + f"心理学家:\n\n{assistant_response.msg.content}\n")
    
    # 检查任务完成标志
    if "CAMEL_TASK_DONE" in user_response.msg.content:
        print(Fore.MAGENTA + "✅ 电子书创作完成！")
        break
    
    input_msg = assistant_response.msg

print(Fore.YELLOW + f"总共进行了 {n} 轮协作对话")