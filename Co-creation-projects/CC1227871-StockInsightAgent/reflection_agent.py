"""Step 4: Reflection 反思模式 — 分析报告自审与优化
来自 hello-agents 教程第4章 Reflection 范式:
  初始分析 -> 反思评审 -> 优化改进 -> 循环直到无需改进
"""
from typing import List, Dict, Any
from llm_client import HelloAgentsLLM
from tools import (
    get_realtime_quote, get_historical_data, get_financial_data,
    calc_indicators, get_news
)


class Memory:
    """短期记忆：存储分析轨迹（初始报告 + 反思 + 改进报告）"""
    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def add_record(self, record_type: str, content: str):
        self.records.append({"type": record_type, "content": content})
        print(f"  [记忆] 新增 '{record_type}' 记录")

    def get_trajectory(self) -> str:
        parts = []
        for r in self.records:
            label = "分析报告" if r['type'] == 'execution' else "评审意见"
            parts.append(f"--- {label} ---\n{r['content']}")
        return "\n\n".join(parts)

    def get_last_execution(self) -> str:
        for r in reversed(self.records):
            if r['type'] == 'execution':
                return r['content']
        return None


# ===== 提示词模板 =====

INITIAL_ANALYSIS_PROMPT = """你是资深股票分析师。请对以下股票进行全面分析。

## 可用数据
{data_section}

## 分析要求
{task}

请输出一份结构化的分析报告，包含:
1. 基本概况与走势判断
2. 技术面分析（趋势、均线、指标、关键价位）
3. 基本面与估值分析
4. 消息面与市场情绪
5. 风险提示
6. 短期/中长期操作建议
"""

REFLECTION_PROMPT = """你是极其严格的股票投资评审专家。你的任务是审查以下分析报告，找出缺陷和遗漏。

## 原始分析需求
{task}

## 待审查报告
{report}

## 评审维度
1. **数据完整性**: 是否遗漏了关键数据维度？是否有数据解读错误？
2. **风险覆盖**: 是否遗漏了重要风险因素？（如：行业政策风险、汇率风险、大股东减持、解禁压力）
3. **逻辑一致性**: 技术面/基本面/消息面的结论是否一致？是否有自相矛盾？
4. **盲区检查**: 有没有未考虑的视角？（如：产业链上下游、跨市场联动、资金流向）
5. **反向思考**: 如果最终判断是看多，请从看空角度挑战；反之亦然。有没有可能判断错了？

请直接输出你的评审意见，指出至少3个具体的缺陷或遗漏。
如果分析报告已经全面、严谨、无明显疏漏，请回答"无需改进"。
"""

REFINE_PROMPT = """你是资深股票分析师。评审专家指出了你上一轮分析报告的缺陷。

## 原始需求
{task}

## 你的上一轮报告
{previous_report}

## 评审意见
{reflection}

请基于评审意见，生成一份改进后的完整分析报告。要特别针对评审指出的问题补充分析和修正。
输出完整的改进版报告（6个章节结构不变，但内容要体现反思后的改进）。
"""


class ReflectionStockAgent:
    """反思式股票分析 Agent — 分析→评审→改进 循环"""

    TOOLS = {
        "GetRealtimeQuote": get_realtime_quote,
        "GetHistoricalData": get_historical_data,
        "CalcIndicators": calc_indicators,
        "GetFinancialData": get_financial_data,
        "GetNews": get_news,
    }

    def __init__(self, llm_client: HelloAgentsLLM, max_iterations: int = 2):
        self.llm_client = llm_client
        self.memory = Memory()
        self.max_iterations = max_iterations

    def run(self, task: str):
        print(f"\n{'='*60}")
        print(f"  Reflection 反思模式 (最多{self.max_iterations}轮)")
        print(f"  问题: {task}")
        print(f"{'='*60}")

        # --- 阶段1: 自动采集数据 ---
        print("\n  [阶段1] 自动采集数据...")
        data_text = self._collect_data(task)

        # --- 阶段2: 初始分析 ---
        print(f"\n  [阶段2] 生成初始分析报告...")
        initial_prompt = INITIAL_ANALYSIS_PROMPT.format(
            data_section=data_text, task=task
        )
        messages = [{"role": "user", "content": initial_prompt}]
        initial_report = self.llm_client.think(messages=messages) or ""
        self.memory.add_record("execution", initial_report)
        print(f"  [初始报告] 已生成 ({len(initial_report)} 字)")

        # --- 阶段3: 反思-改进循环 ---
        for iteration in range(self.max_iterations):
            print(f"\n  [阶段3] 第 {iteration+1}/{self.max_iterations} 轮反思...")

            # 评审
            reflect_prompt = REFLECTION_PROMPT.format(
                task=task, report=self.memory.get_last_execution()
            )
            messages = [{"role": "user", "content": reflect_prompt}]
            feedback = self.llm_client.think(messages=messages) or ""
            self.memory.add_record("reflection", feedback)

            # 检查收敛
            if "无需改进" in feedback:
                print("\n  [评审] 报告已无明显缺陷，反思结束。")
                break

            # 改进
            print(f"\n  [阶段3] 基于评审意见改进报告...")
            refine_prompt = REFINE_PROMPT.format(
                task=task,
                previous_report=self.memory.get_last_execution(),
                reflection=feedback,
            )
            messages = [{"role": "user", "content": refine_prompt}]
            refined_report = self.llm_client.think(messages=messages) or ""
            self.memory.add_record("execution", refined_report)
            print(f"  [改进报告] 已生成 ({len(refined_report)} 字)")

        # --- 输出最终报告 ---
        final_report = self.memory.get_last_execution()
        print(f"\n{'='*60}")
        print(f"  最终分析报告 (经 {sum(1 for r in self.memory.records if r['type']=='reflection')} 轮反思)")
        print(f"{'='*60}")
        print(final_report)
        return final_report

    def _collect_data(self, task: str) -> str:
        """自动从任务中提取股票代码，采集关键数据"""
        import re

        # 提取股票代码
        codes = re.findall(r"\b(\d{6})\b", task)
        if not codes:
            return "（未能自动识别股票代码，请在问题中包含6位代码）"

        code = codes[0]
        parts = []

        # 实时行情
        print(f"    [采集] 实时行情 {code}...")
        r = self.TOOLS["GetRealtimeQuote"](code)
        parts.append(f"### 实时行情\n{r}")

        # 历史K线 (60天)
        print(f"    [采集] 60天K线 {code}...")
        r = self.TOOLS["GetHistoricalData"](f"{code}|daily|60")
        parts.append(f"### 60天历史K线\n{r}")

        # 技术指标 (120天)
        print(f"    [采集] 技术指标 {code}...")
        r = self.TOOLS["CalcIndicators"](f"{code}|daily|120")
        parts.append(f"### 技术指标\n{r}")

        # 财务数据
        print(f"    [采集] 财务数据 {code}...")
        r = self.TOOLS["GetFinancialData"](code)
        parts.append(f"### 财务数据\n{r}")

        # 新闻
        print(f"    [采集] 新闻舆情 {code}...")
        r = self.TOOLS["GetNews"](code)
        parts.append(f"### 新闻舆情\n{r}")

        return "\n\n".join(parts)
