# -*- coding: utf-8 -*-
"""VulnAuditAgent 图形界面（本地 Web 版）
启动后浏览器打开 http://127.0.0.1:8501
"""
import os
import re
import sys
import threading
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

from hello_agents import HelloAgentsLLM, ToolRegistry
from fixed_agent import FixedSimpleAgent as SimpleAgent
from audit_tools import RuleEngineTool, TaintTrackTool, LLMVerifyTool
from main import SYSTEM_PROMPT

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
WEB_DIR = os.path.join(ROOT, "web")

app = FastAPI(title="VulnAuditAgent Web")
TASKS = {}


def build_agent(progress):
    llm = HelloAgentsLLM(temperature=1.0, max_tokens=8192)
    registry = ToolRegistry()
    for t in (RuleEngineTool(), TaintTrackTool(), LLMVerifyTool(llm)):
        t.progress_hook = progress
        registry.register_tool(t)
    return SimpleAgent(name="漏洞审计员", llm=llm, system_prompt=SYSTEM_PROMPT,
                       tool_registry=registry, enable_tool_calling=True)


def run_audit(task_id, rel_path):
    t = TASKS[task_id]
    try:
        agent = build_agent(lambda msg: t["log"].append(msg))
        prompt = (
            f"请审计项目中的 {rel_path} 文件。"
            "严格按照工作流执行，第一条回复就必须是工具调用标记，禁止任何开场白或解释：\n"
            f"1. 调用工具 rule_scan，参数 file_path={rel_path}\n"
            f"2. 调用工具 taint_track，参数 file_path={rel_path}\n"
            "3. 对规则扫描中 严重/高危 的每一条，调用 llm_verify 研判（传入 finding_type、code_snippet、line_number）\n"
            "4. 汇总输出完整 Markdown 审计报告\n"
        )
        report = agent.run(prompt, max_tool_iterations=15)
        t["report"] = report
        t["status"] = "done"
    except Exception as e:
        t["status"] = "error"
        t["error"] = str(e)


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


@app.get("/api/files")
def list_files():
    files = []
    if os.path.isdir(DATA_DIR):
        for fn in sorted(os.listdir(DATA_DIR)):
            if fn.endswith(".py"):
                files.append(f"data/{fn}")
    return {"files": files}


@app.post("/api/audit")
def start_audit(file: str = Query(...)):
    # 防目录穿越
    if not re.fullmatch(r"data/[\w\-.\u4e00-\u9fff]+\.py", file):
        return JSONResponse({"error": "非法文件路径"}, status_code=400)
    if not os.path.isfile(os.path.join(ROOT, file)):
        return JSONResponse({"error": "文件不存在"}, status_code=404)
    task_id = uuid.uuid4().hex[:12]
    TASKS[task_id] = {"status": "running", "log": [], "report": None, "error": None}
    threading.Thread(target=run_audit, args=(task_id, file), daemon=True).start()
    return {"task_id": task_id}


@app.get("/api/status")
def status(task_id: str = Query(...)):
    t = TASKS.get(task_id)
    if not t:
        return JSONResponse({"error": "任务不存在"}, status_code=404)
    return {"status": t["status"], "log": t["log"], "error": t["error"]}


@app.get("/api/result")
def result(task_id: str = Query(...)):
    t = TASKS.get(task_id)
    if not t or t["status"] != "done":
        return JSONResponse({"error": "未完成"}, status_code=404)
    return {"report": t["report"]}


if __name__ == "__main__":
    print("VulnAuditAgent 图形界面: http://127.0.0.1:8501")
    uvicorn.run(app, host="127.0.0.1", port=8501, log_level="warning")
