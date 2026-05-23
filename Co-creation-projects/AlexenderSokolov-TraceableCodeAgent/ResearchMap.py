from __future__ import annotations

import json

from ResearchStep import ResearchStep, step_to_dict, dict_to_step
class ResearchMap:
    def __init__(self):
        self.steps: dict[str, ResearchStep] = {}  # step_id -> ResearchStep
        self.adjacency_list: dict[str, list[str]] = {}  #邻接表
        self.root_step_id: str = ""  #根节点

    def add_step(self, step: ResearchStep) -> None:
        self.steps[step.step_id] = step
        if step.parent_step_id not in self.adjacency_list:
            self.adjacency_list[step.parent_step_id] = []
        self.adjacency_list[step.parent_step_id].append(step.step_id)
        if not self.root_step_id:
            self.root_step_id = step.step_id

    def get_step(self, step_id: str) -> ResearchStep | None:
        return self.steps.get(step_id)

    def get_children_steps(self, step_id: str) -> list[ResearchStep]:
        return [self.steps[child_id] for child_id in self.adjacency_list.get(step_id, [])]

    def get_traceback_path(self, step_id: str) -> list[ResearchStep]:
        """回溯从根节点到当前步骤的完整路径"""
        path = []
        current_id = step_id
        while current_id:
            step = self.steps.get(current_id)
            if not step:
                break
            path.append(step)
            current_id = step.parent_step_id
        return list(reversed(path))
    
    @classmethod
    def save(cls, research_map: ResearchMap, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "steps": {step_id: step_to_dict(step) for step_id, step in research_map.steps.items()},
                "adjacency_list": research_map.adjacency_list,
                "root_step_id": research_map.root_step_id,
            }, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, path: str) -> ResearchMap:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            research_map = ResearchMap()
            research_map.steps = {step_id: dict_to_step(step_data) for step_id, step_data in data.get("steps", {}).items()}
            research_map.adjacency_list = data.get("adjacency_list", {})
            research_map.root_step_id = data.get("root_step_id", "")
            return research_map


