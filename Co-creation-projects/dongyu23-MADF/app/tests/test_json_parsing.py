import unittest
from utils import parse_json_from_response

class TestJsonParsing(unittest.TestCase):
    def test_unescaped_quotes(self):
        # This JSON is invalid because of quotes around "情境认知教育基金会" inside the string
        invalid_json = """
        [
            {
                "name": "Test",
                "bio": "He founded the "Foundation" successfully."
            }
        ]
        """
        result = parse_json_from_response(invalid_json)
        self.assertIsNone(result)
        
    def test_valid_json(self):
        valid_json = '[{"name": "Test"}]'
        result = parse_json_from_response(valid_json)
        self.assertEqual(result[0]['name'], "Test")

if __name__ == '__main__':
    unittest.main()
