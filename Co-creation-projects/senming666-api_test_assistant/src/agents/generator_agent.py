"""
生成Agent - 负责生成测试用例

这是全项目唯一真正用到 LLM 的 Agent——
"该测什么、怎么测"这类需要理解和判断的活，交给大模型。
"""

import json
import re
from hello_agents import HelloAgentsLLM
from src.config import CASE_TYPES

class GeneratorAgent:
    """用 LLM 为接口智能生成测试用例"""

    def __init__(self):
        # HelloAgentsLLM() 自动从 .env 读取 LLM_MODEL_ID / LLM_API_KEY / LLM_BASE_URL
        self.llm = HelloAgentsLLM()

    def generate(self, endpoint):
        """为单个接口生成一组测试用例

        Args:
            endpoint: ParserAgent 提取出的接口字典，如
                {"path": "/users", "method": "GET", "responses": {...}}

        Returns:
            测试用例列表，每个用例是一个字典：
            [
                {
                    "name": "正常获取用户列表",
                    "case_type": "normal",
                    "params": {...},       # 查询参数
                    "body": {...},         # 请求体（GET 通常为空）
                    "expected_status": 200,
                },
                ...
            ]
        """
        prompt = self._build_prompt(endpoint)
        response = self.llm.invoke([{"role": "user", "content": prompt}])
        # 注意：1.0.0 的 invoke 返回 LLMResponse 对象，用 .content 拿文本
        test_cases = self._parse_response(response.content)

        # LLM 输出不可靠，可能返回非列表（dict/字符串），直接返回空列表兜底
        if not isinstance(test_cases, list):
            return []

        # 把 path 和 method 注入到每个用例里
        # （这些是确定性信息，直接从 endpoint 拿，不让 LLM 生成，避免拼错）
        # 顺便过滤掉非 dict 的异常元素，避免 case["path"] 报错
        cleaned = []
        for case in test_cases:
            if not isinstance(case, dict):
                continue
            case["path"] = endpoint["path"]
            case["method"] = endpoint["method"]
            cleaned.append(case)

        return cleaned

    def _build_prompt(self, endpoint):
        """构造提示词，让 LLM 输出结构化的测试用例"""
        prompt = f"""你是一个专业的 API 测试工程师。请为下面这个接口生成测试用例。

接口信息：
- 路径：{endpoint['path']}
- 方法：{endpoint['method']}
- 查询参数：{endpoint.get('parameters', [])}
- 请求体定义（POST/PUT 必须严格参照）：{endpoint.get('request_body')}
- 响应定义：{endpoint.get('responses', {})}

请为以下三类场景各生成 1 个测试用例（共 3 个）：
1. normal（正常场景）：传正确的参数和请求体，期待成功
2. boundary（边界场景）：参数或请求体字段取极端值，如空字符串、0、超长文本
3. error（异常场景）：缺必填参数或请求体字段、传错类型，期待报错

严格要求：
- 只输出一个 JSON 数组，不要有任何解释文字
- 数组里每个元素是一个对象，字段如下：
  "name"（用例名称）、"case_type"（normal/boundary/error）、
  "params"（查询参数对象，GET 用）、"body"（请求体对象，POST/PUT 用）、
  "expected_status"（期望的状态码数字）
- 若接口有"请求体定义"，body 的字段名必须与定义里 required 的字段完全一致，
  不得臆造或改名（这是最重要的要求）

输出示例：
[
  {{"name": "正常获取", "case_type": "normal", "params": {{}}, "body": {{}}, "expected_status": 200}},
  {{"name": "边界测试", "case_type": "boundary", "params": {{"page": 0}}, "body": {{}}, "expected_status": 200}},
  {{"name": "异常测试", "case_type": "error", "params": {{}}, "body": {{}}, "expected_status": 400}}
]

现在请输出 JSON 数组："""
        return prompt

    def _parse_response(self, response):
        """解析 LLM 返回的 JSON

        LLM 有时会在 JSON 外面加 ```json 标记或多余文字，
        所以要先清洗再解析。
        """
        # 提取第一个 [ 到最后一个 ] 之间的内容（JSON 数组）
        match = re.search(r"\[.*\]", response, re.DOTALL)
        if not match:
            return []

        json_text = match.group(0)

        try:
            test_cases = json.loads(json_text)
            return test_cases
        except json.JSONDecodeError:
            # 解析失败就返回空列表，不让整个程序崩溃
            return []
