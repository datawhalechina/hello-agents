"""Offline Newton's second law scenario for reproducible demonstrations."""

from __future__ import annotations

from typing import Any


def _question_bank(round_number: int) -> list[dict[str, Any]]:
    if round_number == 1:
        return [
            {"id": "q1", "type": "choice", "skill": "受力分析",
             "stem": "物体沿水平面做匀速直线运动，它受到的合力是？",
             "options": {"A": "等于重力", "B": "等于零", "C": "沿运动方向", "D": "与速度方向相反"},
             "correct_answer": "B", "explanation": "匀速直线运动时加速度为零，故合力为零。"},
            {"id": "q2", "type": "choice", "skill": "公式应用",
             "stem": "质量 2 kg 的物体受到 6 N 的合力，加速度大小为多少？",
             "options": {"A": "0.33 m/s²", "B": "2 m/s²", "C": "3 m/s²", "D": "12 m/s²"},
             "correct_answer": "C", "explanation": "a=F合/m=6/2=3 m/s²。"},
            {"id": "q3", "type": "choice", "skill": "受力分析",
             "stem": "质量 2 kg 的物体受 10 N 向右与 4 N 向左的水平力，水平面光滑，加速度是？",
             "options": {"A": "7 m/s² 向右", "B": "3 m/s² 向右", "C": "3 m/s² 向左", "D": "5 m/s² 向右"},
             "correct_answer": "B", "explanation": "合力 6 N 向右，a=6/2=3 m/s² 向右。"},
            {"id": "q4", "type": "short", "skill": "规律理解",
             "stem": "在质量不变时，合力大小与加速度大小有什么关系？加速度的方向由什么决定？",
             "rubric": ["说明加速度大小与合力大小成正比", "说明加速度方向与合力方向相同"],
             "explanation": "F合=ma，质量固定时 a 与 F合成正比，方向相同。"},
            {"id": "q5", "type": "short", "skill": "公式应用",
             "stem": "质量 2 kg 的物体放在光滑水平面，受到 6 N 水平向右的拉力。写出水平方向的合力和加速度（含方向）。",
             "rubric": ["写出水平合力为 6 N 向右", "算出加速度为 3 m/s² 向右"],
             "explanation": "水平方向只有拉力，F合=6 N 向右，a=F合/m=3 m/s² 向右。"},
        ]
    return [
        {"id": "q1", "type": "choice", "skill": "受力分析",
         "stem": "物体沿直线运动且速度不断增大。下列哪项一定正确？",
         "options": {"A": "合力为零", "B": "加速度为零", "C": "合力不为零", "D": "物体只受一个力"},
         "correct_answer": "C", "explanation": "速度大小改变意味着加速度不为零，因此合力不为零。"},
        {"id": "q2", "type": "choice", "skill": "公式应用",
         "stem": "质量 4 kg 的物体受到 8 N 的合力，加速度大小为多少？",
         "options": {"A": "0.5 m/s²", "B": "2 m/s²", "C": "4 m/s²", "D": "32 m/s²"},
         "correct_answer": "B", "explanation": "a=8/4=2 m/s²。"},
        {"id": "q3", "type": "choice", "skill": "受力分析",
         "stem": "质量 3 kg 的物体受 12 N 向右和 3 N 向左的水平力，水平面光滑，加速度是？",
         "options": {"A": "3 m/s² 向右", "B": "5 m/s² 向右", "C": "3 m/s² 向左", "D": "4 m/s² 向右"},
         "correct_answer": "A", "explanation": "合力 9 N 向右，a=9/3=3 m/s² 向右。"},
        {"id": "q4", "type": "short", "skill": "规律理解",
         "stem": "若物体质量不变，合力增为原来的 2 倍，加速度大小与方向怎样变化？",
         "rubric": ["说明加速度大小变为原来 2 倍", "说明加速度方向仍与合力方向相同"],
         "explanation": "a=F合/m，因此加速度大小翻倍，方向始终与合力相同。"},
        {"id": "q5", "type": "short", "skill": "公式应用",
         "stem": "质量 4 kg 的物体在光滑水平面上受 8 N 向右的拉力。写出合力和加速度（含方向）。",
         "rubric": ["写出水平合力为 8 N 向右", "算出加速度为 2 m/s² 向右"],
         "explanation": "F合=8 N 向右，a=8/4=2 m/s² 向右。"},
    ]


class DemoBackend:
    """Fixed content; simple keyword grading is intentionally demonstration only."""

    def make_quiz(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        if context["topic"] != "牛顿第二定律":
            raise ValueError("离线演示仅支持牛顿第二定律；其他知识点请配置模型")
        return _question_bank(context["round_number"])

    def grade_short(self, question: dict[str, Any], answer: str) -> dict[str, Any]:
        text = answer.lower().replace(" ", "")
        if question["id"] == "q4":
            first = ("正比" in text or "2倍" in text or "两倍" in text)
            second = "同向" in text or "相同" in text or "一致" in text
        else:
            number = "6" if "6 N" in question["stem"] else "8"
            acceleration = "3" if number == "6" else "2"
            first = number in text and ("合力" in text or "净力" in text) and "右" in text
            second = acceleration in text and ("加速度" in text or "a=" in text) and "右" in text
        score = int(first) + int(second)
        missing = [rubric for matched, rubric in zip((first, second), question["rubric"]) if not matched]
        feedback = "已体现两个评分要点。" if not missing else "仍需说明：" + "；".join(missing)
        return {"score": score, "feedback": feedback + "（离线演示采用简化判分）"}

    def make_plan(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        weak = [skill for skill, item in context["mastery"].items() if item["level"] != "掌握较好"]
        tasks = []
        if "受力分析" in weak:
            tasks.append({"id": "forces", "title": "补习合力与受力分析", "why": "受力分析诊断题仍有失分。",
                          "minutes": 20, "done_when": "能标出水平作用力并求出合力大小与方向",
                          "resource_query": "高中物理 牛顿第二定律 受力分析 合力 讲解"})
        focus = "、".join(weak) if weak else "综合应用"
        tasks.append({"id": "concept", "title": "梳理牛顿第二定律与" + focus,
                      "why": "根据本轮掌握情况巩固相关能力。", "minutes": 20,
                      "done_when": "能解释 F合=ma 中各量和方向的含义",
                      "resource_query": "高中物理 牛顿第二定律 教学 例题"})
        tasks.append({"id": "practice", "title": "完成针对性练习", "why": "用新情境检验理解。",
                      "minutes": 25, "done_when": "独立完成 3 道合力与加速度题并核对单位和方向",
                      "resource_query": "高中物理 牛顿第二定律 练习题 解析"})
        tasks.append({"id": "review", "title": "回顾错因并复测", "why": "检查学习后是否有进步。",
                      "minutes": 15, "done_when": "完成下一轮五题复测并比较能力点结果",
                      "resource_query": ""})
        return tasks

    def answer(self, context: dict[str, Any], question: str) -> str:
        return ("离线演示提示：先确定研究对象和各力的方向，求合力，再用 F合=ma 求加速度。"
                "如需针对具体问题的多轮答疑，请配置模型运行。")

    def search(self, query: str) -> list[dict[str, str]]:
        return []
