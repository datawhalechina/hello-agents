# -*- coding: utf-8 -*-
"""生成 main.ipynb。

为什么不手写 JSON：notebook 的结构（cell id、metadata、执行计数）手写极易出错，
用 nbformat 生成能保证文件合法，且内容随时可从脚本重建、便于维护。

结构参照教材第十六章 16.4.3 建议的七个部分。

注意：本脚本生成的 notebook **不带执行输出**（执行计数为空）。仓库中随项目交付的
main.ipynb 是执行过的版本（带输出），便于直接查看运行结果；若重跑本脚本会覆盖它，
需要再执行一次 `jupyter nbconvert --execute main.ipynb` 才能恢复带输出的形态。
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


CELLS = [
    md(
        """
# 售后政策应答的多范式实证对比

## 项目简介

同一套售后政策库、同一份系统提示词、同一批评测样本，分别用三种智能体范式处理，
用可复现的数据回答一个问题：**在这个"按规则办事"的客服场景里，检索与自治到底买回了什么，代价是多少？**

三种模式只允许"编排方式"这一个变量变化：

| 模式 | 框架类 | 工具 | 代表的能力档位 |
|---|---|---|---|
| A | `SimpleAgent` | 无 | 直接依赖模型自身知识作答 |
| B | `FunctionCallAgent` | `search_policy` | 原生函数调用检索依据 |
| C | `ReActAgent` | `search_policy`、`list_policies`、`check_compliance` | 多步推理 + 出稿后自检红线 |

## 项目信息

- 来源：Hello-Agents 进阶篇毕业设计
- 日期：2026-09
- 框架：HelloAgents 0.2.9（实测版本）
"""
    ),
    md(
        """
## 第一部分：环境配置

依赖装在 Python 3.10+ 环境中，模型走 OpenAI 兼容协议，配置写在工程根目录的 `.env`。
"""
    ),
    code(
        """
# 首次运行前先安装依赖（已装可跳过）
# !pip install -q -r requirements.txt

import sys
from pathlib import Path

# 保证 notebook 在工程根目录打开时能导入 src 包
PROJECT_ROOT = Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))  # 从当前工作目录逐级向上找 .env，密钥不入库

# 抑制第三方库的导入期警告。这类警告会打印本机绝对路径，而 notebook 的输出
# 是要随项目提交的，不该带上本地环境信息（重新生成后请再执行一次验证）
import warnings

warnings.filterwarnings("ignore")

from src.agents import MODES, AgentRunner
from src.evaluator import load_samples, run_evaluation
from src.retriever import PolicyRetriever
from src.tools import CheckComplianceTool, ListPoliciesTool, SearchPolicyTool, build_registry

print("环境就绪")
"""
    ),
    md(
        """
## 第二部分：政策检索与工具定义

先验检索，再验智能体。检索是所有模式共用的地基：地基不准，
后面的对比就分不清"是没查到"还是"查到了没说对"。
"""
    ),
    code(
        """
retriever = PolicyRetriever(PROJECT_ROOT / "data" / "knowledge_base")

print("知识库概况：")
for key, value in retriever.stats().items():
    print(f"  {key}：{value}")

print("\\n典型检索（不需要启动智能体即可看到依据）：")
for query in ["订单三天还没发货", "退款什么时候到账", "收到的包裹少了一件"]:
    hits = retriever.search(query, top_k=2)
    summary = "；".join(f"{h.rule_id or h.name}（{h.score}）" for h in hits) or "未命中"
    print(f"  「{query}」 -> {summary}")
"""
    ),
    code(
        """
# 三个工具都可以单独验证：它们是纯函数，不依赖模型即可产出结果
print("【search_policy】")
print(SearchPolicyTool(retriever).run({"query": "发货超过 48 小时怎么处理"})[:400])

print("\\n【list_policies】")
print(ListPoliciesTool(retriever).run({"domain": "退换货"})[:400])

print("\\n【check_compliance】")
print(CheckComplianceTool().run({"draft": "请您放心，退款明天一定到账，我们一定给您换新。"}))
"""
    ),
    md("## 第三部分：三种模式的智能体构建"),
    code(
        """
for mode, info in MODES.items():
    print(f"模式 {mode}｜{info['label']}｜{info['agent']}")
    print(f"    能力档位：{info['capability']}")

print("\\n各模式实际装配的工具：")
for mode, tool_mode in (("A", "none"), ("B", "search"), ("C", "full")):
    _, tools = build_registry(retriever, tool_mode)
    print(f"  模式 {mode}：{[tool.name for tool in tools] or '（无工具）'}")
"""
    ),
    md(
        """
## 第四部分：功能演示

同一条工单跑三遍。肉眼可见的差异是：没有依据时敢不敢下结论、
有依据时会不会越界承诺、多步自检能不能把越界的表述拦下来。
"""
    ),
    code(
        """
DEMO_TICKET = "我买的蓝牙耳机订单 20260709001，到现在三天还没发货，客服也没人回。我现在很着急，能不能赶紧发货？"

runner = AgentRunner(retriever, quiet=True)

for mode in ("A", "B", "C"):
    result = runner.run(DEMO_TICKET, mode)
    print("=" * 74)
    print(f"模式 {mode}｜{MODES[mode]['label']}")
    print(f"耗时 {result.elapsed_ms} ms｜模型调用 {result.llm_calls} 次｜工具调用 {result.tool_calls} 次")
    print("-" * 74)
    print(result.answer)
    if result.error:
        print(f"[提示] {result.error}")
"""
    ),
    md(
        """
## 第五部分：性能评估

指标全部由字符串规则判定，不让模型当裁判：

| 指标 | 判据 |
|---|---|
| 未完成率 | 达到最大步数仍未定稿 |
| 红线违规率 | 命中数据集 `must_not_contain` 断言 |
| 编号编造率 | 出现知识库编号表之外的规则编号 |
| 依据覆盖率 | `expected_rules` 是否被引用 |
| 追问触发率 | `should_ask` 样本中是否真的追问 |

完整结果见 `outputs/comparison.md`（随项目提交）。
下面先跑前 5 条确认链路，确认无误后把 `samples[:5]` 改成 `samples` 即可跑全量。
"""
    ),
    code(
        """
samples = load_samples(PROJECT_ROOT / "data" / "eval" / "eval_samples.yaml")
print(f"评测样本共 {len(samples)} 条（正常诉求 / 边界 / 信息缺失 / 未覆盖 / 失败样本固化）")

# 演示只跑前 5 条，刻意输出到独立目录：仓库里的 outputs/comparison.md 是 30 条全量结果，
# 不能被这里的演示覆盖掉
outcome = run_evaluation(
    retriever=retriever,
    samples=samples[:5],
    modes=["A", "B", "C"],
    out_dir=PROJECT_ROOT / "outputs" / "notebook-demo",
)
"""
    ),
    code(
        """
from IPython.display import Markdown, display

# 展示本次演示（前 5 条）的对比结果
display(Markdown((PROJECT_ROOT / "outputs" / "notebook-demo" / "comparison.md").read_text(encoding="utf-8")))

# 仓库中的 outputs/comparison.md 是 30 条全量结果，由命令行 `python -m src.evaluator` 生成
print("全量报告：outputs/comparison.md")
"""
    ),
    md(
        """
## 第六部分：总结与展望

### 实现的功能

- 三种可复现的编排方式，共用同一套政策库与提示词，差异只在编排
- 四个脚本可判定的指标 + 规则化红线复核，结论可逐条复查
- 政策检索采用规则级切分 + BM25，工程自包含、可离线运行

### 遇到的挑战

- 框架的 ReAct 用行内正则解析动作，`Finish[...]` 一旦跨行就会解析成空串；
  已在提示词中强制单行，并在外层加入轨迹兜底
- 同一批工具在原生函数调用与文本解析两条路径下的参数名不同（`query` 与 `input`），
  工具必须同时兼容，否则 ReAct 模式永远拿到空参数
- 批量评测会触发供应商限流，已加入指数退避重试，避免脏数据污染结论

### 未来改进方向

- 引入向量检索与重排，观察混合检索能否提升长尾诉求的覆盖
- 把确定性流程作为第四档对照（当前三档都是自治路径）
- 扩充样本到多领域、多模型，检验结论的普适性
"""
    ),
]


def main() -> None:
    notebook = nbf.v4.new_notebook(cells=CELLS)
    notebook.metadata = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.11"},
    }
    target = ROOT / "main.ipynb"
    nbf.write(notebook, str(target))
    print(f"已生成 {target.relative_to(ROOT)}（{len(CELLS)} 个单元）")


if __name__ == "__main__":
    main()
