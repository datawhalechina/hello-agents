
import re

from MyAgent.ReActAndTool.llm_client import HelloAgentsLLM
from MyAgent.ReActAndTool.tool import ToolExecutor
REACT_PROMPT_TEMPLATE = """
请注意，你是一个有能力调用外部工具的智能助手。

可用工具如下：
{tools}

请严格按照以下格式进行回应：

Thought: 你的思考过程，用于分析问题、拆解任务和规划下一步行动。
Action: 你决定采取的行动，必须是以下格式之一：
- `{{tool_name}}[{{tool_input}}]`：调用一个可用工具。
- `Finish[最终答案]`：当你认为已经获得最终答案时。
- 当你收集到足够的信息，能够回答用户的最终问题时，你必须在`Action:`字段后使用 `Finish[最终答案]` 来输出最终答案。


现在，请开始解决以下问题：
Question: {question}
History: {history}
"""

class ReActAgent:
    def __init__(self,llm_client: HelloAgentsLLM, tool_executor: ToolExecutor, max_steps: int = 5):
        self.tool = tool_executor
        self.llm_client = llm_client
        self.max_steps = max_steps
        self.history = []
    def run(self,questions : str):
        self.history = []
        current_step = 0
        
        while(current_step < self.max_steps):
            current_step += 1
            history_str = "\n".join(self.history)
            
            #获取可获得的所有工具
            tools_desc = self.tool.getAvailableTools
            prompt = REACT_PROMPT_TEMPLATE.format(tools = tools_desc, question = questions, history = history_str)
            #构建messages
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)
            if not response_text:
                print("错误：LLM未能返回有效响应。"); break
            thought, action = self._parse_output(response_text)
            if thought: print(f"🤔 思考: {thought}")
            if not action: print("警告：未能解析出有效的Action，流程终止。"); break
            if action.startswith("Finish"):
                # 如果是Finish指令，提取最终答案并结束
                final_answer = self._parse_action_input(action)
                print(f"🎉 最终答案: {final_answer}")
                return final_answer
            tool_name, tool_input = self._parse_action(action)
            if not tool_name or not tool_input:
                self.history.append("Observation: 无效的Action格式，请检查。"); continue
                
            ##执行工具
            tool_function = self.tool.getTool(tool_name)
            observation = tool_function(tool_input) if tool_function else f"错误：未找到名为 '{tool_name}' 的工具。"
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")
            
        print("已达最大步数")
        return None
    
    
    def _parse_output(self,text : str):
        # Thought: 匹配到 Action: 或文本末尾
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        # Action: 匹配到文本末尾
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action
    
    def _parse_action_input(self, action_text: str):
        match = re.match(r"\w+\[(.*)\]", action_text, re.DOTALL)
        return match.group(1) if match else ""

if __name__ == '__main__':
    tool = ToolExecutor()
    agentClient = HelloAgentsLLM()
    reAct = ReActAgent(llm_client= agentClient, tool_executor= tool)
    messages = """帮我给出快速排序算法"""
    reAct.run(messages)
    
    
    
            