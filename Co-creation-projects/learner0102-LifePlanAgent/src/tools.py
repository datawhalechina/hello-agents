from datetime import datetime
from typing import List, Dict, Tuple, Any, Optional
from hello_agents.tools import Tool
from hello_agents.tools.base import ToolParameter
from model import ScheduleItem, Task, UserMemory


def parse_time(time_str: str) -> datetime:
    return datetime.strptime(time_str, "%Y-%m-%d %H:%M")


class get_Tools(Tool):
    """
    多种工具可以供给Agent使用：
    - time_conflict_detect：检测日程冲突，返回冲突信息
    - task_priority_sort：按优先级 high>medium>low 排序任务
    - time_available_calc：计算目标日期可用时间段
    - task_duration_check：检查任务是否超过单次最大时长
    - subtask_split_helper：长周期任务拆分辅助工具，返回阶段描述
    """

    def __init__(self, name: str = "schedule_tools", description: Optional[str] = None):
        """
        初始化日程工具集

        Args:
            name: 工具名称
            description: 工具描述
        """
        if description is None:
            description = self._generate_description()

        super().__init__(name=name, description=description)

    def _generate_description(self) -> str:
        """生成工具描述"""
        return """日程管理工具集，提供以下功能：
        1. time_conflict_detect：检测日程冲突
        2. task_priority_sort：按优先级排序任务
        3. time_available_calc：计算可用时间段
        4. task_duration_check：检查任务时长
        5. subtask_split_helper：拆分长周期任务
        
        调用格式：{"action": "工具名", "arguments": {...}}"""

    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        return [
            ToolParameter(
                name="action",
                type="string",
                description="操作类型: time_conflict_detect, task_priority_sort, time_available_calc, task_duration_check, subtask_split_helper",
                required=True
            ),
            ToolParameter(
                name="arguments",
                type="object",
                description="各工具对应的参数",
                required=True
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        """
        执行工具操作

        Args:
            parameters: 包含 action 和 arguments 的字典
                - action: 工具名称
                - arguments: 工具参数

        Returns:
            操作结果（字符串格式）
        """
        action = parameters.get("action", "").lower()
        arguments = parameters.get("arguments", {})

        if not action:
            return "错误：必须指定 action 参数"

        try:
            if action == "time_conflict_detect":
                return self._format_conflict_result(
                    self.time_conflict_detect_tool(**arguments)
                )
            elif action == "task_priority_sort":
                result = self.task_priority_sort_tool(**arguments)
                return self._format_priority_result(result)
            elif action == "time_available_calc":
                result = self.time_available_calc_tool(**arguments)
                return self._format_available_time_result(result)
            elif action == "task_duration_check":
                result = self.task_duration_check_tool(**arguments)
                return self._format_duration_check_result(result)
            elif action == "subtask_split_helper":
                result = self.subtask_split_helper_tool(**arguments)
                return self._format_subtask_result(result)
            else:
                return f"错误：不支持的操作 '{action}'，支持的操作: time_conflict_detect, task_priority_sort, time_available_calc, task_duration_check, subtask_split_helper"
        except Exception as e:
            return f"执行 '{action}' 失败: {str(e)}"

    # ========== 工具方法 ==========

    def time_conflict_detect_tool(self, schedule_items: List[ScheduleItem]) -> Dict:
        """检测日程冲突，返回冲突信息"""
        conflicts = []
        for i in range(len(schedule_items)):
            start_time_i = parse_time(schedule_items[i].start_time)
            end_time_i = parse_time(schedule_items[i].end_time)
            for j in range(i + 1, len(schedule_items)):
                start_time_j = parse_time(schedule_items[j].start_time)
                end_time_j = parse_time(schedule_items[j].end_time)
                if start_time_i < end_time_j and end_time_i > start_time_j:
                    conflicts.append({
                        "task_a_id": schedule_items[i].task_id,
                        "task_b_id": schedule_items[j].task_id,
                        "task_a_name": schedule_items[i].task_name,
                        "task_b_name": schedule_items[j].task_name,
                        "note": f"{schedule_items[i].start_time} ~ {schedule_items[i].end_time} 与 {schedule_items[j].start_time} ~ {schedule_items[j].end_time} 存在时间重叠"
                    })
        return {
            "has_conflict": len(conflicts) > 0,
            "conflict_pairs": conflicts
        }

    def task_priority_sort_tool(self, task_list: List[Task], memory: UserMemory) -> List[Task]:
        """按优先级 high>medium>low 排序任务"""
        prio_map = {"high": 0, "medium": 1, "low": 2}
        return sorted(task_list, key=lambda x: prio_map.get(x.priority, 1))

    def time_available_calc_tool(self, memory: UserMemory, target_date_str: str) -> List[Tuple[str, str]]:
        """
        计算目标日期可用时间段
        target_date_str: "2026-09-05"
        返回 [(start_time_str, end_time_str), ...]，格式 "2026-09-05 HH:MM"
        """
        base_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        work1_start_time = base_date.replace(hour=8, minute=0)
        work1_end_time = base_date.replace(hour=12, minute=0)
        work2_start_time = base_date.replace(hour=14, minute=0)
        work2_end_time = base_date.replace(hour=18, minute=0)
        slots = [
            (work1_start_time.strftime("%Y-%m-%d %H:%M"), work1_end_time.strftime("%Y-%m-%d %H:%M")),
            (work2_start_time.strftime("%Y-%m-%d %H:%M"), work2_end_time.strftime("%Y-%m-%d %H:%M"))
        ]
        return slots

    def task_duration_check_tool(self, task_list: List[Task], max_time: int) -> Dict:
        """检查任务是否超过单次最大时长"""
        over_list = []
        for task in task_list:
            if task.estimated_duration_min > max_time:
                over_list.append({
                    "task_id": task.task_id,
                    "task_name": task.task_name,
                    "task_duration_time": task.estimated_duration_min
                })
        return {
            "is_over": len(over_list) > 0,
            "over_tasks": over_list
        }

    def subtask_split_helper_tool(self, total_days: int, main_desc: str) -> List[Dict]:
        """长周期任务拆分辅助工具，返回阶段描述"""
        chunk = total_days // 5
        res = []
        for i in range(5):
            res.append({"sub_desc": f"{main_desc} 阶段{i + 1}", "days": chunk})
        return res

    # ========== 格式化方法（用于返回字符串结果） ==========

    def _format_conflict_result(self, result: Dict) -> str:
        """格式化冲突检测结果"""
        if not result["has_conflict"]:
            return "✅ 没有检测到日程冲突"

        output = f"⚠️ 发现 {len(result['conflict_pairs'])} 个冲突：\n"
        for idx, conflict in enumerate(result['conflict_pairs'], 1):
            output += f"{idx}. {conflict['note']}\n"
        return output

    def _format_priority_result(self, result: List[Task]) -> str:
        """格式化优先级排序结果"""
        if not result:
            return "没有任务需要排序"

        output = "任务按优先级排序（高>中>低）：\n"
        for idx, task in enumerate(result, 1):
            output += f"{idx}. {task.task_name} (优先级: {task.priority}, 预计: {task.estimated_duration_min}分钟)\n"
        return output

    def _format_available_time_result(self, result: List[Tuple[str, str]]) -> str:
        """格式化可用时间段结果"""
        if not result:
            return "当天没有可用时间段"

        output = "当天可用时间段：\n"
        for idx, (start, end) in enumerate(result, 1):
            output += f"{idx}. {start} ~ {end}\n"
        return output

    def _format_duration_check_result(self, result: Dict) -> str:
        """格式化时长检查结果"""
        if not result["is_over"]:
            return "✅ 所有任务都在最大时长限制内"

        output = f"⚠️ 发现 {len(result['over_tasks'])} 个任务超过最大时长：\n"
        for idx, task in enumerate(result['over_tasks'], 1):
            output += f"{idx}. {task['task_name']}: {task['task_duration_time']}分钟\n"
        return output

    def _format_subtask_result(self, result: List[Dict]) -> str:
        """格式化子任务拆分结果"""
        if not result:
            return "无法拆分任务"

        output = "任务拆分阶段：\n"
        for idx, phase in enumerate(result, 1):
            output += f"{idx}. {phase['sub_desc']}: {phase['days']}天\n"
        return output