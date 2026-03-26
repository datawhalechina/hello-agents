from openai import OpenAI
from alh.llm.llm_model import LLMModel

class OpenAIModel(LLMModel):
    def __init__(self, base_url: str, api_key: str, model_name: str, system_prompt: str = None):
        super().__init__(system_prompt)
        self.model_name = model_name
        self.openai = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def talk(self, prompt):
        response = self.openai.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt if self.system_prompt else "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        )

        return response.choices[0].message.content
    
    def stream_talk(self, prompt):
        response = self.openai.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt if self.system_prompt else "You are a helpful assistant."},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "</think></think>"}
            ],
            stream=True,
            temperature=0.7,
            top_p=0.8,
            presence_penalty=1.5,
            extra_body={
                "reppen": 1.0,
                "min_p": 0.0,
                "top_k": 20
            }
        )

        for chunk in response:
            if len(chunk.choices) > 0 and chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    
