import json
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from hello_agents import HelloAgentsLLM, SimpleAgent, ToolRegistry

from config import *
from model import UserMemory, Task, Plan, ScheduleItem
from prompt import *
from tools import get_Tools


class MainAgent:
    def __init__(self):
        self.llm = HelloAgentsLLM(model=LLM_MODEL, api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        tool = get_Tools()
        self.respostry = ToolRegistry()
        self.respostry.register_tool(tool)
        self.main_agent = SimpleAgent(
            name="总控MAIN_AGENT",
            llm=self.llm,
            system_prompt=MAIN_AGENT_PROMPT,
            tool_registry=self.respostry
        )
        self.np_parser_agent = SimpleAgent(
            name="子Agent：自然语言解析，用户输入 → Task列表 + 意图",
            llm=self.llm,
            system_prompt=NL_PARSE_PROMPT,
            tool_registry=self.respostry
        )
        # self.np_parser_agent.add_tool(tool)
        self.plan_Agent = SimpleAgent(
            name="子Agent：你是日程规划Agent，用于规划用户日程",
            llm=self.llm,
            system_prompt=PLAN_REASON_PROMPT,
            tool_registry=self.respostry
        )
        # self.plan_Agent.add_tool(tool)
        self.validator_agent = SimpleAgent(
            name="子Agent：你是计划校验Agent，检查生成的日程计划是否违反用户记忆、是否存在时间冲突。",
            llm=self.llm,
            system_prompt=VALIDATE_PROMPT,
            tool_registry=self.respostry
        )
        # self.validator_agent.add_tool(tool)
        self.dialog_history: List[dict] = []

    def _build_context_str(self, user_input: str, memory: UserMemory, current_plan: Optional[Plan], mem: Optional[UserMemory], plan: Optional[Plan]) -> str:
        memory_json = json.dumps(memory.model_dump(), ensure_ascii=False, indent=2)
        cp_json = json.dumps(current_plan.model_dump(), ensure_ascii=False, indent=2) if current_plan else 'null'
        history_text = []
        history_text.append(f"====当前系统时间====\n{datetime.now().strftime('%Y‑%m‑%d %H:%M:%S')}")
        history_text.append("====对话历史====")
        for msg in self.dialog_history:
            role = msg['role']
            cnt = msg["content"]
            history_text.append(f"{role}: {cnt}")
        history_text.append("====用户记忆====")
        history_text.append(memory_json)
        history_text.append(mem)
        history_text.append("====当前已存在计划current_plan====")
        history_text.append(cp_json)
        history_text.append(plan)
        history_text.append("====用户最新输入====")
        history_text.append(user_input)
        return "\n".join(history_text)

    def _build_subagent_payload(self, pass_param: dict, memory: UserMemory, current_plan: Optional[Plan]) -> dict:
        """构造子Agent输入：强制注入公共上下文，不依赖总控pass_to_sub"""
        import datetime
        payload = {**pass_param}
        # 强制注入
        payload["current_system_time"] = datetime.datetime.now().strftime("%Y‑%m‑%d %H:%M:%S")
        payload["user_memory"] = memory.model_dump()
        payload["current_plan"] = current_plan.model_dump() if current_plan else None
        payload["dialog_history"] = self.dialog_history.copy()
        return payload

    def run(self, user_input: str, memory: UserMemory, current_plan: Optional[Plan], mem: Optional[UserMemory] = 'null', plan: Optional[Plan] = 'null') -> Tuple[Optional[Plan], str]:
        try:
            self.dialog_history.append({'role':'user','content':user_input})
            max_loop = 10
            loop_count = 0
            final_plan: Optional[Plan] = None
            final_output: str=""
            while loop_count < max_loop:
                loop_count += 1
                context = self._build_context_str(user_input, memory, current_plan, mem, plan)
                main_raw = self.main_agent.run(context)
                main_raw = main_raw.strip().removeprefix("```json").removesuffix("```").strip()
                try:
                    main_desicion = json.loads(main_raw)
                except:
                    err_msg = f'总控Agent决策解析失败，原始输出：{main_raw[:300]}'
                    final_output = err_msg
                    break

                call_sub = main_desicion.get("call_sub_agent", 'finish')
                pass_param = main_desicion.get("pass_to_sub", {})
                if call_sub == 'finish':
                    # 总控通知结束
                    fp_json = pass_param.get("final_plan_json")
                    final_output = pass_param.get("output_text", "处理完成")
                    if fp_json and fp_json != "null":
                        try:
                            final_plan = Plan.model_validate_json(fp_json)
                        except Exception:
                            final_plan = None
                    break
                if call_sub == 'nl_parser':
                    sub_payload = self._build_subagent_payload(pass_param, memory, current_plan)
                    sub_query = json.dumps(sub_payload, ensure_ascii=False, indent=2)
                    sub_out = self.np_parser_agent.run(sub_query)
                    self.dialog_history.append({'role': 'tool:nl_parser', "content": sub_out})

                elif call_sub == 'planner':
                    sub_payload = self._build_subagent_payload(pass_param, memory, current_plan)
                    plan_query = json.dumps(sub_payload, ensure_ascii=False, indent=2)
                    sub_out = self.plan_Agent.run(plan_query)
                    self.dialog_history.append({'role': 'tool:planner', "content": sub_out})

                elif call_sub == 'validator':
                    sub_payload = self._build_subagent_payload(pass_param, memory, current_plan)
                    sub_query = json.dumps(sub_payload, ensure_ascii=False, indent=2)
                    sub_out = self.validator_agent.run(sub_query)
                    self.dialog_history.append({'role': 'tool:validator', "content": sub_out})

                else:
                    final_output = f"总控调用未知子Agent:{call_sub}"
                    break
            else:
                final_output = "循环已满，处理过程终止"
            self.dialog_history.append({'role':'assistant', "content":final_output})
            return final_plan, final_output

        except Exception as e:
            print(f"总控智能体出现错误：{str(e)}，即将使用默认模式")
            return self.run_bak(user_input, memory, current_plan)

    def run_bak(self, user_input: str, memory: UserMemory, current_plan: Optional[Plan]) -> Tuple[Optional[Plan], str]:
        """
        :param user_input: 用户原始输入
        :param memory: 用户记忆对象
        :param current_plan: 当前已存在计划（修改场景使用）
        :return: (Plan对象 or None, 对外输出文本/需要澄清的问题)
        """
        # self.dialog_history.append(AgentMessage(role="user", content=user_input))
        memory_json = json.dumps(memory.model_dump(), ensure_ascii=False, indent=2)
        # 把用户输入 + 用户记忆拼为子Agent的user query
        nl_user_query = f"""
        用户记忆：
        {memory_json}
        用户输入：
        {user_input}
        
        请输出JSON格式结果，包含
        intent_type, target_date(YYYY‑MM‑DD，解析不出返回null), tasks, modify_operation。
        tasks 为任务数组。
        """
        ### Agent 第一次调用，解析用户问题，然后生成任务列表
        nl_result_raw = self.np_parser_agent.run(nl_user_query)
        nl_result_raw = nl_result_raw.strip().removeprefix("```json").removesuffix("```").strip()
        try:
            nl_out = json.loads(nl_result_raw)
        except json.JSONDecodeError:
            return None, "解析用户需求失败，大模型返回格式异常，请重新描述你的需求。"

        intent_type = nl_out.get("intent_type", "")
        task_dicts = nl_out.get("tasks", [])
        target_date: str | None = nl_out.get("target_date")
        plan_name: str | None = nl_out.get("name_summary")
        modify_operation = nl_out.get("modify_operation", {})
        long_term_meta = nl_out.get("long_term_meta", {})
        if not target_date:
            # 兜底：取系统当前日期
            target_date = datetime.now().strftime("%Y‑%m‑%d %H:%M:%S")
        try:
            task_list: List[Task] = [Task.model_validate(d) for d in task_dicts]
        except Exception:
            return None, "任务数据解析失败，请简化你的描述。"
        ### 识别意图，然后决定怎么做这个任务
        if intent_type == "new_plan":
            task_list_json = json.dumps([t.model_dump() for t in task_list], ensure_ascii=False, indent=2)
            plan_user_query = f"""
            用户记忆：
            {memory_json}
            需要规划的目标日期：
            {target_date}
            待规划任务列表：
            {task_list_json}

            请输出JSON，包含 schedule_items(日程条目数组)、plan_summary。
            日程的时间需要基于目标日期生成，时间格式 YYYY‑MM‑DD HH:MM。
            """

            plan_result_raw = self.plan_Agent.run(plan_user_query)
            plan_result_raw = plan_result_raw.strip().removeprefix("```json").removesuffix("```").strip()
            try:
                plan_out = json.loads(plan_result_raw)
            except json.JSONDecodeError:
                return None, "生成日程失败，格式错误。"
            schedule_dicts = plan_out.get("schedule_items", [])
            try:
                schedule_items: List[ScheduleItem] = [ScheduleItem.model_validate(s) for s in schedule_dicts]
            except Exception:
                return None, "日程条目数据解析失败。"
            new_plan = Plan(
                plan_id=str(uuid.uuid4()),
                plan_name=plan_name,
                create_time=target_date if target_date else datetime.now().strftime("%Y‑%m‑%d %H:%M"),
                source_user_input=user_input,
                tasks=task_list,
                schedule_items=schedule_items,
                plan_summary=plan_out.get("plan_summary", ""),
                conflict_check_result="pending"
            )

            plan_json = json.dumps(new_plan.model_dump(), ensure_ascii=False, indent=2)
            validate_user_query = f"""
            用户记忆：
            {memory_json}

            待校验计划：
            {plan_json}

            请输出JSON：
            {{
              "has_error": bool,
              "need_user_clarify": bool,
              "clarify_question": str,
              "error_msg": str
            }}
            """
            validate_raw = self.validator_agent.run(validate_user_query)
            validate_raw = validate_raw.strip().removeprefix("```json").removesuffix("```").strip()
            try:
                validate_out = json.loads(validate_raw)
            except json.JSONDecodeError:
                new_plan.conflict_check_result = 'unknown'
                return new_plan, new_plan.plan_summary + "\n 校验新建环节解析异常"
            has_error = validate_out.get("has_error", False)
            need_user_clarify = validate_out.get("need_user_clarify", False)
            clarify_question = validate_out.get("clarify_question", "")
            if need_user_clarify:
                return None, clarify_question
            if has_error:
                new_plan.conflict_check_result = "has_error"
            else:
                new_plan.conflict_check_result = "ok"
            return new_plan, new_plan.plan_summary

        elif intent_type == "modify_plan":
            if current_plan is None:
                return None, "当前没有已生成的计划，请先生成一份日程计划之后再执行修改。"
            old_plan_json = json.dumps(current_plan.model_dump(), ensure_ascii=False, indent=2)
            op_json = json.dumps(modify_operation, ensure_ascii=False, indent=2)
            plan_user_query = f"""
            用户记忆：
            {memory_json}
            目标日期：{target_date}
            原始旧计划：
            {old_plan_json}
            用户修改操作：
            {op_json}

            请基于旧计划，按照修改操作重新生成完整的schedule_items。
            输出JSON：{{"schedule_items":[...],"plan_summary":"描述本次修改后的计划"}}
            时间格式 YYYY‑MM‑DD HH:MM。
            """
            plan_result_raw = self.plan_Agent.run(plan_user_query)
            plan_result_raw = plan_result_raw.strip().removeprefix("```json").removesuffix("```").strip()
            try:
                plan_out = json.loads(plan_result_raw)
            except json.JSONDecodeError:
                return None, "修改计划失败，返回格式异常。"

            schedule_dicts = plan_out.get("schedule_items", [])
            try:
                schedule_items: List[ScheduleItem] = [ScheduleItem.model_validate(s) for s in schedule_dicts]
            except Exception:
                return None, "修改后日程数据解析失败。"

            merged_tasks = current_plan.tasks.copy()
            merged_tasks.extend(task_list)
            modified_plan = Plan(
                plan_id=str(uuid.uuid4()),
                plan_name=plan_name,
                create_time=target_date if target_date else datetime.now().strftime("%Y‑%m‑%d %H:%M"),
                source_user_input=f"[修改] {user_input}",
                tasks=task_list,
                schedule_items=schedule_items,
                plan_summary=plan_out.get("plan_summary", ""),
                conflict_check_result="pending"
            )

            plan_json = json.dumps(modified_plan.model_dump(), ensure_ascii=False, indent=2)
            validate_user_query = f"""
            用户记忆：
            {memory_json}

            待校验计划：
            {plan_json}

            请输出JSON：
            {{
              "has_error": bool,
              "need_user_clarify": bool,
              "clarify_question": str,
              "error_msg": str
            }}
            """
            validate_raw = self.validator_agent.run(validate_user_query)
            validate_raw = validate_raw.strip().removeprefix("```json").removesuffix("```").strip()
            try:
                validate_out = json.loads(validate_raw)
            except json.JSONDecodeError:
                modified_plan.conflict_check_result = 'unknown'
                return modified_plan, modified_plan.plan_summary + "\n 校验修改环节解析异常"
            has_error = validate_out.get("has_error", False)
            need_user_clarify = validate_out.get("need_user_clarify", False)
            clarify_question = validate_out.get("clarify_question", "")
            if need_user_clarify:
                return None, clarify_question
            if has_error:
                modified_plan.conflict_check_result = "has_error"
            else:
                modified_plan.conflict_check_result = "ok"
            return modified_plan, modified_plan.plan_summary


        elif intent_type == "long_term_goal":
            """
            1.读取long_term_meta，调用 subtask_split_helper_tool 拆出多个子任务描述
            2.把拆分得到的子任务组装成Task列表
            3.复用new_plan整套规划+校验逻辑
            """
            try:
                total_days = int(long_term_meta.get("total_days", 0))
                daily_duration = int(long_term_meta.get("daily_duration_min", 0))
                goal_desc = long_term_meta.get("goal_desc", "")
            except (ValueError, TypeError):
                return None, "长期目标参数解析失败，请明确说明总天数、每日耗时。"

            if total_days <= 0 or daily_duration < 0:
                return None, "总天数或者每日时长必须大于0"
            try:
                tool = self.respostry.get_tool("subtask_split_helper_tool")
                sub_task_info = tool.run({"total_days": total_days, "goal_desc": goal_desc})
            except:
                print("仓库工具调用失败，进行本地调用")
                sub_task_info = get_Tools.subtask_split_helper_tool(total_days, main_desc=goal_desc)
            # 把拆分结果转为Task模型
            long_tasks: List[Task] = []
            for idx, info in enumerate(sub_task_info):
                t = Task(
                    task_id=f"lt_{uuid.uuid4()}",
                    task_name=info["sub_desc"],
                    description=f"长期目标：{goal_desc}",
                    estimated_duration_min=daily_duration,
                    priority="medium",
                    deadline=None,
                    fixed_time=None,
                    allowed_time=None
                )
                long_tasks.append(t)

            # 合并用户输入附带的任务 + 拆分出来长期子任务
            full_task_list = task_list + long_tasks
            task_list_json = json.dumps([t.model_dump() for t in full_task_list], ensure_ascii=False, indent=2)
            plan_user_query = f"""
            用户记忆：
            {memory_json}
            规划起始目标日期：{target_date}
            长期任务列表：
            {task_list_json}
            请跨多天生成schedule_items，输出JSON，包含schedule_items、plan_summary。
            时间格式 YYYY‑MM‑DD HH:MM。
            """
            plan_result_raw = self.plan_Agent.run(plan_user_query)
            plan_result_raw = plan_result_raw.strip().removeprefix("```json").removesuffix("```").strip()
            try:
                plan_out = json.loads(plan_result_raw)
            except json.JSONDecodeError:
                return None, "修改计划失败，返回格式异常。"

            schedule_dicts = plan_out.get("schedule_items", [])
            try:
                schedule_items: List[ScheduleItem] = [ScheduleItem.model_validate(s) for s in schedule_dicts]
            except Exception:
                return None, "长期任务日程数据解析失败。"

            long_term_plan = Plan(
                plan_id=str(uuid.uuid4()),
                plan_name=plan_name,
                create_time=target_date if target_date else datetime.now().strftime("%Y‑%m‑%d %H:%M"),
                source_user_input=f"[长期任务] {user_input}",
                tasks=task_list,
                schedule_items=schedule_items,
                plan_summary=plan_out.get("plan_summary", ""),
                conflict_check_result="pending"
            )

            plan_json = json.dumps(long_term_plan.model_dump(), ensure_ascii=False, indent=2)
            validate_user_query = f"""
            用户记忆：
            {memory_json}

            待校验计划：
            {plan_json}

            请输出JSON：
            {{
              "has_error": bool,
              "need_user_clarify": bool,
              "clarify_question": str,
              "error_msg": str
            }}
            """
            validate_raw = self.validator_agent.run(validate_user_query)
            validate_raw = validate_raw.strip().removeprefix("```json").removesuffix("```").strip()
            try:
                validate_out = json.loads(validate_raw)
            except json.JSONDecodeError:
                long_term_plan.conflict_check_result = 'unknown'
                return long_term_plan, long_term_plan.plan_summary + "\n 校验长任务环节解析异常"
            has_error = validate_out.get("has_error", False)
            need_user_clarify = validate_out.get("need_user_clarify", False)
            clarify_question = validate_out.get("clarify_question", "")
            if need_user_clarify:
                return None, clarify_question
            if has_error:
                long_term_plan.conflict_check_result = "has_error"
            else:
                long_term_plan.conflict_check_result = "ok"
            return long_term_plan, long_term_plan.plan_summary


        else:
            return None, f"无法识别意图：{intent_type}, 请重新描述你的需求"

    def clear_memory(self):
        """清空本轮对话记忆，保留agent实例，适合开启新会话"""
        self.dialog_history.clear()

    def save_session(self, save_path: Path | str, memory: UserMemory, current_plan: Optional[Plan]):
        """将会话保存到JSON文件"""
        data = {
            "dialog_history": self.dialog_history,
            "user_memory": memory.model_dump(),
            "last_plan": current_plan.model_dump() if current_plan else None
        }
        with open(save_path, "w", encoding="utf‑8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_session(self, load_path: Path | str) -> tuple[UserMemory | None, Plan | None]:
        """从JSON恢复会话，返回(memory, current_plan)，同时填充self.dialog_history"""
        if not Path(load_path).exists():
            return None, None
        with open(load_path, "r", encoding="utf‑8") as f:
            data = json.load(f)
        self.dialog_history = data.get("dialog_history", [])
        mem_data = data.get("user_memory")
        plan_data = data.get("last_plan")
        mem = UserMemory(**mem_data) if mem_data else None
        plan = Plan(**plan_data) if plan_data else None
        return mem, plan


def demo_memory() -> UserMemory:
    return UserMemory(
        user_id="u_001",
        work_start="09:00",
        work_end="18:00",
        rest_days=["Saturday", "Sunday"],
        avoid_time=["12:00‑13:30"],
        preference={"priority_rule": "工作事务优先"},
        hobbies=["慢跑", "看书"],
        dislike=["早起高强度运动"]
    )


def main():
    agent = MainAgent()
    memory = demo_memory()
    current_plan = None
    user_input = "帮我规划今天的日程，我需要复习90分钟，慢跑40分钟。"
    plan, output_text = agent.run(user_input, memory, current_plan)
    if plan is None:
        print(f"输出：{output_text}")
    else:
        print(f"\n计划摘要：{plan.plan_summary}")
        for item in plan.schedule_items:
            print(f"{item.start_time} ~ {item.end_time} | {item.task_name}")


if __name__ == "__main__":
    main()
