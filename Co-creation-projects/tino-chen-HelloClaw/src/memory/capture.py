"""记忆捕获管理器 - 自动识别并存储对话中的重要信息"""

import asyncio
import re
from datetime import datetime
from typing import List, Optional, Tuple


# 记忆触发规则
MEMORY_TRIGGERS = [
    # 明确要求记住
    (r"记住|记下|remember|keep in mind", "fact"),
    # 偏好表达
    (r"我喜欢|我偏好|prefer|like|love|hate|讨厌|不喜欢", "preference"),
    # 决策记录
    (r"决定了|decision|用这个|选定|确定用|就用", "decision"),
    # 电话号码
    (r"\+\d{10,}|\d{3,4}[-\s]?\d{7,8}", "entity"),
    # 邮箱地址
    (r"[\w.-]+@[\w.-]+\.\w+", "entity"),
    # 实体信息（我的xxx是）
    (r"我的\w+是|is my|我的电话|我的邮箱|我的地址|我的名字", "entity"),
    # 事实陈述
    (r"事实上|实际上|the fact is|it turns out", "fact"),
]

# 分类关键词（用于辅助分类）
CATEGORY_KEYWORDS = {
    "preference": ["喜欢", "偏好", "prefer", "like", "love", "hate", "讨厌", "不喜欢", "习惯", "习惯于"],
    "decision": ["决定", "选定", "用这个", "确定", "choose", "decide", "decision"],
    "entity": ["电话", "邮箱", "地址", "名字", "账号", "phone", "email", "address", "account"],
    "fact": ["记住", "记下", "事实", "实际上", "remember", "fact"],
}


class MemoryCaptureManager:
    """记忆捕获管理器

    负责在对话结束后自动识别值得记忆的信息，并进行分类和去重。

    使用方式：
        manager = MemoryCaptureManager(workspace_manager)
        memories = manager.capture("用户：我喜欢简洁的回复风格")
        # 返回: [{"content": "用户喜欢简洁的回复风格", "category": "preference"}]
    """

    def __init__(self, workspace_manager):
        """初始化记忆捕获管理器

        Args:
            workspace_manager: WorkspaceManager 实例
        """
        self.workspace = workspace_manager
        # 编译正则表达式
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), category)
            for pattern, category in MEMORY_TRIGGERS
        ]

    def capture(self, text: str) -> List[dict]:
        """分析文本并捕获值得记忆的信息

        Args:
            text: 要分析的文本（通常是用户消息或对话摘要）

        Returns:
            捕获到的记忆列表，每项包含 content 和 category
        """
        memories = []
        seen_contents = set()  # 用于去重

        # 按句子分割
        sentences = self._split_sentences(text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 5:
                continue

            # 检查是否匹配触发规则
            category = self._match_trigger(sentence)
            if not category:
                continue

            # 提取记忆内容
            content = self._extract_memory(sentence, category)
            if not content:
                continue

            # 去重检查
            content_key = content.lower().strip()
            if content_key in seen_contents:
                continue

            # 检查是否与已有记忆重复
            if self.workspace.check_duplicate_memory(content, threshold=0.7):
                continue

            seen_contents.add(content_key)
            memories.append({
                "content": content,
                "category": category,
                "timestamp": datetime.now().strftime("%H:%M"),
            })

        return memories

    async def acapture(self, text: str) -> List[dict]:
        """异步分析文本并捕获值得记忆的信息

        Args:
            text: 要分析的文本

        Returns:
            捕获到的记忆列表
        """
        # 使用线程池执行 CPU 密集型任务
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.capture, text)

    def capture_and_store(self, text: str, date: datetime = None) -> List[dict]:
        """分析文本并存储捕获到的记忆

        Args:
            text: 要分析的文本
            date: 日期，默认为今天

        Returns:
            实际存储的记忆列表
        """
        memories = self.capture(text)
        stored = []

        for memory in memories:
            try:
                self.workspace.append_classified_memory(
                    content=memory["content"],
                    category=memory["category"],
                    date=date,
                )
                stored.append(memory)
            except Exception as e:
                print(f"⚠️ 存储记忆失败: {e}")

        return stored

    async def acapture_and_store(self, text: str, date: datetime = None) -> List[dict]:
        """异步分析文本并存储捕获到的记忆

        Args:
            text: 要分析的文本
            date: 日期，默认为今天

        Returns:
            实际存储的记忆列表
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.capture_and_store, text, date
        )

    def _split_sentences(self, text: str) -> List[str]:
        """将文本分割为句子

        Args:
            text: 输入文本

        Returns:
            句子列表
        """
        # 按常见分隔符分割
        # 支持中英文句号、问号、感叹号、换行
        sentences = re.split(r'[。！？.!?]\s*|\n+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _match_trigger(self, sentence: str) -> Optional[str]:
        """检查句子是否匹配触发规则

        Args:
            sentence: 要检查的句子

        Returns:
            匹配的分类，如果没有匹配则返回 None
        """
        for pattern, category in self._compiled_patterns:
            if pattern.search(sentence):
                return category
        return None

    def _extract_memory(self, sentence: str, category: str) -> Optional[str]:
        """从句子中提取记忆内容

        Args:
            sentence: 原始句子
            category: 分类

        Returns:
            提取的记忆内容
        """
        # 清理句子
        content = sentence.strip()

        # 移除前缀（如"用户："、"我："等）
        content = re.sub(r'^(用户|我|你|assistant|user)[：:]\s*', '', content)

        # 移除引号
        content = content.strip('"\'""''')

        # 如果内容太短，可能是噪声
        if len(content) < 5:
            return None

        # 根据分类进行适当格式化
        if category == "preference":
            # 确保偏好类记忆以"用户"开头
            if not content.startswith("用户") and not content.startswith("I "):
                content = f"用户{content}"

        return content

    def analyze_conversation(self, messages: List[dict]) -> List[dict]:
        """分析完整对话并提取记忆

        Args:
            messages: 对话消息列表，每项包含 role 和 content

        Returns:
            捕获到的记忆列表
        """
        all_memories = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            # 只分析用户消息
            if role == "user" and content:
                memories = self.capture(content)
                all_memories.extend(memories)

        return all_memories

    def get_category_stats(self) -> dict:
        """获取记忆分类统计

        Returns:
            各分类的记忆数量统计
        """
        # 读取今日记忆
        today_path = self.workspace.get_daily_memory_path()
        stats = {
            "preference": 0,
            "decision": 0,
            "entity": 0,
            "fact": 0,
            "total": 0,
        }

        try:
            with open(today_path, "r", encoding="utf-8") as f:
                content = f.read()

            for category in stats:
                if category != "total":
                    # 统计 [category] 标签出现次数
                    pattern = rf'\[{category}\]'
                    count = len(re.findall(pattern, content, re.IGNORECASE))
                    stats[category] = count
                    stats["total"] += count
        except FileNotFoundError:
            pass

        return stats
