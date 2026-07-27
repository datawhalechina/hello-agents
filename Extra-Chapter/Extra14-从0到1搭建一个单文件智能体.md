# 从0到1搭建一个单文件智能体

## 引言

**不用任何框架，不用 openai SDK，只用 Python 标准库，从一个文件开始，一行一行搭出一个能自主干活的终端智能体**。

最终成品大概 200 行代码，单文件，零依赖。它能聊天、能执行 shell 命令、能记住上次的对话、能在执行危险命令前让你确认。

本章的参考实现是 [EVA](https://github.com/usepr/eva)（`https://github.com/usepr/eva`）——一个 942 行的单文件终端智能体。我们不复制 EVA，我们拆解它背后的思路，然后自己写一个更精简的版本。

---

## 第一步：一个能聊天的程序

先做最简单的事：让 Python 程序能跟 LLM 对话。

所有 OpenAI 兼容的 API（DeepSeek、OpenAI、vLLM、Ollama）都提供同一个端点：`POST /v1/chat/completions`。你只需要发一个 HTTP 请求：

```python
# agent_v1.py
import json
import os
import urllib.request

API_KEY = os.environ["LLM_API_KEY"]
BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

def chat(messages):
    """发一个请求，返回模型回复文本。"""
    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(f"{BASE_URL}/chat/completions", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {API_KEY}")

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


if __name__ == "__main__":
    messages = [{"role": "system", "content": "你是一个有用的助手。"}]
    while True:
        user = input("\n> ")
        if user == "exit":
            break
        messages.append({"role": "user", "content": user})
        reply = chat(messages)
        print(reply)
        messages.append({"role": "assistant", "content": reply})
```

跑起来：

```bash
$ export LLM_API_KEY="sk-xxx"
$ python agent_v1.py

> 你好
你好！有什么我可以帮你的吗？
```

30 行，能聊天了。但模型只能"说"——你问"当前目录有什么文件"，它只能编。因为它看不到你的电脑。

---

## 第二步：让模型能操作电脑

要让它变成"智能体"，它需要**能做事情**。

### 2.1 智能体真的需要那么多工具吗？

很多 Agent 框架一上来就让你定义一堆工具：文件读写、网络请求、数据库查询、图片处理……但仔细想想，**如果你有一个 shell，以上所有事情都能做**：

- 读文件？`cat` / `type`
- 写文件？`echo >` / `Set-Content`
- 网络请求？`curl` / `Invoke-WebRequest`
- 搜索内容？`grep` / `Select-String`
- 处理图片？`ffmpeg` / `magick`

**"会用 shell，就会用一切"**。所以我们只给模型一个工具：执行 shell 命令。这一个工具的能力边界，就是整台电脑的能力边界。

### 2.2 定义工具

OpenAI 的函数调用协议要求提前告诉模型"我有哪些工具可用"，格式是一个 JSON schema：

```python
TOOLS = [{
    "type": "function",
    "function": {
        "name": "run_command",
        "description": (
            "在用户电脑上执行 shell 命令。"
            "可以查看文件、运行程序、操作系统。"
            "每次调用一个命令，需要多个命令时用 && 连接。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的 shell 命令",
                }
            },
            "required": ["command"],
        },
    },
}]
```

### 2.3 改造 chat：同时返回文本和工具调用

加上 `tools` 参数后，模型的回复可能包含 `tool_calls`。把返回类型从字符串改为完整的 message 对象：

```python
def chat(messages, tools=None):
    """调用 LLM，返回完整的 message 对象（含可能的 tool_calls）。"""
    body = {"model": MODEL, "messages": messages, "stream": False}
    if tools:
        body["tools"] = tools

    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {API_KEY}")

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]
```

### 2.4 执行工具

`subprocess.run` 执行命令。注意 `shell=False`，命令作为列表元素传入，防止注入：

```python
import subprocess
import platform

def run_command(command, timeout=60):
    """执行 shell 命令，返回 stdout + stderr。"""
    sh = "powershell.exe" if platform.system() == "Windows" else "/bin/bash"
    try:
        r = subprocess.run(
            [sh, command],
            capture_output=True, text=True, timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return f"[命令超时: {timeout}s]"

    out = r.stdout
    if r.stderr:
        out += "\n[stderr]\n" + r.stderr
    if len(out) > 4000:
        out = out[:4000] + "\n...(输出过长，已截断)"
    return out or "[命令无输出]"
```

串起来试一下：

```python
messages = [{"role": "system", "content": "你是终端助手。用 run_command 工具来操作系统。"}]
messages.append({"role": "user", "content": "当前目录下有什么文件？"})

msg = chat(messages, tools=TOOLS)
messages.append(msg)

for tc in msg.get("tool_calls", []):
    args = json.loads(tc["function"]["arguments"])
    print(f"[执行] {args['command']}")
    result = run_command(**args)
    print(result[:200])
    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

# 把结果喂回模型，让它总结
final = chat(messages, tools=TOOLS)
print(final["content"])
```

此时模型会先调用 `ls`（或 `dir`），看到结果后转述给你。它不再是在"编"文件列表了——它真的看到了。

---

## 第三步：让模型多步推理——实现 Agent Loop

上一步只执行了一轮工具调用。真实场景中，模型需要连续执行多步——先 `ls` 看文件，再 `cat` 看内容，再 `grep` 搜索，每一步都依赖上一步的结果。

这就是 **Agent Loop**：一个 while 循环，模型调用工具 → 拿到结果 → 决定下一步 → 再调用工具 → ……直到它认为任务完成。

```python
def agent_loop(messages):
    """主循环：让模型自主完成多步任务。"""
    while True:
        msg = chat(messages, tools=TOOLS)
        messages.append(msg)

        if msg.get("content"):
            print(msg["content"])

        tool_calls = msg.get("tool_calls", [])
        if not tool_calls:
            # 没有工具调用 = 模型认为任务已完成
            return msg.get("content", "")

        # 执行每个工具调用
        for tc in tool_calls:
            args = json.loads(tc["function"]["arguments"])
            name = tc["function"]["name"]
            if name == "run_command":
                print(f"  🔧 {args['command']}")
                result = run_command(**args)
            else:
                result = f"[未知工具: {name}]"

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })
        # 回到 while 开头，模型看到工具结果后继续推理
```

这个 `while True` 就是 Agent Loop 的全部。模型在循环里不停地"思考 → 行动 → 观察 → 再思考"，直到它认为不用再调工具了，退出循环并输出最终回答。

---

## 第四步：记住聊到哪了——会话管理

现在关掉程序，再打开——对话历史全丢了。每次都要从零开始解释上下文。

解决方法很直接：**把 messages 列表存成 JSON 文件**。

```python
SESSION_FILE = os.path.join(os.getcwd(), ".agent_session.json")

def save_session(messages):
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

def load_session(system_prompt):
    if not os.path.exists(SESSION_FILE):
        return [{"role": "system", "content": system_prompt}]
    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        messages = json.load(f)
    # system prompt 里带有当前环境信息（OS、shell、工作目录等），
    # 两次会话之间环境可能变了，所以每次加载会话时都要用最新的 prompt 替换旧的
    messages[0] = {"role": "system", "content": system_prompt}
    return messages
```

`load_session` 里有一个关键细节：**加载会话时用最新的 system prompt 替换旧的那条**。实际场景中 system prompt 往往带有环境探针采集到的信息——当前 OS、shell 类型、工作目录下有哪些工具——这些在两次会话之间可能已经变了。用旧的 prompt，模型就会带着错误的环境认知工作。

在主循环中接入：

```python
SYSTEM_PROMPT = "你是终端助手。用 run_command 工具来帮助用户。"

messages = load_session(SYSTEM_PROMPT)
if len(messages) > 1:
    print(f"[已恢复上次会话，共 {len(messages)} 条消息]")

while True:
    user = input("\n> ")
    if user == "exit":
        save_session(messages)
        break
    messages.append({"role": "user", "content": user})
    agent_loop(messages)
    save_session(messages)
```

现在你退出程序再打开，模型记得你们上次聊了什么。甚至会记得它执行过哪些命令、看到了什么结果。

---

## 第五步：别让它干坏事——安全审查

现在你的 Agent 能执行任何 shell 命令。包括 `rm -rf /`。你需要一层护栏。

**让 LLM 自己判断命令是否安全**。执行前，用同个模型做一次快速分类：

```python
SAFETY_PROMPT = """判断以下 shell 命令的安全性：
- safe：只读操作（ls, cat, grep, find, head, tail, du, git status, git log 等）
- dangerous：会修改系统（rm, mv, cp, pip install, git commit, mkdir, chmod 等）

命令: {command}
分类 (safe/dangerous):"""

def safety_check(command):
    msg = chat([{"role": "user", "content": SAFETY_PROMPT.format(command=command)}])
    return "dangerous" if "dangerous" in msg["content"].lower() else "safe"
```

在 `agent_loop` 执行工具前插入检查：

```python
for tc in tool_calls:
    args = json.loads(tc["function"]["arguments"])
    cmd = args.get("command", "")

    if safety_check(cmd) == "dangerous":
        print(f"  ⚠️  危险命令: {cmd}")
        confirm = input("  确认执行? (y/n): ")
        if confirm.lower() != "y":
            messages.append({
                "role": "tool", "tool_call_id": tc["id"],
                "content": "[用户取消了此命令]"
            })
            continue

    result = run_command(**args)
    ...
```

不需要白名单，不需要正则——LLM 自己知道 `cat file.txt` 和 `cat /etc/shadow` 的区别。安全的命令静默执行，危险的弹确认。

---

## 第六步：拼起来——完整的单文件智能体

把前面五步的代码拼进一个文件：

```python
#!/usr/bin/env python3
"""单文件终端智能体 —— 零依赖，约 200 行。"""
import json
import os
import platform
import subprocess
import urllib.request

# ── 配置 ─────────────────────────────────────────────
API_KEY = os.environ["LLM_API_KEY"]
BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

SYSTEM_PROMPT = """你是一个终端助手。用 run_command 工具执行 shell 命令来帮助用户。
工作方式：分析需求 → 执行命令 → 观察结果 → 继续或完成。
不确定时先探查（ls/cat/grep），确认后再做修改操作。"""

TOOLS = [{
    "type": "function",
    "function": {
        "name": "run_command",
        "description": "在用户电脑上执行 shell 命令。可查看文件、运行程序、操作系统。",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的 shell 命令"}
            },
            "required": ["command"],
        },
    },
}]

SAFETY_PROMPT = """判断 shell 命令安全性：
- safe：只读操作（ls, cat, grep, find, head, tail, du, git status, git log 等）
- dangerous：修改系统（rm, mv, cp, pip install, git commit, mkdir, chmod 等）

命令: {command}
分类 (safe/dangerous):"""

# ── LLM 调用层 ───────────────────────────────────────
def chat(messages, tools=None):
    """调用 LLM，返回完整 message 对象。"""
    body = {"model": MODEL, "messages": messages, "stream": False}
    if tools:
        body["tools"] = tools

    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {API_KEY}")

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["choices"][0]["message"]

# ── 工具层 ───────────────────────────────────────────
def run_command(command, timeout=60):
    """执行 shell 命令。"""
    sh = "powershell.exe" if platform.system() == "Windows" else "/bin/bash"
    try:
        r = subprocess.run(
            [sh, command],
            capture_output=True, text=True, timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return f"[命令超时: {timeout}s]"

    out = r.stdout
    if r.stderr:
        out += "\n[stderr]\n" + r.stderr
    if len(out) > 4000:
        out = out[:4000] + "\n...(输出过长，已截断)"
    return out or "[命令无输出]"

def safety_check(command):
    msg = chat([{"role": "user", "content": SAFETY_PROMPT.format(command=command)}])
    return "dangerous" if "dangerous" in msg["content"].lower() else "safe"

# ── 会话层 ───────────────────────────────────────────
SESSION_FILE = os.path.join(os.getcwd(), ".agent_session.json")

def save_session(messages):
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

def load_session():
    if not os.path.exists(SESSION_FILE):
        return [{"role": "system", "content": SYSTEM_PROMPT}]
    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        msgs = json.load(f)
    msgs[0] = {"role": "system", "content": SYSTEM_PROMPT}
    return msgs

# ── Agent Loop ───────────────────────────────────────
def agent_loop(messages):
    while True:
        msg = chat(messages, tools=TOOLS)
        messages.append(msg)

        if msg.get("content"):
            print(msg["content"])

        tool_calls = msg.get("tool_calls", [])
        if not tool_calls:
            return msg.get("content", "")

        for tc in tool_calls:
            args = json.loads(tc["function"]["arguments"])
            if tc["function"]["name"] != "run_command":
                result = f"[未知工具: {tc['function']['name']}]"
            else:
                cmd = args.get("command", "")
                if safety_check(cmd) == "dangerous":
                    print(f"  ⚠️  危险命令: {cmd}")
                    if input("  确认执行? (y/n): ").lower() != "y":
                        result = "[用户取消]"
                    else:
                        print(f"  🔧 {cmd}")
                        result = run_command(**args)
                else:
                    print(f"  🔧 {cmd}")
                    result = run_command(**args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

# ── 入口 ─────────────────────────────────────────────
def main():
    messages = load_session()
    if len(messages) > 1:
        print(f"[已恢复会话，{len(messages)} 条消息]")

    try:
        while True:
            user = input("\n> ")
            if user in ("exit", "quit"):
                save_session(messages)
                print("会话已保存。")
                break
            messages.append({"role": "user", "content": user})
            agent_loop(messages)
            save_session(messages)
    except KeyboardInterrupt:
        save_session(messages)
        print("\n会话已保存。")

if __name__ == "__main__":
    main()
```

### 6.1 跑起来

```bash
$ export LLM_API_KEY="sk-your-key"
$ python agent.py

> 帮我看看当前目录下有哪些 Python 文件
  🔧 ls *.py
  🔧 grep -l "def " *.py
当前目录下有 1 个 Python 文件：agent.py。其中定义了 7 个函数。
```

### 6.2 代码分层

```
┌──────────────────────────────────┐
│  main()           ← 用户交互入口  │
├──────────────────────────────────┤
│  agent_loop()     ← 多轮推理循环  │
├──────────────────────────────────┤
│  chat()           ← LLM API 调用 │
├──────────────────────────────────┤
│  run_command()    ← 工具层       │
│  safety_check()                  │
├──────────────────────────────────┤
│  save/load_session ← 会话持久化   │
└──────────────────────────────────┘
```

每一层都极薄——最厚的 `agent_loop` 也就 35 行。但拼在一起，就是一个能聊、能动、能记、能控制风险的智能体。去掉注释和空行，约 170 行。

---

## 回顾：我们做了什么

| 步骤 | 加上的能力 | 核心概念 |
|---|---|---|
| 第一步 | 跟 LLM 对话 | HTTP POST，urllib 直连 API |
| 第二步 | 执行 shell 命令 | 工具定义 + function calling，一个 shell 替代十个工具 |
| 第三步 | 多步自主推理 | Agent Loop = while + tool_calls |
| 第四步 | 记住上次对话 | JSON 序列化会话 |
| 第五步 | 防止危险操作 | LLM 自审命令 + 用户确认 |
| 第六步 | 拼成完整文件 | 分层架构，约 170 行 |

---

## 接下来可以做什么

- **加工具**：试试给 Agent 加上 `web_search`（调搜索 API）或 `read_file`（读指定文件路径）——你会发现在 Agent Loop 里注册一个新工具只需三行代码
- **换模型**：把 `BASE_URL` 指向 Ollama（`http://localhost:11434/v1`），就能用本地模型跑 Agent
- **读 EVA 源码**：[https://github.com/usepr/eva](https://github.com/usepr/eva)，942 行，结构和我们搭的几乎一样——但它多了 thinking token 渲染、思考死循环检测、Goal Mode、Agent 自压缩记忆等工程细节

Agent 的骨架就这些。框架帮你省代码，但从零写帮你理解每个字节在干什么。知道骨架怎么搭，以后用任何框架你都知道背后在发生什么。

