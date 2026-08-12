"""状态模型，用于深度研究工作流。"""

from dataclasses import dataclass, field


@dataclass(kw_only=True)
class TodoItem:
    """单个待办任务项。"""

    id: int
    title: str
    intent: str
    query: str
    status: str = field(default="pending")
    summary: str | None = field(default=None)
    sources_summary: str | None = field(default=None) 
    notices: list[str] = field(default_factory=list)
    note_id: str | None = field(default=None)
    note_path: str | None = field(default=None)
    stream_token: str | None = field(default=None)


@dataclass(kw_only=True)
class SummaryState:
    """深度研究工作流的状态模型。
    
    用于追踪研究主题、搜索结果、待办任务和生成的报告。
    """

    research_topic: str | None = field(default=None)  # 研究主题
    web_research_results: list = field(default_factory=list)
    sources_gathered: list = field(default_factory=list)
    research_loop_count: int = field(default=0)  # 研究循环次数
    running_summary: str | None = field(default=None)  # 传统摘要字段
    todo_items: list = field(default_factory=list)  # 待办任务项列表
    structured_report: str | None = field(default=None)  # 结构化报告（JSON 字符串）
    report_note_id: str | None = field(default=None)  # 报告笔记 ID
    report_note_path: str | None = field(default=None)  # 报告笔记路径
    podcast_script: list | None = field(default=None)  # 播客脚本（JSON 字符串）


@dataclass(kw_only=True)
class SummaryStateOutput:
    """深度研究工作流的输出状态模型。
    
    用于返回研究摘要、报告、待办任务和播客脚本。
    """

    running_summary: str | None = field(default=None)  # 向后兼容的摘要文本
    report_markdown: str | None = field(default=None)
    todo_items: list[TodoItem] = field(default_factory=list)
    podcast_script: list | None = field(default=None)

