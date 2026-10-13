"""Behavior tests for the learning loop without model or network calls."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.study_buddy.agents import HelloAgentsBackend, _normalize_quiz, _read_json
from src.study_buddy.core import StudyBuddy, validate_quiz
from src.study_buddy.demo import DemoBackend


WEAK = {"q1": "A", "q2": "C", "q3": "C", "q4": "加速度与合力同向", "q5": "合力 6 N 向右"}
STRONG = {"q1": "C", "q2": "B", "q3": "A",
          "q4": "合力变为两倍，加速度也变为两倍，方向与合力相同",
          "q5": "合力 8 N 向右；由 a=F/m 得加速度 2 m/s² 向右"}


class FailingSearchBackend(DemoBackend):
    def search(self, query):
        raise RuntimeError("network unavailable")


class FakeAgent:
    name = "测试诊断智能体"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.clears = 0

    def clear_history(self):
        self.clears += 1

    def run(self, prompt, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class StudyBuddyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.buddy = StudyBuddy(DemoBackend(), Path(self.temp.name))
        self.session = self.buddy.open("student", "物理", "牛顿第二定律")

    def test_diagnosis_plan_retest_and_persistence(self):
        first_quiz = self.buddy.begin_quiz(self.session)
        self.assertEqual(len(first_quiz), 5)
        first = self.buddy.submit(self.session, WEAK)
        self.assertEqual(first["mastery"]["受力分析"]["level"], "需要补基础")
        self.assertEqual(self.session["plan"][0]["id"], "forces")
        self.buddy.complete_task(self.session, "forces")
        restored = self.buddy.open("student", "物理", "牛顿第二定律")
        self.assertTrue(restored["plan"][0]["completed"])
        self.assertNotEqual(self.buddy.begin_quiz(restored)[0]["stem"], first_quiz[0]["stem"])
        second = self.buddy.submit(restored, STRONG)
        self.assertEqual(second["mastery"]["受力分析"]["level"], "掌握较好")
        self.assertNotEqual(restored["plan"][0]["id"], "forces")
        self.assertEqual(len(restored["rounds"]), 2)

    def test_incomplete_submission_does_not_change_progress(self):
        self.buddy.begin_quiz(self.session)
        with self.assertRaises(ValueError):
            self.buddy.submit(self.session, {"q1": "B"})
        self.assertEqual(self.session["rounds"], [])
        self.assertIsNotNone(self.session["pending_quiz"])

    def test_search_failure_keeps_plan(self):
        buddy = StudyBuddy(FailingSearchBackend(), Path(self.temp.name))
        session = buddy.open("student", "物理", "牛顿第二定律")
        buddy.begin_quiz(session)
        buddy.submit(session, WEAK)
        self.assertTrue(session["plan"])
        self.assertTrue(any("资源搜索暂不可用" in x for x in session["notices"]))

    def test_free_topic_and_subject_boundary(self):
        free = self.buddy.open("student", "物理", "电磁感应", "高二")
        self.assertFalse(free["reviewed_topic"])
        with self.assertRaises(ValueError):
            self.buddy.open("student", "化学", "化学反应速率")

    def test_invalid_generated_quiz(self):
        with self.assertRaises(ValueError):
            validate_quiz([{"id": "q1", "type": "choice"}])
        self.assertEqual(_read_json('```json\n{"grading":{"score":2}}\n```')["grading"]["score"], 2)

    def test_model_list_options_are_normalized_and_invalid_labels_rejected(self):
        quiz = copy.deepcopy(self.buddy.begin_quiz(self.session))
        quiz[0]["options"] = [f"{letter}. {text}" for letter, text in quiz[0]["options"].items()]
        quiz[1]["options"] = list(quiz[1]["options"].values())
        _normalize_quiz(quiz)
        self.assertEqual(set(quiz[0]["options"]), set("ABCD"))
        self.assertEqual(quiz[1]["options"]["C"], "3 m/s²")
        quiz[0]["options"] = ["A. a", "A. b", "C. c", "D. d"]
        with self.assertRaisesRegex(ValueError, "重复"):
            _normalize_quiz(quiz)

    def test_structured_call_retries_bad_json_with_clean_history(self):
        quiz = copy.deepcopy(self.buddy.begin_quiz(self.session))
        quiz[0]["options"] = list(quiz[0]["options"].values())
        agent = FakeAgent(['{"questions":', json.dumps({"questions": quiz}, ensure_ascii=False)])
        backend = object.__new__(HelloAgentsBackend)
        with patch.dict("os.environ", {"LLM_BASE_URL": "https://api.deepseek.com"}):
            normalized = backend._json_call(agent, "请返回 JSON", "questions", _normalize_quiz)
        self.assertEqual(len(normalized), 5)
        self.assertEqual(set(normalized[0]["options"]), set("ABCD"))
        self.assertEqual(agent.clears, 2)
        self.assertEqual(agent.calls[0]["response_format"], {"type": "json_object"})
        self.assertEqual(agent.calls[0]["extra_body"], {"reasoning_effort": "low"})

    def test_other_provider_does_not_receive_deepseek_parameters(self):
        agent = FakeAgent(['{"grading":{"score":2,"feedback":"完整"}}'])
        backend = object.__new__(HelloAgentsBackend)
        with patch.dict("os.environ", {"LLM_BASE_URL": "https://other-provider.example/v1"}):
            result = backend._json_call(agent, "请返回 JSON", "grading")
        self.assertEqual(result["score"], 2)
        self.assertEqual(agent.calls, [{}])

    def test_invalid_model_quiz_does_not_create_pending_attempt(self):
        class InvalidQuizBackend(DemoBackend):
            def make_quiz(self, context):
                quiz = super().make_quiz(context)
                quiz[0]["options"] = ["A", "B", "C"]
                return quiz

        buddy = StudyBuddy(InvalidQuizBackend(), Path(self.temp.name))
        with self.assertRaises(ValueError):
            buddy.begin_quiz(self.session)
        restored = buddy.open("student", "物理", "牛顿第二定律")
        self.assertIsNone(restored["pending_quiz"])


if __name__ == "__main__":
    unittest.main()
