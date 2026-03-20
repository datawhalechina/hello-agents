"""
AutoGen 软件开发团队协作案例（升级版）
"""

import os
import asyncio
from typing import Dict, Any, List
import re
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.ui import Console

CONTROL_TAGS = {
    "rework": "REWORK_REQUIRED",
    "test_failed": "TEST_FAILED",
    "test_passed": "TEST_PASSED",
    "intervene": "INTERVENE",
    "quality_ok": "QUALITY_OK",
}


def user_proxy_input(prompt: str) -> str:
    """用户代理自动输入：检测到测试通过后立即终止。"""
    normalized_prompt = str(prompt).upper()
    if ("TEST_PASSED" in normalized_prompt or "QA_FINAL_PASS" in normalized_prompt) and "TEST_FAILED" not in normalized_prompt:
        return "TERMINATE"
    return "请继续按协议协作；若 QA 给出 TEST_PASSED，请回复 TERMINATE。"


def create_openai_model_client():
    """创建 OpenAI 模型客户端用于测试"""
    model_id = os.getenv("LLM_MODEL_ID")
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    missing_vars = [name for name, value in [
        ("LLM_MODEL_ID", model_id),
        ("LLM_API_KEY", api_key),
    ] if not value]
    if missing_vars:
        raise ValueError(
            f"Missing required environment variable(s) for OpenAI model client: "
            f"{', '.join(missing_vars)}. "
            f"Please set them before running this script."
        )
    return OpenAIChatCompletionClient(
        model=model_id,
        api_key=api_key,
        base_url=base_url,
        model_info={
            "function_calling": True,
            "max_tokens": 4096,
            "context_length": 32768,
            "vision": False,
            "json_output": True,
            "family": "deepseek",
            "structured_output": True,
        },
    )


def create_product_manager(model_client):
    """创建产品经理智能体"""
    system_message = """你是一位经验丰富的产品经理，专门负责软件产品的需求分析和项目规划。

你的核心职责包括：
1. **需求分析**：深入理解用户需求，识别核心功能和边界条件
2. **技术规划**：基于需求制定清晰的技术实现路径
3. **风险评估**：识别潜在的技术风险和用户体验问题
4. **协调沟通**：与工程师和其他团队成员进行有效沟通

流程控制要求：
- 如果上游出现 REWORK_REQUIRED 或 TEST_FAILED，你必须先输出修订后的需求与实现计划，再明确说“请工程师重新实现”。
- 如果上游是 TEST_PASSED，你只需简要确认范围完成，不再新增需求。

当接到开发任务时，请按以下结构进行分析：
1. 需求理解与分析
2. 功能模块划分
3. 技术选型建议
4. 实现优先级排序
5. 验收标准定义

请简洁明了地回应，并在分析完成后说“请工程师开始实现”。"""

    return AssistantAgent(
        name="ProductManager",
        model_client=model_client,
        system_message=system_message,
    )


def create_engineer(model_client):
    """创建软件工程师智能体"""
    system_message = """你是一位资深的软件工程师，擅长 Python 开发和 Web 应用构建。

你的技术专长包括：
1. **Python 编程**：熟练掌握 Python 语法和最佳实践
2. **Web 开发**：精通 Streamlit、Flask、Django 等框架
3. **API 集成**：有丰富的第三方 API 集成经验
4. **错误处理**：注重代码的健壮性和异常处理

流程控制要求：
- 若收到 REWORK_REQUIRED 或 TEST_FAILED，必须基于审查/测试意见给出修复说明和更新后的完整代码。
- 完成实现后请以“实现完成，请代码审查员检查”收尾。

当收到开发任务时，请：
1. 仔细分析技术需求
2. 选择合适的技术方案
3. 编写完整的代码实现
4. 添加必要的注释和说明
5. 考虑边界情况和异常处理
"""

    return AssistantAgent(
        name="Engineer",
        model_client=model_client,
        system_message=system_message,
    )


def create_code_reviewer(model_client):
    """创建代码审查员智能体"""
    system_message = """你是一位经验丰富的代码审查专家，专注于代码质量和最佳实践。

你的审查重点包括：
1. **代码质量**：检查代码的可读性、可维护性和性能
2. **安全性**：识别潜在的安全漏洞和风险点
3. **最佳实践**：确保代码遵循行业标准和最佳实践
4. **错误处理**：验证异常处理的完整性和合理性

审查流程：
1. 仔细阅读和理解代码逻辑
2. 检查代码规范和最佳实践
3. 识别潜在问题和改进点
4. 提供具体的修改建议
5. 评估代码的整体质量

输出协议：
- 如果代码不通过，请输出 REWORK_REQUIRED，并给出最关键的3条整改建议。
- 如果代码通过，请输出 REVIEW_PASSED，并说明通过依据。
- 一次回答只允许一个结论标签，不要重复输出 REWORK_REQUIRED。
- 你只做审查，不要编写或改写实现代码。
"""

    return AssistantAgent(
        name="CodeReviewer",
        model_client=model_client,
        system_message=system_message,
    )


def create_quality_assurance(model_client):
    """创建测试工程师智能体"""
    system_message = """你是一位专业的软件测试工程师（QA），负责在代码审查后进行测试设计与验证。

你的职责：
1. 基于需求与实现，设计覆盖核心路径和边界条件的测试用例
2. 明确每个用例的预期结果
3. 给出测试结论和失败定位
4. 为工程师提供最小可执行修复建议

输出结构：
1. 测试范围
2. 测试用例与预期
3. 测试结果
4. 结论

输出协议：
- 通过时必须包含 TEST_PASSED。
- 不通过时必须包含 TEST_FAILED，并附上失败原因与修复建议。
- 当测试通过时，必须在最后单独输出一行：QA_FINAL_PASS。
- 你只做测试结论与建议，禁止输出任何代码块（包括```标记）。
- 禁止编写或修改实现代码，仅提供测试相关的反馈。"""

    return AssistantAgent(
        name="QualityAssurance",
        model_client=model_client,
        system_message=system_message,
    )


def create_dialogue_monitor(model_client):
    """创建对话质量监控智能体"""
    system_message = """你是对话质量监控员，负责识别协作过程中的偏题、循环和无进展问题。

监控规则：
1. 偏题：连续两轮与任务目标无关
2. 循环：连续两轮仅重复结论而无新动作
3. 无进展：未出现可执行下一步
4. 角色漂移：智能体输出超出其职责范围的内容（如QA输出代码）

干预协议：
- 正常时输出 QUALITY_OK，并给出一句下一步建议。
- 异常时输出 INTERVENE，并给出：问题类型、原因、纠偏动作。

如果出现 INTERVENE，团队下一轮应优先按纠偏动作推进。"""

    return AssistantAgent(
        name="DialogueMonitor",
        model_client=model_client,
        system_message=system_message,
    )


def create_user_proxy():
    """创建用户代理智能体"""
    return UserProxyAgent(
        name="UserProxy",
        description="""用户代理，负责以下职责：
1. 代表用户提出开发需求
2. 执行最终的代码实现
3. 验证功能是否符合预期
4. 提供用户反馈和建议

当且仅当收到 TEST_PASSED 且结果符合预期时，请回复 TERMINATE。""",
    input_func=user_proxy_input,
    )


def build_collaboration_task() -> str:
    """构建带流程协议的任务描述。"""
    return """我们需要开发一个比特币价格显示应用，具体要求如下：

核心功能：
- 实时显示比特币当前价格（USD）
- 显示24小时价格变化趋势（涨跌幅和涨跌额）
- 提供价格刷新功能

技术要求：
- 使用 Streamlit 框架创建 Web 应用
- 界面简洁美观，用户友好
- 添加适当的错误处理和加载状态

协作流程协议：
1. ProductManager -> Engineer -> CodeReviewer -> QualityAssurance -> DialogueMonitor -> UserProxy
2. 若 CodeReviewer 输出 REWORK_REQUIRED，则进入“需求修订/重新实现”回路。
3. 若 QualityAssurance 输出 TEST_FAILED，则回到工程师修复回路。
4. 若 QualityAssurance 输出“测试通过结论标签”，系统自动结束流程。
5. DialogueMonitor 发现异常时输出 INTERVENE，下一轮必须优先执行纠偏动作。
6. 角色边界：Engineer 负责实现；CodeReviewer 只审查；QualityAssurance 只测试，不输出实现代码。

请团队按协议协作，直到测试通过并结束流程。"""


def summarize_control_signals(result: Any) -> Dict[str, int]:
    """统计结果中出现的控制标签，便于复盘对话质量。"""
    counters = {tag: 0 for tag in CONTROL_TAGS.values()}
    messages = getattr(result, "messages", None)
    if not messages:
        return counters

    for message in messages:
        source = str(getattr(message, "source", ""))
        if source.lower() in {"user", "userproxy"}:
            continue
        content = str(getattr(message, "content", ""))
        upper_content = content.upper()
        for tag in counters:
            if tag in upper_content:
                counters[tag] += 1
    return counters


def _extract_messages(result: Any) -> List[Any]:
    """从运行结果中提取消息列表。"""
    messages = getattr(result, "messages", None)
    return messages if messages else []


def evaluate_protocol_closure(result: Any) -> Dict[str, Any]:
    """评估是否达成协议闭环。"""
    messages = _extract_messages(result)

    has_test_passed = False
    has_test_failed = False
    has_rework = False
    has_intervene = False
    userproxy_terminated = False
    qa_final_pass = False
    qa_role_drift = False

    for message in messages:
        source = str(getattr(message, "source", "")).lower()
        content = str(getattr(message, "content", ""))
        upper_content = content.upper()

        # 只接受 QA 的明确测试结论，避免被任务文本或提示语污染。
        if source == "qualityassurance" and re.search(r"\bTEST_PASSED\b", upper_content):
            has_test_passed = True
        if source == "qualityassurance" and re.search(r"\bQA_FINAL_PASS\b", upper_content):
            qa_final_pass = True
        if source == "qualityassurance" and re.search(r"\bTEST_FAILED\b", upper_content):
            has_test_failed = True
        # 避免任务文本或系统提示中的控制词"污染"返工/干预标记
        if source not in {"user", "system"} and "REWORK_REQUIRED" in upper_content:
            has_rework = True
        if source not in {"user", "system"} and "INTERVENE" in upper_content:
            has_intervene = True

        # 只接受 UserProxy 的精确终止指令，避免“请回复 TERMINATE”被误判为已终止。
        if source == "userproxy" and content.strip().upper() == "TERMINATE":
            userproxy_terminated = True

        if source == "qualityassurance" and "```" in content:
            qa_role_drift = True

   
    # 硬终止可以是 UserProxy 终止或 QA 最终通过
    hard_terminated = userproxy_terminated or qa_final_pass
    
    # 检查是否有 TEST_PASSED 或 QA_FINAL_PASS
    has_test_approval = has_test_passed or qa_final_pass
    
    # 协议成功条件：测试通过且无角色漂移
    protocol_success = has_test_approval and not qa_role_drift

    return {
        "protocol_success": protocol_success,
        "has_test_passed": has_test_passed,
        "has_test_failed": has_test_failed,
        "has_rework": has_rework,
        "has_intervene": has_intervene,
        "userproxy_terminated": userproxy_terminated,
        "qa_final_pass": qa_final_pass,
        "hard_terminated": hard_terminated,
        "has_test_approval": has_test_approval,
        "qa_role_drift": qa_role_drift,
    }


async def run_software_development_team():
    """运行软件开发团队协作"""

    print("🔧 正在初始化模型客户端...")


    model_client = create_openai_model_client()

    print("👥 正在创建智能体团队...")

    # 创建智能体团队
    product_manager = create_product_manager(model_client)
    engineer = create_engineer(model_client)
    code_reviewer = create_code_reviewer(model_client)
    quality_assurance = create_quality_assurance(model_client)
    dialogue_monitor = create_dialogue_monitor(model_client)
    user_proxy = create_user_proxy()

    # 添加终止条件：由 UserProxy 显式输出 TERMINATE 时触发硬终止，确保 QA/监控/用户代理都能完成闭环。
    termination = TextMentionTermination("TERMINATE")

    # 创建团队聊天
    team_chat = RoundRobinGroupChat(
        participants=[
            product_manager,
            engineer,
            code_reviewer,
            quality_assurance,
            dialogue_monitor,
            user_proxy,
        ],
        termination_condition=termination,
        max_turns=30,
    )

    # 定义开发任务
    task = build_collaboration_task()

    # 执行团队协作
    print("🚀 启动 AutoGen 软件开发团队协作...")
    print("=" * 60)

    # 使用 Console 来显示对话过程
    result = await Console(team_chat.run_stream(task=task))
    control_summary = summarize_control_signals(result)
    protocol_report = evaluate_protocol_closure(result)

    print("\n" + "=" * 60)
    print(" 团队协作完成！")
    print(" 控制信号统计：")
    for tag, count in control_summary.items():
        print(f"- {tag}: {count}")

    print(" 协议闭环检查：")
    print(f"- TEST_PASSED 是否出现：{protocol_report['has_test_passed']}")
    print(f"- QA_FINAL_PASS 是否出现：{protocol_report['qa_final_pass']}")
    print(f"- 测试是否通过：{protocol_report['has_test_approval']}")
    print(f"- 系统是否硬终止：{protocol_report['hard_terminated']}")
    print(f"- UserProxy 是否终止：{protocol_report['userproxy_terminated']}")
    print(f"- QA 是否角色漂移：{protocol_report['qa_role_drift']}")
    print(f"- 协议闭环达成：{protocol_report['protocol_success']}")

    return {"result": result, "protocol_report": protocol_report}


# 主程序入口
if __name__ == "__main__":
    try:
        # 运行异步协作流程
        run_output = asyncio.run(run_software_development_team())
        result = run_output["result"]
        protocol_report = run_output["protocol_report"]

        print("\n 协作结果摘要：")
        print("- 参与智能体数量：6个")
        print(f"- 工作流执行状态：{'成功' if result else '需要进一步处理'}")
        print(f"- 协议闭环状态：{'达成' if protocol_report['protocol_success'] else '未达成'}")

    except ValueError as e:
        print(f"❌ 配置错误：{e}")
        print("请检查 .env 文件中的配置是否正确")
    except Exception as e:
        print(f"❌ 运行错误：{e}")
        import traceback

        traceback.print_exc()