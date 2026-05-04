"""
第十二章示例2：BFCL快速开始

对应文档：12.2.5 在HelloAgents中实现BFCL评估 - 方式1

这是最简单的BFCL评估方式，一行代码完成评估、报告生成和官方评估。
"""
from dotenv import load_dotenv
load_dotenv()
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import BFCLEvaluationTool

# 1. 创建要评估的智能体
llm = HelloAgentsLLM()
agent = SimpleAgent(name="TestAgent", llm=llm)

# 2. 创建BFCL评估工具
bfcl_tool = BFCLEvaluationTool()

# 3. 运行评估（自动完成所有步骤）
results = bfcl_tool.run(
    agent=agent,
    category="simple_python",  # 评估类别
    max_samples=5              # 评估样本数（0表示全部）
)

# 4. 查看结果
print(f"准确率: {results['overall_accuracy']:.2%}")
print(f"正确数: {results['correct_samples']}/{results['total_samples']}")

# 运行输出示例：
# ============================================================
# BFCL一键评估
# ============================================================
# 
# 配置:
#    智能体: TestAgent
#    类别: simple_python
#    样本数: 5
# 
# 评估进度: 100%|██████████| 5/5 [00:15<00:00,  3.12s/样本]
# 
# ✅ 评估完成
#    总样本数: 5
#    正确样本数: 5
#    准确率: 100.00%
# 
# 准确率: 100.00%
# 正确数: 5/5

