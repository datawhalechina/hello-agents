"""HelloAgents streaming adapter; the application owns task lifecycle and tool policy."""
from __future__ import annotations

import asyncio
import json
import re
import threading
from urllib.parse import urlparse

from .analysis_documents import ANALYSIS_SKILL


def tool_messages(messages: list[dict]) -> list[dict]:
    """Use actual persisted call IDs only when paired with a real observation."""
    result, index = [], 0
    while index < len(messages):
        item = messages[index]
        following = messages[index + 1] if index + 1 < len(messages) else None
        calls = item.get("tool_calls")
        if item["role"] == "assistant" and calls and following and following["role"] == "user" and following["content"].startswith("工具观察："):
            observation = following["content"][len("工具观察："):]
            paired = None
            if len(calls) == 1:
                paired = [{"role": "tool", "tool_call_id": calls[0]["id"], "content": observation}]
            else:
                try:
                    values = json.loads(observation)["tool_results"]
                    if [value["tool_call_id"] for value in values] == [call["id"] for call in calls]:
                        paired = [{"role": "tool", "tool_call_id": value["tool_call_id"],
                                   "content": json.dumps(value["result"], ensure_ascii=False)} for value in values]
                except (ValueError, KeyError, TypeError):
                    pass
            if paired:
                result.append({"role": "assistant", "content": None, "tool_calls": calls})
                result.extend(paired)
                index += 2
                continue
            # Never send a native assistant batch with missing tool results.
            result.append({"role": item["role"], "content": item["content"]})
            index += 1
        else:
            result.append({"role": item["role"], "content": item["content"]})
            index += 1
    return result


def documentation_schema() -> dict:
    label = {"type": "string", "minLength": 1, "maxLength": 80}
    name = {"type": "string", "minLength": 1, "maxLength": 40}
    node = {"type": "object", "properties": {"id": name, "label": label,
        "level": {"type": "integer", "minimum": 0, "maximum": 8},
        "kind": {"type": "string", "enum": ["process", "decision"]}},
        "required": ["id", "label"], "additionalProperties": False}
    edge = {"type": "object", "properties": {"from": name, "to": name, "label": {"type": "string", "maxLength": 50}},
            "required": ["from", "to"], "additionalProperties": False}
    graph = {"type": "object", "properties": {"title": label,
        "description": {"type": "string", "minLength": 1, "maxLength": 2000},
        "nodes": {"type": "array", "items": node, "minItems": 1, "maxItems": 14},
        "edges": {"type": "array", "items": edge, "maxItems": 24}},
        "required": ["title", "description", "nodes", "edges"], "additionalProperties": False}
    message = {"type": "object", "properties": {"from": name, "to": name, "label": {"type": "string", "minLength": 1, "maxLength": 100},
        "dashed": {"type": "boolean"}}, "required": ["from", "to", "label"], "additionalProperties": False}
    sequence = {"type": "object", "properties": {"title": label,
        "description": {"type": "string", "minLength": 1, "maxLength": 2000},
        "participants": {"type": "array", "items": {"type": "object", "properties": {"id": name, "label": {"type": "string", "minLength": 1, "maxLength": 50}},
            "required": ["id", "label"], "additionalProperties": False}, "minItems": 2, "maxItems": 7},
        "messages": {"type": "array", "items": message, "minItems": 1, "maxItems": 20}},
        "required": ["title", "description", "participants", "messages"], "additionalProperties": False}
    return {"type": "object", "properties": {"architecture": graph, "workflow": graph, "sequence": sequence},
            "required": ["architecture", "workflow", "sequence"], "additionalProperties": False}


def action_tool(unit: dict | None = None, *, analysis_mode: bool = False, analysis_phase: str | None = None) -> dict:
    if analysis_mode and analysis_phase in {"draft", "complete"}:
        properties = ({"overview": {"type": "string", "minLength": 1, "maxLength": 20000},
                       "diagrams": documentation_schema()}
                      if analysis_phase == "draft" else {"message": {"type": "string", "minLength": 1}})
        action = "propose_documentation" if analysis_phase == "draft" else "final"
        return {"type": "function", "function": {
            "name": "submit_action",
            "description": ("可用代码材料已经准备，未覆盖文件见unavailable。直接提交完整中文项目说明和架构/流程/时序图结构，客户端校验后自动应用。"
                            if analysis_phase == "draft" else "五个交付文件已经实际应用。直接提交完成说明。"),
            "parameters": {"type": "object", "properties": {
                "action": {"type": "string", "enum": [action]},
                "args": {"type": "object", "properties": properties, "required": list(properties),
                         "additionalProperties": False},
                "summary": {"type": "string", "description": "简短中文进度说明。"}},
                "required": ["action", "args", "summary"], "additionalProperties": False}}}
    if unit:
        fields = (["purpose", "input_files", "inputs", "output_files", "outputs"]
                  if unit.get("kind") == "header" else ["purpose", "inputs", "outputs"])
        return {"type": "function", "function": {
            "name": "submit_action", "description": "为当前源码单元提交中文注释草稿，不修改任何代码。",
            "parameters": {"type": "object", "properties": {
                "action": {"type": "string", "enum": ["annotate_unit"]},
                "args": {"type": "object", "properties": {
                    "path": {"type": "string", "enum": [unit["path"]]},
                    "base_hash": {"type": "string", "enum": [unit["base_hash"]]},
                    "target_id": {"type": "string", "enum": [unit["target_id"]]},
                    "documentation": {"type": "object", "properties": {
                        field: {"type": "string", "minLength": 1, "maxLength": 4000}
                        for field in fields}, "required": fields, "additionalProperties": False}},
                    "required": ["path", "base_hash", "target_id", "documentation"], "additionalProperties": False},
                "summary": {"type": "string", "description": "简短中文进度说明。"}},
                "required": ["action", "args", "summary"], "additionalProperties": False}}}
    # Describe nested patch fields too; an unconstrained args object encouraged
    # missing paths even though the outer function call was valid JSON.
    edit = {"type": "object", "properties": {
        "old": {"type": "string", "description": "从真实 read 复制的唯一原文，保留每一行缩进与 CRLF/LF，不得省略方法注释前的空格。"},
        "new": {"type": "string", "description": "替换文本；保留原有代码和逐行缩进，只添加或更新注释。"}},
            "required": ["old", "new"], "additionalProperties": False}
    change = {"type": "object", "properties": {
        "path": {"type": "string", "description": "必填，工作区相对文件路径，每一项都不能省略。"},
        "base_hash": {"type": "string", "description": "必填，真实 read 返回的 hash，新文件为 missing。"},
        "content": {"type": ["string", "null"], "description": "完整候选文本，删除为 null；与 edits 二选一。"},
        "edits": {"type": "array", "items": edit, "minItems": 1,
                  "description": "局部替换列表，与 content 二选一；old 必须与原文唯一精确匹配。"}},
        "required": ["path", "base_hash"], "additionalProperties": False}
    args = {"type": "object", "properties": {
        "path": {"type": "string", "description": "工作区相对路径；list 根目录用空字符串或 .，read 必须填写具体文件路径。"},
        "query": {"type": "string", "description": "search 的字面搜索内容。"},
        "offset": {"type": "integer", "minimum": 0, "description": "inventory 的分页偏移。"},
        "start_line": {"type": "integer", "minimum": 1, "description": "read 的起始行（从1开始）；长文件可按 next_start_line 继续读取。"},
        "end_line": {"type": "integer", "minimum": 1, "description": "read 可选结束行；实际范围以工具返回为准。"},
        "force": {"type": "boolean", "description": "read 显式重新读取已经校验完成的文件，用于核对实际源码。"},
        "changes": {"type": "array", "items": change, "minItems": 1, "maxItems": 5,
                    "description": "propose_patch 必填，每个文件都需要 path/base_hash，以及 content 或 edits。"},
        "message": {"type": "string", "description": "final 必填，面向用户的最终说明。"}},
        "additionalProperties": False,
        "description": "使用动作对应字段；read 必填 path，search 必填 query，propose_patch 必填 changes，final 必填 message。"}
    allowed_actions = ACTIONS - {"annotate_unit", "propose_documentation", "read_batch"}
    if analysis_mode:
        args["properties"].update({
            "overview": {"type": "string", "minLength": 1, "maxLength": 20000,
                         "description": "基于真实代码的中文项目说明Markdown，采用约定章节；客户端自动添加三张PNG设计图链接。"},
            "diagrams": documentation_schema()})
        args["description"] = "读取和检索源码后，用propose_documentation只提交overview/diagrams；文件版本由客户端管理。文档包校验后自动应用，收到真实结果后才final。不调用test或propose_patch。"
        allowed_actions = {"list", "read", "search", "git_diff", "inventory", "propose_documentation", "final"}
    return {"type": "function", "function": {
        "name": "submit_action", "description": "提交一个客户端动作，然后等待真实工具结果；不得模拟执行。",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string", "enum": sorted(allowed_actions)},
            "args": args,
            "summary": {"type": "string", "description": "简短中文进度说明。"}},
            "required": ["action", "args", "summary"], "additionalProperties": False}}}


class HelloModel:
    def __init__(self, settings, key: str):
        if not settings["model"] or not settings["base_url"]:
            raise ValueError("请先在模型设置中填写模型名称和 API 地址。")
        if not key and urlparse(settings["base_url"]).hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("请先设置模型 API Key。")
        from hello_agents import HelloAgentsLLM
        from openai import OpenAI
        import httpx
        local = urlparse(settings["base_url"]).hostname in {"localhost", "127.0.0.1", "::1"}

        class TransportLLM(HelloAgentsLLM):
            def _create_client(self):
                # Loopback services must bypass Windows system proxies as well.
                return OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout,
                              max_retries=0, http_client=httpx.Client(trust_env=not local, timeout=self.timeout))

            def think(self, messages, temperature=None):
                self.last_tool_call = None
                self.last_tool_calls = []
                self.batch_action = None
                self.response_action = None
                from openai import BadRequestError
                options = {}
                if urlparse(self.base_url).hostname == "api.deepseek.com":
                    options["extra_body"] = {"thinking": {"type": "disabled"}}
                schema = action_tool(getattr(self, "annotation_unit", None),
                                     analysis_mode=getattr(self, "analysis_mode", False),
                                     analysis_phase=getattr(self, "analysis_phase", None))
                tool_name = schema["function"]["name"]
                try:
                    stream = self._client.chat.completions.create(
                        model=self.model, messages=tool_messages(messages),
                        temperature=self.temperature if temperature is None else temperature,
                        max_tokens=self.max_tokens, stream=True,
                        parallel_tool_calls=False,
                        tools=[schema],
                        tool_choice={"type": "function", "function": {"name": tool_name}},
                        **options)
                except BadRequestError as exc:
                    if any(name in str(exc) for name in ("tools", "tool_choice", "function")):
                        raise ValueError("模型服务拒绝原生工具调用，请检查服务是否支持 tools/tool_choice。") from exc
                    raise
                calls, text, size = {}, [], 0
                with stream:
                    for chunk in stream:
                        if not chunk.choices:
                            continue
                        choice = chunk.choices[0]
                        if choice.delta.content:
                            text.append(choice.delta.content)
                            size += len(choice.delta.content)
                        for part in choice.delta.tool_calls or []:
                            if type(part.index) is not int or part.index < 0:
                                raise ModelProtocolError("原生工具调用缺少有效索引。", [{"code": "invalid_index", "expected_tool": tool_name}])
                            call = calls.setdefault(part.index, {"id": "", "name": "", "arguments": "", "name_parts": [], "id_parts": 0})
                            call["id"] = merge_tool_metadata(call["id"], part.id or "")
                            if part.id:
                                call["id_parts"] += 1
                            if part.function:
                                name_part = part.function.name or ""
                                call["name"] = merge_tool_metadata(call["name"], name_part)
                                if name_part and len(call["name_parts"]) < 6:
                                    call["name_parts"].append(name_part[:80])
                                value = part.function.arguments or ""
                                call["arguments"] += value
                                size += len(value)
                                if value:
                                    yield value
                        if size > 60_000:
                            raise ActionFormatError("模型单轮响应超过大小限制，请减小补丁。")
                        if choice.finish_reason == "length":
                            raise ModelOutputTruncated("模型输出达到 token 或上下文长度上限，被截断；本轮补丁未执行。")
                        if choice.finish_reason not in {None, "stop", "tool_calls"}:
                            raise ActionFormatError(f"模型生成未正常结束（{choice.finish_reason}），本轮动作未执行。")
                if calls:
                    if len(calls) != 1 and not getattr(self, "analysis_mode", False):
                        raise ActionFormatError("每轮仅允许一个原生工具调用，本轮所有动作均未执行。")
                    native = []
                    phase = getattr(self, "analysis_phase", None) if getattr(self, "analysis_mode", False) else None
                    alias = "propose_documentation" if phase == "draft" else "finish_documentation" if phase == "complete" else None
                    allowed_names = {tool_name, alias} - {None}
                    diagnostics = []
                    for index, call in sorted(calls.items()):
                        if call["name"] not in allowed_names or not call["id"]:
                            diagnostics.append({"code": "missing_call_id" if not call["id"] else "tool_name_mismatch",
                                "phase": phase, "index": index, "expected_tool": tool_name,
                                "received_tool": call["name"][:160], "id_present": bool(call["id"]),
                                "id_chars": len(call["id"]), "argument_chars": len(call["arguments"]),
                                "name_parts": call["name_parts"], "id_part_count": call["id_parts"]})
                        native.append({"id": call["id"], "type": "function", "function": {
                            "name": call["name"], "arguments": call["arguments"]}})
                    if diagnostics:
                        message = "模型未返回工具调用 ID。" if any(item["code"] == "missing_call_id" for item in diagnostics) else f"工具名不匹配：当前要求 {tool_name}，返回 {diagnostics[0]['received_tool'] or '空名称'}。"
                        raise ModelProtocolError(message, diagnostics)
                    if phase in {"draft", "complete"}:
                        if len(native) != 1:
                            raise ActionFormatError("文档提交或完成动作必须单独调用，本轮未执行。")
                        self.response_action = documentation_action(alias, native[0]["function"]["arguments"])
                        self.last_tool_call = native[0]
                    elif len(native) > 1:
                        self.batch_action = native_read_batch(native)
                        for call, action in zip(native, self.batch_action["args"]["actions"]):
                            call["function"]["arguments"] = json.dumps(action, ensure_ascii=False)
                    else:
                        self.last_tool_call = native[0]
                    self.last_tool_calls = native
                else:
                    # Compatibility for gateways that still return action text.
                    yield "".join(text)

        self.llm = TransportLLM(model=settings["model"], api_key=key or "local", base_url=settings["base_url"], provider="custom", temperature=0.2, max_tokens=8192, timeout=60)

    async def generate(self, messages: list[dict], emit) -> str:
        self.last_tool_call, self.last_tool_calls = None, []
        self.llm.annotation_unit = None
        self.llm.analysis_mode = False
        self.llm.analysis_phase = None
        if len(messages) >= 2 and messages[1]["role"] == "user":
            try:
                request = json.loads(messages[1]["content"])
                self.llm.analysis_mode = request.get("skill") == ANALYSIS_SKILL
                if self.llm.analysis_mode:
                    self.llm.analysis_phase = request.get("analysis_output", {}).get("phase")
            except (ValueError, TypeError, AttributeError):
                pass
        if len(messages) == 2 and messages[1]["role"] == "user":
            try:
                request = json.loads(messages[1]["content"])
                if request.get("client_mode") == "annotation_unit":
                    self.llm.annotation_unit = request["annotation_unit"]
            except (ValueError, KeyError, TypeError, AttributeError):
                pass
        loop, queue, stopped = asyncio.get_running_loop(), asyncio.Queue(), threading.Event()

        def publish(kind, value):
            if stopped.is_set():
                return
            try:
                loop.call_soon_threadsafe(queue.put_nowait, (kind, value))
            except RuntimeError:
                pass  # The service may have shut down after cancellation.

        def worker():
            stream = None
            try:
                stream = self.llm.think(messages)
                parts, pending, total = [], "", 0
                for chunk in stream:
                    if stopped.is_set():
                        break
                    total += len(chunk)
                    if total > 60_000:
                        raise ValueError("模型单步输出超过限制，请拆分任务。")
                    parts.append(chunk)
                    pending += chunk
                    if len(pending) >= 180:
                        publish("delta", pending)
                        pending = ""
                if pending:
                    publish("delta", pending)
                publish("done", "".join(parts))
            except Exception as exc:
                publish("error", exc)
            finally:
                if stream:
                    stream.close()

        thread = threading.Thread(target=worker, daemon=True, name="code-assistant-model")
        thread.start()
        try:
            while True:
                kind, value = await queue.get()
                if kind == "done":
                    self.last_tool_call = getattr(self.llm, "last_tool_call", None)
                    self.last_tool_calls = getattr(self.llm, "last_tool_calls", [])
                    if getattr(self.llm, "response_action", None):
                        return json.dumps(self.llm.response_action, ensure_ascii=False)
                    if getattr(self.llm, "batch_action", None):
                        return json.dumps(self.llm.batch_action, ensure_ascii=False)
                    return value
                if kind == "error":
                    from openai import APITimeoutError
                    import httpx
                    for diagnostic in getattr(value, "diagnostics", []):
                        await emit("model.protocol_diagnostic", {**diagnostic,
                            "message": f"工具协议诊断：预期 {diagnostic.get('expected_tool')}，返回 {diagnostic.get('received_tool', '未提供')}，调用 ID {'存在' if diagnostic.get('id_present') else '缺失'}。"})
                    if isinstance(value, (APITimeoutError, httpx.TimeoutException, TimeoutError)):
                        raise ModelRequestTimeout("模型请求超时，未收到完整响应，本轮未执行工具。") from value
                    if isinstance(value, ValueError):
                        raise value
                    raise ValueError(str(value))
                await emit("model.delta", {"text": value})
        finally:
            stopped.set()

    def close(self):
        # The 0.2.9 learning release exposes no close() API; isolate that detail here.
        self.llm._client.close()


class ActionFormatError(ValueError):
    """A response cannot be used as one unambiguous local tool action."""


class ModelProtocolError(ActionFormatError):
    def __init__(self, message, diagnostics):
        super().__init__(message)
        self.diagnostics = diagnostics


def merge_tool_metadata(previous: str, incoming: str) -> str:
    """Handle first, repeated full and cumulative metadata without duplicating it."""
    if not incoming or incoming == previous:
        return previous
    if not previous or incoming.startswith(previous):
        return incoming
    if previous.startswith(incoming):
        return previous
    return previous + incoming


class ModelRequestTimeout(ValueError):
    """A transport timeout is separate from invalid model output or task limits."""


class ModelOutputTruncated(ActionFormatError):
    """An incomplete output must never become a proposed file modification."""


# Some providers append simulated observations. These are discarded, never executed
# or passed back to the model as evidence. Other trailing content remains an error.
SIMULATED_OBSERVATIONS = re.compile(r"(?:\s*<system>\s*工具观察：(?:(?!</system>).)*</system>)*\s*", re.DOTALL)
ACTIONS = {"list", "read", "search", "git_diff", "inventory", "propose_patch", "propose_documentation", "annotate_unit", "test", "final", "read_batch"}
READ_ONLY_ACTIONS = {"list", "read", "search", "git_diff", "inventory"}


def documentation_action(tool_name: str, raw: str) -> dict:
    expected = "propose_documentation" if tool_name == "propose_documentation" else "final"
    try:
        try:
            arguments = json.loads(raw)
        except ValueError:
            repaired = _complete_outer_object(raw)
            if repaired is None:
                raise
            arguments = json.loads(repaired)
    except (ValueError, TypeError) as exc:
        raise ActionFormatError("请按当前工具 schema 提交完整文档参数，不要返回读取动作或不完整 JSON。") from exc
    # Accept the previous complete action envelope only for the exact same
    # stage action. No document text, graph data or missing values are guessed.
    if isinstance(arguments, dict) and "action" in arguments:
        if arguments["action"] != expected:
            raise ActionFormatError(f"action 必须为 {expected}，实际为 {str(arguments['action'])[:80]}。")
        extras = set(arguments) - {"action", "args", "summary", "base_hashes"}
        if extras:
            raise ActionFormatError("不支持的外层字段：" + "、".join("$." + key for key in sorted(extras)) + "。")
        arguments = arguments.get("args")
    if isinstance(arguments, dict) and isinstance(arguments.get("summary"), str):
        arguments = {key: value for key, value in arguments.items() if key != "summary"}
    if not isinstance(arguments, dict):
        raise ActionFormatError("args 必须为 JSON 对象。")
    arguments = dict(arguments)
    if expected == "propose_documentation":
        # These are obsolete client metadata, never document/graph content.
        # Ignore their values; the runtime uses its own pre-request baseline.
        arguments.pop("base_hashes", None)
        if isinstance(arguments.get("diagrams"), dict):
            diagrams = dict(arguments["diagrams"])
            diagrams.pop("base_hashes", None)
            arguments["diagrams"] = diagrams
    required = {"overview", "diagrams"} if expected == "propose_documentation" else {"message"}
    missing, extras = required - arguments.keys(), arguments.keys() - required
    errors = []
    if missing:
        errors.append("缺少字段：" + "、".join("args." + key for key in sorted(missing)))
    if extras:
        errors.append("不支持字段：" + "、".join("args." + key for key in sorted(extras)))
    if errors:
        raise ActionFormatError("；".join(errors) + "。")
    if expected == "propose_documentation":
        if not isinstance(arguments["overview"], str):
            raise ActionFormatError("args.overview 必须为文本。")
        if not isinstance(arguments["diagrams"], dict):
            raise ActionFormatError("args.diagrams 必须为对象。")
        diagram_keys = {"architecture", "workflow", "sequence"}
        absent = diagram_keys - arguments["diagrams"].keys()
        extra = arguments["diagrams"].keys() - diagram_keys
        if absent or extra:
            details = (["缺少字段：" + "、".join("args.diagrams." + key for key in sorted(absent))] if absent else [])
            if extra:
                details.append("不支持字段：" + "、".join("args.diagrams." + key for key in sorted(extra)))
            raise ActionFormatError("；".join(details) + "。")
    elif not isinstance(arguments["message"], str):
        raise ActionFormatError("args.message 必须为文本。")
    return {"action": expected, "args": arguments,
            "summary": "提交项目说明和设计图" if expected == "propose_documentation" else "完成项目解析"}


def native_read_batch(calls: list[dict]) -> dict:
    """Validate the whole native response before allowing any read to run."""
    if not isinstance(calls, list) or not 2 <= len(calls) <= 16:
        raise ActionFormatError("一次只读批次须包含2–16个原生工具调用，本轮未执行。")
    ids, actions = set(), []
    for call in calls:
        if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
            raise ActionFormatError("批次包含不完整的原生工具调用，本轮未执行。")
        function = call.get("function", {})
        call_id = call.get("id")
        if (not isinstance(call_id, str) or not 1 <= len(call_id) <= 200 or call_id in ids
                or function.get("name") != "submit_action"):
            raise ActionFormatError("批次包含重复、未知或不完整的原生工具调用，本轮未执行。")
        ids.add(call_id)
        action = parse_action(function.get("arguments", ""))
        if action["action"] not in READ_ONLY_ACTIONS:
            raise ActionFormatError("多个原生调用只能全部为只读动作；修改、测试和结束必须单独提交，本轮未执行。")
        actions.append(action)
    return {"action": "read_batch", "args": {"actions": actions}, "summary": f"依次处理 {len(actions)} 个只读调用"}


def _complete_outer_object(text: str) -> str | None:
    """Close only one missing root brace after otherwise complete JSON values.

    Never repair open strings, nested containers, mismatched delimiters, commas
    or escapes: those could change the actual tool parameters or file content.
    """
    stack, quoted, escaped = [], False, False
    for character in text:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in "{[":
            stack.append(character)
        elif character in "}]":
            if not stack or stack.pop() != {"}": "{", "]": "["}[character]:
                return None
    if not quoted and not escaped and stack == ["{"]:
        candidate = text + "}"
        try:
            json.loads(candidate)
        except (json.JSONDecodeError, RecursionError):
            return None
        return candidate
    return None


def parse_action(text: str, *, diagnostics: list[str] | None = None) -> dict:
    repairs = []
    stripped = text.lstrip("\ufeff").strip()
    if not stripped:
        raise ActionFormatError("模型返回了空内容，没有可执行的动作 JSON。")
    if stripped.startswith("<｜｜DSML｜｜"):
        raise ActionFormatError("模型返回了 DSML 工具标记；当前客户端要求单个动作 JSON。")
    fenced = stripped.startswith("```")
    if fenced:
        header, separator, stripped = stripped.partition("\n")
        if not separator or header.strip().lower() not in {"```", "```json"}:
            raise ActionFormatError("模型没有返回有效的 JSON 代码块。")
        stripped = stripped.lstrip()
    try:
        data, end = json.JSONDecoder().raw_decode(stripped)
    except (json.JSONDecodeError, RecursionError) as exc:
        candidate = _complete_outer_object(stripped) if isinstance(exc, json.JSONDecodeError) and exc.pos == len(stripped) else None
        if candidate is None:
            location = f"（第 {exc.lineno} 行，第 {exc.colno} 列）" if isinstance(exc, json.JSONDecodeError) else ""
            raise ActionFormatError(f"模型动作 JSON 不完整或转义不合法{location}，本轮未执行；请缩小补丁并返回完整参数。") from exc
        stripped = candidate
        data, end = json.JSONDecoder().raw_decode(stripped)
        repairs.append("已补齐工具参数末尾缺失的单个外层大括号；未修改补丁文本。")
    trailing = stripped[end:]
    # The first object is already complete. A lone duplicated root delimiter
    # contains no arguments or instructions; never discard other write tails.
    if trailing.strip() == "}":
        trailing = ""
        repairs.append("已忽略完整动作末尾多余的单个大括号；未修改补丁文本。")
    if fenced:
        trailing = trailing.lstrip()
        if not trailing.startswith("```"):
            raise ActionFormatError("模型的 JSON 代码块没有正确结束。")
        trailing = trailing[3:]
    if not isinstance(data, dict) or not isinstance(data.get("action"), str) or data["action"] not in ACTIONS:
        raise ActionFormatError("模型返回了不支持的动作。")
    if not isinstance(data.get("args", {}), dict):
        raise ActionFormatError("动作参数需要是 JSON 对象。")
    if "summary" not in data and isinstance(data.get("args", {}).get("summary"), str):
        data["args"] = dict(data["args"])
        data["summary"] = data["args"].pop("summary")
        repairs.append("已将误放在 args 中的进度说明归位。")
    if "summary" in data and not isinstance(data["summary"], str):
        raise ActionFormatError("动作 summary 需要是简短字符串。")
    if data["action"] not in READ_ONLY_ACTIONS and not SIMULATED_OBSERVATIONS.fullmatch(trailing):
        raise ActionFormatError("修改或结束动作附带了额外内容，本轮未执行。")
    if diagnostics is not None:
        diagnostics.extend(repairs)
    return {key: data[key] for key in ("action", "args", "summary") if key in data}
