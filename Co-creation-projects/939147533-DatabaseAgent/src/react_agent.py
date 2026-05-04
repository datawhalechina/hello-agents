"""
数据库Agent - 基于ReAct框架的智能数据库查询助手
"""
import re
from typing import Optional, List
from hello_agents import ReActAgent, HelloAgentsLLM, Config, Message, ToolRegistry
from tools import OracleQueryTool, SQLGeneratorTool, format_query_result
from config import DatabaseConfig


DATABASE_AGENT_PROMPT = """你是一个专业的数据库查询助手。你可以理解用户的自然语言查询，将其转换为SQL语句，从Oracle数据库中获取数据并格式化输出。

## 可用工具
{tools}

## 工作流程
请严格按照以下格式进行回应：

Thought: 你的思考过程，分析用户需求并规划下一步行动。
Action: 你决定采取的行动，必须是以下格式之一：
- `{{tool_name}}[{{tool_input}}]` - 调用指定工具
- `Finish[最终答案]` - 当你有足够信息给出最终答案时

## 使用指南
1. 当用户提出查询需求时，首先使用 GetSchema 工具获取数据库表结构
2. 使用 GenerateSQL 工具将自然语言转换为SQL语句
3. 使用 ExecuteQuery 工具执行SQL并获取结果

## 当前任务
**Question:** {question}

## 执行历史
{history}

现在开始你的推理和行动：
"""


class DatabaseAgent(ReActAgent):
    """数据库查询Agent"""
    
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        db_config: DatabaseConfig,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_steps: int = 5
    ):
        super().__init__(name, llm, system_prompt, config)
        
        self.db_config = db_config
        self.max_steps = max_steps
        self.current_history: List[str] = []
        self.prompt_template = DATABASE_AGENT_PROMPT
        
        self.oracle_tool = OracleQueryTool(db_config)
        self.sql_generator = SQLGeneratorTool(llm)
        
        self.tool_registry = ToolRegistry()
        self.tool_registry.register_function(
            "GetSchema",
            "获取数据库表结构信息，包括所有表名和字段定义。",
            self._get_schema
        )
        self.tool_registry.register_function(
            "GenerateSQL",
            "将自然语言查询转换为Oracle SQL语句。",
            self._generate_sql
        )
        self.tool_registry.register_function(
            "ExecuteQuery",
            "执行SQL查询并返回结果。",
            self._execute_query
        )
        
        self.schema_cache = None
        print(f"✅ {name} 初始化完成，最大步数: {max_steps}")
    
    def _get_schema(self, input_text: str) -> str:
        """获取数据库表结构信息，包括所有表名和字段定义"""
        schema_info = self.oracle_tool.get_schema_info()
        self.schema_cache = schema_info
        return schema_info
    
    def _generate_sql(self, input_text: str) -> str:
        """将自然语言查询转换为Oracle SQL语句"""
        if not self.schema_cache:
            self.schema_cache = self.oracle_tool.get_schema_info()
        
        sql = self.sql_generator.generate_sql(input_text, self.schema_cache)
        
        is_valid, msg = self.sql_generator.validate_sql(sql)
        if not is_valid:
            return f"SQL生成失败: {msg}"
        
        return f"生成的SQL: {sql}"
    
    def _execute_query(self, input_text: str) -> str:
        """执行SQL查询并返回结果"""
        sql = input_text.strip()
        
        if sql.startswith("生成的SQL: "):
            sql = sql.replace("生成的SQL: ", "")
        
        result = self.oracle_tool.execute_query(sql)
        
        if not result["success"]:
            return f"查询执行失败: {result['error']}"
        
        formatted_result = format_query_result(result)
        return formatted_result
    
    def run(self, input_text: str, **kwargs) -> str:
        """运行数据库Agent"""
        self.current_history = []
        current_step = 0
        
        print(f"\n🤖 {self.name} 开始处理问题: {input_text}")
        
        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- 第 {current_step} 步 ---")
            # 1. 构建提示词
            tools_desc = self.tool_registry.get_tools_description()
            history_str = "\n".join(self.current_history)
            prompt = self.prompt_template.format(
                tools=tools_desc,
                question=input_text,
                history=history_str
            )
            # 2. 调用LLM
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm.invoke(messages, **kwargs)
            # 3. 解析输出
            thought, action = self._parse_output(response_text)
            
            if thought:
                print(f"🤔 思考: {thought}")
            
            if action and action.startswith("Finish"):
                final_answer = self._parse_action_input(action)
                self.add_message(Message(input_text, "user"))
                self.add_message(Message(final_answer, "assistant"))
                return final_answer
            
            if action:
                tool_name, tool_input = self._parse_action(action)
                observation = self.tool_registry.execute_tool(tool_name, tool_input)
                print(f"🎬 行动: {tool_name}[{tool_input}]")
                print(f"👀 观察: {observation}")
                self.current_history.append(f"Action: {action}")
                self.current_history.append(f"Observation: {observation}")
        
        final_answer = "抱歉，我无法在限定步数内完成这个任务。"
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_answer, "assistant"))
        return final_answer
    
    def _parse_output(self, text: str):
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action
    
    def _parse_action(self, action_text: str):
        match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        return (match.group(1), match.group(2)) if match else (None, None)
    
    def _parse_action_input(self, action_text: str):
        match = re.match(r"\w+\[(.*)\]", action_text, re.DOTALL)
        return match.group(1) if match else ""