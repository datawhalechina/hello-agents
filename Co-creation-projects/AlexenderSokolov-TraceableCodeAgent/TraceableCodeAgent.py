from ResearchMap import ResearchMap
from ResearchStep import ResearchStep
from hello_agents import ReActAgent, HelloAgentsLLM, Config
from hello_agents.tools.builtin import ReadTool, WriteTool
from hello_agents.tools.registry import ToolRegistry
from hello_agents.tools.response import ToolResponse, ToolStatus
import uuid
import time
import json
import os

from dotenv import load_dotenv
load_dotenv()
CONFIG = Config(
    subagent_enabled=False,
    skills_enabled=False,
    session_enabled=False,
    trace_enabled=True,  # 开启trace功能
    todowrite_enabled=False,
    devlog_enabled=False,
)


#artifact服务，将工具响应序列化到 reports/artifacts/<uuid>.json
class ArtifactService:
    def __init__(self, base_dir="reports/artifacts"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save(self, tool_response: ToolResponse) -> str:
        aid = str(uuid.uuid4())
        path = os.path.join(self.base_dir, f"{aid}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(tool_response.to_json())
            return aid
        except Exception:
            return ""


class MappingService:
    """
    负责在 ResearchStep 中记录工具调用与产物之间的映射关系。
    约定：当工具响应中包含可保存为产物的内容时，自动调用 ArtifactService 保存，并把生成的 artifact_id 关联到当前步骤。
    """

    def __init__(self, artifact_service: ArtifactService):
        self.artifact_service = artifact_service

    def map_tool_response(self, step: ResearchStep, tool_response: ToolResponse):
        if not step or not tool_response:
            return
        if self.has_artifact(tool_response):
            artifact_id = self.artifact_service.save(tool_response)
            if artifact_id:
                step.artifact_ids.append(artifact_id)
    
    def has_artifact(self, tool_response: ToolResponse) -> bool:
        """
        判断工具响应中是否包含可保存为产物的内容。
        约定：如果 response.data 包含 'artifact'/'artifact_id'/'file_path' 等字段则认为有产物。
        """
        if not tool_response:
            return False
        data = getattr(tool_response, "data", {}) or {}
        ctx = getattr(tool_response, "context", {}) or {}
        keys = set(data.keys()) | set(ctx.keys())
        indicator_keys = {"artifact", "artifact_id", "file_path", "path", "content"}
        return len(keys & indicator_keys) > 0

def parse_tool_response(tool_response: ToolResponse) -> dict:
    """
    从 ToolResponse 中提取有用信息，构建一个统一的字典格式，便于后续处理和存储。
    约定：提取 status, text, data, error 四个核心字段，当然如果存在的话。
    """
    if not tool_response:
        return {}
    status = getattr(tool_response, "status", "")
    if isinstance(status, ToolStatus):
        status = status.value
    result = {
        "status": status,
        "text": getattr(tool_response, "text", ""),
        "data": getattr(tool_response, "data", {}),
        "error": getattr(tool_response, "error_info", None),
    }
    return result

def parse_action(thought: str) -> dict | None:
    """
    从 LLM 的文本输出中解析出工具调用意图，期望格式为 JSON，例如：
    {"name": "ReadTool", "params": {"path": "README.md"}}
    返回 None 表示没有工具调用意图。
    """
    if not thought:
        return None
    try:
        payload = json.loads(thought)
        if isinstance(payload, dict) and ("name" in payload or "tool" in payload):
            name = payload.get("name") or payload.get("tool")
            params = payload.get("params") or payload.get("args") or {}
            return {"name": name, "params": params}
    except Exception:
        pass
    return None


def _parse_tool_input(input_text: str) -> dict:
    """把工具输入统一解析为 dict。支持 JSON 字符串、普通字符串和空输入。"""
    if input_text is None:
        return {}

    if isinstance(input_text, dict):
        return input_text

    if not isinstance(input_text, str):
        return {"input": str(input_text)}

    text = input_text.strip()
    if not text:
        return {}

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    return {"input": text}




class TraceableAgent(ReActAgent):
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        tool_registry: ToolRegistry = None,
        config: Config = CONFIG,
        system_prompt: str = "",
        max_steps: int = 10,
    ):
        #tool_registry, system_prompt, config
        super().__init__(
            name,
            llm,
            tool_registry=tool_registry,
            system_prompt=system_prompt,
            config=config,
            max_steps=max_steps,
        )
        self.research_map = ResearchMap()
        self.current_step_id = ""
        self.latest_reasoning = ""
        
        self.artifact_service = ArtifactService()
        self.mapping_service = MappingService(self.artifact_service)

    def _record_tool_step(self, tool_name: str, arguments: dict, tool_response: ToolResponse) -> None:
        """将一次真实工具调用写入 ResearchMap。"""
        response_payload = parse_tool_response(tool_response)
        step = ResearchStep()
        step.step_id = str(uuid.uuid4())
        step.parent_step_id = self.current_step_id
        step.step_type = "tool_call"
        step.timestamp = time.time()
        step.task = f"调用工具: {tool_name}"
        step.thought = self.latest_reasoning or f"执行工具 {tool_name}"
        step.action = {
            "request": {
                "name": tool_name,
                "params": arguments or {},
            },
            "response": response_payload,
        }
        step.observation = response_payload.get("text", "") or ""

        status = getattr(tool_response, "status", None)
        if status == ToolStatus.ERROR:
            step.status = "failed"
            error_info = getattr(tool_response, "error_info", None) or {}
            step.error_msg = error_info.get("message", step.observation)
        else:
            step.status = "success"


        self.mapping_service.map_tool_response(step, tool_response)

        self.research_map.add_step(step)
        self.current_step_id = step.step_id

    def _record_builtin_step(self, tool_name: str, arguments: dict, result: dict) -> None:
        """记录 Thought/Finish 这类内置工具调用。"""
        step = ResearchStep()
        step.step_id = str(uuid.uuid4())
        step.parent_step_id = self.current_step_id
        step.step_type = "think" if tool_name == "Thought" else "conclusion"
        step.timestamp = time.time()
        step.task = f"内置工具: {tool_name}"
        if tool_name == "Thought":
            step.thought = str(arguments.get("reasoning", ""))
        else:
            step.thought = self.latest_reasoning or ""
        step.action = {
            "request": {
                "name": tool_name,
                "params": arguments or {},
            },
            "response": {
                "status": "success",
                "text": result.get("content", ""),
                "data": {
                    "reasoning": arguments.get("reasoning") if tool_name == "Thought" else None,
                    "answer": arguments.get("answer") if tool_name == "Finish" else None,
                },
                "error": None,
            },
        }
        step.observation = result.get("content", "")
        step.status = "success"

        if tool_name == "Thought":
            self.latest_reasoning = str(arguments.get("reasoning", ""))

        self.research_map.add_step(step)
        self.current_step_id = step.step_id

    def _execute_tool_call(self, tool_name: str, arguments: dict) -> str:
        """
        对接 ReActAgent 的真实工具执行链路。
        每次工具调用都会记录一个 ResearchStep（含 request/response/error）。
        """
        if not self.tool_registry:
            response = ToolResponse.error(code="NO_TOOL_REGISTRY", message="未配置工具注册表")
            self._record_tool_step(tool_name, arguments, response)
            return "❌ 错误：未配置工具注册表"

        response = None

        #Tool 对象
        tool = self.tool_registry.get_tool(tool_name)
        if tool:
            try:
                typed_arguments = self._convert_parameter_types(tool_name, arguments)
                response = tool.run_with_timing(typed_arguments)
            except Exception as exc:
                response = ToolResponse.error(
                    code="EXECUTION_ERROR",
                    message=f"工具调用失败：{exc}",
                    context={"tool_name": tool_name, "args": arguments},
                )
        else:
            # 函数工具
            func = self.tool_registry.get_function(tool_name)
            if func:
                try:
                    input_text = arguments.get("input", "")
                    response = self.tool_registry.execute_tool(tool_name, input_text)
                except Exception as exc:
                    response = ToolResponse.error(
                        code="EXECUTION_ERROR",
                        message=f"工具调用失败：{exc}",
                        context={"tool_name": tool_name, "args": arguments},
                    )
            else:
                response = ToolResponse.error(
                    code="NOT_FOUND",
                    message=f"未找到工具 '{tool_name}'",
                    context={"tool_name": tool_name},
                )

        #统一写入 ResearchStep
        self._record_tool_step(tool_name, arguments, response)

        if response.status == ToolStatus.ERROR:
            error_code = response.error_info.get("code", "UNKNOWN") if response.error_info else "UNKNOWN"
            return f"❌ 错误 [{error_code}]: {response.text}"
        if response.status == ToolStatus.PARTIAL:
            return f"⚠️ 部分成功: {response.text}"
        return response.text

    def _handle_builtin_tool(self, tool_name: str, arguments: dict) -> dict:
        """覆盖内置工具处理，确保 Thought/Finish 也写入 Research Map。没改之前不记录"""
        if tool_name == "Thought":
            reasoning = arguments.get("reasoning", "")
            result = {
                "content": f"推理: {reasoning}",
                "finished": False,
            }
            self._record_builtin_step(tool_name, arguments, result)
            return result

        if tool_name == "Finish":
            answer = arguments.get("answer", "")
            result = {
                "content": f"最终答案: {answer}",
                "finished": True,
                "final_answer": answer,
            }
            self._record_builtin_step(tool_name, arguments, result)
            return result

        result = {
            "content": f"未知的内置工具: {tool_name}",
            "finished": False,
        }
        self._record_builtin_step(tool_name, arguments, result)
        return result
        

    # 按步骤ID回看：直接跳转到任意步骤
    def view_step(self, input_text: str = "") -> dict:
        payload = _parse_tool_input(input_text)
        step_id = str(
            payload.get("step_id")
            or payload.get("id")
            or payload.get("step")
            or payload.get("input")
            or self.current_step_id
            or self.research_map.root_step_id
        ).strip()

        if step_id in {"current", "latest", "last"}:
            step_id = self.current_step_id

        step = self.research_map.get_step(step_id)
        if not step:
            return {
                "error": "步骤不存在",
                "requested_step_id": step_id,
                "available_step_ids": list(self.research_map.steps.keys())[-20:],
            }
        return step.__dict__

    #完整路径回溯：从当前步骤一直看到最开始
    def traceback_current(self, input_text: str = "") -> dict:
        payload = _parse_tool_input(input_text)
        step_id = str(payload.get("step_id") or payload.get("id") or self.current_step_id or self.research_map.root_step_id).strip()

        if step_id in {"current", "latest", "last"}:
            step_id = self.current_step_id

        if not step_id:
            return {"error": "当前没有可回溯的步骤", "path": []}

        path = self.research_map.get_traceback_path(step_id)
        return {
            "step_id": step_id,
            "count": len(path),
            "path": [step.__dict__ for step in path],
        }

    #按关键词搜索：找到所有包含关键词的步骤
    def search_steps(self, input_text: str = "") -> dict:
        payload = _parse_tool_input(input_text)
        keyword = str(payload.get("keyword") or payload.get("query") or payload.get("input") or "").strip()
        if not keyword:
            return {"error": "keyword 不能为空", "results": []}
        results = []
        for step in self.research_map.steps.values():
            if (keyword in step.thought
                or keyword in step.task
                    or keyword in step.observation):
                results.append(step.__dict__)
        return {"keyword": keyword, "count": len(results), "results": results}

    #按产物回溯：找到生成某个文件的所有步骤
    def trace_artifact(self, input_text: str = "") -> dict:
        payload = _parse_tool_input(input_text)
        artifact_id = str(payload.get("artifact_id") or payload.get("id") or payload.get("input") or "").strip()
        if not artifact_id:
            return {"error": "artifact_id 不能为空", "results": []}
        results = []
        for step in self.research_map.steps.values():
            if artifact_id in step.artifact_ids:
                results.append(step.__dict__)
        return {"artifact_id": artifact_id, "count": len(results), "results": results}

    def list_steps(self, input_text: str = "") -> dict:
        """列出当前 Research Map 中的步骤 ID，便于运行时调试。"""
        payload = _parse_tool_input(input_text)
        limit = payload.get("limit", 50)
        try:
            limit = max(1, int(limit))
        except Exception:
            limit = 50

        step_ids = list(self.research_map.steps.keys())
        return {
            "count": len(step_ids),
            "root_step_id": self.research_map.root_step_id,
            "current_step_id": self.current_step_id,
            "step_ids": step_ids[-limit:],
        }

    def get_current_step(self, input_text: str = "") -> dict:
        """返回当前步骤的完整内容。"""
        if not self.current_step_id:
            return {"error": "当前没有步骤"}
        step = self.research_map.get_step(self.current_step_id)
        if not step:
            return {"error": "当前步骤不存在", "current_step_id": self.current_step_id}
        return {"current_step_id": self.current_step_id, "step": step.__dict__}
    
    #这里重写 execute_tool 方法，在执行工具调用后自动记录到 ResearchStep 中，并通过 MappingService 关联产物
    def execute_tool(self, action: dict) -> ToolResponse:
        """
        使用 ToolRegistry.execute_tool 执行工具调用，返回 ToolResponse 对象。
        action: {"name": str, "params": dict}
        """
        if not action or "name" not in action:
            return ToolResponse.error(code="INVALID_ACTION", message="action 格式错误: 缺少 name")

        name = action["name"]
        params = action.get("params", {})

        #ToolRegistry.execute_tool's input:str/dict
        try:
            response = None
            if hasattr(self, "tool_registry") and self.tool_registry:
                response = self.tool_registry.execute_tool(name, params)
            else:
                #备用从全局注册表获取
                from hello_agents.tools.registry import global_registry

                response = global_registry.execute_tool(name, params)
        except Exception as e:
            return ToolResponse.error(code="EXECUTION_ERROR", message=str(e))

        return response
    
    
    
    def run(self, input_text: str, **kwargs) -> str:
        """
        对齐 ReActAgent.run 签名：接受 input_text 并返回最终答案。
        这里初始化一个 root 步骤用于 trace，然后委托给父类实现实际的运行逻辑。
        """
        #initialze
        root_step = ResearchStep()
        root_step.step_id = str(uuid.uuid4())
        root_step.step_type = "root"
        root_step.task = input_text
        root_step.thought = "接收用户任务并初始化执行上下文"
        root_step.action = {
            "request": {
                "name": "run",
                "params": {"input_text": input_text},
            },
            "response": {
                "status": "success",
                "text": "根步骤创建成功",
                "data": {},
                "error": None,
            },
        }
        root_step.observation = "已创建 root 节点并准备进入 ReAct 主循环"
        root_step.timestamp = time.time()
        root_step.status = "success"
        self.research_map.add_step(root_step)
        self.current_step_id = root_step.step_id
        self.latest_reasoning = ""

        final_answer = super().run(input_text, **kwargs)

        return final_answer
    def get_research_map(self) -> ResearchMap:
        return self.research_map


def build_traceable_agent(max_steps: int = 10) -> TraceableAgent:
    registry = ToolRegistry()
    read_tool = ReadTool(project_root=".", registry=registry)
    write_tool = WriteTool(project_root=".", registry=registry)
    registry.register_tool(read_tool)
    registry.register_tool(write_tool)

    llm = HelloAgentsLLM()

    system_prompt = """
你是一个具有完整回溯（trace）能力的代码分析与改进智能体。你的行为必须可复现、可审计，每一步（思考/行动/观察）都要记录到 Research Map 中。记录规范、工具调用格式和输出要求如下：

1) 总体目标
- 目标：读取仓库并生成一份可直接阅读的分析报告，保存为 reports/repo-analysis-report.md。
- 报告分节：项目概览、目录结构、核心入口、运行方式、扩展建议、风险与待确认项。

2) 严格原则
- 只基于实际读取到的文件与内容进行断言；无法确认的信息必须标注为 “未确认”，不得编造。
- 每次读取/修改/生成文件都要作为工具调用并记录其 ToolResponse 与 artifact_id（若有产物）。

3) Trace 记录规范（ResearchStep 必须包含字段）
- 必须记录：`step_id`、`parent_step_id`、`task`、`thought`（LLM 内部推理，简短）、`action`（工具调用或操作描述）、`observation`（工具响应摘要）、`artifact_ids`（保存的产物ID列表）、`status`（success/failure）、`timestamp`。
- 示例 ResearchStep（JSON）：
    {"step_id":"...", "parent_step_id":"...", "task":"读取 README", "thought":"先检查根目录与 README", "action":{"name":"ReadTool","params":{"path":"README.md"}},"observation":"发现项目描述、依赖说明","artifact_ids":[],"status":"success","timestamp":...}

4) 工具调用格式（当需要时必须以 JSON 输出工具意图，保证格式）
- 工具调用格式示例（严格 JSON，单行或包裹在代码块）：
    {"name":"ReadTool","params":{"path":"README.md"}}
- 仅在确实需要外部读取/写入时才调用工具。对于每次调用，记录 ToolResponse 并通过 MappingService 保存任何可作为产物的内容（并把生成的 `artifact_id` 关联到当前步骤）。

5) 分析流程（步骤化）
- 第一步：枚举根目录与关键配置文件（README*, pyproject.toml, requirements.txt, setup.py, .env, src/, examples/, tests/ 等），并把结果写入 Research Map。
- 第二步：识别核心入口（例如 if __name__ == "__main__"、FastAPI/Uvicorn 启动脚本、CLI 命令等）并记录路径及对应行号/片段（精确文件相对路径）。
- 第三步：列出依赖与技术栈（依据 requirements.txt、pyproject.toml、源代码导入等），明确哪些是“已确认”来源。
- 第四步：扫描示例与测试，记录可复现运行方式与示例命令。
- 第五步：撰写最终报告（见第6项格式），并把报告内容写入 reports/repo-analysis-report.md（若不存在则创建）。

6) 最终报告要求（应该要能够可以直接交付）
- 每节包含简短结论 + 证据（最小化陈述，附相对路径链接或文件片段引用）。
- 风险与待确认项：列出需人工确认或无法自动判断的项，标注“优先级：高/中/低”与推荐下一步。
- 输出为 Markdown，使用清晰小节与短句。

7) 格式与输出约束
- 所有用户可见输出（包括最终回复和报告）使用中文。
- 工具调用必须返回标准 ToolResponse；在生成的 ResearchStep 中引用 `artifact_id`。
- 不要在思考（chain-of-thought）中泄露内部推理给最终用户；对外展示仅给出简洁的“思考摘要”与可验证的证据。

8) Research Map 只读工具
- 你可以使用以下只读工具读取 Research Map：
    - view_step：按步骤 ID 查看单个步骤
    - traceback_current：查看当前步骤到根节点的完整路径
    - search_steps：按关键词搜索步骤
    - trace_artifact：按 artifact_id 追踪产物来源步骤
    - list_steps：列出当前已记录的步骤 ID
    - get_current_step：查看当前最新步骤
- 这些工具只用于审查和回溯，不会修改 Research Map。

9) 错误与异常处理
- 若工具调用失败，记录失败原因（`status=error`）并在 Research Map 中创建一个可追溯的失败步骤；继续下一可行步骤并在最终报告中汇总失败项与建议补救措施。

10) 可选但推荐的行为
- 在可能的情况下，把关键发现（如核心入口、示例运行命令、主要依赖）写在报告最前面作为“快速上手”小节。
- 保持每一步短小，便于回溯与自动化审查。

请按以上规范执行代码分析并生成报告。如果需要调用工具，请严格按照工具调用格式输出，并确保每次调用都被记录在 Research Map 中。最终输出应该是一个清晰、结构化的 Markdown 报告，直接交付给用户。
如果用户提出需要修改或补充的地方，请直接在 Research Map 中添加新的步骤进行修改，并在最终报告中反映这些修改。
"""
    agent = TraceableAgent("TraceableAgent", llm, tool_registry=registry, config=CONFIG, system_prompt=system_prompt, max_steps=max_steps)

    #将 Research Map 的只读查询能力显式注册为工具，供模型在运行时调用，之前没注册用不了
    registry.register_function(
        agent.view_step,
        name="view_step",
        description="根据步骤 ID 读取 Research Map 中单个步骤的完整记录",
    )
    registry.register_function(
        agent.traceback_current,
        name="traceback_current",
        description="读取当前步骤到根节点的完整回溯路径",
    )
    registry.register_function(
        agent.search_steps,
        name="search_steps",
        description="按关键词搜索 Research Map 中的步骤",
    )
    registry.register_function(
        agent.trace_artifact,
        name="trace_artifact",
        description="根据 artifact_id 追踪生成该产物的步骤",
    )
    registry.register_function(
        agent.list_steps,
        name="list_steps",
        description="列出当前 Research Map 中已经记录的步骤 ID",
    )
    registry.register_function(
        agent.get_current_step,
        name="get_current_step",
        description="查看当前最新步骤的完整内容",
    )
    return agent
