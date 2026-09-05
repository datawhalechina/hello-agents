"""
考研复试智能出题系统 - 主程序

本程序使用 Camel-AI 多智能体框架，模拟教研团队进行协作出题和校验。
核心流程：
  1. 协调员 Agent：分析命题大纲，分配工作任务
  2. 出题专家 Agent：根据大纲要求生成高质量试题
  3. 校验专家 Agent：多维度校验题目，确保符合标准

依赖环境：
  - 需要在 .env 文件中配置 QWEN_API（阿里云通义千问 API 密钥）
  - 需要 Python 3.12+
  - 需要 camel-ai 依赖
"""

from camel.tasks import Task
from camel.societies.workforce import Workforce
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.agents import ChatAgent, CriticAgent
from dotenv import load_dotenv
import os
from prompts import (
    COORDINATOR_AGENT_SYSTEM_MESSAGE,
    TASK_AGENT_SYSTEM_MESSAGE,
    EXAM_GENERATION_PROMPT,
    EXAM_VALIDATION_PROMPT
)

# ==================== 初始化环境和模型 ====================

# 从 .env 文件加载环境变量（包括 QWEN_API）
load_dotenv()

# 创建通义千问模型实例
# ModelType.QWEN_PLUS 是一个高性能的模型，适合复杂的教研任务
model = ModelFactory.create(
    model_platform=ModelPlatformType.QWEN,
    model_type=ModelType.QWEN_PLUS,
    api_key=os.getenv('QWEN_API'),
)

# ==================== 创建智能体 ====================

# 1. 协调员 Agent：负责任务分析和工作分配
# 协调员会分析输入的命题大纲，并将其分解为具体的工作任务
coordinator_agent = ChatAgent(
    system_message=COORDINATOR_AGENT_SYSTEM_MESSAGE,
    model=model
)

# 2. 任务管理 Agent：负责任务分解、失败分析和质量评估
task_agent = ChatAgent(
    system_message=TASK_AGENT_SYSTEM_MESSAGE,
    model=model,
)

# ==================== 创建多智能体团队 ====================

# 创建 Workforce（工作团队），模拟教研团队的协作过程
workforce = Workforce(
    name="考研复试教研团队",
    coordinator_agent=coordinator_agent,      # 协调员
    task_agent=task_agent,                    # 任务管理员
    failure_handling_config={
        "max_retries": 5,                     # 失败最多重试 5 次
        "enabled_strategies": ["retry", "replan"],  # 启用重试和重规划策略
        "halt_on_max_retries": False,        # 重试失败后继续执行其他策略
    },
)

# ==================== 创建专家工作者 ====================

# 3. 出题专家 Agent：根据大纲生成高质量试题
test_agent = ChatAgent(
    system_message=EXAM_GENERATION_PROMPT,
    model=model
)

# 4. 校验专家 Agent（Critic Agent）：校验题目质量并提出改进建议
circle_agent = CriticAgent(
    system_message=EXAM_VALIDATION_PROMPT,
    model=model
)

# 将专家 Agent 添加到团队中
workforce.add_single_agent_worker(
    description="考研复试命题专家",
    worker=test_agent,
).add_single_agent_worker(
    description="考研复试命题校验专家",
    worker=circle_agent,
)



# ==================== 定义命题大纲 ====================

# 命题大纲是整个系统的输入，详细描述了题目的要求
# 包括：科目、院校层级、题型、数量、难度、答题场景、配套内容要求等
题目大纲 = """
# 考研复试命题大纲
## 一、基础配置
1.  考试科目：计算机网络
2.  目标院校层级：211院校
## 二、题型与数量要求
1.  题型大类：简答题、算法题
2.  具体细节：2道简答题+1道算法题，共3道题（简答题考）
3.  排序要求：按「简答题→算法题」顺序编号（如简答题1、算法题2）
## 三、难度要求
1.  难度：中档题
2.  难度定义：基础题侧重概念记忆与基础应用，中档题侧重原理分析与简单综合，难题侧重场景建模与深度拓展
## 四、答题场景
1.  场景类型：书面笔答
2.  场景要求：题目描述完整，答题需包含详细步骤，算法题可提供伪代码或核心逻辑
## 五、配套内容要求（必须完整提供）
1.  每道题必须包含以下完整结构，不可省略任何部分：
    - 【题目描述】：完整的题目正文
    - 【考查知识点】：明确标注该题考查的核心知识点
    - 【难度标签】：标注「基础/中档/难题」
    - 【参考答案】：完整的标准答案，简答题需包含所有要点，算法题需包含详细步骤和伪代码/核心逻辑
    - 【答案解析/核心思路】：解释答案的推导过程和关键点
2.  输出格式必须清晰展示上述所有部分，便于直接使用
## 六、其他要求
1.  表述风格：贴合211院校计算机网络复试真题风格，语言严谨、无歧义
2.  考点覆盖：仅围绕计算机网络核心考点命题，优先覆盖TCP/IP协议栈、网络层/传输层/应用层核心机制，无超纲内容
"""

# ==================== 执行出题任务 ====================

# 创建任务对象，包含命题大纲作为任务内容
task = Task(
    content=题目大纲,
    id="0",
)

# 将任务提交给团队处理
# 系统会：
#   1. 协调员分析大纲
#   2. 分配给出题专家生成试题
#   3. 分配给校验专家校验质量
#   4. 返回最终结果
task = workforce.process_task(task)

# ==================== 输出结果 ====================

# 打印最终生成的题目和答案
print(task.result)
