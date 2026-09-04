"""
WebSocket 聊天端点 — Agent 流式对话 + ask_for_answer 请求-响应协议

协议:
  Client → Server:
    { type: "chat", content: "...", files: ["uploads/foo.txt", ...] }
      files 可选：本次上传的文件路径（项目根相对），隐式交给 Agent 用 file_manage 处理
    { type: "cancel" }
    { type: "user_answer", request_id: "...", answer: "approved"|"rejected", detail: "..." }
    { type: "ping" }

  Server → Client:
    { type: "chunk", content: "..." }
    { type: "tool_call", call_id: "...", tool: "...", args: {...} }
    { type: "tool_result", call_id: "...", tool: "...", result: "..." }
    { type: "tool_error", call_id: "...", tool: "...", error: "..." }
    { type: "ask_user", request_id: "...", question: "..." }
    { type: "done" }
    { type: "error", message: "..." }
    { type: "pong" }
"""
import asyncio
import json
import threading
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from tool.logger_handler import logger
from Agent import Agent, build_file_note, strip_file_note

router = APIRouter()

# 单条 chat 消息最多携带的上传文件数
_MAX_FILES_PER_MESSAGE = 10


def _coerce_files(raw: Any) -> list[str]:
    """把 WS 载荷中的 files 字段规整为去空白字符串列表（上限 _MAX_FILES_PER_MESSAGE）"""
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for f in raw:
        if isinstance(f, str) and f.strip():
            out.append(f.strip())
        if len(out) >= _MAX_FILES_PER_MESSAGE:
            break
    return out

# ── Agent 实例缓存（按 session_id）──
_agents: dict[str, Agent] = {}
# 已删除会话墓碑：防止任何后续连接/重连把已删除的会话文件重新创建出来
_deleted_sessions: set[str] = set()
_lock = threading.Lock()


def _get_or_create_agent(session_id: str | None) -> Agent:
    """获取或创建 Agent 实例"""
    if session_id:
        with _lock:
            if session_id in _deleted_sessions:
                # 会话已被删除：按 ephemeral 处理，绝不重建 JSONL 文件
                logger.info(f"[chat] 已删除会话 {session_id} 以 ephemeral 处理，避免复活")
                return Agent()
            if session_id not in _agents:
                _agents[session_id] = Agent(session_id=session_id)
            return _agents[session_id]
    return Agent()  # ephemeral


def evict_agent(session_id: str) -> None:
    """删除会话时调用：从缓存移除 Agent 并记录墓碑，阻止其后续状态保存。

    否则 WebSocket 断开时的 finally 块会调用 _save_session_state()，
    把刚删除的会话文件重新写回磁盘（"复活"已删除会话）。
    将 session_id 置为 None 后，_save_session_state() 成为 no-op；
    记录墓碑后，_get_or_create_agent 也不会再为该 id 重建 Agent/文件。
    """
    with _lock:
        agent = _agents.pop(session_id, None)
        _deleted_sessions.add(session_id)
    if agent is not None:
        agent.session_id = None
        logger.info(f"[chat] 已驱逐 Agent 缓存: session={session_id}")


def evict_all_agents_for_model_change() -> None:
    """模型切换时调用：仅清空缓存，不做墓碑、不动进行中的流。

    进行中的 WebSocket 持有自己的 agent 局部引用，其流与 finally 保存不受影响；
    新连接会基于新模型重建 Agent。
    """
    with _lock:
        _agents.clear()
    logger.info("[chat] 模型变更：已驱逐全部 Agent 缓存")


# ── ask_for_answer 的 WebSocket 适配 ──

# 全局映射: request_id → asyncio.Event
_pending_requests: dict[str, asyncio.Event] = {}
_pending_results: dict[str, str] = {}


async def _websocket_ask_user(ws: WebSocket, question: str) -> str:
    """
    替代 input() 的 ask_for_answer 实现。
    通过 WebSocket 向客户端发送确认请求，等待用户回答后返回。
    """
    request_id = uuid.uuid4().hex[:12]
    event = asyncio.Event()
    _pending_requests[request_id] = event

    await ws.send_json({
        "type": "ask_user",
        "request_id": request_id,
        "question": question,
    })

    # 等待客户端回答（带超时 5 分钟）
    try:
        await asyncio.wait_for(event.wait(), timeout=300.0)
    except asyncio.TimeoutError:
        _pending_requests.pop(request_id, None)
        _pending_results.pop(request_id, None)
        return "用户回答: 超时未响应，操作视为被拒绝。"

    answer = _pending_results.pop(request_id, "用户取消输入，操作视为被拒绝。")
    _pending_requests.pop(request_id, None)
    return answer


def resolve_user_answer(request_id: str, answer: str):
    """由 WebSocket 消息处理调用：解析用户回答并恢复等待的协程"""
    _pending_results[request_id] = answer
    event = _pending_requests.get(request_id)
    if event:
        event.set()


# ── 工具包装：将 ask_for_answer 的 input() 替换为 WebSocket 版本 ──

def _wrap_input_for_websocket(ws: WebSocket):
    """
    通过 monkey-patch input() 将 ask_for_answer 重定向到 WebSocket。
    LangGraph 编译后的 graph 不直接暴露 .tools 属性，
    所以我们直接 patch builtins.input 即可——所有工具共享同一个 input()。
    """
    import builtins
    original_input = builtins.input

    def ws_input(prompt: str = "") -> str:
        """同步包装器：在事件循环中运行异步 ask_user"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # 从同步上下文中调用异步 — 创建新任务等待
            future = asyncio.run_coroutine_threadsafe(
                _websocket_ask_user(ws, prompt), loop
            )
            return future.result(timeout=310)
        else:
            return loop.run_until_complete(_websocket_ask_user(ws, prompt))

    builtins.input = ws_input
    return original_input


def _unwrap_input(original_input):
    """恢复原始 input() 函数"""
    import builtins
    builtins.input = original_input


async def _send_chunk(ws: WebSocket, chunk: str) -> None:
    """发送单个 chunk：仅当它是带 type 的内部结构消息时原样发送，
    否则一律包装为 {"type":"chunk"}；空白内容直接丢弃。"""
    try:
        parsed = json.loads(chunk)
        if isinstance(parsed, dict) and isinstance(parsed.get("type"), str):
            await ws.send_json(parsed)
            return
    except (json.JSONDecodeError, TypeError):
        pass
    stripped = chunk.strip()
    if not stripped:
        return
    await ws.send_json({"type": "chunk", "content": stripped})


# ── WebSocket 端点 ──

@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(ws: WebSocket, session_id: str):
    await ws.accept()
    logger.info(f"[chat] WebSocket 连接: session={session_id}")

    # 处理特殊 session_id
    agent_sid = None if session_id in ("_ephemeral", "null", "undefined") else session_id
    agent = _get_or_create_agent(agent_sid)
    original_input = None
    cancel_event = asyncio.Event()

    try:
        # 发送当前会话信息
        await ws.send_json({
            "type": "session_info",
            "session_id": agent.session_id or "ephemeral",
            "message_count": len(agent.messages),
        })

        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "chat":
                content = data.get("content", "")
                files = _coerce_files(data.get("files"))
                if not content.strip() and not files:
                    continue

                # 包装 input() 为 WebSocket 版本
                original_input = _wrap_input_for_websocket(ws)
                # 每回合独立的取消事件：旧回合的取消状态不会泄漏到新回合，
                # 已取消回合的线程会一直看到 is_set() 而终止，避免双流并行污染消息历史
                cancel_event = asyncio.Event()

                try:
                    # 在单独的线程中运行 Agent.stream（因为它是同步生成器）
                    # 同时监听取消信号
                    chunks = []
                    stream_finished = False

                    def run_stream():
                        nonlocal stream_finished
                        try:
                            user_query = content.strip()
                            # 模型实际看到的用户消息 = query + 上传文件注释块；回显跳过需一并比对
                            note = build_file_note(files) if files else None
                            combined = (user_query + "\n\n" + note).strip() if note else None
                            saw_first = False
                            for chunk in agent.stream(content, file_paths=files):
                                if cancel_event.is_set():
                                    break
                                c = chunk.strip()
                                if not c:
                                    continue  # 过滤空白 chunk（不再产生 {"content":""}）
                                # 结构化事件（todo 等带 type 的 JSON）直接转发，不占用回显跳过槽位
                                try:
                                    parsed = json.loads(c)
                                    if isinstance(parsed, dict) and isinstance(parsed.get("type"), str):
                                        chunks.append(c + '\n')
                                        continue
                                except (json.JSONDecodeError, TypeError):
                                    pass
                                # 仅「逐字复述用户问题/问题+附件注释」才跳过回显，避免误删合法回复
                                if not saw_first:
                                    saw_first = True
                                    if (
                                        c == user_query
                                        or (note and (
                                            c == note
                                            or c == combined
                                            or strip_file_note(c).strip() == user_query
                                        ))
                                    ):
                                        logger.info(f"[chat] 跳过回显: {c[:80]}")
                                        continue
                                chunks.append(c + '\n')
                            stream_finished = True
                        except Exception as e:
                            logger.exception(f"[chat] Agent 流错误")
                            chunks.append(json.dumps({"type": "error", "message": str(e)}))

                    stream_thread = threading.Thread(target=run_stream)
                    stream_thread.start()

                    # 并发泵：发送 chunks 的同时读取入站消息（cancel / user_answer）。
                    # 旧版 pump 在 turn 期间从不调用 ws.receive()，导致：
                    #   1) cancel 消息要等整个 turn 结束才被读到 → 停止按钮是死控件；
                    #   2) ask_for_answer 的 user_answer 也无法即时恢复等待中的协程。
                    # 用 asyncio.wait_for 短超时轮询入站消息，两个问题一并解决。
                    while True:
                        # 1) 先发完当前积累的 chunks
                        while chunks:
                            await _send_chunk(ws, chunks.pop(0))
                        # 2) 流线程结束则收尾
                        if not stream_thread.is_alive():
                            break
                        # 3) 短等待入站消息；超时则继续泵
                        try:
                            data = await asyncio.wait_for(ws.receive(), timeout=0.05)
                        except asyncio.TimeoutError:
                            continue
                        raw = data.get("text")
                        if not raw:
                            continue
                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        mtype = msg.get("type", "")
                        if mtype == "cancel":
                            cancel_event.set()
                            break
                        elif mtype == "user_answer":
                            request_id = msg.get("request_id", "")
                            answer = msg.get("answer", "rejected")
                            detail = msg.get("detail", "")
                            result = f"用户回答: {answer}"
                            if detail:
                                result += f" —— {detail}"
                            resolve_user_answer(request_id, result)

                    # 处理剩余 chunks（客户端可能已断开，容错）
                    try:
                        while chunks:
                            await _send_chunk(ws, chunks.pop(0))
                    except (WebSocketDisconnect, RuntimeError):
                        pass

                    if cancel_event.is_set():
                        await ws.send_json({"type": "interrupted"})
                    else:
                        await ws.send_json({"type": "done"})

                finally:
                    if original_input:
                        _unwrap_input(original_input)
                        original_input = None

            elif msg_type == "cancel":
                cancel_event.set()
                await ws.send_json({"type": "done"})

            elif msg_type == "user_answer":
                request_id = data.get("request_id", "")
                answer = data.get("answer", "rejected")
                detail = data.get("detail", "")
                result = f"用户回答: {answer}"
                if detail:
                    result += f" —— {detail}"
                resolve_user_answer(request_id, result)

            elif msg_type == "ping":
                await ws.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"[chat] WebSocket 断开: session={session_id}")
    except Exception as e:
        logger.exception(f"[chat] WebSocket 异常: session={session_id}")
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        if original_input:
            _unwrap_input(original_input)
        # 保存会话状态
        if agent.session_id:
            try:
                agent._save_session_state()
            except Exception:
                pass
