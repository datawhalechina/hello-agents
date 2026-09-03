"""
生成Agent - 负责生成测试用例

这是全项目唯一真正用到 LLM 的 Agent——
"该传什么值、字段怎么填"这类需要理解和判断的活，交给大模型。

但有几件事不能交给 LLM，因为它们有明确对错：
- 生成哪些类型的用例（normal/boundary/error），要看接口有没有可测输入；
- 期望状态码，要按文档的 responses 和用例类型确定；
- 期望响应 schema，要按状态码从文档里取。

这些都由 ParserAgent 的确定性方法算出，LLM 只负责填充 params/body 的具体值。
"""

import json
import re
import base64
from hello_agents import HelloAgentsLLM
from src.config import CASE_TYPES, MINIMAL_PNG_BASE64
from src.agents.parser_agent import ParserAgent


class GeneratorAgent:
    """用 LLM 为接口智能生成测试用例"""

    def __init__(self):
        # HelloAgentsLLM() 自动从 .env 读取 LLM_MODEL_ID / LLM_API_KEY / LLM_BASE_URL
        self.llm = HelloAgentsLLM()
        # 复用 ParserAgent 的确定性方法（判状态码 / 取响应 schema）
        self.parser = ParserAgent()

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
                    "params": {...},        # 查询参数（含路径参数值）
                    "body": {...},          # 请求体
                    "expected_status": 200, # 由文档确定，非 LLM 生成
                    "expected_schema": {...}, # 由文档确定
                    "content_type": "...",  # 请求体媒体类型
                },
                ...
            ]
        """
        # 先确定要生成哪些类型的用例，不能机械地每个接口都生成 3 条
        case_types = self._decide_case_types(endpoint)
        prompt = self._build_prompt(endpoint, case_types)
        response = self.llm.invoke([{"role": "user", "content": prompt}])
        # 注意：1.0.0 的 invoke 返回 LLMResponse 对象，用 .content 拿文本
        test_cases = self._parse_response(response.content)

        # LLM 输出不可靠，可能返回非列表（dict/字符串），直接返回空列表兜底
        if not isinstance(test_cases, list):
            return []

        # 逐个规范化：注入确定性字段，覆盖 LLM 不可靠的输出
        cleaned = []
        for case in test_cases:
            if not isinstance(case, dict):
                continue
            cleaned.append(self._normalize_case(case, endpoint))

        return cleaned

    def _decide_case_types(self, endpoint):
        """根据接口结构决定生成哪些类型的用例

        - normal：永远生成
        - boundary：有可测试输入（query 参数或请求体）才生成
        - error：有必填输入（必填 query/请求体/路径参数）才生成

        像 GET /api/health 这种没参数没请求体的接口，只生成 normal 一条，
        避免硬凑"非法参数"用例，结果实际返回 200 却被判成失败。
        """
        types = ["normal"]
        if self.parser.has_testable_inputs(endpoint):
            types.append("boundary")
        if (self.parser.has_validation_input(endpoint)
                or self.parser.has_required_path_param(endpoint)):
            types.append("error")
        return types

    def _normalize_case(self, case, endpoint):
        """规范化单个用例：注入确定性的字段，修正 LLM 的不可靠输出

        Args:
            case: LLM 生成的单个用例
            endpoint: 接口字典

        Returns:
            规范化后的用例
        """
        # 用例类型只在固定集合里取值，非法值回退 normal
        case_type = case.get("case_type")
        if case_type not in CASE_TYPES:
            case_type = "normal"

        case["case_type"] = case_type
        case["path"] = endpoint["path"]
        case["method"] = endpoint["method"]
        case["content_type"] = endpoint.get("request_content_type") or "application/json"

        # 期望状态码由文档 + 用例类型确定，不信任 LLM 填的值
        case["expected_status"] = self.parser.get_expected_status(endpoint, case_type)
        # 期望响应 schema 同样由文档确定，$ref 已在解析时展开
        case["expected_schema"] = self.parser.get_response_schema(
            endpoint, case["expected_status"]
        )

        # body 统一成 dict，方便后面做 multipart 拆分
        body = case.get("body")
        if not isinstance(body, dict):
            body = {}
            case["body"] = body

        # multipart 文件上传：把文件字段从 body 拆到 files，其余字段留在 body
        if "multipart" in case["content_type"].lower():
            case["files"] = self._build_files(endpoint, body)

        return case

    def _build_files(self, endpoint, body):
        """为 multipart 上传生成 files 参数

        OpenAPI 里文件字段用 contentMediaType 或 format=binary 标识，
        这类字段要作为文件上传（files），不能作为普通表单字段（data）。
        文件内容用最小合法 PNG 占位，保证能通过后端的内容校验。

        Args:
            endpoint: 接口字典
            body: 请求体（dict，会被就地修改：文件字段被弹出）

        Returns:
            files 字典 {"字段名": ("文件名", 字节内容, "MIME")}；没有文件字段返回 None
        """
        schema = endpoint.get("request_body")
        if not isinstance(schema, dict):
            return None

        properties = schema.get("properties") or {}
        files = {}
        for field, field_schema in properties.items():
            if not isinstance(field_schema, dict):
                continue
            is_file = (
                "contentMediaType" in field_schema
                or field_schema.get("format") == "binary"
            )
            if not is_file or field not in body:
                continue
            body.pop(field)
            # 占位内容固定是 PNG，文件名也强制 .png 后缀，
            # 保证「扩展名 ↔ MIME ↔ 文件头」三者一致，否则后端校验会 415
            files[field] = (
                f"{field}.png",
                base64.b64decode(MINIMAL_PNG_BASE64),
                "image/png",
            )
        return files or None

    def _build_prompt(self, endpoint, case_types):
        """构造提示词，让 LLM 输出结构化的测试用例"""
        case_desc = self._describe_case_types(endpoint, case_types)
        prompt = f"""你是一个专业的 API 测试工程师。请为下面这个接口生成测试用例。

接口信息：
- 路径：{endpoint['path']}
- 方法：{endpoint['method']}
- 路径/查询参数定义：{endpoint.get('parameters', [])}
- 请求体定义（POST/PUT/PATCH 必须严格参照）：{endpoint.get('request_body')}
- 响应定义：{endpoint.get('responses', {})}

{case_desc}

严格要求：
- 只输出一个 JSON 数组，不要有任何解释文字
- 数组里每个元素是一个对象，字段如下：
  "name"（用例名称）、"case_type"（normal/boundary/error）、
  "params"（查询参数和路径参数对象）、"body"（请求体对象）、
  "expected_status"（期望状态码数字，可随便填，后端会按文档覆盖）
- 若接口有"请求体定义"，body 的字段名必须与定义里 required 的字段完全一致，
  不得臆造或改名（这是最重要的要求）
- 路径参数（如 path 里的 {{friendship_id}}）的值也放在 params 里，用和字段名相同的键
- 字符串字段取值要满足定义里的 minLength/maxLength/pattern 约束；
  用户名这类要求唯一的字段，用带随机后缀的值（如 user_12345）
- 语义上要求互相一致的字段（如 password 和 confirm_password 这种两次输入）要填成相同的值

现在请输出 JSON 数组："""
        return prompt

    def _describe_case_types(self, endpoint, case_types):
        """把要生成的用例类型描述成给 LLM 的自然语言要求"""
        lines = ["请为以下场景各生成 1 个测试用例："]
        for ct in case_types:
            if ct == "normal":
                lines.append("- normal（正常）：传正确参数和请求体，期待成功（2xx）")
            elif ct == "boundary":
                lines.append(
                    "- boundary（边界）：参数/字段取刚好满足约束的边界值"
                    "（如字符串长度恰好等于 minLength 或 maxLength），仍期待成功（2xx）"
                )
            elif ct == "error":
                if self.parser.has_validation_input(endpoint):
                    lines.append(
                        "- error（异常）：缺少某个必填的请求体字段，或查询参数传错类型，"
                        "期待 4xx（校验失败）"
                    )
                else:
                    # 只有必填路径参数时，缺路径参数导致路由不匹配
                    lines.append(
                        "- error（异常）：params 里不填路径参数（保持缺省），期待 404"
                    )
        return "\n".join(lines)

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
