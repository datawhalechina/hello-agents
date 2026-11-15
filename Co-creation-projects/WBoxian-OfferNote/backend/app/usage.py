"""按一次业务调用归集普通响应和流式响应的最终用量，不保存提示词或回答正文。"""

from contextvars import ContextVar

CURRENT_CALL = ContextVar("offernote_model_call", default=None)


def instrument(llm):
    create = llm._client.chat.completions.create
    state = CURRENT_CALL.get()
    if state is not None:
        state["clients"].append(llm._client)

    def tracked(**kwargs):
        if state is not None:
            state["requests"] += 1
        response = create(**kwargs)
        if kwargs.get("stream"):
            return tracked_stream(response, state)
        if state is not None:
            usage = response.usage
            state["responses"] += 1
            if usage is not None and all(
                type(getattr(usage, field, None)) is int and getattr(usage, field) >= 0
                for field in ("prompt_tokens", "completion_tokens", "total_tokens")
            ):
                state["reported"] += 1
                state["input_tokens"] += usage.prompt_tokens
                state["output_tokens"] += usage.completion_tokens
                state["tokens"] += usage.total_tokens
            state["finish_reason"] = response.choices[0].finish_reason
        choice = response.choices[0]
        if choice.finish_reason == "length":
            from .engine import ModelError

            raise ModelError(
                "模型输出达到 Token 上限，结果被截断；请在模型设置中提高最大输出 Token，或减少本场面试轮数后重试。"
            )
        return response

    llm._client.chat.completions.create = tracked
    return llm


def begin_call(config):
    state = {
        "config": config,
        "clients": [],
        "requests": 0,
        "responses": 0,
        "reported": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "tokens": 0,
        "finish_reason": None,
        "repairs": 0,
        "validation_errors": [],
    }
    return state, CURRENT_CALL.set(state)


def public_usage(state):
    return {
        "tokens": state["tokens"] if state["reported"] else None,
        "input_tokens": state["input_tokens"] if state["reported"] else None,
        "output_tokens": state["output_tokens"] if state["reported"] else None,
        "usage_complete": state["requests"] > 0
        and state["reported"] == state["requests"]
        and not state.get("stream_incomplete", False),
        "model_requests": state["requests"],
        "finish_reason": state["finish_reason"],
        "repairs": state["repairs"],
        "validation_errors": state["validation_errors"],
    }


def end_call(state, token):
    try:
        for client in state["clients"]:
            client.close()
    finally:
        CURRENT_CALL.reset(token)


def tracked_stream(response, state):
    """同一流中的 usage 是累计快照，只计最后一次；不计推理正文。"""
    snapshot = None
    finish_reason = None
    final_usage = False
    if state is not None:
        state["stream_incomplete"] = True
    try:
        for chunk in response:
            usage = getattr(chunk, "usage", None)
            if state is not None and usage is not None:
                fields = ("prompt_tokens", "completion_tokens", "total_tokens")
                values = tuple(getattr(usage, field, None) for field in fields)
                if all(type(value) is int and value >= 0 for value in values):
                    if snapshot is None:
                        state["reported"] += 1
                    for name, value, old in zip(
                        ("input_tokens", "output_tokens", "tokens"),
                        values,
                        snapshot or (0, 0, 0),
                    ):
                        state[name] += value - old
                    snapshot = values
                    final_usage = bool(
                        finish_reason
                        or (chunk.choices and chunk.choices[0].finish_reason)
                    )
            if chunk.choices and chunk.choices[0].finish_reason:
                finish_reason = chunk.choices[0].finish_reason
                if state is not None:
                    state["finish_reason"] = finish_reason
            yield chunk
        if state is not None:
            state["responses"] += 1
            state["stream_incomplete"] = not final_usage
        if finish_reason == "length":
            from .engine import ModelError

            raise ModelError(
                "模型输出达到 Token 上限，流式回答未保存；请提高输出预算后重试。"
            )
    finally:
        response.close()
