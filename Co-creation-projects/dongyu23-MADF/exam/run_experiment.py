
import requests
import time
import json
import sys
import os
from typing import List, Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "experiment_admin"
PASSWORD = "admin_password"

def login_or_register() -> str:
    """Authenticates the user and returns an access token."""
    # Try login
    login_url = f"{API_BASE_URL}/auth/login"
    payload = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    try:
        response = requests.post(login_url, data=payload)
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            print(f"✅ Successfully logged in as {USERNAME}")
            return token
        elif response.status_code == 401 or response.status_code == 404:
            # Try register
            print(f"User {USERNAME} not found or password wrong. Attempting to register...")
            register_url = f"{API_BASE_URL}/auth/register"
            reg_payload = {
                "username": USERNAME,
                "password": PASSWORD
            }
            reg_response = requests.post(register_url, json=reg_payload)
            
            if reg_response.status_code == 200:
                print(f"✅ Successfully registered user {USERNAME}")
                # Login again
                response = requests.post(login_url, data=payload)
                if response.status_code == 200:
                    return response.json().get("access_token")
            
            print(f"❌ Registration failed: {reg_response.text}")
            sys.exit(1)
        else:
            print(f"❌ Login failed: {response.text}")
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the backend server. Is it running on http://localhost:8000?")
        sys.exit(1)

def generate_personas(token: str, prompt: str, n: int) -> List[int]:
    """Calls the God Agent to generate personas and returns their IDs."""
    url = f"{API_BASE_URL}/god/generate"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "prompt": prompt,
        "n": n
    }
    
    print(f"🤖 God Agent is generating {n} personas based on prompt: '{prompt}'...")
    print("   (This may take 30-60 seconds, please wait...)")
    
    try:
        # Increased timeout for LLM generation
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        
        if response.status_code == 200:
            personas = response.json()
            print(f"✅ Successfully generated {len(personas)} personas:")
            for p in personas:
                print(f"   - {p['name']} ({p['title']})")
            return [p['id'] for p in personas]
        else:
            print(f"❌ Generation failed: {response.text}")
            return []
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out. The model might be taking too long.")
        return []

def create_forum(token: str, topic: str, participant_ids: List[int], duration: int = 30) -> int:
    """Creates a new forum."""
    url = f"{API_BASE_URL}/forums/"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "topic": topic,
        "participant_ids": participant_ids,
        "duration_minutes": duration
    }
    
    print(f"📝 Creating forum with topic: '{topic}'...")
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        forum = response.json()
        print(f"✅ Forum created successfully (ID: {forum['id']})")
        return forum['id']
    else:
        print(f"❌ Failed to create forum: {response.text}")
        sys.exit(1)

def start_forum(token: str, forum_id: int):
    """Starts the forum loop."""
    url = f"{API_BASE_URL}/forums/{forum_id}/start"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"🚀 Starting forum {forum_id}...")
    response = requests.post(url, headers=headers)
    
    if response.status_code == 200:
        print(f"✅ Forum {forum_id} is now RUNNING!")
        print(f"   You can view the discussion at: http://localhost:5173/forums/{forum_id}")
    else:
        print(f"❌ Failed to start forum: {response.text}")

def main():
    print("=== MADF Experiment Automation Script ===")
    
    # 1. Configuration (Pre-defined for one-click execution)
    token = login_or_register()
    
    # Experiment 1: AI Impact on Art (Standard)
    exp1_topic = "人工智能生成内容（AIGC）是否会导致人类艺术创造力的枯竭？"
    exp1_prompt = "请生成4位不同背景的专家，包括一位持技术乐观主义的AI研究员，一位坚持传统技法的油画艺术家，一位关注版权与伦理的知识产权律师，以及一位研究数字文化的社会学家。他们将深入探讨AIGC对人类艺术未来的影响。"
    exp1_agents = 4
    exp1_duration = 20 # minutes
    
    print(f"\n🚀 Starting Experiment 1: {exp1_topic}")
    p_ids_1 = generate_personas(token, exp1_prompt, exp1_agents)
    if p_ids_1:
        f_id_1 = create_forum(token, exp1_topic, p_ids_1, exp1_duration)
        start_forum(token, f_id_1)
        
    # Experiment 2: Future of Work (Standard)
    # Note: To run purely ablation, we might need to modify backend config. 
    # For now, let's run a second distinct topic to demonstrate capability.
    exp2_topic = "在后稀缺经济时代，工作的意义将如何重构？"
    exp2_prompt = "请生成3位具有前瞻性的思想家：一位主张全民基本收入（UBI）的经济学家，一位强调自我实现的心理学家，和一位通过算法管理自动化工厂的企业家。讨论当AI承担大部分劳动后，人类如何寻找存在意义。"
    exp2_agents = 3
    exp2_duration = 15
    
    print(f"\n🚀 Starting Experiment 2: {exp2_topic}")
    p_ids_2 = generate_personas(token, exp2_prompt, exp2_agents)
    if p_ids_2:
        f_id_2 = create_forum(token, exp2_topic, p_ids_2, exp2_duration)
        start_forum(token, f_id_2)

    print("\n=== All Experiments Launched ===")
    print("Please monitor the frontend dashboard.")

if __name__ == "__main__":
    main()
