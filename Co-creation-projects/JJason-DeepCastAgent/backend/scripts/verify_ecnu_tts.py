import os
import sys

import requests
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Load env
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

def test_tts_api():
    api_key = os.getenv("TTS_API_KEY") or os.getenv("LLM_API_KEY")
    base_url = os.getenv("TTS_BASE_URL", "https://chat.ecnu.edu.cn/open/api/v1/audio/speech")
    model = os.getenv("TTS_MODEL", "ecnu-tts")
    
    print("Testing TTS API...")
    print(f"URL: {base_url}")
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
        "input": "你好，这是一个测试语音。",
        "voice": "xiayu",
        "speed": 1.0
    }

    try:
        response = requests.post(base_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            output_file = "test_tts_output.mp3"
            with open(output_file, "wb") as f:
                f.write(response.content)
            print(f"✅ Success! Audio saved to {output_file}")
            print(f"Response size: {len(response.content)} bytes")
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_tts_api()
