import openai
import requests
import json
import os
from typing import Dict, Any, Optional

# 检查OpenAI版本
OPENAI_V2 = openai.__version__ >= '2.0.0'

# 导入配置
import sys
import os

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

try:
    from config.settings import settings
except ImportError:
    # 如果导入失败，使用环境变量创建配置
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    class Settings:
        openai_api_key = os.getenv('OPENAI_API_KEY', '')
        base_url = os.getenv('BASE_URL', None)
        model_name = os.getenv('MODEL_NAME', 'gpt-4')
        temperature = float(os.getenv('TEMPERATURE', 0.7))
        max_tokens = int(os.getenv('MAX_TOKENS', 1000))

    settings = Settings()


class LLMClient:
    """LLM客户端，处理与多种AI模型的通信"""

    def __init__(self, api_key: str, model_name: str = "gpt-4"):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = getattr(settings, 'base_url', None)

        # 检测API类型
        self.api_type = self._detect_api_type()

    def _detect_api_type(self) -> str:
        """检测API类型"""
        if self.base_url:
            if 'open.bigmodel.cn' in self.base_url:
                return 'zhipu'
            elif 'anthropic.com' in self.base_url:
                return 'anthropic'
            elif 'google.com' in self.base_url:
                return 'google'
            else:
                return 'custom'
        else:
            return 'openai'

    def _prepare_request_data(self, messages: list, **kwargs) -> Dict[str, Any]:
        """准备请求数据，适配不同API"""
        base_data = {
            "messages": messages,
            "temperature": kwargs.get('temperature', settings.temperature),
            "max_tokens": kwargs.get('max_tokens', settings.max_tokens)
        }

        if self.api_type == 'zhipu':
            # 智谱AI接口
            return {
                "model": self.model_name,
                "messages": messages,
                "temperature": kwargs.get('temperature', settings.temperature),
                "max_tokens": kwargs.get('max_tokens', settings.max_tokens)
            }
        elif self.api_type == 'anthropic':
            # Anthropic Claude接口
            return {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": kwargs.get('max_tokens', settings.max_tokens),
                "temperature": kwargs.get('temperature', settings.temperature)
            }
        elif self.api_type == 'google':
            # Google Gemini接口
            return {
                "contents": [{"role": "user", "parts": [{"text": messages[0]["content"]}]}],
                "generationConfig": {
                    "temperature": kwargs.get('temperature', settings.temperature),
                    "maxOutputTokens": kwargs.get('max_tokens', settings.max_tokens)
                }
            }
        else:
            # OpenAI或自定义接口
            return base_data

    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送请求到不同的API"""
        headers = {
            "Content-Type": "application/json"
        }

        if self.api_type == 'zhipu':
            headers["Authorization"] = f"Bearer {self.api_key}"
            url = f"{self.base_url}/chat/completions"
        elif self.api_type == 'anthropic':
            headers["x-api-key"] = self.api_key
            headers["anthropic-version"] = "2023-06-01"
            url = f"{self.base_url}/messages"
        elif self.api_type == 'google':
            headers["Authorization"] = f"Bearer {self.api_key}"
            url = f"{self.base_url}/v1beta/models/{self.model_name}:generateContent"
        else:
            # OpenAI
            openai.api_key = self.api_key
            url = f"{self.base_url}/chat/completions" if self.base_url else None

        if url:
            # Debug: Print the request details
            print(f"DEBUG: Making request to {url}")
            print(f"DEBUG: Headers: {headers}")
            print(f"DEBUG: Data: {json.dumps(data, indent=2, ensure_ascii=False)}")

            response = requests.post(url, headers=headers, json=data)
            print(f"DEBUG: Status code: {response.status_code}")
            print(f"DEBUG: Response: {response.text}")

            response.raise_for_status()
            return response.json()
        else:
            # 使用OpenAI库
            if OPENAI_V2:
                # v2.x版本
                client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=data["messages"],
                    temperature=data["temperature"],
                    max_tokens=data["max_tokens"],
                    **{k: v for k, v in kwargs.items() if k not in ['temperature', 'max_tokens']}
                )
                return response.model_dump()
            else:
                # v1.x版本
                response = openai.ChatCompletion.create(
                    model=self.model_name,
                    messages=data["messages"],
                    temperature=data["temperature"],
                    max_tokens=data["max_tokens"],
                    **{k: v for k, v in kwargs.items() if k not in ['temperature', 'max_tokens']}
                )
                return response.to_dict()

    def generate(self,
                prompt: str,
                max_tokens: int = 1000,
                temperature: float = 0.7,
                **kwargs) -> str:
        """
        生成文本内容

        Args:
            prompt: 提示词
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他参数

        Returns:
            生成的文本内容
        """
        try:
            # 准备消息
            messages = [{"role": "user", "content": prompt}]

            # 准备请求数据
            data = self._prepare_request_data(
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            # 发送请求
            if self.api_type in ['zhipu', 'anthropic', 'google']:
                result = self._make_request("chat/completions", data)
            else:
                if OPENAI_V2:
                    # v2.x版本
                    client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
                    result = client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        **kwargs
                    )
                    result = result.model_dump()
                else:
                    # v1.x版本
                    result = openai.ChatCompletion.create(
                        model=self.model_name,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        **kwargs
                    )
                    result = result.to_dict()

            # 解析响应
            if self.api_type == 'zhipu':
                return result["choices"][0]["message"]["content"]
            elif self.api_type == 'anthropic':
                return result["content"][0]["text"]
            elif self.api_type == 'google':
                return result["candidates"][0]["content"]["parts"][0]["text"]
            else:
                return result["choices"][0]["message"]["content"]

        except Exception as e:
            raise RuntimeError(f"生成失败 ({self.api_type}): {str(e)}")

    def stream_generate(self,
                      prompt: str,
                      max_tokens: int = 1000,
                      temperature: float = 0.7,
                      **kwargs):
        """
        流式生成文本内容

        Args:
            prompt: 提示词
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他参数

        Yields:
            生成的文本片段
        """
        try:
            # 智谱AI目前不支持流式生成，直接返回完整内容
            if self.api_type == 'zhipu':
                content = self.generate(prompt, max_tokens, temperature, **kwargs)
                for char in content:
                    yield char
                return

            # 使用OpenAI流式接口
            if OPENAI_V2:
                # v2.x版本
                client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True,
                    **kwargs
                )
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                # v1.x版本
                response = openai.ChatCompletion.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True,
                    **kwargs
                )
                for chunk in response:
                    if chunk.choices[0].delta.get("content"):
                        yield chunk.choices[0].delta.content
        except Exception as e:
            raise RuntimeError(f"流式生成失败: {str(e)}")

    def get_api_info(self) -> Dict[str, Any]:
        """获取API信息"""
        return {
            "api_type": self.api_type,
            "model_name": self.model_name,
            "base_url": self.base_url
        }