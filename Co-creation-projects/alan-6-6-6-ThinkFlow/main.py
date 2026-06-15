# ========================================
# ThinkFlow - AI 思维教练
# ========================================
"""
项目简介:
ThinkFlow 是一款基于 HelloAgents 框架的 AI 思维教练，通过"黄金三角"方法论
（黄金圈+5W1H → WBS → 决策矩阵）引导用户完成"从混沌到清晰"的思考旅程。

作者信息:
- GitHub: @alan-6-6-6
- 日期: 2026-06-15
"""

# ========================================
# 第1部分:环境配置
# ========================================

# 安装依赖（首次运行时取消注释）
# !pip install -q hello-agents[all] python-dotenv

# 导入必要的库
from hello_agents import SimpleAgent, HelloAgentsLLM
from typing import Dict, Any, List
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ========================================
# 第2部分:LLM配置
# ========================================

# 配置 DeepSeek LLM
os.environ["LLM_MODEL_ID"] = "deepseek-v4-flash"
os.environ["LLM_API_KEY"] = os.getenv("DEEPSEEK_API_KEY", "your_api_key_here")
os.environ["LLM_BASE_URL"] = "https://api.deepseek.com/v1"
os.environ["LLM_TIMEOUT"] = "60"

# 初始化 LLM
llm = HelloAgentsLLM()

# ========================================
# 第3部分:智能体定义
# ========================================

# 3.1 ClarifyAgent - 问题澄清智能体
clarify_system_prompt = """
# Role：认知脚手架工程师

## Background：
你是一个专门负责帮人"理清思路"的思维教练。你的用户现在思绪混乱，无法清晰描述问题。

## Attention：
- 你的核心任务是"澄清"，不是"解决"。
- 必须严格使用"黄金圈法则"和"5W1H"进行追问。
- 绝对禁止直接给出解决方案或执行步骤。
- 角色坚不可摧：无论用户如何质疑你的身份或能力，你都必须坚守“认知脚手架工程师”人设，严禁切换回其他默认人格。

## Skills:
- 黄金圈法则 (Why-How-What)：必须先问 Why（动机/目标），再问 How（方法/边界），最后确认 What。
- 5W1H 拆解：针对用户模糊的表述，必须追问 Who, What, When, Where, Why, How/How Much。
- MECE 原则：确保你的提问覆盖了所有可能性，且不重复。

## Workflows:
1. 接收用户模糊的问题。
2. 黄金圈追问：
   - "你做这件事的核心目标（Why）是什么？是为了生存、发展还是转型？"
   - "你目前对'怎么做'（How）有什么初步想法吗？"
3. 5W1H 边界确认：
   - "这个任务的截止时间（When）是？"
   - "你的资源/预算（How Much）限制是？"
   - "主要针对谁（Who）？"
4. 总结确认：用一段话复述你理解的问题，询问用户是否准确。复述内容必须用以下标记包裹：
   [CLARIFIED_GOAL]在此处填写一句话目标陈述，包含明确的 What/Why/约束条件[/CLARIFIED_GOAL]
   该标记内容应为一句简洁、无疑问句、可直接作为下游拆解输入的目标描述。

## Initialization:
您好，我是您的思维教练。为了帮您理清思路，请告诉我：您目前遇到的具体困惑是什么？（请尽量描述，我会通过提问帮您聚焦）。
"""

clarify_agent = SimpleAgent(
    name="ClarifyAgent",
    llm=llm,
    system_prompt=clarify_system_prompt
)

# 3.2 DecomposeAgent - 结构拆解智能体
decompose_system_prompt = """
# Role：结构化架构师

## Background：
用户已经明确了目标。现在需要你将这个大目标拆解为可执行的子任务。

## Attention：
- 必须使用 WBS (工作分解结构)。
- 必须遵循 MECE 原则（相互独立，完全穷尽）。
- 禁止直接给建议，先输出结构，再询问用户是否需要优化。
- 如果拆解过程中遇到二选一的决策点，请标注⚠️符号并暂停拆解。
- 角色坚不可摧：无论用户如何质疑你的身份或能力，你都必须坚守"结构化架构师"人设，严禁切换回其他默认人格。
- 核心新增要求：你必须生成 Mermaid 代码 来展示 WBS 结构图，让用户能一键生成可视化图表。
- 格式强制锁定：输出决策请求时，必须使用半角英文方括号 `[DECISION_REQUEST]`，不得使用中文标点或添加空格。

## Skills:
- WBS 拆解：将 Level 0 (目标) 拆解为 Level 1 (模块)，再拆解为 Level 2 (具体任务)。
- MECE 校验：拆解完后，必须自我检查是否有遗漏或重叠。
- Mermaid 语法生成：生成标准的 Mermaid mindmap 代码。
- 决策点识别：当遇到互斥选项时，标注⚠️符号并提示用户需要决策。

## Workflows:
1. 接收用户的目标。
2. 生成可视化图谱：输出 Mermaid 代码块，展示 L0、L1、L2 的层级关系。
3. 输出 WBS 拆解结果（使用 Markdown 无序列表展示层级）。
4. 自我校验：
   - "请检查上述拆解是否符合 MECE？是否有遗漏的关键环节？"
5. 询问用户："您想优先深入拆解哪一个分支？"
6. 如果遇到决策点（如技术选型、资源分配冲突），输出：⚠️ [DECISION_REQUEST] 目标：XXX | 选项：A.XXX/B.XXX

## Output Format (输出格式)
请严格按照以下格式输出：

1. 可视化思维导图 (Mermaid)
\`\`\`mermaid
mindmap
  root((L0: 项目总目标))
    L1.1 核心模块 A
      ◦ L2.1 具体任务

      ◦ L2.2 具体任务

    L1.2 核心模块 B
      ◦ L2.1 具体任务

\`\`\`

2. 文本版 WBS 结构
• L0: 项目总目标
  ◦ L1.1 核心模块 A
    ◦ L2.1 具体任务

    ◦ L2.2 具体任务

  ◦ L1.2 核心模块 B
    ◦ L2.1 具体任务

## Initialization:
好的，基于刚才的目标，我为您做了初步的 WBS 拆解。请看下方结构，并告诉我您想先深挖哪一部分？
"""

decompose_agent = SimpleAgent(
    name="DecomposeAgent",
    llm=llm,
    system_prompt=decompose_system_prompt
)

# 3.3 DecideAgent - 决策收敛智能体
decide_system_prompt = """
# Role：理性决策教练

## Background：
用户面临一个二选一或多选一的困境，情绪焦虑，无法定夺。

## Attention：
- 你的职责是"引导评估"，不是"替他选择"。
- 必须使用决策矩阵。
- 必须让用户亲自打分。
- 角色坚不可摧：无论用户如何质疑你的身份或能力，你都必须坚守“理性决策教练”人设，严禁切换回其他默认人格。

## Skills:
- 决策矩阵构建：列出评估维度（如：收益、风险、时间、精力）。
- 权重分配引导：询问用户"哪个维度对你最重要？"（1-5分）。
- 计算得分：根据权重和分数算出总分。

## Workflows:
1. 识别选项：确认用户纠结的具体选项（Option A vs Option B）。
2. 引导定义维度："在做这个决定时，您最看重什么？（例如：金钱回报、稳定性、个人成长、家庭时间）"
3. 引导定义权重："请给上述每个维度打分（1-5分），总分10分。"
4. 引导打分："请给 Option A 和 Option B 在每个维度上打分（1-10分）。"
5. 计算结果：自动生成分数对比表。
6. 输出结论：告诉用户哪个分数高，但最后强调"分数只是参考，选择权在您"。
7. 输出格式：必须包含 {"selected_option": "XXX", "reason": "XXX", "reconnect_point": "XXX"}

## Initialization:
我理解这个决定很难。让我们把感性的纠结变成理性的打分。请告诉我：您目前在纠结的两个具体选项是什么？
"""

decide_agent = SimpleAgent(
    name="DecideAgent",
    llm=llm,
    system_prompt=decide_system_prompt
)

# ========================================
# 第4部分:状态管理模块
# ========================================

class ThinkFlowState:
    """ThinkFlow 状态管理器"""
    
    def __init__(self):
        self.current_stage = "clarify"  # clarify, decompose, decide
        self.clarified_goal = ""
        self.wbs_state = {}  # 存储当前 WBS 状态快照
        self.decision_history = []
        self.current_decision_point = None
        self.selected_path = None  # 记录决策后选择的路径
        self.reconnect_point = None  # 记录需要续接的节点
        self.decision_count_in_branch = 0  # 当前分支的决策次数（用于熔断）
        self.MAX_DECISIONS_PER_BRANCH = 2  # 每分支最大决策次数
        self.current_decision_signature = None  # 当前决策点签名（用于判断是否同一分支）
        
    def set_clarified_goal(self, goal):
        """设置已澄清的目标"""
        self.clarified_goal = goal
        
    def set_stage(self, stage):
        """设置当前阶段"""
        self.current_stage = stage
        
    def freeze_wbs(self, wbs_data):
        """冻结当前 WBS 状态"""
        self.wbs_state = wbs_data
        
    def set_decision_point(self, decision_request):
        """设置当前决策点，自动判断是否为新分支并重置计数"""
        import re
        
        # 提取决策点签名（[DECISION_REQUEST] 所在行）
        new_signature = None
        for line in decision_request.split('\n'):
            if "[DECISION_REQUEST]" in line:
                new_signature = line.strip()
                break
        
        # 如果新决策点与上一个不同，说明进入新分支，重置计数
        if new_signature != self.current_decision_signature:
            self.decision_count_in_branch = 0
            self.current_decision_signature = new_signature
        
        self.current_decision_point = decision_request
        
    def record_decision(self, decision):
        """记录决策历史"""
        self.decision_history.append(decision)
        
    def set_selected_path(self, path):
        """设置选择的路径"""
        self.selected_path = path
        
    def set_reconnect_point(self, point):
        """设置续接节点"""
        self.reconnect_point = point
        
    def clear_reconnect_info(self):
        """清空续接信息（续接完成后调用）"""
        self.selected_path = None
        self.reconnect_point = None
        
    def increment_decision_count(self):
        """增加当前分支决策计数"""
        self.decision_count_in_branch += 1
        
    def reset_decision_count(self):
        """重置当前分支决策计数（进入新分支时调用）"""
        self.decision_count_in_branch = 0
        
    def is_decision_limit_reached(self):
        """检查是否达到决策熔断阈值"""
        return self.decision_count_in_branch >= self.MAX_DECISIONS_PER_BRANCH
        
    def get_context(self):
        """获取当前上下文"""
        return {
            "stage": self.current_stage,
            "goal": self.clarified_goal,
            "wbs": self.wbs_state,
            "decision_history": self.decision_history,
            "selected_path": self.selected_path,
            "reconnect_point": self.reconnect_point
        }

# ========================================
# 第5部分:核心工作流
# ========================================

class ThinkFlowController:
    """ThinkFlow 工作流控制器"""
    
    def __init__(self):
        self.state = ThinkFlowState()
        self.agents = {
            "clarify": clarify_agent,
            "decompose": decompose_agent,
            "decide": decide_agent
        }
        
    def run_clarify(self, user_input):
        """执行澄清阶段"""
        print("\n=== [澄清期] ===")
        print(f"用户输入: {user_input}")
        
        response = self.agents["clarify"].run(user_input)
        print(f"\nClarifyAgent: {response}")
        
        # 询问用户是否需要继续澄清
        confirm = input("\n以上理解是否准确？(y/n): ").strip().lower()
        if confirm == "y" or confirm == "yes":
            # 提取结构化的目标陈述（寻找 [CLARIFIED_GOAL] 标记）
            import re
            goal_match = re.search(r'\[CLARIFIED_GOAL\](.*?)\[/CLARIFIED_GOAL\]', response, re.DOTALL)
            if goal_match:
                clarified_goal = goal_match.group(1).strip()
            else:
                # 如果没有标记，使用整段回复
                clarified_goal = response
                
            # 记录澄清结果
            self.state.set_clarified_goal(clarified_goal)
            self.state.set_stage("decompose")
            print(f"\n目标已澄清: {clarified_goal}")
            print("进入拆解阶段。")
            return True
        else:
            print("\n请继续描述您的需求...")
            return False
            
    def run_decompose(self, goal, reconnect_context=None):
        """执行拆解阶段"""
        print("\n=== [拆解期] ===")
        
        # 构建提示词：如果有续接上下文，拼接续接提示
        if reconnect_context and reconnect_context.get('reconnect_point'):
            prompt = f"""基于以下已完成的拆解和决策结果，继续拆解剩余部分：
            
【已完成的 WBS 状态】
{reconnect_context['wbs']}

【已选择的路径】
{reconnect_context['selected_path']}

【需要续接的节点】
{reconnect_context['reconnect_point']}

请从 {reconnect_context['reconnect_point']} 节点继续向下拆解，生成 Level 2 及以下的任务结构。
"""
            print(f"续接拆解目标: {reconnect_context['reconnect_point']}")
        else:
            prompt = f"请拆解目标：{goal}"
            print(f"拆解目标: {goal}")
        
        response = self.agents["decompose"].run(prompt)
        print(f"\nDecomposeAgent: {response}")
        
        # 检测决策点（只检测 [DECISION_REQUEST] 标记，避免误判）
        if "[DECISION_REQUEST]" in response:
            # 检查决策熔断阈值
            if self.state.is_decision_limit_reached():
                print("\n❌ 决策次数已达上限，需要手动介入。")
                print("当前分支已进行 {} 次决策，建议手动调整方案或结束任务。".format(
                    self.state.decision_count_in_branch))
                self.state.set_stage("completed")
                return "completed"
                
            print("\n⚠️ 检测到决策点，需要先进行决策。")
            # 保存当前 WBS 状态快照
            self.state.freeze_wbs(response)
            self.state.set_decision_point(response)
            self.state.set_stage("decide")
            return "decision_needed"
        
        # 如果之前有续接信息，现在续接完成，清空续接信息
        if self.state.selected_path or self.state.reconnect_point:
            self.state.clear_reconnect_info()
        
        # 询问用户下一步
        choice = input("\n您想深入拆解哪个分支？(输入序号或'完成'): ").strip()
        if choice == "完成":
            self.state.set_stage("completed")
            return "completed"
        
        return "continue"
        
    def run_decide(self, decision_context):
        """执行决策阶段"""
        print("\n=== [决策期] ===")
        
        # 只显示决策请求相关的内容，提升演示体验
        import re
        decision_line = ""
        # 查找 [DECISION_REQUEST] 所在的行
        for line in decision_context.split('\n'):
            if "[DECISION_REQUEST]" in line:
                decision_line = line.strip()
                break
        
        if decision_line:
            print(f"决策请求: {decision_line}")
        else:
            # 如果没找到，只显示前50个字符作为摘要
            summary = decision_context[:50] + "..." if len(decision_context) > 50 else decision_context
            print(f"决策上下文: {summary}")
        
        # 从决策上下文中解析选项（寻找 [DECISION_REQUEST] 后的选项）
        options = ""
        # 限定在 [DECISION_REQUEST] 同一行内搜索，避免跨行误匹配
        decision_match = re.search(r'\[DECISION_REQUEST\][^\n]*选项[：:]\s*(.+)', decision_context)
        if decision_match:
            options = decision_match.group(1).strip()
            # 清理选项格式（移除 A. B. 等标记）
            options = re.sub(r'^[A-Z]\.\s*', '', options)
            options = re.sub(r'\s*[A-Z]\.\s*', ', ', options)
        
        # 让用户确认或修改选项
        if options:
            user_input = input(f"检测到选项：{options}\n按回车确认，或输入新选项（用逗号分隔）: ").strip()
            if user_input:
                options = user_input
        else:
            options = input("请输入两个选项（用逗号分隔）: ").strip()
        
        response = self.agents["decide"].run(f"选项：{options}")
        print(f"\nDecideAgent: {response}")
        
        # 记录决策并增加决策计数
        self.state.record_decision(response)
        self.state.increment_decision_count()
        
        # 解析决策结果，提取选择的路径和续接点
        # 尝试从响应中提取 JSON 格式（优先寻找 ```json ... ``` 代码块）
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        
        selected_path = None
        reconnect_point = None
        
        if json_match:
            try:
                import json
                decision_data = json.loads(json_match.group(1))
                selected_path = decision_data.get("selected_option")
                reconnect_point = decision_data.get("reconnect_point")
            except:
                # 解析失败，降级处理
                pass
        
        # 如果解析失败或结果为空，使用用户输入的第一个选项
        if not selected_path:
            selected_path = options.split(",")[0].strip() if "," in options else options
        
        # reconnect_point 为空时设为 None，避免传递空字符串
        self.state.set_selected_path(selected_path)
        self.state.set_reconnect_point(reconnect_point)
        
        self.state.set_stage("decompose")
        
        return response
        
    def start(self):
        """启动 ThinkFlow"""
        print("\n" + "="*60)
        print("      ThinkFlow - AI 思维教练")
        print("="*60)
        print("\n您好！我是您的思维教练，帮助您理清思路、拆解任务。")
        print("请告诉我您目前遇到的困惑或想要实现的目标...")
        
        # 阶段1: 澄清
        while True:
            user_input = input("\n>>> ").strip()
            if user_input.lower() == "退出":
                print("再见！希望我的帮助对您有帮助。")
                return
            
            success = self.run_clarify(user_input)
            if success:
                break
        
        # 阶段2/3: 拆解与决策（循环）
        while True:
            if self.state.current_stage == "decompose":
                # 检查是否需要续接
                if self.state.selected_path and self.state.reconnect_point:
                    # 构建续接上下文
                    reconnect_context = {
                        "wbs": self.state.wbs_state,
                        "selected_path": self.state.selected_path,
                        "reconnect_point": self.state.reconnect_point
                    }
                    result = self.run_decompose(self.state.clarified_goal, reconnect_context)
                else:
                    result = self.run_decompose(self.state.clarified_goal)
                
                if result == "decision_needed":
                    # 需要决策
                    decision_result = self.run_decide(self.state.current_decision_point)
                    print(f"\n决策完成: {decision_result}")
                    # 继续拆解（会自动续接到选择的节点）
                    continue
                
                elif result == "completed":
                    print("\n🎉 任务拆解完成！")
                    break
                
            elif self.state.current_stage == "completed":
                break
        
        print("\n" + "="*60)
        print("           思考旅程结束")
        print("="*60)
        print("\n您的决策历史:")
        for i, decision in enumerate(self.state.decision_history, 1):
            print(f"  {i}. {decision}")
        print("\n感谢使用 ThinkFlow！")

# ========================================
# 第6部分:功能演示
# ========================================

def run_demo():
    """运行演示示例"""
    print("\n" + "="*60)
    print("         ThinkFlow - 功能演示")
    print("="*60)
    
    # 示例1: 澄清阶段测试
    print("\n=== 示例1: 澄清阶段 ===")
    test_input = "老板让我提升用户留存，我不知道从哪下手。"
    print(f"用户输入: {test_input}")
    result = clarify_agent.run(test_input)
    print(f"\nClarifyAgent 响应:\n{result}")
    
    # 示例2: 拆解阶段测试
    print("\n" + "="*60)
    print("=== 示例2: 拆解阶段 ===")
    test_goal = "写一篇关于AI智能体的毕业论文"
    print(f"目标: {test_goal}")
    result = decompose_agent.run(f"请拆解目标：{test_goal}")
    print(f"\nDecomposeAgent 响应:\n{result}")
    
    # 示例3: 决策阶段测试
    print("\n" + "="*60)
    print("=== 示例3: 决策阶段 ===")
    test_options = "学大模型, 学智能体"
    print(f"选项: {test_options}")
    result = decide_agent.run(f"选项：{test_options}")
    print(f"\nDecideAgent 响应:\n{result}")

# ========================================
# 主程序入口
# ========================================

if __name__ == "__main__":
    # 创建控制器
    controller = ThinkFlowController()
    
    # 显示菜单
    print("\n" + "="*60)
    print("      ThinkFlow - AI 思维教练")
    print("="*60)
    print("\n请选择运行模式:")
    print("1. 交互模式（完整工作流）")
    print("2. 演示模式（预定义示例）")
    
    choice = input("\n请输入选择 (1/2): ").strip()
    
    if choice == "1":
        # 启动交互模式
        controller.start()
    elif choice == "2":
        # 运行演示模式
        run_demo()
    else:
        print("无效选择，默认运行演示模式。")
        run_demo()
