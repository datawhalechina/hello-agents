from typing import Optional

from dotenv import load_dotenv

from MyAgent.ReActAndTool.llm_client import HelloAgentsLLM


load_dotenv()
class MyLLM(HelloAgentsLLM):
    def __init__(self,
                 model: Optional[str] = None,
                 apiKey : Optional[str] = None,
                 baseUrl : Optional[str] = None,
                 provider: Optional[str] = "auto",
                 ):
        #如果是处理的modelscope
        if provider == "modelscope":
            print("正在使用自定义的 ModelScope Provider")
            self.provider = "modelscope"
            #TODO