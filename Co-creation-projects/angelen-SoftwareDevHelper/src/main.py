from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
import json
import shutil
import uuid
import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

from .agents.helper_agent import get_helper_agent

app = FastAPI(title="SoftwareDevHelper API")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载前端静态文件
frontend_dir = os.path.join(os.path.dirname(__file__), "../frontend")
app.mount("/static", StaticFiles(directory=os.path.join(frontend_dir, "static")), name="static")

# 数据目录
data_dir = os.path.join(os.path.dirname(__file__), "../data")
sessions_dir = os.path.join(data_dir, "sessions")
os.makedirs(sessions_dir, exist_ok=True)
user_memory_file = os.path.join(data_dir, "user_memory.json")

# 初始化智能体 (这里需要修改为支持多会话的智能体实例管理，但为了简单，我们每次请求动态恢复上下文)
# 由于 SimpleAgent 默认在内存中保存历史，为了支持多会话，我们需要为每个会话维护一个 Agent 实例
# 或者在每次请求时将历史记录注入到 Agent 中。
# 为了保持与 HelloAgents 框架的兼容性，我们在内存中缓存 Agent 实例。
agent_sessions = {}

def get_or_create_agent(session_id: str):
    if session_id not in agent_sessions:
        agent = get_helper_agent()
        # 尝试加载历史记录
        session_file = os.path.join(sessions_dir, f"{session_id}.json")
        if os.path.exists(session_file):
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                history = data.get("messages", [])
                # 简单恢复历史记录到 agent
                # 注意：SimpleAgent 内部使用 _history 列表存储消息
                for msg in history:
                    from hello_agents.core.message import Message
                    if msg.get("isUser"):
                        agent._history.append(Message(role="user", content=msg.get("text", "")))
                    else:
                        # 检查是否包含 tool_calls，这里为了简化，我们只恢复文本，
                        # 避免不完整的 tool_calls 导致后续大模型调用报错
                        agent._history.append(Message(role="assistant", content=msg.get("text", "")))
        agent_sessions[session_id] = agent
    return agent_sessions[session_id]

def save_session_history(session_id: str, title: str, text: str, is_user: bool, tool_calls: list = None):
    session_file = os.path.join(sessions_dir, f"{session_id}.json")
    history = []
    if os.path.exists(session_file):
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            history = data.get("messages", [])
            title = data.get("title", title)

    msg_data = {
        "text": text,
        "isUser": is_user,
        "timestamp": datetime.datetime.now().isoformat()
    }
    if tool_calls:
        msg_data["tool_calls"] = tool_calls

    history.append(msg_data)

    with open(session_file, "w", encoding="utf-8") as f:
        json.dump({"title": title, "messages": history, "updated_at": datetime.datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)

class ChatRequest(BaseModel):
    message: str
    session_id: str

class UserLevelRequest(BaseModel):
    level: str

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open(os.path.join(frontend_dir, "templates/index.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/sessions")
async def get_sessions():
    sessions = []
    for filename in os.listdir(sessions_dir):
        if filename.endswith(".json"):
            session_id = filename[:-5]
            with open(os.path.join(sessions_dir, filename), "r", encoding="utf-8") as f:
                data = json.load(f)
                sessions.append({
                    "id": session_id,
                    "title": data.get("title", "新会话"),
                    "updated_at": data.get("updated_at", "")
                })
    # 按更新时间倒序排序
    sessions.sort(key=lambda x: x["updated_at"], reverse=True)
    return {"sessions": sessions}

@app.get("/api/sessions/{session_id}")
async def get_session_history(session_id: str):
    session_file = os.path.join(sessions_dir, f"{session_id}.json")
    if not os.path.exists(session_file):
        return {"messages": []}
    with open(session_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        return {"messages": data.get("messages", [])}

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    session_file = os.path.join(sessions_dir, f"{session_id}.json")
    if os.path.exists(session_file):
        os.remove(session_file)
    if session_id in agent_sessions:
        del agent_sessions[session_id]
    return {"status": "success"}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        session_id = request.session_id
        if not session_id:
            session_id = str(uuid.uuid4())
            
        agent = get_or_create_agent(session_id)
        
        # 确定会话标题（取第一句话的前15个字符）
        title = request.message[:15] + "..." if len(request.message) > 15 else request.message
        
        # 保存用户消息
        save_session_history(session_id, title, request.message, True)
        
        # 获取回复
        # 在运行前记录历史长度
        history_len_before = len(agent.get_history())
        response = agent.run(request.message)
        
        # 获取运行期间新增的历史记录，提取工具调用信息
        tool_calls_info = []
        current_history = agent.get_history()
        new_messages = current_history[history_len_before:]
        
        for msg in new_messages:
            # 查找带有 tool_calls 的 assistant 消息
            if msg.role == "assistant" and getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    # 获取 function 对象
                    func = getattr(tc, "function", None)
                    if func:
                        # 确保 arguments 是字符串
                        args = getattr(func, "arguments", "{}")
                        if not isinstance(args, str):
                            try:
                                args = json.dumps(args, ensure_ascii=False)
                            except:
                                args = str(args)
                        tool_calls_info.append({
                            "id": getattr(tc, "id", ""),
                            "name": getattr(func, "name", ""),
                            "arguments": args,
                            "result": "" # 稍后填充
                        })
            # 查找 tool 角色的消息（工具执行结果）
            elif msg.role == "tool":
                tool_call_id = getattr(msg, "tool_call_id", None)
                if tool_call_id:
                    for tc_info in tool_calls_info:
                        if tc_info["id"] == tool_call_id:
                            tc_info["result"] = msg.content
                            break

        # 保存助手消息（同时保存工具调用信息）
        save_session_history(session_id, title, response, False, tool_calls=tool_calls_info)

        return {"response": response, "session_id": session_id, "tool_calls": tool_calls_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload_project")
async def upload_project(session_id: str = Form(...), file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="只接受 .zip 格式的压缩包")

    upload_dir = os.path.join(os.path.dirname(__file__), "../outputs/uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    file_path = os.path.join(upload_dir, f"{file_id}_{file.filename}")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        agent = get_or_create_agent(session_id)
        
        prompt = f"用户上传了项目压缩包，路径为：{file_path}。请根据当前题目要求，编写 pytest 测试用例，并使用 code_test 工具进行测试打分，最后给出反馈并更新用户水平记录。"

        save_session_history(session_id, "上传项目测试", f"[上传项目] {file.filename}", True)

        history_len_before = len(agent.get_history())
        response = agent.run(prompt)
        
        tool_calls_info = []
        current_history = agent.get_history()
        new_messages = current_history[history_len_before:]
        
        for msg in new_messages:
            if msg.role == "assistant" and getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    func = getattr(tc, "function", None)
                    if func:
                        # 确保 arguments 是字符串
                        args = getattr(func, "arguments", "{}")
                        if not isinstance(args, str):
                            try:
                                args = json.dumps(args, ensure_ascii=False)
                            except:
                                args = str(args)
                        tool_calls_info.append({
                            "id": getattr(tc, "id", ""),
                            "name": getattr(func, "name", ""),
                            "arguments": args,
                            "result": ""
                        })
            elif msg.role == "tool":
                tool_call_id = getattr(msg, "tool_call_id", None)
                if tool_call_id:
                    for tc_info in tool_calls_info:
                        if tc_info["id"] == tool_call_id:
                            tc_info["result"] = msg.content
                            break

        save_session_history(session_id, "上传项目测试", response, False, tool_calls=tool_calls_info)

        return {"response": response, "file_path": file_path, "session_id": session_id, "tool_calls": tool_calls_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user_memory")
async def get_user_memory():
    if not os.path.exists(user_memory_file):
        return {"level": "beginner", "history": []}
    with open(user_memory_file, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/user_memory/level")
async def update_user_level(request: UserLevelRequest):
    memory = {"level": "beginner", "history": []}
    if os.path.exists(user_memory_file):
        with open(user_memory_file, "r", encoding="utf-8") as f:
            memory = json.load(f)
            
    memory["level"] = request.level
    
    with open(user_memory_file, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)
        
    return {"status": "success", "level": memory["level"]}

@app.delete("/api/user_memory")
async def reset_user_memory():
    """重置用户记忆（清空历史并重置为 beginner）"""
    default_memory = {"level": "beginner", "history": []}
    
    os.makedirs(os.path.dirname(user_memory_file), exist_ok=True)
    with open(user_memory_file, "w", encoding="utf-8") as f:
        json.dump(default_memory, f, ensure_ascii=False, indent=2)
        
    return {"status": "success"}
