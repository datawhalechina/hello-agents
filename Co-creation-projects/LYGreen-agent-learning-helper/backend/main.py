# 学习资源（搜索）、学习资料（下载）、学习进度（记忆）

# 用户输入：查找资料，生成习题，答疑解惑

# =====================================
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from alh.command.command import Command
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class Request(BaseModel):
    command: str
    data: Optional[dict] = None

class Response(BaseModel):
    result: str
    data: dict

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/command")
def parse_command(request: Request):
    command = Command.get_instance()
    data = command.run(request.command, request.data)
    return Response(result="success", data=data)
