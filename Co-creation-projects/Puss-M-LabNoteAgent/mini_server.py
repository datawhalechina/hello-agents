# -*- coding: utf-8 -*-
"""极简 OpenAI 兼容 server（/v1/chat/completions，支持 tools/function calling）

用途：给 HelloAgentsLLM 等需要 OpenAI 协议的客户端提供本地模型后端，
让 LabNoteAgent 的 demo 在没有任何付费 API 的情况下离线可复现。

用法:
  python mini_server.py --model ../../models/qwen25vl-3b --port 8080
仅实现 demo 所需子集：非流式 chat completions + tool_calls 解析。
"""
import argparse
import json
import re
import uuid

import torch
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, Qwen2_5_VLForConditionalGeneration

app = FastAPI(title="mini-openai-server")
STATE = {"model": None, "tokenizer": None}


class Message(BaseModel):
    role: str
    content: object = None
    tool_calls: object = None
    tool_call_id: str = None
    name: str = None


class ChatRequest(BaseModel):
    model: str = "local"
    messages: list[Message]
    tools: list = None
    tool_choice: object = None
    temperature: float = 0.7
    max_tokens: int = 512


def load(model_path: str, quantize: bool = False):
    tok = AutoTokenizer.from_pretrained(model_path)
    kwargs = {}
    if quantize:
        from transformers import BitsAndBytesConfig
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
        )
    mdl = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        model_path, torch_dtype=torch.bfloat16, device_map="cuda:0", **kwargs,
    )
    mdl.eval()
    STATE["model"], STATE["tokenizer"] = mdl, tok
    print("model loaded:", model_path, "(4bit)" if quantize else "(bf16)")


TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)


def build_tools_prompt(tools: list) -> str:
    """Qwen2.5 官方工具模板（VL 版模板不含 tools 段，手动注入同格式）。"""
    import json as _json
    tools_json = _json.dumps(tools, ensure_ascii=False, indent=2)
    return (
        "\n\n# Tools\n\n"
        "You may call one or more functions to assist with the user query.\n\n"
        "You are provided with function signatures within <tools></tools> XML tags:\n"
        f"<tools>\n{tools_json}\n</tools>\n\n"
        "For each function call, return a json object with function name and arguments within "
        "<tool_call></tool_call> XML tags:\n"
        '<tool_call>\n{"name": <function-name>, "arguments": <args-json-object>}\n</tool_call>'
    )


def _balanced_json(s: str):
    """从字符串中提取第一个平衡的 {...} 块并解析（容忍尾随文本/截断）。"""
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _parse_call_obj(fragment: str):
    """把一段（可能不规范的）tool_call 内容解析成调用列表。"""
    calls = []
    obj = None
    try:
        obj = json.loads(fragment)
    except json.JSONDecodeError:
        obj = _balanced_json(fragment)
    if isinstance(obj, dict) and obj.get("name"):
        args = obj.get("arguments", obj.get("parameters", {}))
        if isinstance(args, str):
            args2 = _balanced_json(args)
            args = args2 if args2 is not None else {}
        calls.append({
            "id": "call_" + uuid.uuid4().hex[:8],
            "type": "function",
            "function": {"name": obj["name"], "arguments": json.dumps(args, ensure_ascii=False)},
        })
    return calls


def extract_tool_calls(text: str):
    """从模型输出解析工具调用：标准 <tool_call> 块 + 裸 JSON 兜底。"""
    calls = []
    for m in re.finditer(r"<tool_call>(.*?)</tool_call>", text, re.S):
        calls.extend(_parse_call_obj(m.group(1)))
    if not calls:
        # 兜底：无标签的 {"name": ..., "arguments": {...}} 裸输出
        for m in re.finditer(r'\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:', text, re.S):
            calls.extend(_parse_call_obj(text[m.start():]))
            if calls:
                break
    content = re.sub(r"<tool_call>.*?</tool_call>", "", text, flags=re.S)
    content = re.sub(r"</?(tools|tool_call)>", "", content).strip()
    return content, calls


@app.post("/v1/chat/completions")
def chat(req: ChatRequest):
    try:
        tok, mdl = STATE["tokenizer"], STATE["model"]
        msgs = [m.model_dump(exclude_none=True) for m in req.messages]
        if req.tools:
            tool_section = build_tools_prompt(req.tools)
            if msgs and msgs[0].get("role") == "system":
                msgs[0]["content"] = (msgs[0].get("content") or "") + tool_section
            else:
                msgs.insert(0, {"role": "system", "content": tool_section.strip()})
        prompt = tok.apply_chat_template(
            msgs, tools=req.tools or None, tokenize=False, add_generation_prompt=True,
        )
        inputs = tok(prompt, return_tensors="pt").to(mdl.device)
        with torch.inference_mode():
            out = mdl.generate(
                **inputs, max_new_tokens=req.max_tokens, temperature=req.temperature,
                do_sample=req.temperature > 0, pad_token_id=tok.eos_token_id,
            )
        text = tok.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        content, calls = extract_tool_calls(text)

        message = {"role": "assistant", "content": content if content else None}
        finish = "stop"
        if calls:
            message["tool_calls"] = calls
            finish = "tool_calls"
        return {
            "id": "chat" + uuid.uuid4().hex[:12],
            "object": "chat.completion",
            "created": 0,
            "model": req.model,
            "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": {"prompt_tokens": inputs.input_ids.shape[1], "completion_tokens": 0, "total_tokens": 0},
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"error": str(e), "tb": traceback.format_exc()[-1200:]})


@app.get("/v1/models")
def models():
    return {"data": [{"id": "local-mini", "object": "model"}]}


if __name__ == "__main__":
    import uvicorn
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=str, required=True)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--quantize", action="store_true", help="用 bitsandbytes NF4 4bit 加载（6GB 显存跑 7B）")
    args = ap.parse_args()
    load(args.model, args.quantize)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
