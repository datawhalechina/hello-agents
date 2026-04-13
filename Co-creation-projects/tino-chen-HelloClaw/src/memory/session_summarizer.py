"""会话总结器 - 自动生成会话摘要"""

import os
import re
from datetime import datetime
from typing import List, Optional, Dict, Any


class SessionSummarizer:
    """会话总结器

    负责在创建新会话时总结旧会话内容，生成结构化摘要保存到 memory 目录。
    """

    def __init__(
        self,
        workspace_manager,
        llm_client=None,
        model_id: str = None,
        api_key: str = None,
        base_url: str = None,
    ):
        """初始化会话总结器

        Args:
            workspace_manager: 工作空间管理器
            llm_client: LLM 客户端（可选，用于生成总结）
            model_id: 模型 ID
            api_key: API Key
            base_url: API Base URL
        """
        self.workspace = workspace_manager
        self._llm_client = llm_client
        self._model_id = model_id
        self._api_key = api_key
        self._base_url = base_url

    async def summarize_session(
        self,
        messages: List[dict],
        last_n: int = 10,
        session_id: str = None,
    ) -> Optional[str]:
        """总结会话内容

        Args:
            messages: 会话消息列表
            last_n: 只取最后 N 轮对话
            session_id: 会话 ID（用于日志）

        Returns:
            生成的总结文件路径，如果失败返回 None
        """
        if not messages:
            return None

        # 提取最后 N 轮对话
        excerpt = self._extract_excerpt(messages, last_n)
        if not excerpt:
            return None

        try:
            # 生成 slug 和总结
            slug = await self._generate_slug(excerpt)
            summary = await self._generate_summary(excerpt)

            if not slug or not summary:
                return None

            # 保存到文件
            filename = self._generate_filename(slug)
            self.workspace.save_session_summary(filename, summary)

            return filename

        except Exception as e:
            print(f"⚠️ 会话总结失败: {e}")
            return None

    def _extract_excerpt(
        self,
        messages: List[dict],
        last_n: int = 10,
    ) -> str:
        """提取会话摘要文本

        Args:
            messages: 消息列表
            last_n: 取最后 N 轮对话

        Returns:
            提取的文本
        """
        # 只保留 user 和 assistant 消息
        conversation = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                # 截断过长的内容
                if len(content) > 500:
                    content = content[:500] + "..."
                conversation.append(f"[{role.upper()}]: {content}")

        # 只取最后 N 轮
        if len(conversation) > last_n * 2:
            conversation = conversation[-(last_n * 2) :]

        return "\n".join(conversation)

    async def _generate_slug(self, excerpt: str) -> str:
        """生成描述性 slug

        Args:
            excerpt: 会话摘要文本

        Returns:
            3-5 个单词的 slug
        """
        if not self._llm_client:
            # 如果没有 LLM，使用简单方法生成 slug
            return self._generate_simple_slug(excerpt)

        prompt = f"""根据以下对话内容，生成一个简短的英文描述（3-5个单词，用连字符连接）。
只输出描述本身，不要其他内容。

对话内容:
{excerpt[:1000]}

描述:"""

        try:
            # 调用 LLM
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )

            response = await client.chat.completions.create(
                model=self._model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.3,
            )

            slug = response.choices[0].message.content.strip()
            # 清理 slug
            slug = re.sub(r"[^a-zA-Z0-9\-]", "", slug.replace(" ", "-").lower())
            slug = re.sub(r"-+", "-", slug).strip("-")

            # 限制长度
            if len(slug) > 50:
                slug = slug[:50]

            return slug or "conversation"

        except Exception as e:
            print(f"⚠️ 生成 slug 失败: {e}")
            return self._generate_simple_slug(excerpt)

    def _generate_simple_slug(self, excerpt: str) -> str:
        """使用简单方法生成 slug

        从对话中提取关键词
        """
        # 提取一些常见的关键词
        keywords = []
        common_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "dare",
            "ought",
            "used",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "again",
            "further",
            "then",
            "once",
            "here",
            "there",
            "when",
            "where",
            "why",
            "how",
            "all",
            "each",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "just",
            "and",
            "but",
            "if",
            "or",
            "because",
            "until",
            "while",
            "about",
            "what",
            "which",
            "who",
            "whom",
            "this",
            "that",
            "these",
            "those",
            "i",
            "me",
            "my",
            "myself",
            "we",
            "our",
            "ours",
            "ourselves",
            "you",
            "your",
            "yours",
            "yourself",
            "yourselves",
            "he",
            "him",
            "his",
            "himself",
            "she",
            "her",
            "hers",
            "herself",
            "it",
            "its",
            "itself",
            "they",
            "them",
            "their",
            "theirs",
            "themselves",
        }

        # 提取英文单词
        words = re.findall(r"\b[a-zA-Z]{3,}\b", excerpt.lower())
        word_count = {}
        for word in words:
            if word not in common_words:
                word_count[word] = word_count.get(word, 0) + 1

        # 取频率最高的词
        sorted_words = sorted(word_count.items(), key=lambda x: -x[1])
        keywords = [w for w, _ in sorted_words[:3]]

        if keywords:
            return "-".join(keywords)
        return "conversation"

    async def _generate_summary(self, excerpt: str) -> str:
        """生成结构化总结

        Args:
            excerpt: 会话摘要文本

        Returns:
            Markdown 格式的总结
        """
        if not self._llm_client:
            # 如果没有 LLM，返回简单格式
            return self._generate_simple_summary(excerpt)

        prompt = f"""请为以下对话生成一个结构化的会话总结。

要求：
1. 使用 Markdown 格式
2. 包含以下部分：
   - 主题：一句话概括
   - 关键点：3-5 个要点
   - 待办：如果有提到任务或待办事项
3. 简洁明了，总字数不超过 300 字

对话内容:
{excerpt[:2000]}

总结:"""

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )

            response = await client.chat.completions.create(
                model=self._model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3,
            )

            summary = response.choices[0].message.content.strip()

            # 添加元信息头
            header = f"""---
date: {datetime.now().strftime("%Y-%m-%d %H:%M")}
type: session-summary
---

"""
            return header + summary

        except Exception as e:
            print(f"⚠️ 生成总结失败: {e}")
            return self._generate_simple_summary(excerpt)

    def _generate_simple_summary(self, excerpt: str) -> str:
        """生成简单格式的总结"""
        header = f"""---
date: {datetime.now().strftime("%Y-%m-%d %H:%M")}
type: session-summary
---

# 会话摘要

## 对话节选

"""
        # 截取前 500 字符
        content = excerpt[:500]
        if len(excerpt) > 500:
            content += "..."
        return header + content

    def _generate_filename(self, slug: str) -> str:
        """生成文件名

        Args:
            slug: 描述性 slug

        Returns:
            文件名（YYYY-MM-DD-slug.md）
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        return f"{date_str}-{slug}.md"
