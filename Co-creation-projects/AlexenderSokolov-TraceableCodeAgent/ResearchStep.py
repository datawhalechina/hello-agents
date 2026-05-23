import json
from typing import Any
class ResearchStep:
    def __init__(self):
        self.step_id: str = "" 
        self.parent_step_id: str = "" 
        self.step_type: str = ""  # think/tool_call/observation/conclusion
        self.timestamp: float = 0.0
        self.task: str = ""  # 当前步骤要完成的子任务
        self.thought: str = ""  #Agent的思考过程
        # 工具调用记录：统一为字典，包含请求与响应两部分
        # {
        #   "request": {"name": "ReadTool", "params": {...}},
        #   "response": {"status": "success|partial|error", "text": "...", "data": {...}, "error": {...}}
        # }
        self.action: dict = {}
        self.observation: str = ""  #工具返回的结果
        self.status: str = ""  # 状态：success/failed/skipped/retried
        self.artifact_ids: list[str] = []#关联的产物ID
        self.error_msg: str = ""  # 错误信息（如果失败）

def step_to_dict(step: ResearchStep) -> dict:
    return {
        "step_id": step.step_id,
        "parent_step_id": step.parent_step_id,
        "step_type": step.step_type,
        "timestamp": step.timestamp,
        "task": step.task,
        "thought": step.thought,
        "action": step.action,
        "observation": step.observation,
        "status": step.status,
        "artifact_ids": step.artifact_ids,
        "error_msg": step.error_msg,
    }

def dict_to_step(data: dict) -> ResearchStep:
    step = ResearchStep()
    step.step_id = data.get("step_id", "")
    step.parent_step_id = data.get("parent_step_id", "")
    step.step_type = data.get("step_type", "")
    step.timestamp = data.get("timestamp", 0.0)
    step.task = data.get("task", "")
    step.thought = data.get("thought", "")
    step.action = data.get("action", {})
    step.observation = data.get("observation", "")
    step.status = data.get("status", "")
    step.artifact_ids = data.get("artifact_ids", [])
    step.error_msg = data.get("error_msg", "")
    return step

def serialize_step(step: ResearchStep) -> str:
    import json
    return json.dumps(step_to_dict(step), ensure_ascii=False)

def deserialize_step(step_str: str) -> ResearchStep:
    import json
    data = json.loads(step_str)
    return dict_to_step(data)

