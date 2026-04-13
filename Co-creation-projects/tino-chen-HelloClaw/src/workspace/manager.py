"""工作空间管理器"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Set


# 配置文件列表
CONFIG_FILES = [
    "BOOTSTRAP",
    "IDENTITY",
    "SOUL",
    "USER",
    "MEMORY",
    "AGENTS",
    "HEARTBEAT",
]

# 模板目录（相对于当前文件）
TEMPLATES_DIR = Path(__file__).parent / "templates"


def get_default_global_config() -> dict:
    """获取默认全局配置（从模板文件读取）"""
    template_path = TEMPLATES_DIR / "config.json"
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"llm": {"model_id": "", "base_url": "", "api_key": ""}}


class WorkspaceManager:
    """工作空间管理器

    负责：
    - 创建和管理工作空间目录结构
    - 加载和保存配置文件
    - 管理记忆文件（每日记忆、长期记忆）
    """

    def __init__(self, workspace_path: str):
        """初始化工作空间管理器

        Args:
            workspace_path: 工作空间根目录路径
        """
        self.workspace_path = os.path.expanduser(workspace_path)
        self.memory_path = os.path.join(self.workspace_path, "memory")
        self.sessions_path = os.path.join(self.workspace_path, "sessions")

    # ==================== 全局配置读取 ====================

    def load_global_config(self) -> dict:
        """加载全局 config.json

        Returns:
            配置字典，如果文件不存在返回空字典
        """
        config_path = os.path.expanduser("~/.helloclaw/config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def get_llm_config(self) -> dict:
        """获取 LLM 配置

        优先级：config.json 非空值 > 环境变量 > 默认值

        Returns:
            包含 model_id, api_key, base_url 的字典
        """
        global_config = self.load_global_config()
        llm_config = global_config.get("llm", {})

        return {
            "model_id": llm_config.get("model_id") or os.getenv("LLM_MODEL_ID") or "glm-4",
            "api_key": llm_config.get("api_key") or os.getenv("LLM_API_KEY"),
            "base_url": llm_config.get("base_url") or os.getenv("LLM_BASE_URL"),
        }

    # ==================== 入职状态检测 ====================

    def is_onboarding_completed(self) -> bool:
        """检查入职是否完成

        入职完成的标志：BOOTSTRAP.md 不存在。
        同时会检查身份是否已确定，如果是则自动删除 BOOTSTRAP.md。

        Returns:
            入职是否已完成
        """
        # 先检查是否需要删除 BOOTSTRAP（身份已确定但文件还在）
        self._check_and_delete_bootstrap()

        return not os.path.exists(self.get_config_path("BOOTSTRAP"))

    def ensure_workspace_exists(self):
        """确保工作空间存在

        如果工作空间不存在，创建默认目录和配置文件
        """
        # 创建目录
        os.makedirs(self.workspace_path, exist_ok=True)
        os.makedirs(self.memory_path, exist_ok=True)
        os.makedirs(self.sessions_path, exist_ok=True)

        # 创建默认配置文件
        for config_name in CONFIG_FILES:
            config_path = self.get_config_path(config_name)
            if not os.path.exists(config_path):
                self._create_default_config(config_name)

        # 检查是否需要删除 BOOTSTRAP（遗留工作空间迁移）
        self._check_and_delete_bootstrap()

    def get_config_path(self, name: str) -> str:
        """获取配置文件路径

        Args:
            name: 配置文件名称（不含扩展名）

        Returns:
            配置文件完整路径
        """
        return os.path.join(self.workspace_path, f"{name}.md")

    def load_config(self, name: str) -> Optional[str]:
        """加载配置文件内容

        Args:
            name: 配置文件名称

        Returns:
            配置文件内容，如果不存在返回 None
        """
        config_path = self.get_config_path(name)
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def save_config(self, name: str, content: str):
        """保存配置文件

        Args:
            name: 配置文件名称
            content: 配置文件内容
        """
        config_path = self.get_config_path(name)
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)

        # 如果保存的是 IDENTITY，检查是否需要删除 BOOTSTRAP
        if name == "IDENTITY":
            self._check_and_delete_bootstrap()

    def list_configs(self) -> list:
        """列出所有配置文件

        Returns:
            配置文件名称列表
        """
        configs = []
        for name in CONFIG_FILES:
            config_path = self.get_config_path(name)
            if os.path.exists(config_path):
                configs.append(name)
        return configs

    def get_daily_memory_path(self, date: datetime = None) -> str:
        """获取每日记忆文件路径

        Args:
            date: 日期，默认为今天

        Returns:
            每日记忆文件路径
        """
        date = date or datetime.now()
        filename = date.strftime("%Y-%m-%d.md")
        return os.path.join(self.memory_path, filename)

    def append_to_daily_memory(self, content: str, date: datetime = None):
        """追加内容到每日记忆

        Args:
            content: 记忆内容
            date: 日期，默认为今天
        """
        memory_path = self.get_daily_memory_path(date)
        timestamp = datetime.now().strftime("%H:%M:%S")

        with open(memory_path, "a", encoding="utf-8") as f:
            f.write(f"\n## {timestamp}\n\n{content}\n")

    def search_memory(self, keyword: str, include_daily: bool = True) -> list:
        """搜索记忆

        Args:
            keyword: 搜索关键词
            include_daily: 是否包含每日记忆

        Returns:
            匹配的记忆片段列表
        """
        results = []

        # 搜索长期记忆
        memory_content = self.load_config("MEMORY")
        if memory_content and keyword.lower() in memory_content.lower():
            results.append({
                "source": "MEMORY.md",
                "content": memory_content,
            })

        # 搜索每日记忆
        if include_daily:
            for filename in os.listdir(self.memory_path):
                if filename.endswith(".md"):
                    filepath = os.path.join(self.memory_path, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        if keyword.lower() in content.lower():
                            results.append({
                                "source": f"memory/{filename}",
                                "content": content,
                            })

        return results

    def search_memory_enhanced(
        self,
        keyword: str,
        include_daily: bool = True,
        context_lines: int = 3,
    ) -> list:
        """增强版记忆搜索，返回带行号的上下文

        Args:
            keyword: 搜索关键词
            include_daily: 是否包含每日记忆
            context_lines: 上下文行数

        Returns:
            匹配的记忆片段列表，包含行号和上下文
        """
        results = []

        # 搜索长期记忆
        memory_content = self.load_config("MEMORY")
        if memory_content:
            matches = self._find_matches_with_context(
                memory_content, keyword, context_lines
            )
            if matches:
                results.append({
                    "source": "MEMORY.md",
                    "matches": matches,
                })

        # 搜索每日记忆
        if include_daily:
            for filename in sorted(os.listdir(self.memory_path)):
                if filename.endswith(".md"):
                    filepath = os.path.join(self.memory_path, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    matches = self._find_matches_with_context(
                        content, keyword, context_lines
                    )
                    if matches:
                        results.append({
                            "source": f"memory/{filename}",
                            "matches": matches,
                        })

        return results

    def _find_matches_with_context(
        self,
        content: str,
        keyword: str,
        context_lines: int = 3,
    ) -> list:
        """在内容中查找匹配并返回带行号的上下文

        Args:
            content: 文件内容
            keyword: 搜索关键词
            context_lines: 上下文行数

        Returns:
            匹配片段列表，每个包含 start_line, end_line, content
        """
        lines = content.split("\n")
        keyword_lower = keyword.lower()

        # 找到所有匹配的行号
        matched_lines = set()
        for i, line in enumerate(lines):
            if keyword_lower in line.lower():
                # 添加匹配行及其上下文
                for j in range(
                    max(0, i - context_lines),
                    min(len(lines), i + context_lines + 1),
                ):
                    matched_lines.add(j)

        if not matched_lines:
            return []

        # 合并相邻的行范围
        sorted_lines = sorted(matched_lines)
        ranges = []
        start = sorted_lines[0]
        end = sorted_lines[0]

        for line_num in sorted_lines[1:]:
            if line_num <= end + 1:
                end = line_num
            else:
                ranges.append((start, end))
                start = line_num
                end = line_num
        ranges.append((start, end))

        # 构建结果
        results = []
        for start_line, end_line in ranges:
            # 行号从 1 开始
            context = "\n".join(
                f"{i + 1:4d} | {lines[i]}"
                for i in range(start_line, end_line + 1)
            )
            results.append({
                "start_line": start_line + 1,
                "end_line": end_line + 1,
                "content": context,
            })

        return results

    def read_memory_lines(
        self,
        filename: str,
        start_line: int = None,
        end_line: int = None,
    ) -> Optional[str]:
        """读取记忆文件的指定行范围

        Args:
            filename: 文件名（MEMORY.md 或 YYYY-MM-DD.md）
            start_line: 起始行（从 1 开始），默认为 1
            end_line: 结束行，默认为文件末尾

        Returns:
            带行号的内容，如果文件不存在返回 None
        """
        # 确定文件路径
        if filename == "MEMORY.md":
            filepath = self.get_config_path("MEMORY")
        else:
            filepath = os.path.join(self.memory_path, filename)

        if not os.path.exists(filepath):
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            return ""

        # 默认值
        start = max(1, start_line or 1) - 1  # 转为 0-indexed
        end = end_line or len(lines)

        # 读取指定范围
        selected_lines = lines[start:end]

        # 格式化输出（带行号）
        result_lines = []
        for i, line in enumerate(selected_lines, start=start + 1):
            # 移除末尾换行符再添加行号
            result_lines.append(f"{i:4d} | {line.rstrip()}")

        return "\n".join(result_lines)

    def list_memory_files(self) -> list:
        """列出所有记忆文件

        Returns:
            记忆文件信息列表
        """
        files = []

        # 长期记忆
        memory_path = self.get_config_path("MEMORY")
        if os.path.exists(memory_path):
            stat = os.stat(memory_path)
            files.append({
                "name": "MEMORY.md",
                "type": "longterm",
                "size": stat.st_size,
                "updated_at": stat.st_mtime,
            })

        # 每日记忆
        if os.path.exists(self.memory_path):
            for filename in sorted(os.listdir(self.memory_path), reverse=True):
                if filename.endswith(".md"):
                    filepath = os.path.join(self.memory_path, filename)
                    stat = os.stat(filepath)
                    files.append({
                        "name": filename,
                        "type": "daily",
                        "size": stat.st_size,
                        "updated_at": stat.st_mtime,
                    })

        return files

    def _check_and_delete_bootstrap(self):
        """检查身份是否已确定，如果是则删除 BOOTSTRAP.md"""
        bootstrap_path = self.get_config_path("BOOTSTRAP")

        # BOOTSTRAP 不存在，无需处理
        if not os.path.exists(bootstrap_path):
            return

        # 检查身份是否已确定
        if self._is_identity_established():
            os.remove(bootstrap_path)

    def _is_identity_established(self) -> bool:
        """检查身份是否已确定（名称字段有实际内容）

        Returns:
            身份是否已确定
        """
        identity = self.load_config("IDENTITY")
        if not identity:
            return False

        # 尝试匹配名称字段
        # 格式: - **名称：** xxx 或 - **名称:** xxx
        match = re.search(r'\*\*名称[：:]\*\*\s*(.+?)(?:\n|$)', identity)
        if match:
            name = match.group(1).strip()
            # 如果名称不是占位符，则认为身份已确定
            # 占位符特征：以下划线开头、包含"选一个"、包含"（"
            if name and not name.startswith('_') and '选一个' not in name and '（' not in name:
                return True

        return False

    def _create_default_config(self, name: str):
        """创建默认配置文件

        从模板文件读取内容，如果模板不存在则使用基础模板

        Args:
            name: 配置文件名称
        """
        template_path = TEMPLATES_DIR / f"{name}.md"

        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            # 回退到基础模板
            content = f"# {name}\n\n（待配置）"

        # 替换日期占位符
        content = content.replace("{date}", datetime.now().strftime("%Y-%m-%d"))

        self.save_config(name, content)

    def reset_to_templates(self, reset_sessions: bool = False, reset_memory: bool = False, reset_global_config: bool = False):
        """重置工作空间到初始模板

        Args:
            reset_sessions: 是否清除会话
            reset_memory: 是否清除每日记忆
            reset_global_config: 是否重置全局配置

        警告：这将覆盖所有配置文件！
        """
        # 重置配置文件（包括 BOOTSTRAP）
        for config_name in CONFIG_FILES:
            self._create_default_config(config_name)

        # 清除会话
        if reset_sessions:
            self._clear_sessions()

        # 清除每日记忆
        if reset_memory:
            self._clear_daily_memory()

        # 重置全局配置
        if reset_global_config:
            self._reset_global_config()

    def _clear_sessions(self):
        """清除所有会话"""
        if os.path.exists(self.sessions_path):
            for filename in os.listdir(self.sessions_path):
                if filename.endswith(".json"):
                    filepath = os.path.join(self.sessions_path, filename)
                    os.remove(filepath)

    def _clear_daily_memory(self):
        """清除所有每日记忆"""
        if os.path.exists(self.memory_path):
            for filename in os.listdir(self.memory_path):
                if filename.endswith(".md"):
                    filepath = os.path.join(self.memory_path, filename)
                    os.remove(filepath)

    def _reset_global_config(self):
        """重置全局配置文件"""
        config_path = os.path.expanduser("~/.helloclaw/config.json")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(get_default_global_config(), f, indent=2, ensure_ascii=False)

    # ==================== 会话总结相关 ====================

    def save_session_summary(self, filename: str, content: str):
        """保存会话总结到 memory 目录

        Args:
            filename: 文件名（如 2026-02-26-project-discussion.md）
            content: 总结内容
        """
        filepath = os.path.join(self.memory_path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def list_session_summaries(self) -> list:
        """列出所有会话总结

        Returns:
            会话总结文件列表
        """
        summaries = []

        if not os.path.exists(self.memory_path):
            return summaries

        for filename in sorted(os.listdir(self.memory_path), reverse=True):
            if filename.endswith(".md") and "-" in filename:
                # 排除纯日期格式（每日记忆）
                if re.match(r"\d{4}-\d{2}-\d{2}\.md$", filename):
                    continue

                # 会话总结格式：YYYY-MM-DD-slug.md
                filepath = os.path.join(self.memory_path, filename)
                stat = os.stat(filepath)

                # 尝试提取 slug
                match = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)\.md$", filename)
                if match:
                    date_str = match.group(1)
                    slug = match.group(2)
                else:
                    date_str = ""
                    slug = filename[:-3]

                summaries.append({
                    "filename": filename,
                    "date": date_str,
                    "slug": slug,
                    "size": stat.st_size,
                    "updated_at": stat.st_mtime,
                })

        return summaries

    def load_session_summary(self, filename: str) -> Optional[str]:
        """加载会话总结内容

        Args:
            filename: 文件名

        Returns:
            总结内容，如果不存在返回 None
        """
        filepath = os.path.join(self.memory_path, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        return None

    # ==================== 记忆分类与去重 ====================

    def append_classified_memory(
        self,
        content: str,
        category: str,
        date: datetime = None,
    ):
        """追加带分类标签的记忆

        Args:
            content: 记忆内容
            category: 分类标签（preference/decision/entity/fact）
            date: 日期，默认为今天
        """
        memory_path = self.get_daily_memory_path(date)
        timestamp = datetime.now().strftime("%H:%M")

        # 确保文件存在且有标题
        if not os.path.exists(memory_path):
            date_str = (date or datetime.now()).strftime("%Y-%m-%d")
            with open(memory_path, "w", encoding="utf-8") as f:
                f.write(f"# {date_str}\n")

        # 追加带分类标签的记忆
        with open(memory_path, "a", encoding="utf-8") as f:
            f.write(f"\n## {timestamp} - 自动捕获\n\n- [{category}] {content}\n")

    def check_duplicate_memory(self, content: str, threshold: float = 0.7) -> bool:
        """检查记忆是否重复

        通过关键词重叠检测判断是否与已有记忆重复。

        Args:
            content: 待检查的内容
            threshold: 相似度阈值，默认 0.7

        Returns:
            是否重复（True 表示重复，应跳过）
        """
        # 提取关键词
        keywords = self._extract_keywords(content)
        if not keywords:
            return False

        # 检查今日记忆
        today_path = self.get_daily_memory_path()
        if os.path.exists(today_path):
            with open(today_path, "r", encoding="utf-8") as f:
                today_content = f.read()
            if self._calculate_overlap(keywords, today_content) >= threshold:
                return True

        # 检查长期记忆
        longterm_content = self.load_config("MEMORY")
        if longterm_content:
            if self._calculate_overlap(keywords, longterm_content) >= threshold:
                return True

        # 检查最近的每日记忆
        recent_files = self.get_recent_memory_day(days=2)
        for filename in recent_files:
            filepath = os.path.join(self.memory_path, filename)
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    file_content = f.read()
                if self._calculate_overlap(keywords, file_content) >= threshold:
                    return True

        return False

    def cleanup_old_memories(self, days: int = 30) -> List[str]:
        """清理过期的每日记忆

        Args:
            days: 保留天数，超过此天数将被清理

        Returns:
            被删除的文件名列表
        """
        deleted = []
        cutoff_date = datetime.now() - timedelta(days=days)

        if not os.path.exists(self.memory_path):
            return deleted

        for filename in os.listdir(self.memory_path):
            if not filename.endswith(".md"):
                continue

            # 尝试解析日期
            try:
                date_str = filename.replace(".md", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                # 检查是否过期
                if file_date < cutoff_date:
                    filepath = os.path.join(self.memory_path, filename)
                    os.remove(filepath)
                    deleted.append(filename)
            except ValueError:
                # 文件名不是日期格式，跳过
                continue

        return deleted

    def get_recent_memory_day(self, days: int = 2) -> List[str]:
        """获取最近 N 天的记忆文件名列表

        Args:
            days: 天数

        Returns:
            记忆文件名列表（YYYY-MM-DD.md 格式）
        """
        files = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            filename = date.strftime("%Y-%m-%d.md")
            filepath = os.path.join(self.memory_path, filename)
            if os.path.exists(filepath):
                files.append(filename)
        return files

    def _extract_keywords(self, text: str) -> Set[str]:
        """提取关键词（过滤中文停用词）

        Args:
            text: 输入文本

        Returns:
            关键词集合
        """
        # 中文停用词表
        stopwords = {
            "的", "了", "是", "在", "我", "有", "和", "就", "不", "人",
            "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
            "你", "会", "着", "没有", "看", "好", "自己", "这", "那",
            "什么", "这个", "那个", "可以", "就是", "这样", "然后",
            "还是", "但是", "因为", "所以", "如果", "虽然", "可能",
            "需要", "应该", "或者", "而且", "已经", "还有", "一直",
            "的话", "一下", "一些", "一点", "东西", "知道", "觉得",
            "喜欢", "偏好", "用户", "记住", "记下", "决定", "选定",
        }

        # 使用正则提取中文词和英文单词
        # 中文：2 字及以上
        # 英文：3 字母及以上
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        english_words = re.findall(r'[a-zA-Z]{3,}', text)

        keywords = set()

        # 添加中文词（过滤停用词）
        for word in chinese_words:
            if word not in stopwords:
                keywords.add(word.lower())

        # 添加英文词（转小写）
        for word in english_words:
            keywords.add(word.lower())

        return keywords

    def _calculate_overlap(self, keywords: Set[str], text: str) -> float:
        """计算关键词在文本中的匹配率

        Args:
            keywords: 关键词集合
            text: 目标文本

        Returns:
            匹配率（0.0 - 1.0）
        """
        if not keywords:
            return 0.0

        text_lower = text.lower()
        matched = sum(1 for kw in keywords if kw in text_lower)

        return matched / len(keywords)
