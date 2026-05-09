"""
10.3.4 在智能体中使用A2A工具
（2）实战案例：论文写作团队（研究员、撰写员、审稿人协作）

研究员(Researcher): 负责研究和收集资料
撰写员(Writer): 负责撰写论文内容
审稿人(Reviewer): 负责评审论文质量并提出修改建议

扩展功能：
- 冲突解决：协商(negotiation)和投票(voting)机制
"""

from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import A2ATool
from hello_agents.protocols import A2AServer
from hello_agents.protocols.a2a.conflict_resolution import (
    ConflictResolver,
    ConflictStrategy,
)
import threading
import time
from dotenv import load_dotenv

load_dotenv()
llm = HelloAgentsLLM()

conflict_resolver = ConflictResolver(strategy=ConflictStrategy.VOTING)

# ============ 1. 创建研究员Agent服务 ============
researcher = A2AServer(name="researcher", description="研究员，负责研究和收集资料")


@researcher.skill("research")
def do_research(topic: str) -> str:
    return f"""## 研究资料：{topic}

1. 背景介绍
   - {topic}是当前研究热点
   - 有很多相关文献和研究成果

2. 主要观点
   - 观点A：基于xxx理论...
   - 观点B：根据xxx研究...
   - 观点C：实践表明...

3. 参考资料
   - [1] Smith et al. (2023) - Introduction to {topic}
   - [2] Zhang et al. (2024) - Advanced studies in {topic}
   - [3] Johnson (2024) - Practical applications"""


@researcher.skill("search_papers")
def search_papers(keyword: str) -> str:
    return f"""找到与'{keyword}'相关的论文：
- Paper 1: "{keyword}的现状与展望" (2024)
- Paper 2: "基于{keyword}的新方法" (2023)
- Paper 3: "{keyword}理论与实践" (2023)"""


# ============ 2. 创建撰写员Agent服务 ============
writer = A2AServer(name="writer", description="撰写员，负责撰写论文内容")


@writer.skill("write")
def write_paper(topic: str, content: str = "") -> str:
    if content:
        return f"""## {topic}

### 摘要
本文研究了{topic}，通过分析相关理论和实践，提出了新的视角和方法。

### 引言
{topic}是...

### 方法
本研究采用文献综述和案例分析相结合的方法...

### 结论
基于研究发现，我们得出以下结论：{content}

### 参考文献
[1] Smith et al. (2023)
[2] Zhang et al. (2024)
"""
    return f"""## {topic}

### 摘要
本文研究了{topic}，通过分析相关理论和实践，提出了新的视角和方法。

### 引言
{topic}是当前研究的热点问题...

### 方法
本研究采用文献综述和案例分析相结合的方法...

### 结论
本研究为{topic}提供了新的理论框架和实践指导。

### 参考文献
[1] Smith et al. (2023)
[2] Zhang et al. (2024)
"""


@writer.skill("revise")
def revise_paper(paper: str, feedback: str) -> str:
    return f"""## 修改后的论文

根据审稿人反馈进行了以下修改：

### 采纳的修改建议：
{feedback}

### 修改内容：
1. 补充了相关文献综述
2. 增加了实验验证部分
3. 完善了结论的描述

### 修改后的论文内容：
{paper[:200]}...

(完整论文已根据反馈修改)
"""


# ============ 3. 创建审稿人Agent服务 ============
reviewer = A2AServer(
    name="reviewer", description="审稿人，负责评审论文质量并提出修改建议"
)


@reviewer.skill("review")
def review_paper(paper: str) -> str:
    return """## 审稿意见

### 总体评价
论文结构完整，但存在以下问题需要修改：

### 具体问题：
1. **引言部分** - 应更详细地介绍研究背景和��义
2. **方法论** - 建议补充具体的实验设计细节
3. **数据分析** - 需要增加更多的统计验证
4. **结论** - 结论部分过于笼统，应更具体

### 修改建议：
- 增加1000字左右的文献综述
- 补充实验方法的详细描述
- 增加表格或图表来展示数据
- 细化结论，每一点都要有数据支撑

### 评分：72/100 (需要修改后重审)
"""


@reviewer.skill("final_review")
def final_review(paper: str) -> str:
    return """## 最终审稿意见

### 审稿结论：接受(Accepted)

### 评价：
论文已经根据审稿意见进行了充分修改：
- 文献综述完整且具有代表性
- 方法论描述清晰
- 数据分析充分
- 结论有数据支撑

### 小建议（可选）：
- 可考虑增加更多的应用场景讨论
- 建议 future work 可以扩展到其他领域

### 最终评分：85/100
"""


# ============ 4. 启动服务 ============
threading.Thread(target=lambda: researcher.run(port=6000), daemon=True).start()
threading.Thread(target=lambda: writer.run(port=6001), daemon=True).start()
threading.Thread(target=lambda: reviewer.run(port=6002), daemon=True).start()
time.sleep(2)

# ============ 5. 创建主编Agent（协调三个智能体协作）===========
editor = SimpleAgent(
    name="主编",
    llm=llm,
    system_prompt="""你是论文主编，负责协调研究员、撰写员和审稿人三个角色完成论文写作。

协作流程：
1. 首先让研究员(Researcher)研究主题并收集资料
2. 然后让撰写员(Writer)根据研究资料撰写论文
3. 让审稿人(Reviewer)评审论文并提出修改建议
4. 根据审稿意见让撰写员修改论文
5. 再次让审稿人审稿，直到通过为止

请协调好三个智能体的工作，确保论文质量。
""",
)

researcher_tool = A2ATool(
    agent_url="http://localhost:6000",
    name="researcher",
    description="研究员，负责研究和收集资料",
)
editor.add_tool(researcher_tool)

writer_tool = A2ATool(
    agent_url="http://localhost:6001", name="writer", description="撰写员，负责撰写论文"
)
editor.add_tool(writer_tool)

reviewer_tool = A2ATool(
    agent_url="http://localhost:6002",
    name="reviewer",
    description="审稿人，负责评审论文",
)
editor.add_tool(reviewer_tool)


# ============ 6. 处理论文写作任务 ============
def handle_paper_writing(topic: str, max_rounds: int = 2):
    print(f"\n{'=' * 60}")
    print(f"论文主题：{topic}")
    print(f"{'=' * 60}")

    current_paper = None
    feedback = None

    for round_num in range(1, max_rounds + 1):
        print(f"\n--- 第 {round_num} 轮协作 ---")

        if round_num == 1:
            print("\n[主编] 步骤1：让研究员收集研究资料...")
            research_result = researcher.skills["research"](topic)

            print("\n[主编] 步骤2：让撰写员撰写论文...")
            current_paper = writer.skills["write"](topic, research_result[:100])

            print("\n[主编] 步骤3：让审稿人评审论文...")
            review_result = reviewer.skills["review"](current_paper)
        else:
            print("\n[主编] 步骤1：根据反馈修改论文...")
            current_paper = writer.skills["revise"](current_paper, feedback)

            print("\n[主编] 步骤2：让审稿人再次审稿...")
            review_result = reviewer.skills["final_review"](current_paper)

        print("\n--- 审稿结果 ---")
        print(review_result)

        if "接受" in review_result or "Accepted" in review_result:
            print("\n✅ 论文已通过审稿！")
            break

        feedback = review_result

    print(f"\n{'=' * 60}")
    print(f"最终论文：{current_paper[:300]}...")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    handle_paper_writing("人工智能在医疗诊断中的应用")

    print("\n" + "=" * 60)
    print("扩展：冲突解决演示")
    print("=" * 60)

    print("\n【场景1】审稿人与研究员对评分有分歧 - 使用投票")
    positions = {"researcher": "评分85", "reviewer": "评分72", "writer": "评分78"}
    result = conflict_resolver.resolve(
        issue="论文评分争议", positions=positions, options=["85", "72", "78"]
    )
    print(f"各方观点: {positions}")
    print(f"投票结果: {result}")

    print("\n【场景2】撰写员与审稿人对修改建议有分歧 - 使用协商")
    positions = {
        "writer": "建议只修改引言部分",
        "reviewer": "建议修改全文",
        "researcher": "建议修改全文",
    }
    result = conflict_resolver.resolve_by_negotiation(
        issue="修改范围",
        participants=["writer", "reviewer", "researcher"],
        positions=positions,
    )
    print(f"各方观点: {positions}")
    print(f"协商结果: {result}")
