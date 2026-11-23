"""Deterministic test fixtures, never imported by production code."""
from copy import deepcopy
from src.config import AppError
from src.prompts import BRIEF_KEYS

BRIEF = {**dict.fromkeys(BRIEF_KEYS, ""), "title": "测试用待办工具", "target_users": "个人开发者",
         "problem": "忘记重要任务", "core_features": "新增任务、查看任务", "exclusions": "不做支付", "constraints": "本地运行"}


class ModelDouble:
    def __init__(self):
        self.calls = []
        self.fail = None
        self.conflicts = []
        self.invalid_source = False

    def run(self, role, context):
        self.calls.append((role, deepcopy(context)))
        if self.fail == role:
            raise AppError("测试注入：模型暂时不可用", 502)
        if role == "interview":
            return {"brief": deepcopy(BRIEF), "reply": "已整理你的回答。", "question": "任务主要在什么时候添加？",
                    "options": ["工作时", "下班后"], "ready": False, "assumptions": ["成功标准尚未确定"]}
        if role == "research":
            return {"competitors": [{"name": "仅用于测试的来源条目", "positioning": "测试定位", "features": "测试功能",
                                     "difference": "测试局限", "source_ids": ["S99" if self.invalid_source else "S1"]}], "summary": "测试摘要"}
        if role == "assess":
            return {"verdict": "可先做原型", "reason": "测试判断", "technical_path": ["先做本地版本"],
                    "dependencies": [], "risks": ["用户需求待验证"], "validation_steps": ["邀请用户试用"]}
        if role == "writer":
            return {"user_stories": ["作为用户希望记录任务"], "requirements": [{"name": "新增任务",
                    "description": "输入任务名称后保存", "acceptance": "保存后能在任务列表看到同名任务"}],
                    "nonfunctional": [], "milestones": ["先完成添加与列表"], "open_questions": ["是否需要截止时间？"]}
        if role == "audit":
            return {"conflicts": self.conflicts}
        raise AssertionError(role)


class SearchDouble:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def search(self, query):
        self.calls.append(query)
        if self.fail:
            raise AppError("测试注入：搜索失败", 502)
        return [{"id": "S1", "title": "测试页面", "url": "https://example.com/test-only",
                 "content": "仅用于自动化测试的摘录", "retrieved_at": "2026-01-01T00:00:00+00:00"}]
