import asyncio
from typing import Any, AsyncGenerator, Dict

from app.config import settings
from app.agents.mermaid.code_utils import apply_direction, prune_complexity
from app.agents.mermaid.pipeline import MermaidPipeline
from app.tools.mermaid_validator_tool import MermaidValidatorTool


class MermaidAgentService:
    def __init__(self):
        self.validator = MermaidValidatorTool()
        self.pipeline = MermaidPipeline(self.validator)

    async def stream_chat(self, mode: str, prompt: str, direction: str = "TD") -> AsyncGenerator[Dict[str, Any], None]:
        yield {"type": "status", "phase": "start", "message": "开始生成"}
        yield {"type": "status", "phase": "generating", "message": "模型生成中"}

        try:
            llm_timeout = max(30, int(settings.llm_timeout))
            standard_timeout = llm_timeout * 2 + 20
            single_timeout = llm_timeout + 20
            validate_timeout = 20

            optimized_text = ""
            generated_from_optimized = False
            if mode == "standard":
                yield {"type": "status", "phase": "optimizing", "message": "文本优化中"}
                standard_result = await asyncio.wait_for(
                    asyncio.to_thread(self.pipeline.generate_standard, prompt), timeout=standard_timeout
                )
                optimized_text = standard_result.get("optimized_text", "")
                raw_code = standard_result.get("mermaid_code", "")
                generated_from_optimized = bool(standard_result.get("generated_from_optimized", False))
                yield {"type": "status", "phase": "creating", "message": "基于优化文本生成流程图"}
            else:
                raw_code = await asyncio.wait_for(
                    asyncio.to_thread(self.pipeline.generate_once, mode, prompt), timeout=single_timeout
                )

            extracted = prune_complexity(raw_code, mode)
            extracted = apply_direction(extracted, direction)

            yield {"type": "status", "phase": "validating", "message": "语法校验中"}
            validation = await asyncio.wait_for(
                asyncio.to_thread(self.pipeline.post_validate, extracted), timeout=validate_timeout
            )

            yield {
                "type": "result",
                "mode": mode,
                "valid": validation["valid"],
                "attempts": validation["attempts"],
                "mermaid_code": validation["mermaid_code"],
                "optimized_text": optimized_text,
                "generated_from_optimized": generated_from_optimized,
                "message": validation.get("message", ""),
            }

            yield {"type": "done"}
        except asyncio.TimeoutError:
            yield {
                "type": "error",
                "phase": "timeout",
                "message": "生成超时，请简化输入后重试。",
            }
            yield {"type": "done"}
        except Exception as exc:
            yield {
                "type": "error",
                "phase": "exception",
                "message": f"生成失败: {str(exc)}",
            }
            yield {"type": "done"}
