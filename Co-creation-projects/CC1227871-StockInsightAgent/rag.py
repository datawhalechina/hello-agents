"""Step 7: RAG 投资知识库 — 文档分块 + TF-IDF 检索"""
import os
import re
import json
import math
from collections import Counter
from typing import List, Dict, Tuple


class InvestmentKnowledgeBase:
    """轻量投资知识库 — 无需外部嵌入 API，TF-IDF 检索"""

    def __init__(self, path: str = "memory/knowledge_base.json"):
        self.path = path
        self.chunks: List[Dict] = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.chunks = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.chunks = []

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)

    # ===== 文档导入 =====
    def add_text(self, text: str, title: str = "", source: str = "") -> str:
        """导入文本，自动分块"""
        chunks = self._chunk_text(text, title, source)
        self.chunks.extend(chunks)
        self._save()
        return f"已导入 '{title}'，共 {len(chunks)} 个知识块 (总计 {len(self.chunks)} 块)"

    def add_file(self, filepath: str) -> str:
        """导入文件 (支持 .txt .md)"""
        if not os.path.exists(filepath):
            return f"文件不存在: {filepath}"
        try:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()
            except UnicodeDecodeError:
                with open(filepath, "r", encoding="gbk") as f:
                    text = f.read()
        except Exception as e:
            return f"读取文件失败: {e}"
        title = os.path.basename(filepath)
        return self.add_text(text, title, filepath)

    def _chunk_text(self, text: str, title: str, source: str,
                    chunk_size: int = 300, overlap: int = 50) -> List[Dict]:
        """按段落+句子边界智能分块"""
        # 先按段落分割
        paragraphs = re.split(r"\n\s*\n", text)
        chunks = []
        current = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current) + len(para) < chunk_size:
                current += ("\n" if current else "") + para
            else:
                if current:
                    chunks.append(current)
                # 如果段落太长，按句子分
                if len(para) > chunk_size:
                    sentences = re.split(r"(?<=[。！？\.!?])\s*", para)
                    sub = ""
                    for s in sentences:
                        if len(sub) + len(s) < chunk_size:
                            sub += s
                        else:
                            if sub:
                                chunks.append(sub)
                            sub = s
                    if sub:
                        current = sub
                    else:
                        current = ""
                else:
                    current = para
        if current:
            chunks.append(current)

        return [{
            "id": f"{title}_{i}",
            "title": title,
            "source": source,
            "content": c,
        } for i, c in enumerate(chunks)]

    # ===== 检索 =====
    def search(self, query: str, top_k: int = 5) -> str:
        """TF-IDF 检索最相关的知识块"""
        if not self.chunks:
            return "知识库为空。可以用 '导入知识 文件路径' 来添加文档。"

        # 构建词汇表
        all_docs = [c["content"] for c in self.chunks]
        tokenized_docs = [self._tokenize(d) for d in all_docs]
        tokenized_query = self._tokenize(query)

        # TF-IDF 计算
        df = Counter()
        for tokens in tokenized_docs:
            df.update(set(tokens))
        N = len(tokenized_docs)

        scores = []
        for i, doc_tokens in enumerate(tokenized_docs):
            tf = Counter(doc_tokens)
            score = 0
            for term in set(tokenized_query):
                if term in tf:
                    tf_val = tf[term] / max(len(doc_tokens), 1)
                    idf_val = math.log((N + 1) / (df[term] + 1)) + 1
                    score += tf_val * idf_val
            if score > 0:
                scores.append((score, i))

        scores.sort(key=lambda x: x[0], reverse=True)

        if not scores:
            # 回退到关键词匹配
            for i, (doc, doc_tokens) in enumerate(zip(all_docs, tokenized_docs)):
                if any(kw in doc_tokens for kw in tokenized_query):
                    scores.append((0.5, i))
            scores.sort(key=lambda x: x[0], reverse=True)

        if not scores:
            return f"未找到与 '{query}' 相关的知识"

        lines = [f"知识库检索结果 (查询: '{query}'):"]
        for score, idx in scores[:top_k]:
            chunk = self.chunks[idx]
            lines.append(f"\n--- [{score:.2f}] {chunk['title']} ---")
            lines.append(chunk["content"][:400])

        return "\n".join(lines)

    def _tokenize(self, text: str) -> List[str]:
        """简单中文分词 (2-gram)"""
        # 提取中文字符和英文单词
        words = re.findall(r"[一-鿿]{1,2}|[a-zA-Z]+", text.lower())
        return [w for w in words if len(w) >= 2]

    def stats(self) -> str:
        titles = set(c["title"] for c in self.chunks)
        return (f"知识库: {len(self.chunks)} 个知识块, "
                f"{len(titles)} 篇文档")

    def clear(self) -> str:
        self.chunks = []
        self._save()
        return "知识库已清空"


# ===== 预置投资知识 =====
INVESTMENT_KNOWLEDGE = """
# 股票估值方法

## 市盈率 (PE)
PE = 股价 / 每股收益。反映市场愿意为每元利润支付的价格。
- PE < 10: 可能低估（需排除盈利质量差的情况）
- PE 10-20: 合理区间
- PE 20-30: 中等偏高，通常对应成长股
- PE > 30: 高估值，需有高增长支撑
行业差异大：银行 PE 通常 5-10 倍，科技股 PE 可达 30-50 倍。

## 市净率 (PB)
PB = 股价 / 每股净资产。适用于重资产行业（银行、地产、制造业）。
- PB < 1: 破净，可能严重低估
- PB 1-2: 合理偏低
- PB 2-5: 正常水平
- PB > 5: 偏高，需有高 ROE 支撑

## PEG 指标
PEG = PE / 净利润增长率(%)。用于成长股估值。
- PEG < 0.5: 显著低估
- PEG 0.5-1.0: 合理偏低
- PEG 1.0-1.5: 合理
- PEG > 2.0: 高估

## 股息率
股息率 = 每股分红 / 股价。衡量现金回报。
- 股息率 > 4%: 高股息，防御性强
- 股息率 2-4%: 正常水平
- 股息率 < 2%: 偏低

# 技术指标解读

## MACD 金叉死叉
- 金叉: DIF 上穿 DEA，买入信号。零轴上方金叉更强。
- 死叉: DIF 下穿 DEA，卖出信号。零轴下方死叉更弱。
- 顶背离: 股价新高 MACD 未新高，见顶信号。
- 底背离: 股价新低 MACD 未新低，见底信号。

## RSI 相对强弱指标
- RSI > 80: 严重超买，回调风险大
- RSI 70-80: 超买区域，短期可能回调
- RSI 30-70: 正常区间
- RSI 20-30: 超卖区域，短期可能反弹
- RSI < 20: 严重超卖，反弹概率高

## 均线系统
- 多头排列: MA5 > MA10 > MA20 > MA60，上升趋势
- 空头排列: MA5 < MA10 < MA20 < MA60，下降趋势
- 金叉: 短期均线上穿长期均线
- 死叉: 短期均线下穿长期均线

## 布林带
- 价格触及上轨: 短期超买，可能回调
- 价格触及下轨: 短期超卖，可能反弹
- 带宽收窄: 变盘信号，可能突破
- 带宽扩大: 趋势加速

# 风险控制原则

## 仓位管理
- 单只股票不超过总仓位 20%
- 单一行业不超过总仓位 30%
- 永远保留 10-20% 现金应对极端情况
- 分批建仓: 至少分 3 次买入，降低成本集中风险

## 止损原则
- 技术止损: 跌破关键支撑位（MA60/前低）止损
- 比例止损: 亏损超过 8-10% 无条件止损
- 时间止损: 买入后 20 个交易日未达预期，重新评估
- 基本面止损: 公司基本面出现重大恶化，立即止损

## 风险收益比
- 每笔交易的风险收益比应 >= 1:2
- 预期收益应至少是潜在亏损的 2 倍

# A股交易规则

## 交易时间
- 早盘集合竞价: 9:15-9:25
- 连续竞价: 9:30-11:30, 13:00-15:00
- 深交所尾盘集合竞价: 14:57-15:00

## 涨跌幅限制
- 主板: ±10%
- 创业板(300开头)/科创板(688开头): ±20%
- ST 股票: ±5%
- 新股上市前 5 日无涨跌幅限制

## T+1 制度
A股实行 T+1 交易，当日买入次日才能卖出。
"""


# 全局单例
_kb_instance = None


def get_kb() -> InvestmentKnowledgeBase:
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = InvestmentKnowledgeBase()
        # 首次初始化时导入预置知识
        if not _kb_instance.chunks:
            _kb_instance.add_text(INVESTMENT_KNOWLEDGE, "投资基础知识", "built-in")
    return _kb_instance


# ===== 工具函数 =====

def rag_search(query: str) -> str:
    """搜索投资知识库。输入: 查询关键词或问题"""
    return get_kb().search(query.strip())


def rag_import(query: str) -> str:
    """导入文档到知识库。输入: 文件路径"""
    return get_kb().add_file(query.strip())


def rag_stats(query: str = "") -> str:
    """查看知识库统计"""
    return get_kb().stats()
