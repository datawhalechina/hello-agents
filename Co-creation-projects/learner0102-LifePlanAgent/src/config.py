from dotenv import load_dotenv
import os
load_dotenv()

# LLM大模型配置
LLM_MODEL = "填写你要用的大模型"
LLM_API_KEY = os.getenv("API_KEY")
LLM_BASE_URL = os.getenv("BASE_URL")
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 1500

# Agent系统常量
BUFFER_MINUTE = 30  # 任务之间缓冲时间，30分钟
MAX_SINGLE_TASK_MIN = 120  # 单次任务最大时长

# 意图枚举
INTENT_NEW_PLAN = "new_plan"
INTENT_MODIFY_PLAN = "modify_plan"
INTENT_QUERY_CONFLICT = "query_conflict"
INTENT_LONG_TERM_GOAL = "long_term_goal"
