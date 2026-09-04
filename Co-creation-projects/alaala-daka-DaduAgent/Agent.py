import json
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from factory.model_generator import chatmodel
from agent_tools.middleware import tool_monitor,task_reflection_trigger,todo_continue_trigger
from agent_tools.agent_tools import search,calculator,todo,reflection,rag_summarize,get_todo_state,restore_todo_state,reset_todo_state
from agent_tools.file_manage_tools import file_manage, ask_for_answer
from agent_tools.session_tool import session as session_tool, set_current_agent
from session.session_store import (
    save_session_messages, load_session_messages,
    list_sessions, delete_session, get_session_info, session_exists,
    save_session_todos, load_session_todos,
    save_session_title, load_session_title, truncate_title
)
from tool.prompt_loader import system_prompt_load
from tool.config_handler import FileManage_Config, Session_Config
from tool.logger_handler import logger
"""
组建Agent，集成文件管理工具（支持 manual/auto 双模式）与会话管理
"""
def _content_to_text(content) -> str:
    """将消息 content 归一化为纯文本（兼容字符串 / content block 列表）"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text", "")))
            else:
                parts.append(str(getattr(block, "get", lambda k, d="": d)("text", "")))
        return "".join(parts)
    return str(content)


# ── 上传文件注释块协议（与前端 history 剥离共用）──
# 格式：随用户消息追加固定标记块，Agent（模型）可见文件路径；
# 前端在历史回显时用 strip_file_note 剥离该块并渲染附件 chip。
_FILE_NOTE_BEGIN = "[已上传文件]"
_FILE_NOTE_END = "[/已上传文件]"


def build_file_note(file_paths: list[str]) -> str:
    """生成「已上传文件」注释块：列出文件路径供 Agent 用 file_manage 读取/修改"""
    lines = "\n".join(f"- {p}" for p in file_paths)
    return f"{_FILE_NOTE_BEGIN}\n{lines}\n{_FILE_NOTE_END}"


def strip_file_note(text: str) -> str:
    """从文本中剥离 [已上传文件]...[/已上传文件] 块（连同周围空白）"""
    import re
    return re.sub(r"\s*\[已上传文件\][\s\S]*?\[/已上传文件\]\s*", "", text).strip()


def _sanitize_history(messages: list) -> list:
    """修复历史中 tool_calls 与其 ToolMessage 不匹配的记录。

    场景：早期 stream() 只保留最后一条 ToolMessage，导致 AIMessage 的
    tool_calls 有多条但没有对应的 ToolMessage，DeepSeek 会以 400 拒绝。
    策略：AIMessage 只保留「后续确有 ToolMessage 回应的」tool_call；
    其余未匹配的 tool_call 被剥离；完全无匹配且无文本的 AIMessage 直接删除；
    找不到任何前置 tool_call 的孤儿 ToolMessage 一并删除。
    """
    from langchain_core.messages import AIMessage, ToolMessage

    # Pass 1: 对每个 AIMessage，统计其后被 ToolMessage 回应过的 call_id
    answered: dict = {}
    for i, m in enumerate(messages):
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            answered[i] = set()
            call_ids = {tc.get("id") for tc in m.tool_calls}
            for j in range(i + 1, len(messages)):
                if isinstance(messages[j], ToolMessage):
                    if messages[j].tool_call_id in call_ids:
                        answered[i].add(messages[j].tool_call_id)

    # Pass 2: 重建
    out: list = []
    kept_tool_ids: set = set()          # 已被保留的 tool_call_id
    for i, m in enumerate(messages):
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            kept = [tc for tc in m.tool_calls if tc.get("id") in answered.get(i, set())]
            if not kept:
                # 没有任何有效工具结果：若本身无文本则丢弃，否则退化为纯文本消息
                if not _content_to_text(m.content).strip():
                    continue
                m.tool_calls = []
            else:
                m.tool_calls = kept
                kept_tool_ids.update(tc.get("id") for tc in kept)
            out.append(m)
        elif isinstance(m, ToolMessage):
            if m.tool_call_id in kept_tool_ids:   # 只保留被有效工具调用引用的结果
                out.append(m)
        else:
            out.append(m)
    return out


_TITLE_PROMPT = (
    "你是会话标题生成助手。请根据用户的第一条消息，生成一个不超过20个字符的会话主题标题。\n"
    "要求：只输出标题本身；中文为主（除非消息本身是英文）；"
    "不要引号、标点、解释或多余文字；长度严格不超过20个字符。\n"
    "用户消息：{message}"
)


def _generate_title(first_message_text: str) -> str:
    """用 DeepSeek chatmodel 生成 ≤20 字符会话标题；失败/空结果时回退截断"""
    try:
        resp = chatmodel.invoke(_TITLE_PROMPT.format(message=first_message_text[:200]))
        text = _content_to_text(getattr(resp, "content", ""))
        text = text.strip().strip('"').strip("'").strip()
        if not text:
            return truncate_title(first_message_text)
        return truncate_title(text)  # 防御性截断：LLM 输出超长也被限制到 20 字符
    except Exception:
        logger.warning("[Agent] 标题生成失败，回退到截断标题")
        return truncate_title(first_message_text)


class Agent():
    def __init__(self, session_id: str | None = None) -> None:
        # ── 会话管理初始化 ──
        self.session_id = None
        self.messages = []

        # 加载基础系统提示词并附加文件管理模式说明
        base_prompt = system_prompt_load()
        mode_section = _build_mode_section()
        full_prompt = base_prompt + "\n" + mode_section

        self.agent=create_agent(
            model=chatmodel,
            middleware=[task_reflection_trigger,todo_continue_trigger,tool_monitor],
            tools=[calculator,todo,search,reflection,rag_summarize,file_manage,ask_for_answer,session_tool],
            system_prompt=full_prompt
        )

        # 注册当前 Agent 实例供 session 工具使用
        set_current_agent(self)

        # 加载或创建会话
        if session_id:
            self._load_session_state(session_id)
        # session_id 为 None 时保持 ephemeral 模式（不持久化）

    def stream(self, query: str, file_paths: list[str] | None = None):
        from langchain_core.messages import AIMessage, ToolMessage
        query = query.strip()
        paths = [p.strip() for p in (file_paths or []) if p and p.strip()]
        if not query and not paths:
            return
        self.messages = _sanitize_history(self.messages)
        # 隐式传递上传文件路径：追加注释块到 HumanMessage 内容（模型可见、随会话持久化）
        human_content = query
        if paths:
            human_content = (query + "\n\n" + build_file_note(paths)).strip()
        self.messages.append(HumanMessage(content=human_content))
        # 本轮起始消息数：用于识别快照中"本轮新增"的消息（发 todo 事件只认增量）
        last_len = len(self.messages)
        # 失败回滚目标：从未产出任何 chunk 时，也保持"历史 + 本轮提问"这一一致状态
        last_good = list(self.messages)
        try:
            msg_dict = {
                'messages': self.messages
            }
            for chunk in self.agent.stream(msg_dict, stream_mode='values'):
                msgs = chunk.get("messages")
                if not msgs:
                    continue
                # values 模式每次都是完整快照；整体替换可确保 ToolNode 并行返回的
                # 全部 ToolMessage 都被保留（修复 tool_calls 缺配导致的 400 历史污染）
                self.messages = list(msgs)   # 拷贝，避免别名到 graph 内部列表
                last_good = self.messages
                mes = msgs[-1]
                # 本轮新增消息中出现 todo ToolMessage → 发一次快照事件（并行 add 也只发一条）
                new_msgs = msgs[last_len:]
                last_len = len(msgs)
                if any(isinstance(m, ToolMessage) and getattr(m, "name", None) == "todo"
                       for m in new_msgs):
                    yield json.dumps({"type": "todo", "todos": get_todo_state()[0]},
                                     ensure_ascii=False)
                # 只输出 AI 的回复，跳过用户消息和系统消息（避免重复用户问题）
                if isinstance(mes, AIMessage):
                    text = _content_to_text(mes.content)
                    if text.strip():
                        yield text.strip() + '\n'
        except Exception:
            # 失败时回滚到最后一个完整快照，绝不留半成品/被污染的历史
            self.messages = last_good
            raise

        # 每轮对话结束后自动保存（如果会话活跃）
        if self.session_id and Session_Config.get("auto_save", True):
            self._save_session_state()
            self._ensure_session_title()

    # ── 会话状态管理 ──

    def _load_session_state(self, session_id: str) -> None:
        """从磁盘加载会话的消息和 todo 状态"""
        messages = load_session_messages(session_id)
        if messages is not None:
            # 修复历史遗留的 tool_calls/ToolMessage 不匹配（防止加载后下一次对话被 400 拒绝）
            self.messages = _sanitize_history(messages)
            self.session_id = session_id
            todos_state = load_session_todos(session_id)
            if todos_state:
                restore_todo_state(*todos_state)
            # 遗留会话（有消息但无存储标题）打开时补齐标题
            self._ensure_session_title()
            logger.info(f"[Agent] 已加载会话 [{session_id}]：{len(self.messages)} 条消息")
        else:
            self.session_id = session_id
            self._save_session_state()
            logger.info(f"[Agent] 已创建新会话 [{session_id}]")

    def _save_session_state(self) -> None:
        """保存当前消息和 todo 状态到磁盘"""
        if not self.session_id:
            return
        save_session_messages(self.session_id, self.messages)
        todos, counter = get_todo_state()
        save_session_todos(self.session_id, todos, counter)
        logger.debug(f"[Agent] 已保存会话 [{self.session_id}]：{len(self.messages)} 条消息")

    def _first_user_message_text(self) -> str:
        """返回 messages 中第一条非空用户消息文本；无则返回 ''"""
        for msg in self.messages:
            if isinstance(msg, dict):
                if msg.get("role") != "user":
                    continue
                content = msg.get("content", "")
            elif isinstance(msg, HumanMessage):
                content = msg.content
            else:
                continue
            text = strip_file_note(_content_to_text(content)).strip()
            if text:
                return text
        return ""

    def _ensure_session_title(self) -> None:
        """首次对话后 / 打开遗留会话时，生成并持久化会话标题（仅一次）。

        已存在标题、无 session_id、无用户消息 → no-op。
        LLM 失败自动回退为第一条用户消息的截断，绝不把 hash 当标题。
        """
        if not self.session_id:
            return
        if load_session_title(self.session_id):
            return
        first_text = self._first_user_message_text()
        if not first_text:
            return
        title = _generate_title(first_text)
        if title:
            save_session_title(self.session_id, title)
            logger.info(f"[Agent] 已生成会话标题 [{self.session_id}]: {title}")

    # ── 会话操作接口（供 session_tool 和 REPL 调用）──

    def new_session(self, name: str = "") -> str:
        """创建新会话"""
        import secrets
        if self.session_id:
            self._save_session_state()
        id_len = Session_Config.get("session_id_length", 8)
        sid = secrets.token_hex(id_len // 2)
        self.messages = []
        self.session_id = sid
        reset_todo_state()
        self._save_session_state()
        logger.info(f"[Agent] 创建新会话 [{sid}]" + (f" —— {name}" if name else ""))
        return sid

    def switch_session(self, session_id: str) -> bool:
        """切换到指定会话"""
        if not session_exists(session_id):
            return False
        if self.session_id:
            self._save_session_state()
        self.messages = []
        self._load_session_state(session_id)
        logger.info(f"[Agent] 已切换到会话 [{session_id}]")
        return True

    def list_sessions(self) -> list[dict]:
        """列出所有已保存的会话"""
        return list_sessions()

    def delete_session(self, session_id: str) -> bool:
        """删除指定会话（不能删除当前活跃会话）"""
        if session_id == self.session_id:
            return False
        return delete_session(session_id)

    def get_session_info(self, session_id: str) -> dict | None:
        """获取会话详细信息"""
        return get_session_info(session_id)

    def get_tool_names(self) -> list[str]:
        """返回当前 Agent 已注册的工具名称列表"""
        return [
            "search", "calculator", "todo", "reflection",
            "rag_summarize", "file_manage", "ask_for_answer", "session"
        ]

    @classmethod
    def create_with_config(
        cls,
        session_id: str | None = None,
        tool_whitelist: list[str] | None = None,
        model_name: str | None = None,
    ):
        """
        使用指定配置创建 Agent 实例。
        读取最新的 YAML 配置（而非模块级缓存），支持工具白名单和模型覆盖。
        """
        from factory.model_generator import create_chatmodel
        from tool.config_handler import FileManage_Config

        # 如指定模型，临时替换 chatmodel
        if model_name:
            import factory.model_generator as mg
            mg.chatmodel = create_chatmodel(model_name)

        agent = cls(session_id=session_id)

        # 工具白名单过滤
        if tool_whitelist:
            all_tools = {
                "search": search,
                "calculator": calculator,
                "todo": todo,
                "reflection": reflection,
                "rag_summarize": rag_summarize,
                "file_manage": file_manage,
                "ask_for_answer": ask_for_answer,
                "session": session_tool,
            }
            enabled = [all_tools[name] for name in tool_whitelist if name in all_tools]
            agent.agent = create_agent(
                model=agent.agent.model,
                middleware=agent.agent.middleware,
                tools=enabled,
                system_prompt=agent.agent.system_prompt,
            )

        return agent

def _build_mode_section() -> str:
    """根据 FileManageConfig 中的模式，构建附加到系统提示词的模式说明"""
    mode = FileManage_Config.get("mode", "manual")
    allowed_paths = FileManage_Config.get("allowed_paths", ["."])
    blocked_patterns = FileManage_Config.get("blocked_patterns", [])

    allowed_str = ", ".join(allowed_paths)
    blocked_str = ", ".join(blocked_patterns[:10])  # 仅展示前10个

    if mode == "manual":
        section = f"""
## 文件管理模式 - 手动模式 (MANUAL)

当前文件管理处于 **手动模式**。你必须遵循以下规则：

### 操作权限
- ✅ **自由执行**（无需用户批准）: read / list / info / exists / search
- 🔐 **需用户批准**（必须先调用 ask_for_answer）: write / append / delete / mkdir

### 批准流程
1. 你调用 file_manage write/append/delete/mkdir（不加 --approved）
2. file_manage 返回预览信息和拒绝提示
3. 你根据提示调用 ask_for_answer 向用户说明操作细节
4. 用户回复后，用返回结果判断是否获批
5. 如获批: 用 **--approved** 标记重新调用 file_manage 完成操作
   格式: file_manage("write --approved <路径> | <内容>")
6. 如被拒: 放弃该操作，告知用户

### 示例
```
用户: "帮我创建一个 test.txt，内容是 hello"
Agent:
  Thought: 手动模式写文件需要批准，先预览操作。
  Action: file_manage("write test.txt | hello")
  Observation: [手动模式 - 需要用户批准] ... 请先调用 ask_for_answer ...
Agent:
  Thought: 需要获得用户批准。
  Action: ask_for_answer("是否允许在项目根目录创建 test.txt？内容: hello")
  Observation: 用户回答: yes
Agent:
  Thought: 用户已批准，执行写入。
  Action: file_manage("write --approved test.txt | hello")
  Observation: ✅ 已写入文件 ...
```

### 安全边界
- 允许操作目录: {allowed_str}
- 全局拦截模式: {blocked_str} ...
- 每次写入/删除操作都会记录到日志
"""
    else:
        section = f"""
## 文件管理模式 - 自动模式 (AUTO)

当前文件管理处于 **自动模式**。你可以较自由地执行文件 CRUD 操作，但有以下硬性限制：

### 自动模式禁止的操作
1. ❌ **禁止删除目录**（delete 仅支持删除单个文件）
2. ❌ **禁止操作系统敏感路径**: /etc/, C:\\Windows, ~/.ssh 等
3. ❌ **禁止操作匹配封锁模式的文件**: {blocked_str} ...
4. ❌ **禁止写入不允许的扩展名文件**（如 .exe, .dll）
5. ❌ **文件大小限制**: 读 {FileManage_Config.get('max_file_size_read', 1048576) // 1024 // 1024}MB / 写 {FileManage_Config.get('max_file_size_write', 5242880) // 1024 // 1024}MB

### 允许的操作
- ✅ read / list / info / exists / search: 自由查询
- ✅ write / append / delete / mkdir: 在安全边界内自由执行

### 安全边界
- 允许操作目录: {allowed_str}
- 所有操作都会被记录到日志
- 遇到被拦截的操作时，如实告知用户原因并建议手动处理

### 注意事项
- 不要删除任何看起来重要的文件
- 不确定是否安全的操作，先向用户说明
- 路径遍历攻击 (. . /) 在任何模式下都会被自动拦截
"""
    return section
