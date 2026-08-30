import os
import sys
import types
import unittest


dotenv = types.ModuleType("dotenv")
dotenv.load_dotenv = lambda: None
sys.modules["dotenv"] = dotenv


class FakeSerpApiClient:
    response = {}

    def __init__(self, params):
        self.params = params

    def get_dict(self):
        return self.response


serpapi = types.ModuleType("serpapi")
serpapi.SerpApiClient = FakeSerpApiClient
sys.modules["serpapi"] = serpapi

from tools import search  # noqa: E402


class SearchAnswerBoxListTest(unittest.TestCase):
    def setUp(self):
        os.environ["SERPAPI_API_KEY"] = "test-key"

    def tearDown(self):
        os.environ.pop("SERPAPI_API_KEY", None)

    def test_extracts_answers_from_answer_box_objects(self):
        FakeSerpApiClient.response = {
            "answer_box_list": [
                {"answer": "first answer"},
                {"answer": "second answer"},
            ]
        }

        self.assertEqual(search("query"), "first answer\nsecond answer")

    def test_falls_back_when_list_has_no_text_answer(self):
        FakeSerpApiClient.response = {
            "answer_box_list": [{"title": "answer without text"}, None],
            "answer_box": {"answer": "fallback answer"},
        }

        self.assertEqual(search("query"), "fallback answer")


if __name__ == "__main__":
    unittest.main()
