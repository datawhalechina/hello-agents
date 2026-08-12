import os
import json
import zipfile
import subprocess
import shutil
from typing import Dict, Any, List

from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools import Tool, ToolParameter, ToolResponse
from hello_agents.tools.response import ToolStatus

class UserMemoryTool(Tool):
    """管理用户水平记忆的工具"""

    def __init__(self, memory_file: str = "user_memory.json"):
        super().__init__(
            name="user_memory",
            description="获取或更新用户的编程水平和做题记录"
        )
        self.memory_file = os.path.join(os.path.dirname(__file__), "../../data", memory_file)
        self._ensure_memory_file()

    def _ensure_memory_file(self):
        if not os.path.exists(self.memory_file):
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump({"level": "beginner", "history": []}, f)

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        action = parameters.get("action")
        
        with open(self.memory_file, "r", encoding="utf-8") as f:
            memory = json.load(f)

        if action == "get":
            return ToolResponse.success(text=json.dumps(memory, ensure_ascii=False))
        elif action == "update":
            new_level = parameters.get("level")
            new_record = parameters.get("record")
            if new_level:
                memory["level"] = new_level
            if new_record:
                memory["history"].append(new_record)
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(memory, f, ensure_ascii=False, indent=2)
            return ToolResponse.success(text="记忆更新成功")
        else:
            return ToolResponse.error(text="无效的 action")

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="操作类型，可选 'get' 或 'update'",
                required=True
            ),
            ToolParameter(
                name="level",
                type="string",
                description="用户的新水平评估 (例如 'beginner', 'intermediate', 'advanced')",
                required=False
            ),
            ToolParameter(
                name="record",
                type="string",
                description="新完成的题目记录",
                required=False
            )
        ]

class CodeTestTool(Tool):
    """代码自动测试与打分工具"""

    def __init__(self):
        super().__init__(
            name="code_test",
            description="解压用户上传的项目压缩包，运行测试并给出评分"
        )
        self.extract_dir = os.path.join(os.path.dirname(__file__), "../../outputs/extracted")

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        zip_path = parameters.get("zip_path")
        test_code = parameters.get("test_code") # 由LLM生成的测试代码
        
        if not zip_path or not os.path.exists(zip_path):
            return ToolResponse.error(text="错误：压缩包路径不存在")
            
        if not test_code:
            return ToolResponse.error(text="错误：缺少测试代码")

        # 清理旧的解压目录
        if os.path.exists(self.extract_dir):
            shutil.rmtree(self.extract_dir)
        os.makedirs(self.extract_dir, exist_ok=True)

        # 解压
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.extract_dir)
        except Exception as e:
            return ToolResponse.error(text=f"解压失败: {str(e)}")

        # 写入测试文件
        test_file_path = os.path.join(self.extract_dir, "test_generated.py")
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(test_code)

        # 运行测试
        try:
            result = subprocess.run(
                ["pytest", test_file_path, "-v"],
                cwd=self.extract_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout + "\n" + result.stderr
            score = 100 if result.returncode == 0 else 0 # 简单评分逻辑，可根据pytest输出优化
            
            return ToolResponse.success(
                text=json.dumps({
                    "score": score,
                    "test_output": output,
                    "status": "success" if result.returncode == 0 else "failed"
                }, ensure_ascii=False)
            )
            
        except subprocess.TimeoutExpired:
            return ToolResponse.error(text="测试执行超时")
        except Exception as e:
            return ToolResponse.error(text=f"测试执行出错: {str(e)}")

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="zip_path",
                type="string",
                description="用户上传的项目压缩包绝对路径",
                required=True
            ),
            ToolParameter(
                name="test_code",
                type="string",
                description="用于测试用户代码的 pytest 测试代码",
                required=True
            )
        ]

def get_helper_agent() -> SimpleAgent:
    """初始化并返回学习助手智能体"""
    tool_registry = ToolRegistry()
    tool_registry.register_tool(UserMemoryTool())
    tool_registry.register_tool(CodeTestTool())

    model_id = os.environ.get("LLM_MODEL_ID", "Qwen/Qwen2.5-72B-Instruct")
    llm = HelloAgentsLLM(model=model_id)

    system_prompt = """你是一个专业的软件开发学习助手。你的职责是：
1. 使用 user_memory 工具了解用户的当前编程水平和历史做题记录。
2. 根据用户水平，为他们出适合的编程题目，或者从网上搜索真实的开发案例。
3. 在用户开发过程中，提供有针对性的建议和指导。
4. 当用户完成开发并上传项目压缩包后，你需要：
   - 仔细分析题目要求。
   - 编写严谨的 pytest 测试用例代码。注意：用户的代码通常在解压目录的某个子文件夹中（如 `test-projects/main.py`），你的测试代码需要能够递归查找 `.py` 文件并动态导入模块，而不是简单地假设代码在当前目录下。可以参考使用 `sys.path.insert(0, str(project_root))` 来辅助导入。
   - 使用 code_test 工具，传入压缩包路径和你的测试代码，对用户的项目进行自动化测试。
   - 根据测试结果给出最终打分和详细的代码审查反馈。
5. 任务完成后，使用 user_memory 工具更新用户的水平评估和做题记录。

请始终保持鼓励和专业的态度。"""

    from hello_agents.core.config import Config
    
    # 禁用 TodoWrite 工具，避免在 Azure/Gemini 下出现 schema 验证错误
    config = Config(todowrite_enabled=False)

    return SimpleAgent(
        name="SoftwareDevHelper",
        llm=llm,
        system_prompt=system_prompt,
        tool_registry=tool_registry,
        config=config
    )
