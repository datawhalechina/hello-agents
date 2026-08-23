"""
MathModelAgent FastAPI后端

提供RESTful API接口
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.code_executor import CodeExecutor
from src.template_manager import TemplateManager, CumcmTemplate, McmIcmTemplate


# 创建FastAPI应用
app = FastAPI(
    title="MathModelAgent API",
    description="智能数学建模助手API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化组件
code_executor = CodeExecutor(timeout=60)
template_manager = TemplateManager()


# 数据模型
class CodeExecutionRequest(BaseModel):
    """代码执行请求"""
    code: str
    context: Optional[Dict[str, Any]] = None


class CodeExecutionResponse(BaseModel):
    """代码执行响应"""
    success: bool
    stdout: str
    stderr: str
    figure: Optional[str] = None
    variables: Dict[str, Any] = {}


class PaperGenerationRequest(BaseModel):
    """论文生成请求"""
    template_name: str
    context: Dict[str, Any]
    output_path: str


class PaperGenerationResponse(BaseModel):
    """论文生成响应"""
    success: bool
    output_path: str
    message: str


class TemplateInfo(BaseModel):
    """模板信息"""
    name: str
    variables: List[str]
    content_length: int


# API端点
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "MathModelAgent API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.post("/api/code/execute", response_model=CodeExecutionResponse)
async def execute_code(request: CodeExecutionRequest):
    """
    执行Python代码
    
    Args:
        request: 代码执行请求
        
    Returns:
        执行结果
    """
    try:
        result = code_executor.execute(request.code, request.context)
        return CodeExecutionResponse(
            success=result['success'],
            stdout=result['stdout'],
            stderr=result['stderr'],
            figure=result.get('figure'),
            variables=result.get('variables', {})
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/code/execute-with-fix", response_model=CodeExecutionResponse)
async def execute_code_with_fix(request: CodeExecutionRequest):
    """
    执行代码并在失败时尝试修复
    
    Args:
        request: 代码执行请求
        
    Returns:
        执行结果
    """
    try:
        result = code_executor.execute_with_fix(request.code)
        return CodeExecutionResponse(
            success=result['success'],
            stdout=result['stdout'],
            stderr=result['stderr'],
            figure=result.get('figure'),
            variables=result.get('variables', {})
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/templates", response_model=List[TemplateInfo])
async def list_templates():
    """
    列出所有可用模板
    
    Returns:
        模板信息列表
    """
    templates = []
    for template_name in template_manager.list_templates():
        info = template_manager.get_template_info(template_name)
        if info:
            templates.append(TemplateInfo(**info))
    return templates


@app.post("/api/paper/generate", response_model=PaperGenerationResponse)
async def generate_paper(request: PaperGenerationRequest):
    """
    生成论文
    
    Args:
        request: 论文生成请求
        
    Returns:
        生成结果
    """
    try:
        output_path = template_manager.generate(
            request.template_name,
            request.context,
            request.output_path
        )
        return PaperGenerationResponse(
            success=True,
            output_path=output_path,
            message="论文生成成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/templates/{template_name}")
async def get_template(template_name: str):
    """
    获取模板详情
    
    Args:
        template_name: 模板名称
        
    Returns:
        模板详情
    """
    info = template_manager.get_template_info(template_name)
    if not info:
        raise HTTPException(status_code=404, detail=f"模板不存在: {template_name}")
    return info


# WebSocket连接管理
class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket端点
    
    用于实时通信
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            
            # 处理消息
            if data.startswith("execute:"):
                code = data[8:]
                result = code_executor.execute(code)
                
                # 发送结果
                import json
                await manager.send_message(
                    json.dumps({
                        "type": "execution_result",
                        "data": result
                    }),
                    websocket
                )
            else:
                await manager.send_message(
                    f"收到消息: {data}",
                    websocket
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


# 启动命令
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
