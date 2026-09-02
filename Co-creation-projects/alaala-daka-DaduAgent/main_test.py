"""
Agent test — 会话感知 REPL
"""
import json
from dotenv import load_dotenv
load_dotenv()

from Agent import Agent
from session.session_store import list_sessions, session_exists


def _render_todos(todos: list) -> None:
    """把 todo 快照事件渲染为可读的待办清单（REPL 下替代原始 JSON）"""
    done = sum(1 for t in todos if t.get("status") == "done")
    print(f"\n📋 待办清单 [{done}/{len(todos)} 已完成]", flush=True)
    for t in todos:
        icon = {"pending": "⬜", "in_progress": "🔄", "done": "✅"}.get(t.get("status"), "❓")
        line = f"  {icon} [{t.get('id')}] {t.get('title', '')}"
        if t.get("desc"):
            line += f"  — {t['desc']}"
        print(line, flush=True)

if __name__=='__main__':
    # ── 选择或创建会话 ──
    sessions = list_sessions()
    if sessions:
        print("已有会话:")
        for s in sessions:
            print(f"  [{s['session_id']}] {s.get('message_count', 0)} 条消息 | {s.get('updated_at', '')}")
        print()
        sid = input("输入会话ID继续对话（直接回车创建新会话）: ").strip()
    else:
        print("没有现有会话，将创建新会话。")
        sid = ""

    if not sid:
        name = input("新会话名称（直接回车跳过）: ").strip()
        a = Agent()
        sid = a.new_session(name)
        print(f"已创建新会话 [{sid}]")
    else:
        if session_exists(sid):
            a = Agent(session_id=sid)
        else:
            print(f"会话 [{sid}] 不存在，将创建新会话。")
            a = Agent()
            a.session_id = sid
            a._save_session_state()

    # ── REPL 循环 ──
    print(f"当前会话: [{a.session_id}]")
    print("输入 'quit' 退出 | '/sessions' 列出会话 | '/switch <id>' 切换 | '/new [名称]' 新建 | '/help' 帮助")

    while True:
        user_mess=input("User_input: ").strip()

        if not user_mess:
            continue  # 跳过空输入，避免产生空 HumanMessage

        if user_mess.lower() in ('quit', 'exit', 'q'):
            break

        # ── 会话管理斜杠命令 ──
        if user_mess == '/sessions':
            sessions = a.list_sessions()
            if not sessions:
                print("暂无保存的会话。")
            else:
                print("会话列表:")
                for s in sessions:
                    marker = " ← 当前" if s["session_id"] == a.session_id else ""
                    print(f"  [{s['session_id']}] {s.get('message_count', 0)} 条消息 | {s.get('updated_at', '')}{marker}")
            continue

        if user_mess.startswith('/switch '):
            target = user_mess[8:].strip()
            if not target:
                print("用法: /switch <会话ID>")
            elif a.switch_session(target):
                print(f"已切换到会话 [{target}]（{len(a.messages)} 条消息）")
            else:
                print(f"会话 [{target}] 不存在")
            continue

        if user_mess.startswith('/new'):
            name = user_mess[4:].strip()
            sid = a.new_session(name)
            print(f"已创建新会话 [{sid}]")
            continue

        if user_mess == '/help':
            print("""
会话管理命令:
  /sessions          列出所有会话
  /switch <会话ID>   切换到指定会话
  /new [名称]        创建新会话
  /info [会话ID]     查看会话详情
  quit / exit / q    退出（自动保存当前会话）

Agent 也可以通过 session 工具管理会话:
  - "帮我列出所有会话"
  - "创建一个名为'代码审查'的新会话"
  - "切换到会话 abc12345"
""")
            continue

        if user_mess.startswith('/info'):
            target = user_mess[5:].strip() if len(user_mess) > 5 else a.session_id
            info = a.get_session_info(target)
            if info:
                print(f"会话 [{info['session_id']}]:")
                print(f"  消息数: {info['message_count']}")
                print(f"  文件大小: {info.get('size_human', '未知')}")
                print(f"  创建时间: {info.get('created_at', '未知')}")
                print(f"  更新时间: {info.get('updated_at', '未知')}")
            else:
                print(f"会话 [{target}] 不存在")
            continue

        # ── 正常对话 ──
        for content in a.stream(user_mess):
            try:
                parsed = json.loads(content)
                if (isinstance(parsed, dict) and parsed.get("type") == "todo"
                        and isinstance(parsed.get("todos"), list)):
                    _render_todos(parsed["todos"])
                    continue
            except (json.JSONDecodeError, TypeError):
                pass
            print(content, flush=True, end='')

    # ── 退出时保存 ──
    if a.session_id:
        a._save_session_state()
        print(f"\n会话 [{a.session_id}] 已保存。")
    print("本轮对话结束")
