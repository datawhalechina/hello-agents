"""
Agent工具实现
"""
from langchain_core.tools import tool
from tavily import TavilyClient
from tool.config_handler import System_Config, Chroma_Config
from tool.logger_handler import logger
from vector_uploader_service.rag_summarize import Rag_Summarize
from dotenv import load_dotenv
load_dotenv()
"""
Travily网络搜索工具
"""
@tool(description="网络搜索工具，用于搜索具有时效性知识和知识库以外的知识，输入为你要查询的问题字符串")
def search(query:str)->str:
    tavily_client=TavilyClient(
        api_key=System_Config["tavily_api_key"],
    )
    response=tavily_client.search(query=query,search_depth='basic',topic='general',max_results=4)
    search_content=''
    for res in response["results"]:
        search_content+=res['title']+'\n'
        search_content+=res['content']+'\n'
    return search_content

"""
计算器工具 -- 基于AST的安全表达式求值
"""
import ast
import math
import operator

# 安全求值器:仅允许白名单内的节点和运算符，避免 eval 的安全风险
_SAFE_OPS = {
    ast.Add:      operator.add,
    ast.Sub:      operator.sub,
    ast.Mult:     operator.mul,
    ast.Div:      operator.truediv,
    ast.Pow:      operator.pow,
    ast.USub:     operator.neg,
    ast.UAdd:     operator.pos,
    ast.Mod:      operator.mod,
    ast.FloorDiv: operator.floordiv,
}

_SAFE_FUNCS = {
    "abs":    abs,
    "round":  round,
    "min":    min,
    "max":    max,
    "sum":    sum,
    "pow":    pow,
    "sqrt":   math.sqrt,
    "log":    math.log,
    "log10":  math.log10,
    "log2":   math.log2,
    "exp":    math.exp,
    "sin":    math.sin,
    "cos":    math.cos,
    "tan":    math.tan,
    "asin":   math.asin,
    "acos":   math.acos,
    "atan":   math.atan,
    "pi":     math.pi,
    "e":      math.e,
    "ceil":   math.ceil,
    "floor":  math.floor,
    "factorial": math.factorial,
    "gcd":    math.gcd,
    "radians": math.radians,
    "degrees": math.degrees,
}


def _safe_eval(node: ast.AST) -> float:
    """递归遍历 AST 节点，仅计算白名单内的运算"""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError(f"不支持的常量类型: {type(node.value).__name__}")

    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _SAFE_OPS[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.operand))

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
        if name in _SAFE_FUNCS:
            args = [_safe_eval(a) for a in node.args]
            return _SAFE_FUNCS[name](*args)

    raise ValueError(f"表达式包含不支持的操作: {ast.dump(node)}")


@tool(description="""安全计算器工具，基于AST白名单求值，支持以下运算和函数:

运算符: + - * / // % ** （及正负号 +x / -x）
常量: pi, e
基础: abs, round, min, max, sum, pow, sqrt
指数对数: exp, log, log2, log10
三角: sin, cos, tan, asin, acos, atan
取整: ceil, floor
数论/转换: factorial, gcd, radians, degrees

输入为一个数学表达式字符串，例如 '3+5*2'、'sqrt(16)+log(e)'、'sin(pi/2)'、'ceil(3.14)'""")
def calculator(expression: str) -> str:
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _safe_eval(tree)
        # 结果若为整数则去掉小数点后缀
        if isinstance(result, float) and result == int(result) and not math.isinf(result):
            result = int(result)
        return str(result)
    except SyntaxError:
        return f"错误: 表达式语法无效 ---- '{expression}'"
    except (ValueError, ZeroDivisionError, OverflowError) as e:
        return f"错误: {e}"

"""
待办清单工具 -- 支持 Agent 自主管理任务计划与执行进度
"""
from datetime import datetime
from typing import Any

# 内存存储:任务列表，每条记录为 {"id", "title", "desc", "status", "created_at", "done_at"}
_TODOS: list[dict[str, Any]] = []
_TODO_ID_COUNTER = 0

_STATUS_ICON = {
    "pending":     "⬜",
    "in_progress": "🔄",
    "done":        "✅",
}


def _format_todos(todos: list[dict[str, Any]]) -> str:
    """将任务列表格式化为 Agent 友好的文本"""
    if not todos:
        return "（空）暂无待办事项。"

    total = len(todos)
    done_count = sum(1 for t in todos if t["status"] == "done")
    progress = f"{done_count}/{total}"

    lines = [f"📋 待办清单 [{progress} 已完成]", "─" * 36]
    for t in todos:
        icon = _STATUS_ICON.get(t["status"], "❓")
        line = f"  {icon} [{t['id']}] {t['title']}"
        if t.get("desc"):
            line += f"\n       └ {t['desc']}"
        if t["status"] == "done" and t.get("done_at"):
            line += f"  ✓{t['done_at']}"
        lines.append(line)
    return "\n".join(lines)


@tool(description="""待办清单工具，用于记录和追踪任务计划与执行进度。

操作命令（输入以下格式的字符串）:
  add <标题>                    → 添加新任务
  add <标题> | <描述>           → 添加带描述的任务
  list [all|pending|done]       → 列出任务（默认 all）
  doing <id>                    → 将任务标记为"进行中"
  done <id>                     → 将任务标记为"已完成"
  delete <id>                   → 删除任务
  clear done                    → 清除所有已完成任务
  reset                         → 清空全部任务

示例:'add 实现登录模块 | 含OAuth和JWT两种方式'、'list pending'、'done 3'""")
def todo(command: str) -> str:
    global _TODO_ID_COUNTER

    cmd = command.strip()
    if not cmd:
        return "错误: 请输入操作命令，例如 'list' 或 'add 任务名称'"

    parts = cmd.split(maxsplit=1)
    action = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    # ── add ──
    if action == "add":
        if not arg:
            return "错误: 用法 'add <标题>' 或 'add <标题> | <描述>'"
        if "|" in arg:
            title, _, desc = arg.partition("|")
            title, desc = title.strip(), desc.strip()
        else:
            title, desc = arg, ""
        _TODO_ID_COUNTER += 1
        item = {
            "id": _TODO_ID_COUNTER,
            "title": title,
            "desc": desc,
            "status": "pending",
            "created_at": datetime.now().strftime("%m-%d %H:%M"),
            "done_at": None,
        }
        _TODOS.append(item)
        return f"✅ 已添加任务 [{item['id']}] {title}" + (f"\n   描述: {desc}" if desc else "")

    # ── list ──
    if action == "list":
        filter_status = arg.lower() if arg else "all"
        if filter_status in ("pending", "in_progress", "done"):
            filtered = [t for t in _TODOS if t["status"] == filter_status]
        else:
            filtered = _TODOS
        return _format_todos(filtered)

    # ── done / doing ──
    if action in ("done", "doing"):
        if not arg:
            return f"错误: 用法 '{action} <任务ID>'"
        try:
            tid = int(arg)
        except ValueError:
            return f"错误: 任务ID必须是数字，收到 '{arg}'"
        for t in _TODOS:
            if t["id"] == tid:
                if action == "done":
                    t["status"] = "done"
                    t["done_at"] = datetime.now().strftime("%m-%d %H:%M")
                    return f"✅ 任务 [{tid}] {t['title']} 已完成。"
                else:
                    t["status"] = "in_progress"
                    return f"🔄 任务 [{tid}] {t['title']} 标记为进行中。"
        return f"错误: 未找到ID为 {tid} 的任务"

    # ── delete ──
    if action == "delete":
        if not arg:
            return "错误: 用法 'delete <任务ID>'"
        try:
            tid = int(arg)
        except ValueError:
            return f"错误: 任务ID必须是数字，收到 '{arg}'"
        for i, t in enumerate(_TODOS):
            if t["id"] == tid:
                removed = _TODOS.pop(i)
                return f"🗑 已删除任务 [{tid}] {removed['title']}。"
        return f"错误: 未找到ID为 {tid} 的任务"

    # ── clear done ──
    if action == "clear" and arg.lower() == "done":
        before = len(_TODOS)
        _TODOS[:] = [t for t in _TODOS if t["status"] != "done"]
        removed = before - len(_TODOS)
        return f"🗑 已清除 {removed} 条已完成任务。"

    # ── reset ──
    if action == "reset":
        count = len(_TODOS)
        _TODOS.clear()
        _TODO_ID_COUNTER = 0
        return f"🗑 已清空全部 {count} 条任务。"

    return f"错误: 未知操作 '{action}'。支持: add / list / doing / done / delete / clear done / reset"

# ── Todo 状态导出/恢复（供会话持久化使用）──

def get_todo_state() -> tuple:
    """导出当前 todo 状态快照：(任务列表, ID计数器)"""
    return list(_TODOS), _TODO_ID_COUNTER


def restore_todo_state(todos: list, counter: int) -> None:
    """从快照恢复 todo 状态"""
    global _TODOS, _TODO_ID_COUNTER
    _TODOS.clear()
    _TODOS.extend(todos)
    _TODO_ID_COUNTER = counter


def reset_todo_state() -> None:
    """重置 todo 状态"""
    global _TODOS, _TODO_ID_COUNTER
    _TODOS.clear()
    _TODO_ID_COUNTER = 0



"""
反思总结笔记本工具 -- Agent 任务结束时的经验沉淀、检索与管理
================================================================
存储:专有 Chroma collection，支持语义搜索
触发:Middleware 在任务完成时注入反思提示，Agent 主动调用本工具记录
"""
from datetime import datetime, timedelta
from typing import Any
from langchain_chroma import Chroma
from factory.model_generator import create_embeddingmodel


def _build_reflection_chroma() -> Chroma:
    """构建反思笔记专用 Chroma collection（与知识库共用同一 embedding 配置）"""
    return Chroma(
        collection_name=Chroma_Config.get("reflection_collection_name", "agent_reflections"),
        persist_directory=Chroma_Config["persist_directory"],
        embedding_function=create_embeddingmodel(),
    )


# ── 初始化专有 Chroma collection ──
_reflection_chroma = _build_reflection_chroma()

# ── 严重程度映射 ──
_SEVERITY_ICON: dict[str, str] = {
    "fatal":   "💀",
    "high":    "🔴",
    "medium":  "🟡",
    "low":     "🟢",
}
_SEVERITY_LABEL: dict[str, str] = {
    "fatal":   "致命",
    "high":    "严重",
    "medium":  "一般",
    "low":     "轻微",
}

_VALID_SEVERITIES = frozenset(_SEVERITY_ICON.keys())

# 严重程度排序权重：0 最小 → 排序 reverse 后 fatal 在前（"重要优先"展示）
_SEVERITY_RANK: dict[str, int] = {"fatal": 0, "high": 1, "medium": 2, "low": 3}

def _max_ref_num() -> int:
    """现有 ids 中最大 ref_N 的 N；无则 0。修复'按总数计数'导致删除后重复 id 的 bug。"""
    try:
        ids = _reflection_chroma.get(include=[])["ids"]
    except Exception:
        return 0
    nums = []
    for rid in ids:
        if isinstance(rid, str) and rid.startswith("ref_"):
            try:
                nums.append(int(rid.split("_", 1)[1]))
            except ValueError:
                continue  # 跳过畸形 id（如 ref_abc），不影响稳定性
    return max(nums) if nums else 0


def _next_ref_id() -> str:
    """始终基于 max+1：删除后不重排、永不复用现存 id、跨重启稳定。"""
    return f"ref_{_max_ref_num() + 1}"


def _build_page_content(error_desc: str, solution: str, philosophy: str) -> str:
    """组装入库文本，便于语义搜索时匹配完整信息"""
    parts = [
        f"错误描述:{error_desc}",
        f"解决方案:{solution}",
        f"哲学理解:{philosophy}",
    ]
    return "\n".join(parts)


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _fmt_notes(entries: list[dict[str, Any]], with_similarity: bool = False) -> str:
    """批量格式化反思笔记"""
    if not entries:
        return "（空）暂无反思笔记。\n\n💡 试试: reflection add 错误 | 解决方案 | 哲学理解"

    lines = [f"📖 反思笔记本 [共 {len(entries)} 条]", "═" * 48]
    for i, entry in enumerate(entries, 1):
        meta = entry.get("metadata", {})
        content = entry.get("page_content", entry.get("content", ""))
        sev = meta.get("severity", "medium")
        icon = _SEVERITY_ICON.get(sev, "❓")
        label = _SEVERITY_LABEL.get(sev, sev)
        tags = meta.get("tags", "general")
        ts = meta.get("timestamp", "未知")
        rid = meta.get("ref_id", "?")

        content_display = content.replace("\n", "\n   │ ")
        lines.append(f"  {icon} [{rid}] {label} | 🏷 {tags} | 📅 {ts}")
        lines.append(f"   │ {content_display}")
        if with_similarity and "similarity" in entry:
            lines.append(f"   📊 相关度: {entry['similarity']:.3f}")
        if i < len(entries):
            lines.append("   ·")
    return "\n".join(lines)


@tool(description="""反思总结笔记本工具，用于在每次任务结束后沉淀经验教训并支持回顾检索。

存储于专有向量库，支持语义搜索，让 Agent 能在未来遇到相似场景时检索历史教训。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
操作命令（输入以下格式的字符串）:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  add <错误描述> | <解决方案> | <哲学理解>
       → 添加反思笔记（必填三字段）
  add <错误描述> | <解决方案> | <哲学理解> | <标签> | <严重程度>
       → 添加时指定标签（逗号分隔）和严重程度（fatal/high/medium/low）

  list                         → 列出全部笔记
  list <关键词>                → 按关键词语义搜索
  list tag:<标签>              → 按标签过滤
  list severity:<级别>         → 按严重程度过滤

  search <查询文本>            → 语义搜索相关笔记

  delete <ref_id>              → 删除指定笔记（如 delete ref_3）

  update <ref_id> | <新错误描述> | <新解决方案> | <新哲学理解>
  update <ref_id> | <新错误描述> | <新解决方案> | <新哲学理解> | <标签> | <严重程度>

  cleanup <天数>               → 清除 N 天前的旧笔记（如 cleanup 30）

  stats                        → 查看统计概览（按标签 & 严重程度分布）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
示例:
  'add 忘记处理空指针 | 添加 is None 检查 | 永远先考虑边界条件'
  'add token超限导致截断 | 对长文本先切片再送入 | 分治是处理大规模输入的核心 | token,截断,分治 | high'
  'list'
  'list token'
  'list severity:high'
  'search 空指针异常'
  'update ref_3 | 更好的错误描述 | 更好的解决方案 | 更深的理解'
  'delete ref_5'
  'cleanup 90'
  'stats'""")
def reflection(command: str) -> str:
    cmd = command.strip()
    if not cmd:
        return _help_text()

    parts = cmd.split(maxsplit=1)
    action = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    # ── add ──
    if action == "add":
        return _cmd_add(arg)

    # ── list ──
    if action == "list":
        return _cmd_list(arg)

    # ── search ──
    if action == "search":
        return _cmd_search(arg)

    # ── delete ──
    if action == "delete":
        return _cmd_delete(arg)

    # ── update ──
    if action == "update":
        return _cmd_update(arg)

    # ── cleanup ──
    if action == "cleanup":
        return _cmd_cleanup(arg)

    # ── stats ──
    if action == "stats":
        return _cmd_stats()

    return f"错误: 未知操作 '{action}'。支持: add / list / search / delete / update / cleanup / stats"


# ═══════════════════════════════════════════════════════════
#  命令实现
# ═══════════════════════════════════════════════════════════

def _parse_add_arg(arg: str) -> tuple[str, str, str, str, str]:
    """解析 add/update 参数: 错误|解决方案|哲学|[标签]|[严重程度]"""
    fields = [f.strip() for f in arg.split("|")]
    if len(fields) < 3:
        raise ValueError(
            "参数不足，需要至少 3 个字段（用 | 分隔）:\n"
            "  错误描述 | 解决方案 | 哲学理解\n"
            "  可选追加: | 标签(逗号分隔) | 严重程度(fatal/high/medium/low)"
        )
    error_desc = fields[0]
    solution = fields[1]
    philosophy = fields[2]
    tags = fields[3] if len(fields) > 3 and fields[3] else "general"
    severity = fields[4] if len(fields) > 4 and fields[4] else "medium"

    if severity not in _VALID_SEVERITIES:
        severity = "medium"
    return error_desc, solution, philosophy, tags, severity


def _cmd_add(arg: str) -> str:
    if not arg:
        return "错误: 用法 'add <错误描述> | <解决方案> | <哲学理解>' 或追加 '| <标签> | <严重程度>'"

    try:
        error_desc, solution, philosophy, tags, severity = _parse_add_arg(arg)
    except ValueError as e:
        return f"错误: {e}"

    ref_id = _next_ref_id()
    ts = _now_iso()
    page_content = _build_page_content(error_desc, solution, philosophy)

    _reflection_chroma.add_texts(
        texts=[page_content],
        ids=[ref_id],
        metadatas=[{
            "ref_id": ref_id,
            "error_desc": error_desc,
            "solution": solution,
            "philosophy": philosophy,
            "tags": tags,
            "severity": severity,
            "timestamp": ts,
        }],
    )
    icon = _SEVERITY_ICON.get(severity, "")
    return (
        f"✅ 反思笔记已记录 [{ref_id}]\n"
        f"   {icon} 严重程度: {_SEVERITY_LABEL.get(severity, severity)}\n"
        f"   🏷 标签: {tags}\n"
        f"   📅 {ts}\n"
        f"   ─────────────────\n"
        f"   ❌ 错误: {error_desc}\n"
        f"   ✅ 解决: {solution}\n"
        f"   💡 领悟: {philosophy}"
    )


def _cmd_list(arg: str) -> str:
    # 解析过滤器
    tag_filter = None
    severity_filter = None
    keyword = None

    remain_parts = []
    for token in arg.split() if arg else []:
        if token.startswith("tag:"):
            tag_filter = token[4:]
        elif token.startswith("severity:"):
            severity_filter = token[9:]
        else:
            remain_parts.append(token)

    keyword = " ".join(remain_parts) if remain_parts else None

    # 有关键词 → 语义搜索
    if keyword:
        return _cmd_search_internal(keyword, tag_filter, severity_filter)

    # 无关键词 → 全量列出 + Python 侧过滤
    try:
        all_data = _reflection_chroma.get()
    except Exception as e:
        logger.warning(f"[reflection] list 获取数据失败: {e}")
        return "（空）暂无反思笔记。"

    if not all_data or not all_data["ids"]:
        return "（空）暂无反思笔记。"

    entries = []
    for i, doc_id in enumerate(all_data["ids"]):
        meta = all_data["metadatas"][i] if all_data["metadatas"] else {}
        content = all_data["documents"][i] if all_data["documents"] else ""

        # Python 侧过滤
        if tag_filter and tag_filter.lower() not in meta.get("tags", "").lower():
            continue
        if severity_filter and severity_filter.lower() != meta.get("severity", "").lower():
            continue

        entries.append({"metadata": meta, "page_content": content})

    return _fmt_notes(entries)


def _cmd_search(arg: str) -> str:
    if not arg:
        return "错误: 用法 'search <查询文本>' 进行语义搜索"
    return _cmd_search_internal(arg, tag_filter=None, severity_filter=None)


def _cmd_search_internal(query: str, tag_filter: str | None, severity_filter: str | None) -> str:
    """内部语义搜索，支持额外过滤"""
    try:
        results = _reflection_chroma.similarity_search_with_score(query=query, k=10)
    except Exception as e:
        logger.warning(f"[reflection] 语义搜索失败: {e}")
        return f"搜索失败: {e}"

    if not results:
        return f"未找到与 '{query}' 相关的反思笔记。"

    entries = []
    for doc, score in results:
        meta = doc.metadata

        # 过滤
        if tag_filter and tag_filter.lower() not in meta.get("tags", "").lower():
            continue
        if severity_filter and severity_filter.lower() != meta.get("severity", "").lower():
            continue

        entries.append({
            "metadata": meta,
            "page_content": doc.page_content,
            "similarity": 1.0 - score if score <= 1.0 else 1.0 / (1.0 + score),
        })

    if not entries:
        return f"未找到匹配过滤条件的笔记（关键词 '{query}' 有结果但被过滤条件排除）。"

    return _fmt_notes(entries, with_similarity=True)


def _cmd_delete(arg: str) -> str:
    if not arg:
        return "错误: 用法 'delete <ref_id>'（如 delete ref_3）"

    ref_id = arg.strip()
    try:
        _reflection_chroma.delete(ids=[ref_id])
        return f"🗑 已删除反思笔记 [{ref_id}]。"
    except Exception as e:
        logger.warning(f"[reflection] 删除失败: {e}")
        return f"删除失败: 未找到笔记 [{ref_id}]，或 Chroma 不支持按 ID 删除。\n可尝试: cleanup <天数> 按时间清理。"


def _cmd_update(arg: str) -> str:
    if not arg:
        return "错误: 用法 'update <ref_id> | <新错误描述> | <新解决方案> | <新哲学理解>' 可追加标签和严重程度"

    fields = [f.strip() for f in arg.split("|")]
    if len(fields) < 4:
        return "错误: 需要 ref_id + 三个字段（错误|解决方案|哲学理解），用 | 分隔"

    ref_id = fields[0]
    try:
        error_desc, solution, philosophy, tags, severity = _parse_add_arg("|".join(fields[1:]))
    except ValueError as e:
        return f"错误: {e}"

    # 先取原记录的时间戳
    try:
        existing = _reflection_chroma.get(ids=[ref_id])
        old_ts = (
            existing["metadatas"][0].get("timestamp")
            if existing and existing["metadatas"]
            else _now_iso()
        )
    except Exception:
        old_ts = _now_iso()

    # 删除旧记录
    try:
        _reflection_chroma.delete(ids=[ref_id])
    except Exception:
        pass

    # 写入新记录
    ts = _now_iso()
    page_content = _build_page_content(error_desc, solution, philosophy)
    _reflection_chroma.add_texts(
        texts=[page_content],
        ids=[ref_id],
        metadatas=[{
            "ref_id": ref_id,
            "error_desc": error_desc,
            "solution": solution,
            "philosophy": philosophy,
            "tags": tags,
            "severity": severity,
            "timestamp": old_ts,
            "updated_at": ts,
        }],
    )
    return f"✅ 反思笔记 [{ref_id}] 已更新。\n   📅 原创建: {old_ts} | 更新于: {ts}"


def _cmd_cleanup(arg: str) -> str:
    if not arg:
        return "错误: 用法 'cleanup <天数>'，将清除指定天数之前的旧笔记"

    try:
        days = int(arg.strip())
    except ValueError:
        return f"错误: 天数必须是整数，收到 '{arg}'"

    if days <= 0:
        return "错误: 天数必须大于 0"

    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    try:
        all_data = _reflection_chroma.get()
    except Exception as e:
        return f"获取数据失败: {e}"

    if not all_data or not all_data["ids"]:
        return "（空）没有可清理的笔记。"

    to_delete = []
    kept = 0
    for i, doc_id in enumerate(all_data["ids"]):
        meta = all_data["metadatas"][i] if all_data["metadatas"] else {}
        ts = meta.get("timestamp", "")
        if ts and ts < cutoff_str:
            to_delete.append(doc_id)
        else:
            kept += 1

    if not to_delete:
        return f"没有超过 {days} 天的旧笔记（共 {len(all_data['ids'])} 条）。"

    try:
        _reflection_chroma.delete(ids=to_delete)
    except Exception as e:
        logger.warning(f"[reflection] cleanup 批量删除失败: {e}")
        return f"批量删除失败: {e}"

    return f"🗑 已清除 {len(to_delete)} 条 {days} 天前的旧笔记。\n   ✅ 保留 {kept} 条近期笔记。\n   📅 截止时间: {cutoff_str}"


def _cmd_stats() -> str:
    try:
        all_data = _reflection_chroma.get()
    except Exception as e:
        return f"获取数据失败: {e}"

    if not all_data or not all_data["ids"]:
        return "📊 暂无反思笔记，无统计数据。"

    total = len(all_data["ids"])

    # 按严重程度统计
    sev_counts: dict[str, int] = {}
    # 按标签统计
    tag_counts: dict[str, int] = {}
    # 时间范围
    timestamps: list[str] = []

    for i in range(total):
        meta = all_data["metadatas"][i] if all_data["metadatas"] else {}
        sev = meta.get("severity", "medium")
        sev_counts[sev] = sev_counts.get(sev, 0) + 1

        tags_str = meta.get("tags", "general")
        for t in tags_str.split(","):
            t = t.strip()
            if t:
                tag_counts[t] = tag_counts.get(t, 0) + 1

        ts = meta.get("timestamp", "")
        if ts:
            timestamps.append(ts)

    lines = [
        "📊 反思笔记本统计",
        "═" * 40,
        f"   📝 总计笔记: {total} 条",
        "",
        "   严重程度分布:",
    ]
    for sev in ["fatal", "high", "medium", "low"]:
        count = sev_counts.get(sev, 0)
        if count > 0:
            icon = _SEVERITY_ICON.get(sev, "❓")
            label = _SEVERITY_LABEL.get(sev, sev)
            bar = "█" * min(count, 20)
            lines.append(f"   {icon} {label}: {count} {bar}")

    lines.append("")
    lines.append("   标签分布:")
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    for tag, count in sorted_tags[:10]:
        lines.append(f"   🏷 {tag}: {count}")

    if timestamps:
        timestamps.sort()
        lines.append("")
        lines.append(f"   📅 最早: {timestamps[0]}")
        lines.append(f"   📅 最新: {timestamps[-1]}")

    return "\n".join(lines)


def _help_text() -> str:
    return """📖 反思笔记本 -- 使用指南
═══════════════════════════════
add <错误描述> | <解决方案> | <哲学理解> [| <标签> | <严重程度>]
list [关键词] [tag:标签] [severity:级别]
search <查询文本>
delete <ref_id>
update <ref_id> | <错误> | <解决> | <理解> [| <标签> | <严重程度>]
cleanup <天数>
stats"""


# ═══════════════════════════════════════════════════════════
#  结构化数据访问（供 Web 面板 / REST API 使用，返回 dict）
# ═══════════════════════════════════════════════════════════

def _reflection_meta_to_dict(meta: dict) -> dict:
    """metadata → 前端 JSON 安全 dict。tags 保持逗号分隔字符串（与存储一致，可无损回写）。"""
    return {
        "ref_id":     meta.get("ref_id", ""),
        "error_desc": meta.get("error_desc", ""),
        "solution":   meta.get("solution", ""),
        "philosophy": meta.get("philosophy", ""),
        "tags":       meta.get("tags", "general"),
        "severity":   meta.get("severity", "medium"),
        "timestamp":  meta.get("timestamp", ""),
        "updated_at": meta.get("updated_at", ""),
    }


def _validate_ref_fields(error_desc: str, solution: str, philosophy: str, severity: str) -> None:
    """新增/更新共用的字段校验；tags 单独处理。"""
    if not (error_desc.strip() and solution.strip() and philosophy.strip()):
        raise ValueError("错误描述 / 解决方案 / 哲学理解 不能为空")
    if severity not in _VALID_SEVERITIES:
        raise ValueError(f"无效严重程度: {severity}（可选 fatal/high/medium/low）")


def _normalize_tags(tags: str | None) -> str:
    """去首尾空格、剔除空标签与分隔符 |（防止污染 CLI 的 '|' 解析），逗号连接。"""
    if not tags:
        return "general"
    cleaned = ",".join(t.strip().replace("|", "") for t in tags.split(",") if t.strip())
    return cleaned or "general"


def list_reflections() -> list[dict]:
    """全部笔记，按严重程度降序（fatal>high>medium>low），同级内按 timestamp 倒序。返回结构化 dict 列表。"""
    try:
        all_data = _reflection_chroma.get()
    except Exception as e:
        logger.warning(f"[reflection] list 获取数据失败: {e}")
        return []
    if not all_data or not all_data["ids"]:
        return []
    entries = []
    for i, _ in enumerate(all_data["ids"]):
        meta = all_data["metadatas"][i] if all_data["metadatas"] else {}
        entries.append(_reflection_meta_to_dict(meta))
    # 先按时间倒序（稳定），再按严重程度升序稳定排序：
    # fatal(0) 在前、low(3) 在后、未知(99) 兜底最后；同级内保持时间倒序。
    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    entries.sort(key=lambda e: _SEVERITY_RANK.get(e.get("severity", "medium"), 99))
    return entries


def get_reflection(ref_id: str) -> dict | None:
    """按 id 取单条；不存在返回 None。"""
    try:
        data = _reflection_chroma.get(ids=[ref_id])
    except Exception as e:
        logger.warning(f"[reflection] get {ref_id} 失败: {e}")
        return None
    if not data or not data["ids"]:
        return None
    meta = data["metadatas"][0] if data["metadatas"] else {}
    return _reflection_meta_to_dict(meta)


def create_reflection(error_desc: str, solution: str, philosophy: str,
                      tags: str = "general", severity: str = "medium") -> dict:
    """新增。id 来自 _next_ref_id()（max+1）。返回创建后的 dict。"""
    _validate_ref_fields(error_desc, solution, philosophy, severity)
    _tags = _normalize_tags(tags)
    ref_id = _next_ref_id()
    ts = _now_iso()
    page_content = _build_page_content(error_desc.strip(), solution.strip(), philosophy.strip())
    _reflection_chroma.add_texts(
        texts=[page_content],
        ids=[ref_id],
        metadatas=[{
            "ref_id": ref_id,
            "error_desc": error_desc.strip(),
            "solution": solution.strip(),
            "philosophy": philosophy.strip(),
            "tags": _tags,
            "severity": severity,
            "timestamp": ts,
        }],
    )
    return get_reflection(ref_id)


def update_reflection(ref_id: str, error_desc: str | None = None, solution: str | None = None,
                      philosophy: str | None = None, tags: str | None = None,
                      severity: str | None = None) -> dict | None:
    """局部更新：仅合并非 None 字段，保留原 timestamp，写入 updated_at。返回更新后 dict；不存在返回 None。"""
    existing = get_reflection(ref_id)
    if existing is None:
        return None
    new_desc = error_desc if error_desc is not None else existing["error_desc"]
    new_sol = solution if solution is not None else existing["solution"]
    new_phi = philosophy if philosophy is not None else existing["philosophy"]
    new_tags = _normalize_tags(tags if tags is not None else existing["tags"])
    new_sev = severity if severity is not None else existing["severity"]
    _validate_ref_fields(new_desc, new_sol, new_phi, new_sev)

    old_ts = existing["timestamp"]
    page_content = _build_page_content(new_desc.strip(), new_sol.strip(), new_phi.strip())
    # Chroma 无法原地更新 page_content 的 embedding → 沿用现有"先删后插"策略
    _reflection_chroma.delete(ids=[ref_id])
    _reflection_chroma.add_texts(
        texts=[page_content],
        ids=[ref_id],
        metadatas=[{
            "ref_id": ref_id,
            "error_desc": new_desc.strip(),
            "solution": new_sol.strip(),
            "philosophy": new_phi.strip(),
            "tags": new_tags,
            "severity": new_sev,
            "timestamp": old_ts,
            "updated_at": _now_iso(),
        }],
    )
    return get_reflection(ref_id)


def delete_reflection(ref_id: str) -> bool:
    """删除；存在并删除成功返回 True，否则 False（不重排、不重编号）。"""
    if get_reflection(ref_id) is None:
        return False
    _reflection_chroma.delete(ids=[ref_id])
    return True


"""
返回rag库搜索总结结果
"""
@tool(description='RAG检索总结工具，传入搜索内容，能够返回本地知识库中相关内容的总结')
def rag_summarize(query:str)->str:
    return Rag_Summarize.model_summary(query)

"""
用户交互提问工具 -- 需求澄清与信息补充
=========================================
用途：当 Agent 对用户意图、需求细节或技术约束的把握不足 95% 时，主动向用户发起提问以消除歧义。

调用原则：
  1. 每次只问一个问题 -- 聚焦单一决策点，避免让用户一次性回答多个问题
  2. 可连续调用 -- 一个问题澄清后再问下一个，逐步收敛至 >=95% 的理解度
  3. 问题应具体、可操作 -- 避免笼统的「还有什么需要补充的吗」，而是给出明确选项或具体方向
  4. 提问时机：
     a. 用户初始需求模糊，关键信息缺失（如技术栈未定、数据格式不明、目标平台未说明）
     b. 任务执行中途遇到岔路口需要用户决策（如多种实现方案、取舍权衡）
     c. 工具返回结果存在歧义，需要用户确认解读方向
     d. 任务范围出现膨胀风险，需要用户确认优先级或裁剪范围

问题设计指南：
  - 优：用「你倾向于 A 方案还是 B 方案？」替代「你想怎么做？」
  - 优：用「数据源是 MySQL 还是 PostgreSQL？」替代「用什么数据库？」
  - 优：必要时给出推荐选项并附简短理由，如「推荐 A 因为安全性更高，你接受吗？」
  - 劣：一次性抛出多个无关问题、过于开放式的提问、用技术黑话让用户困惑
"""
@tool(description="""需求澄清与信息补充工具 -- 当 Agent 对用户意图的理解不足 95% 时主动提问。

调用规则:
  - 每次只问一个问题（聚焦单一决策点）
  - 可连续多次调用，逐层深入，直至理解度 >= 95%
  - 问题应具体明确，最好提供选项而非开放式提问
  - 不猜测用户意图，不替用户做主观决策

适用场景:
  - 用户需求模糊、关键信息缺失（技术栈/数据格式/平台/范围）
  - 执行中途遇到多方案分叉需要用户决策
  - 工具返回结果存在歧义需用户确认
  - 任务范围可能膨胀需确认优先级

输入: 一个清晰、具体的问题字符串
返回: 用户的回答字符串（以 [user回答] 为前缀）""")
def ask_for_answer(query:str)->str:
    user_answer=input(f"[Agent提问]{query}")
    return f'[user回答]{user_answer}'