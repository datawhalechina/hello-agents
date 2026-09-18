# my_llm.py
import os
from typing import Optional
from hello_agents import HelloAgentsLLM

class MyLLM(HelloAgentsLLM):
    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[str] = "auto",
        **kwargs
    ):
        # 检查provider是否为我们想处理的'modelscope'
        if provider == "modelscope":
            print("正在使用自定义的 ModelScope Provider")

            # 解析 ModelScope 的凭证
            modelscope_api_key = api_key or os.getenv("MODELSCOPE_API_KEY")
            modelscope_base_url = base_url or "https://api-inference.modelscope.cn/v1/"
            modelscope_model = model or os.getenv("LLM_MODEL_ID") or "Qwen/Qwen2.5-VL-72B-Instruct"

            # 验证凭证是否存在
            if not modelscope_api_key:
                raise ValueError("ModelScope API key not found. Please set MODELSCOPE_API_KEY environment variable.")

            # ModelScope 兼容 OpenAI API，通过父类的 openai provider 完成初始化
            # 必须调用 super().__init__()，确保父类的 _adapter 等属性被正确设置
            super().__init__(
                model=modelscope_model,
                api_key=modelscope_api_key,
                base_url=modelscope_base_url,
                provider="openai",
                **kwargs
            )
            self.provider = "modelscope"

        else:
            # 如果不是 modelscope, 则完全使用父类的原始逻辑来处理
            super().__init__(model=model, api_key=api_key, base_url=base_url, provider=provider, **kwargs)
