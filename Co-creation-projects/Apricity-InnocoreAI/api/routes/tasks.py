"""
任务相关API路由
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging
import json
import asyncio

# from ...agents.controller import agent_controller, TaskType
# 临时注释，避免相对导入错误
agent_controller = None
TaskType = None

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic模型
class TaskSubmitRequest(BaseModel):
    task_type: str
    input_data: Dict[str, Any]
    priority: int = 0

class TaskResponse(BaseModel):
    id: str
    type: str
    status: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    priority: int

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                # 连接已断开，移除
                self.active_connections.remove(connection)

manager = ConnectionManager()

@router.post("/submit", response_model=Dict[str, Any])
async def submit_task(request: TaskSubmitRequest):
    """提交任务"""
    try:
        # 验证任务类型
        try:
            task_type = TaskType(request.task_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"不支持的任务类型: {request.task_type}")
        
        # 提交任务
        task_id = await agent_controller.submit_task(
            task_type=task_type,
            input_data=request.input_data,
            priority=request.priority
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "任务已提交"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{task_id}/execute", response_model=Dict[str, Any])
async def execute_task(task_id: str):
    """执行任务"""
    try:
        result = await agent_controller.execute_task(task_id)
        
        return {
            "success": True,
            "task_id": task_id,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"执行任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{task_id}/status", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        status = await agent_controller.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return TaskResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{task_id}", response_model=Dict[str, Any])
async def cancel_task(task_id: str):
    """取消任务"""
    try:
        success = await agent_controller.cancel_task(task_id)
        
        if success:
            return {"success": True, "message": "任务已取消"}
        else:
            return {"success": False, "message": "任务无法取消（可能正在执行或已完成）"}
        
    except Exception as e:
        logger.error(f"取消任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[TaskResponse])
async def list_tasks():
    """获取任务列表"""
    try:
        # 获取活跃任务
        active_tasks = []
        for task_id, task in agent_controller.active_tasks.items():
            active_tasks.append(TaskResponse(
                id=task["id"],
                type=task["type"].value,
                status=task["status"].value,
                created_at=task["created_at"].isoformat(),
                started_at=task["started_at"].isoformat() if task["started_at"] else None,
                completed_at=task["completed_at"].isoformat() if task["completed_at"] else None,
                priority=task["priority"]
            ))
        
        # 获取历史任务（最近50个）
        history_tasks = []
        for task in agent_controller.task_history[-50:]:
            history_tasks.append(TaskResponse(
                id=task["id"],
                type=task["type"].value,
                status=task["status"].value,
                created_at=task["created_at"].isoformat(),
                started_at=task["started_at"].isoformat() if task["started_at"] else None,
                completed_at=task["completed_at"].isoformat() if task["completed_at"] else None,
                priority=task["priority"]
            ))
        
        return active_tasks + history_tasks
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/status", response_model=Dict[str, Any])
async def get_agents_status():
    """获取智能体状态"""
    try:
        status = await agent_controller.get_agent_status()
        return {
            "success": True,
            "agents": status
        }
        
    except Exception as e:
        logger.error(f"获取智能体状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workflow/full", response_model=Dict[str, Any])
async def run_full_workflow(input_data: Dict[str, Any]):
    """运行完整工作流"""
    try:
        # 提交完整工作流任务
        task_id = await agent_controller.submit_task(
            task_type=TaskType.FULL_WORKFLOW,
            input_data=input_data,
            priority=1  # 高优先级
        )
        
        # 执行任务
        result = await agent_controller.execute_task(task_id)
        
        return {
            "success": True,
            "task_id": task_id,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"运行完整工作流失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/{task_id}")
async def websocket_task_updates(websocket: WebSocket, task_id: str):
    """WebSocket任务更新"""
    await manager.connect(websocket)
    try:
        # 发送初始状态
        status = await agent_controller.get_task_status(task_id)
        if status:
            await manager.send_personal_message(
                json.dumps({"type": "status", "data": status}),
                websocket
            )
        
        # 监听任务状态变化
        while True:
            await asyncio.sleep(1)  # 每秒检查一次
            
            status = await agent_controller.get_task_status(task_id)
            if status:
                await manager.send_personal_message(
                    json.dumps({"type": "status", "data": status}),
                    websocket
                )
                
                # 如果任务完成，断开连接
                if status["status"] in ["completed", "failed", "cancelled"]:
                    break
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket连接异常: {str(e)}")
        manager.disconnect(websocket)

@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """WebSocket流式通信（用于写作助教等实时交互）"""
    await manager.connect(websocket)
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理不同类型的消息
            if message.get("type") == "writing_assistance":
                # 处理写作辅助请求
                await handle_writing_assistance(websocket, message.get("data", {}))
            elif message.get("type") == "ping":
                # 心跳检测
                await manager.send_personal_message(
                    json.dumps({"type": "pong"}),
                    websocket
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket流式通信异常: {str(e)}")
        manager.disconnect(websocket)

async def handle_writing_assistance(websocket: WebSocket, data: Dict[str, Any]):
    """处理写作辅助请求"""
    try:
        # 提交写作辅助任务
        task_id = await agent_controller.submit_task(
            task_type=TaskType.WRITING_ASSISTANCE,
            input_data=data
        )
        
        # 发送任务ID
        await manager.send_personal_message(
            json.dumps({"type": "task_started", "task_id": task_id}),
            websocket
        )
        
        # 执行任务
        result = await agent_controller.execute_task(task_id)
        
        # 发送结果
        await manager.send_personal_message(
            json.dumps({"type": "task_completed", "result": result}),
            websocket
        )
        
    except Exception as e:
        await manager.send_personal_message(
            json.dumps({"type": "error", "message": str(e)}),
            websocket
        )