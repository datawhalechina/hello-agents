"""
第十二章示例5：GAIA快速开始

对应文档：12.3.5 在HelloAgents中实现GAIA评估 - 方式1

这是最简单的GAIA评估方式，一行代码完成评估。

重要提示：
1. GAIA是受限数据集，需要先在HuggingFace上申请访问权限
2. 需要设置HF_TOKEN环境变量
3. 必须使用GAIA官方系统提示词
"""
from dotenv import load_dotenv
load_dotenv()
import os
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import GAIAEvaluationTool
# GAIA官方系统提示词（必须使用）
GAIA_SYSTEM_PROMPT = """You are a general AI assistant. I will ask you a question. Report your thoughts, and finish your answer with the following template: FINAL ANSWER: [YOUR FINAL ANSWER].
YOUR FINAL ANSWER should be a number OR as few words as possible OR a comma separated list of numbers and/or strings.
If you are asked for a number, don't use comma to write your number neither use units such as $ or percent sign unless specified otherwise.
If you are asked for a string, don't use articles, neither abbreviations (e.g. for cities), and write the digits in plain text unless specified otherwise.
If you are asked for a comma separated list, apply the above rules depending of whether the element to be put in the list is a number or a string."""

# 1. 设置HuggingFace Token（如果还没设置）
# os.environ["HF_TOKEN"] = "your_huggingface_token_here"

# 2. 创建智能体（必须使用GAIA官方系统提示词）
llm = HelloAgentsLLM()
agent = SimpleAgent(
    name="TestAgent",
    llm=llm,
    system_prompt=GAIA_SYSTEM_PROMPT  # 必须使用官方提示词
)

# 3. 创建GAIA评估工具
gaia_tool = GAIAEvaluationTool()

# 4. 运行评估
results = gaia_tool.run(
    agent=agent,
    level=1,              # 评估级别（1=简单，2=中等，3=困难）
    max_samples=2,        # 评估样本数（0表示全部）
    export_results=True,  # 导出结果到GAIA官方格式
    generate_report=True  # 生成详细报告
)

# 5. 查看结果
print(f"\n评估结果:")
if "error" in results:
    print(f"❌ 评估失败: {results['error']}")
else:
    print(f"精确匹配率: {results['exact_match_rate']:.2%}")
    print(f"部分匹配率: {results['partial_match_rate']:.2%}")
    print(f"正确数: {results.get('correct_samples', results.get('exact_matches', 0))}/{results['total_samples']}")

# 运行输出示例：
# ============================================================
# GAIA一键评估
# ============================================================
# 
# 配置:
#    智能体: TestAgent
#    级别: Level 1
#    样本数: 2
# 
# ✅ GAIA数据集加载完成
#    数据源: gaia-benchmark/GAIA
#    分割: validation
#    级别: 1
#    样本数: 2
# 
# 评估进度: 100%|██████████| 2/2 [00:10<00:00,  5.23s/样本]
# 
# ✅ 评估完成
#    总样本数: 2
#    正确样本数: 2
#    精确匹配率: 100.00%
#    部分匹配率: 100.00%
# 
# ✅ 结果已导出到 ./evaluation_results/gaia_submission.json
# ✅ 报告已生成到 ./evaluation_results/gaia_report.md
# 
# 评估结果:
# 精确匹配率: 100.00%
# 部分匹配率: 100.00%
# 正确数: 2/2

