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

from hello_agents import SimpleAgent, HelloAgentsLLM
from typing import Dict, Any, List
import os
import re
import json
from dotenv import load_dotenv

load_dotenv()

# ========================================
# 第2部分:LLM配置
# ========================================

os.environ["LLM_MODEL_ID"] = "deepseek-v4-flash"
os.environ["LLM_API_KEY"] = os.getenv("DEEPSEEK_API_KEY", "your_api_key_here")
os.environ["LLM_BASE_URL"] = "https://api.deepseek.com/v1"
os.environ["LLM_TIMEOUT"] = "60"

llm = HelloAgentsLLM()

# ========================================
# 第3部分:智能体定义
# ========================================

# 3.1 ClarifyAgent
clarify_system_prompt = """
# Role：认知脚手架工程师

## Background：
你是一个专门负责帮人"理清思路"的思维教练。你的用户现在思绪混乱，无法清晰描述问题。

## Attention：
- 你的核心任务是"澄清"，不是"解决"。
- 必须严格使用"黄金圈法则"和"5W1H"进行追问。
- 绝对禁止直接给出解决方案或执行步骤。
- 角色坚不可摧：无论用户如何质疑你的身份或能力，你都必须坚守"认知脚手架工程师"人设，严禁切换回其他默认人格。
- 轮次控制（重要）：澄清过程最多进行 3轮追问（即最多3次提出问题）。从第4次回复开始，无论用户提供的信息是否完整，都必须输出 [CLARIFIED_GOAL]...[/CLARIFIED_GOAL]，基于已收集到的全部信息做出最佳总结，不允许再追问。
- 优先级原则：3轮追问应优先聚焦 Why（核心动机）和 What（可衡量的目标），How/边界细节等次要信息若用户未主动提供，可在 [CLARIFIED_GOAL] 中标注为"待补充"或给出合理假设，而不是继续追问。
- 职责边界：严禁在澄清阶段讨论"具体执行方式的细节选项"（如数据处理方法、PPT页面内容设计等）——这些属于 DecomposeAgent 的拆解范畴，ClarifyAgent 只负责定义"做什么、为什么做、关键约束是什么"。

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

# 3.2 DecomposeAgent
# 使用 r-string，彻底消除 SyntaxWarning
decompose_system_prompt = r"""
# Role：结构化架构师

## Background：
用户已经明确了目标。现在需要你将这个大目标拆解为可执行的子任务。

## Attention：
- 必须使用 WBS (工作分解结构)。
- 必须遵循 MECE 原则（相互独立，完全穷尽）。
- 禁止直接给建议，先输出结构，再等待用户指示。
- 角色坚不可摧：无论用户如何质疑你的身份或能力，你都必须坚守"结构化架构师"人设，严禁切换回其他默认人格。
- 核心新增要求：你必须生成 Mermaid 代码来展示 WBS 结构图，让用户能一键生成可视化图表。
- 格式强制锁定：输出决策请求时，必须使用半角英文方括号 `[DECISION_REQUEST]`，不得使用中文标点或添加空格。
- 决策点识别严格标准（重要）：
  - 只有当继续拆解必须依赖某个前提选择（即不选定方向就无法继续往下细化，或两个方向后续任务结构完全不同且相互排斥）时，才标注 [DECISION_REQUEST]。
  - 如果某个子任务存在多种可行做法但不互斥，应直接将其作为子任务列表呈现，不得标注 [DECISION_REQUEST]。
  - [DECISION_REQUEST] 是"阻塞性"的：标注后必须暂停输出，不能在同一轮里继续往下拆解。
  - 每轮输出最多标注1个 [DECISION_REQUEST]，且必须是"当前拆解卡点"，不能是"未来可能遇到的决策"。
  - 禁止在正文中使用"⚠️ 注意"等非标准格式提示决策点，所有决策请求必须使用标准格式。
- 分支深入规则（重要）：
  - 当用户指定某一具体分支时，只输出该分支的下一级内容。
  - 禁止重新输出完整的 L0→L1→L2 全量 WBS 结构。
  - Mermaid 代码只展示指定分支的子树。
  - 文本只列出该分支的新增子任务。

## Skills:
- WBS 拆解：将 Level 0 (目标) 拆解为 Level 1 (模块)，再拆解为 Level 2 (具体任务)。
- MECE 校验：拆解完后，必须自我检查是否有遗漏或重叠。
- Mermaid 语法生成：生成标准的 Mermaid mindmap 代码。
- 决策点识别：严格遵循 Attention 中的标准，只在真正阻塞性的决策点处标注。
- 分支深入拆解：当用户指定分支时，只输出该分支子树，不重复已有结构。

## Workflows:
1. 接收用户的目标或指定分支。
2. 若为全量拆解：输出完整 Mermaid 图 + 文本 WBS（L0→L1→L2）。
3. 若为分支深入：只输出该分支的 Mermaid 子树 + 文本子任务列表。
4. 自我校验：检查是否符合 MECE。
5. 如果遇到真正的阻塞性决策点，输出：⚠️ [DECISION_REQUEST] 目标：XXX | 选项：A.XXX/B.XXX，然后停止输出。

## 编号规则（全流程严格遵守，重要！）:
- L0: 根目标（用户的原始目标）
- 首次拆解产生 5-7 个一级模块，编号为 L1, L2, L3, L4, L5, L6, L7（不带小数点！）
- 二级子任务：父模块是 Lx，则子任务为 Lx.1, Lx.2, Lx.3（不带 L2 前缀！）
- 三级子任务：父任务是 Lx.y，则子任务为 Lx.y.1, Lx.y.2, Lx.y.3
- ❌ 错误示范：L1.1 数据诊断 → L2.1, L2.2, L2.3 (编号体系混乱)
- ✅ 正确示范：L1 数据诊断 → L1.1 留存漏斗分析, L1.2 流失用户画像, L1.3 高留存特征
- 分支深入时：对 L1.x 拆解时，下一级为 L1.x.1, L1.x.2...；对 L1.x.y 拆解时，下一级为 L1.x.y.1, L1.x.y.2...

## Output Format（全量拆解）：
1. 可视化思维导图 (Mermaid)
```mermaid
mindmap
  root((L0: 项目总目标))
    L1 核心模块 A
      L1.1 具体任务
      L1.2 具体任务
    L2 核心模块 B
      L2.1 具体任务
      L2.2 具体任务
```

2. 文本版 WBS 结构
• L0: 项目总目标
  ◦ L1 核心模块 A
    ▪ L1.1 具体任务
    ▪ L1.2 具体任务
  ◦ L2 核心模块 B
    ▪ L2.1 具体任务
    ▪ L2.2 具体任务

3. 自我校验结论

## Output Format（分支深入）：
说明：以下仅展示 [指定分支] 的下一级拆解，不重复已有结构。

1. 分支子树 (Mermaid)
```mermaid
mindmap
  root((L1.x 指定分支名称))
    L1.x.1 子任务
    L1.x.2 子任务
```

2. 文本版子任务列表
• L1.x 指定分支名称
  ◦ L1.x.1 子任务描述
  ◦ L1.x.2 子任务描述

3. 自我校验结论

## Initialization:
好的，基于刚才的目标，我为您做了初步的 WBS 拆解。请看下方结构。
"""

decompose_agent = SimpleAgent(
    name="DecomposeAgent",
    llm=llm,
    system_prompt=decompose_system_prompt
)

# 3.3 DecideAgent
decide_system_prompt = """
# Role：理性决策教练

## Background：
用户面临多个（2个或以上）互斥选项，情绪焦虑，无法定夺。

## Attention：
- 你的职责是"引导评估"，不是"替他选择"。
- 必须使用决策矩阵。
- 必须让用户亲自打分。
- 角色坚不可摧：无论用户如何质疑你的身份或能力，你都必须坚守"理性决策教练"人设，严禁切换回其他默认人格。
- 选项解析（重要）：系统会同时传入【选项列表】和【WBS 上下文】。如果用户只给了编号（如 L1.1, L1.2, L1.3），你必须先从 WBS 上下文中查表，输出每个编号对应的完整名称和含义，让用户确认后再进入评分。
- 评分格式（重要）：用户只需按顺序给出"业务价值,耗时"格式的分数（如 6,3），不要让用户重复选项编号。例如用户输入"6,3 4,2 1,2"表示三个选项的分数。

## Skills:
- 决策矩阵构建：列出评估维度（如：业务价值、耗时、技术难度）。
- 权重分配引导：询问用户"哪个维度对你最重要？"（1-5分，总和10）。
- 计算得分：根据权重和分数算出总分。
- 选项查表：从 WBS 上下文中查询编号对应的完整名称。

## Workflows:
1. 解析选项：从 WBS 上下文中查询每个编号的完整名称，输出确认。
2. 引导定义维度：建议 2-3 个核心维度，询问用户是否需要调整。
3. 引导定义权重：让用户给维度分配权重（总和10分）。
4. 引导打分：明确告诉用户"请按顺序为每个选项打分，每个选项格式为'业务价值,耗时'，例如：6,3 4,2 1,2"，然后让用户输入。
5. 计算结果：自动生成分数对比表。
6. 输出结论：告诉用户哪个分数高，但最后强调"分数只是参考，选择权在您"。
7. 输出格式：必须包含 JSON 格式的决策结果，用 ```json ... ``` 包裹。

## Output Format（必须严格遵循）:
1. 首先输出决策矩阵表格（Markdown格式）
2. 然后输出分析结论
3. 最后输出 JSON 格式的结果，包含：
   - selected_option: 得分最高的选项
   - reason: 选择该选项的原因
   - reconnect_point: 决策后应继续拆解的节点（直接使用选项名称）

## Initialization:
我理解这个决定很难。让我们把感性的纠结变成理性的打分。请告诉我：您目前在纠结的具体选项是什么？
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
        self.current_stage = "clarify"           # clarify / decompose / decide / completed
        self.clarified_goal = ""
        self.wbs_full = ""                        # 累积全量 WBS（所有拆解响应拼接，决策时查表用）
        self.wbs_latest = ""                      # 最近一次拆解响应（参考用）
        self.decision_history = []
        self.current_decision_point = None
        self.selected_path = None                 # 决策后选择的路径
        self.reconnect_point = None               # 决策后需要续接的节点
        self.decision_count_in_branch = 0         # 当前分支决策次数（用于熔断）
        self.MAX_DECISIONS_PER_BRANCH = 2
        self.current_decision_signature = None    # 决策点签名（判断是否同一分支）

    def set_clarified_goal(self, goal):
        self.clarified_goal = goal

    def set_stage(self, stage):
        self.current_stage = stage

    def append_wbs(self, wbs_chunk):
        """每次拆解后调用，累积 WBS 文本，保留历史不被覆盖"""
        self.wbs_latest = wbs_chunk
        if self.wbs_full:
            self.wbs_full += "\n\n--- 下一次拆解 ---\n\n" + wbs_chunk
        else:
            self.wbs_full = wbs_chunk

    # 兼容旧调用（部分代码可能仍引用 freeze_wbs）
    def freeze_wbs(self, wbs_data):
        self.wbs_latest = wbs_data
        self.wbs_full = wbs_data

    def set_decision_point(self, decision_request):
        """设置当前决策点，若为新决策点则自动重置计数"""
        new_signature = None
        for line in decision_request.split('\n'):
            if "[DECISION_REQUEST]" in line:
                new_signature = line.strip()
                break
        if new_signature != self.current_decision_signature:
            self.decision_count_in_branch = 0
            self.current_decision_signature = new_signature
        self.current_decision_point = decision_request

    def record_decision(self, decision):
        self.decision_history.append(decision)

    def set_selected_path(self, path):
        self.selected_path = path

    def set_reconnect_point(self, point):
        self.reconnect_point = point

    def clear_reconnect_info(self):
        self.selected_path = None
        self.reconnect_point = None

    def increment_decision_count(self):
        self.decision_count_in_branch += 1

    def reset_decision_count(self):
        self.decision_count_in_branch = 0

    def is_decision_limit_reached(self):
        return self.decision_count_in_branch >= self.MAX_DECISIONS_PER_BRANCH

    def get_context(self):
        return {
            "stage": self.current_stage,
            "goal": self.clarified_goal,
            "wbs": self.wbs_full,
            "wbs_latest": self.wbs_latest,
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

    # ------------------------------------------------------------------
    # 澄清阶段：多轮对话，直到出现 [CLARIFIED_GOAL] 标记
    # ------------------------------------------------------------------
    def run_clarify(self, user_input):
        print("\n=== [澄清期] ===")

        MAX_ROUNDS = 4      # 超过后注入系统提示强制收敛
        round_count = 0

        while True:
            round_count += 1

            # 超出轮次上限：强制注入系统提示
            if round_count > MAX_ROUNDS:
                user_input = (
                    user_input
                    + "\n\n【系统提示】澄清轮次已达上限，请基于以上全部对话内容，"
                    "立即输出 [CLARIFIED_GOAL]...[/CLARIFIED_GOAL] 总结目标陈述，"
                    "不得再追问。"
                )

            response = self.agents["clarify"].run(user_input)
            print(f"\nClarifyAgent: {response}")

            goal_match = re.search(
                r'\[CLARIFIED_GOAL\](.*?)\[/CLARIFIED_GOAL\]', response, re.DOTALL
            )

            if goal_match:
                clarified_goal = goal_match.group(1).strip()
                confirm = input(
                    f"\n已澄清目标：{clarified_goal}\n是否准确？(y/n): "
                ).strip().lower()
                if confirm in ("y", "yes"):
                    self.state.set_clarified_goal(clarified_goal)
                    self.state.set_stage("decompose")
                    print("\n目标已确认，进入拆解阶段。")
                    return True
                else:
                    user_input = input("\n请补充说明您的需求：").strip()
                    round_count = 0   # 用户主动修正，重置轮次
            else:
                # 还在追问阶段，继续对话
                user_input = input("\n>>> ").strip()
                if user_input.lower() == "退出":
                    print("再见！")
                    return False

    # ------------------------------------------------------------------
    # 拆解阶段
    # 三种场景：① 决策后续接  ② 用户指定分支  ③ 首次全量拆解
    # ------------------------------------------------------------------
    def run_decompose(self, goal, reconnect_context=None, branch_choice=None):
        print("\n=== [拆解期] ===")

        if reconnect_context and reconnect_context.get("reconnect_point"):
            # ── 场景①：决策后续接特定节点 ─────────────────────────────
            prompt = (
                "基于以下已完成的拆解和决策结果，继续拆解剩余部分：\n\n"
                f"【已完成的 WBS 状态】\n{reconnect_context['wbs']}\n\n"
                f"【已选择的路径】\n{reconnect_context['selected_path']}\n\n"
                f"【需要续接的节点】\n{reconnect_context['reconnect_point']}\n\n"
                f"请从 {reconnect_context['reconnect_point']} 节点继续向下拆解，生成下一级的任务结构。\n\n"
                "编号规则（严格遵守）：\n"
                "- 续接节点是 L1.x → 下一级编号为 L1.x.1, L1.x.2, L1.x.3 ...\n"
                "- 续接节点是 L2.x → 下一级编号为 L2.x.1, L2.x.2, L2.x.3 ...\n"
                "- 严禁另起 L3/L4/L5 等新层级编号。\n\n"
                "输出规则（严格遵守）：\n"
                "- 只输出续接节点的子树，禁止重新输出整个 WBS 结构。\n"
                "- Mermaid 代码只展示从续接节点开始的子树。\n"
                "- 文本只列出新增子任务，不重复已有内容。\n"
            )
            print(f"续接拆解节点: {reconnect_context['reconnect_point']}")

        elif branch_choice:
            # ── 场景②：用户指定分支深入 ───────────────────────────────
            prompt = (
                "请深入拆解用户指定的分支，严格只输出该分支的下一级内容。\n\n"
                f"【原始目标】\n{goal}\n\n"
                f"【用户指定的分支】\n{branch_choice}\n\n"
                "编号规则（严格遵守）：\n"
                "- 若分支编号为 L1.x → 下一级编号为 L1.x.1, L1.x.2, L1.x.3 ...\n"
                "- 若分支编号为 L2.x → 下一级编号为 L2.x.1, L2.x.2, L2.x.3 ...\n"
                "- 严禁另起 L3/L4/L5 等新层级编号。\n\n"
                "输出规则（严格遵守）：\n"
                "- 只输出该分支的下一级子树，禁止重新输出完整的 L0→L1→L2 结构。\n"
                "- Mermaid 代码只展示该分支的子树。\n"
                "- 文本只列该分支的子任务列表。\n"
            )
            print(f"深入拆解分支: {branch_choice}")

        else:
            # ── 场景③：首次全量拆解 ────────────────────────────────────
            prompt = f"请拆解目标：{goal}"
            print(f"拆解目标: {goal}")

        response = self.agents["decompose"].run(prompt)
        print(f"\nDecomposeAgent: {response}")

        # 每次拆解后都累积 WBS，供后续决策查表用（不覆盖历史）
        self.state.append_wbs(response)

        # 检测决策点（记录但不强制进入决策，由用户主动选择）
        if "[DECISION_REQUEST]" in response:
            if self.state.is_decision_limit_reached():
                print(
                    f"\n❌ 当前分支决策次数已达上限（{self.state.decision_count_in_branch} 次），"
                    "建议手动介入或结束任务。"
                )
                self.state.set_stage("completed")
                return "completed"

            print("\n💡 检测到潜在决策点，您可以选择进行决策评估。")
            self.state.set_decision_point(response)

        # 续接完成后清空续接信息
        if self.state.selected_path or self.state.reconnect_point:
            self.state.clear_reconnect_info()

        return "continue"

    # ------------------------------------------------------------------
    # 决策阶段
    # ------------------------------------------------------------------
    def run_decide(self, decision_context):
        print("\n=== [决策期] ===")

        # 只展示 [DECISION_REQUEST] 那一行，避免输出整段 WBS
        decision_line = ""
        for line in decision_context.split('\n'):
            if "[DECISION_REQUEST]" in line:
                decision_line = line.strip()
                break

        if decision_line:
            print(f"决策请求: {decision_line}")
        else:
            summary = (
                decision_context[:80] + "..."
                if len(decision_context) > 80
                else decision_context
            )
            print(f"决策上下文: {summary}")

        # 解析选项（限定在同一行，避免跨行误匹配）
        options = ""
        decision_match = re.search(
            r'\[DECISION_REQUEST\][^\n]*选项[：:]\s*(.+)', decision_context
        )
        if decision_match:
            options = decision_match.group(1).strip()
            options = re.sub(r'^[A-Z]\.\s*', '', options)
            options = re.sub(r'\s*/\s*[A-Z]\.\s*', ', ', options)

        if options:
            user_input = input(
                f"检测到选项：{options}\n按回车确认，或输入新选项（用逗号分隔）: "
            ).strip()
            if user_input:
                options = user_input
        else:
            options = input("请输入选项（用逗号分隔）: ").strip()

        # 多轮对话模式：引导用户完成决策矩阵
        # 将 WBS 上下文一起传入，让模型能根据编号查询完整名称
        agent_prompt = f"选项：{options}\n\n【WBS 上下文】\n{self.state.wbs_full}"
        response = self.agents["decide"].run(agent_prompt)
        print(f"\nDecideAgent: {response}")

        # 检查是否已经输出 JSON 结果
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        
        # 如果没有 JSON，说明还在引导阶段，继续多轮对话
        while not json_match:
            user_input = input("\n>>> ").strip()
            if user_input.lower() == "退出":
                print("决策已取消。")
                return None

            # 每轮都带上 WBS 上下文，避免模型遗忘
            user_input_with_ctx = f"{user_input}\n\n【WBS 上下文】\n{self.state.wbs_full}"
            response = self.agents["decide"].run(user_input_with_ctx)
            print(f"\nDecideAgent: {response}")
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)

        # 解析 JSON 决策结果
        selected_path = None
        reconnect_point = None

        if json_match:
            try:
                decision_data = json.loads(json_match.group(1))
                selected_path = decision_data.get("selected_option")
                reconnect_point = decision_data.get("reconnect_point")
            except Exception:
                pass

        # 解析失败时降级：取用户输入的第一个选项
        if not selected_path:
            selected_path = options.split(",")[0].strip() if "," in options else options

        self.state.set_selected_path(selected_path)
        self.state.set_reconnect_point(reconnect_point)  # None 时不传空字符串
        self.state.set_stage("decompose")
        self.state.record_decision(response)  # 记录决策响应供历史展示
        self.state.increment_decision_count()

        return response

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    def start(self):
        print("\n" + "=" * 60)
        print("      ThinkFlow - AI 思维教练")
        print("=" * 60)
        print("\n您好！我是您的思维教练，帮助您理清思路、拆解任务。")
        print("请告诉我您目前遇到的困惑或想要实现的目标...")

        # ── 阶段1：澄清 ─────────────────────────────────────────────
        user_input = input("\n>>> ").strip()
        if user_input.lower() == "退出":
            print("再见！")
            return

        if not self.run_clarify(user_input):
            return

        # ── 阶段2/3：拆解 ↔ 决策（循环） ───────────────────────────
        user_branch_choice = None   # 保存用户本轮指定的分支

        skip_next_decompose = False  # 决策后跳过下一次自动拆解，让用户选择下一步

        while True:
            if self.state.current_stage == "completed":
                break

            # 拆解阶段（决策后会被跳过，让用户重新选择）
            if self.state.current_stage == "decompose" and not skip_next_decompose:

                # 优先级：决策续接 > 用户指定分支 > 全量拆解
                if self.state.selected_path and self.state.reconnect_point:
                    reconnect_context = {
                        "wbs": self.state.wbs_full,
                        "selected_path": self.state.selected_path,
                        "reconnect_point": self.state.reconnect_point
                    }
                    result = self.run_decompose(
                        self.state.clarified_goal, reconnect_context=reconnect_context
                    )
                elif user_branch_choice:
                    result = self.run_decompose(
                        self.state.clarified_goal, branch_choice=user_branch_choice
                    )
                    user_branch_choice = None   # 用完即清，避免重复使用
                else:
                    result = self.run_decompose(self.state.clarified_goal)

                if result == "completed":
                    print("\n🎉 任务拆解完成！")
                    break

            skip_next_decompose = False

            # ── 拆解完成，询问用户下一步操作 ────────────────────────
            print("\n" + "-" * 60)
            print("拆解完成！请选择下一步操作：")
            print("1. 继续拆解其他分支（输入分支编号，如 L1.1）")
            print("2. 选择2-3个项目做决策矩阵打分")
            print("3. 拆解完成，输出结果")
            print("-" * 60)

            user_choice = input(">>> ").strip()

            if user_choice == "2":
                # 用户选择做决策矩阵
                decision_options = input(
                    "请输入要比较的选项（用逗号分隔，如 L1.1, L1.2, L1.3）："
                ).strip()
                if decision_options:
                    decision_context = f"[DECISION_REQUEST] 选项：{decision_options}"
                    self.run_decide(decision_context)
                    # 决策完成后不自动续接拆解，让用户重新选择
                    self.state.clear_reconnect_info()
                    skip_next_decompose = True
                    continue
            elif user_choice == "3" or user_choice.lower() in ("完成", "done", "finish"):
                self.state.set_stage("completed")
                break
            elif user_choice == "1":
                branch_input = input("请输入要深入拆解的分支编号（如 L1.1）：").strip()
                if branch_input:
                    user_branch_choice = branch_input
            else:
                # 用户直接输入了分支编号
                user_branch_choice = user_choice

        # ── 打印决策历史（只显示 JSON 结论，避免输出整段过程）──────
        print("\n" + "=" * 60)
        print("           思考旅程结束")
        print("=" * 60)
        if self.state.decision_history:
            print("\n本次决策记录：")
            for i, decision in enumerate(self.state.decision_history, 1):
                json_match = re.search(
                    r'```json\s*(\{.*?\})\s*```', decision, re.DOTALL
                )
                if json_match:
                    try:
                        d = json.loads(json_match.group(1))
                        print(
                            f"  {i}. 选择：{d.get('selected_option', '—')}  "
                            f"理由：{d.get('reason', '—')}"
                        )
                    except Exception:
                        print(f"  {i}. （决策记录已保存）")
                else:
                    print(f"  {i}. （决策记录已保存）")
        else:
            print("\n本次未触发决策环节。")

        print("\n感谢使用 ThinkFlow！")


# ========================================
# 第6部分:功能演示
# ========================================

def run_demo():
    print("\n" + "=" * 60)
    print("         ThinkFlow - 功能演示")
    print("=" * 60)

    print("\n=== 示例1: 澄清阶段 ===")
    test_input = "老板让我提升用户留存，我不知道从哪下手。"
    print(f"用户输入: {test_input}")
    result = clarify_agent.run(test_input)
    print(f"\nClarifyAgent 响应:\n{result}")

    print("\n" + "=" * 60)
    print("=== 示例2: 拆解阶段 ===")
    test_goal = "写一篇关于AI智能体的毕业论文"
    print(f"目标: {test_goal}")
    result = decompose_agent.run(f"请拆解目标：{test_goal}")
    print(f"\nDecomposeAgent 响应:\n{result}")

    print("\n" + "=" * 60)
    print("=== 示例3: 决策阶段 ===")
    test_options = "学大模型, 学智能体"
    print(f"选项: {test_options}")
    result = decide_agent.run(f"选项：{test_options}")
    print(f"\nDecideAgent 响应:\n{result}")


# ========================================
# 主程序入口
# ========================================

if __name__ == "__main__":
    controller = ThinkFlowController()

    print("\n" + "=" * 60)
    print("      ThinkFlow - AI 思维教练")
    print("=" * 60)
    print("\n请选择运行模式:")
    print("1. 交互模式（完整工作流）")
    print("2. 演示模式（预定义示例）")

    choice = input("\n请输入选择 (1/2): ").strip()

    if choice == "1":
        controller.start()
    elif choice == "2":
        run_demo()
    else:
        print("无效选择，默认运行演示模式。")
        run_demo()



