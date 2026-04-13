import os
import sys

import requests
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Load env
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

def test_llm_api():
    """测试 ECNU LLM API 是否可用。"""
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://chat.ecnu.edu.cn/open/api/v1")
    model = os.getenv("LLM_MODEL_ID", "ecnu-max")
    
    # Ensure URL ends with /chat/completions
    if not base_url.endswith("/chat/completions"):
        url = f"{base_url.rstrip('/')}/chat/completions"
    else:
        url = base_url

    print("Testing LLM API...")
    print(f"URL: {url}")
    print(f"Model: {model}")
    print(f"API Key: {api_key[:8]}..." if api_key else "API Key: None")

    if not api_key:
        print("❌ Error: API Key not found in environment variables")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "你好，请回复“API 测试成功”"}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            print("✅ Success!")
            print(f"Response: {content}")
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_llm_api()
