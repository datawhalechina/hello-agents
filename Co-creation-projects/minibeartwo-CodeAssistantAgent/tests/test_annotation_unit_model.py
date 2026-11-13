"""The real streaming adapter restricts long-file rounds to the active unit."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from backend.model import HelloModel, parse_action
from backend.runtime import annotation_unit_messages


async def test_native_annotation_unit_schema_and_return_to_general_tools():
    requests = []
    unit = {"path": "module.py", "base_hash": "actual-source-hash", "target_id": "function-10",
            "kind": "function", "name": "echo", "parameters": ["value"],
            "source": "def echo(value):\n    return value\n", "progress": {"done": 1, "total": 2}}
    expected = {"action": "annotate_unit", "args": {key: unit[key] for key in ("path", "base_hash", "target_id")},
                "summary": "说明当前函数"}
    expected["args"]["documentation"] = {"purpose": "返回原值。", "inputs": "value：待返回值。", "outputs": "返回 value。"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            action = expected if len(requests) == 1 else {"action": "final", "args": {"message": "完成。"}, "summary": "结束"}
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.end_headers()
            chunk = {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "actual-test-call",
                "type": "function", "function": {"name": "submit_action", "arguments": json.dumps(action, ensure_ascii=False)}}]},
                "finish_reason": None}]}
            self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())
            self.wfile.write(b'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}]}\n\ndata: [DONE]\n\n')
            self.wfile.flush()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    model = HelloModel({"model": "local-test", "base_url": f"http://127.0.0.1:{server.server_port}/v1"}, "")

    async def emit(kind, data):
        pass

    try:
        task = {"prompt": "注释整个项目", "skill": "annotate-project-zh", "skill_instructions": "保留源码，仅添加注释。"}
        response = await model.generate(annotation_unit_messages(unit, task), emit)
        assert parse_action(response) == expected
        schema = requests[0]["tools"][0]["function"]["parameters"]
        assert schema["properties"]["action"]["enum"] == ["annotate_unit"]
        args = schema["properties"]["args"]["properties"]
        assert args["target_id"]["enum"] == [unit["target_id"]]
        assert set(args["documentation"]["required"]) == {"purpose", "inputs", "outputs"}
        assert set(args) == {"path", "base_hash", "target_id", "documentation"}
        await model.generate([{"role": "system", "content": "继续普通任务。"}, {"role": "user", "content": "完成。"}], emit)
        ordinary = requests[1]["tools"][0]["function"]["parameters"]["properties"]["action"]["enum"]
        assert "read" in ordinary and "propose_patch" in ordinary and "annotate_unit" not in ordinary
    finally:
        model.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
