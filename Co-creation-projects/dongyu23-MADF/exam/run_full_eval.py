import sys
import os
import time
import requests
import argparse
from datetime import datetime

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.crud import create_forum, get_forum
from app.schemas import ForumCreate

# Import our new tools
# Ensure project root is in python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# And also add exam folder itself
exam_dir = os.path.dirname(os.path.abspath(__file__))
if exam_dir not in sys.path:
    sys.path.append(exam_dir)

# Import assuming running from project root or inside exam/
try:
    from exam.generate_roles import generate_roles
    from exam.baseline_eval import create_baseline_forum
    from exam.standard_eval import evaluate_forum
    from exam.ablation_study import compare_forums
except ImportError:
    # Fallback for direct execution
    from generate_roles import generate_roles
    from baseline_eval import create_baseline_forum
    from standard_eval import evaluate_forum
    from ablation_study import compare_forums

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "experiment_admin"
PASSWORD = "admin_password"

def get_token():
    # Simple login as experiment_admin or create
    login_url = f"{API_BASE_URL}/auth/login"
    payload = {"username": USERNAME, "password": PASSWORD}
    try:
        resp = requests.post(login_url, data=payload)
        if resp.status_code == 200:
            return resp.json()["access_token"]
        
        # Try registering
        reg_url = f"{API_BASE_URL}/auth/register"
        requests.post(reg_url, json=payload)
        resp = requests.post(login_url, data=payload)
        if resp.status_code == 200:
            return resp.json()["access_token"]
            
        print(f"Failed to login/register as {USERNAME}.")
        return None
    except:
        print("Backend not running?")
        return None

def run_standard_forum(topic: str, persona_ids: list, duration_minutes: int = 5, ablation_flags: dict = None):
    """
    Creates a forum, starts it via API, and waits for completion.
    """
    db = SessionLocal()
    try:
        if ablation_flags:
            print(f"Creating Forum with Ablation Flags: {ablation_flags}...")
        else:
            print(f"Creating Standard Forum: '{topic}' with {len(persona_ids)} agents...")
        
        # We need the user ID for creator_id.
        from app.crud import get_user_by_username
        user = get_user_by_username(db, USERNAME)
        if not user:
            print(f"User {USERNAME} not found in DB.")
            return None

        # 1. Create Forum in DB
        f_create = ForumCreate(
            topic=topic,
            participant_ids=persona_ids,
            duration_minutes=duration_minutes,
            moderator_id=persona_ids[0] if persona_ids else 1 # Default to first agent
        )
            
        forum = create_forum(db, f_create, user.id)
        print(f"Forum Created (ID: {forum.id}). Duration: {duration_minutes} min.")
        
        # 2. Start Forum via API
        token = get_token()
        if not token:
            print("Cannot get API token. Is backend running?")
            return None
            
        start_url = f"{API_BASE_URL}/forums/{forum.id}/start"
        headers = {"Authorization": f"Bearer {token}"}
        
        # Pass ablation flags
        payload = {}
        if ablation_flags:
            payload["ablation_flags"] = ablation_flags
            
        resp = requests.post(start_url, json=payload, headers=headers)
        
        if resp.status_code != 200:
            print(f"Failed to start forum: {resp.text}")
            return None
            
        print("Forum started. Waiting for completion...")
        
        # 3. Wait for completion
        # Poll DB status
        while True:
            db.expire_all() # Refresh
            f = get_forum(db, forum.id)
            if not f:
                print("Forum disappeared?")
                break
                
            status = f.status
            print(f"  Status: {status} (Time: {datetime.now().strftime('%H:%M:%S')})")
            
            if status == "completed":
                print("Forum Completed!")
                break
            elif status == "closed":
                print("Forum Closed (Time's up)!")
                break
            elif status == "failed":
                print("Forum Failed!")
                break
                
            time.sleep(10) # Poll every 10s
            
        return forum.id

    finally:
        db.close()

def run_full_evaluation(topic: str, num_agents: int = 3, duration: int = 5):
    print("="*50)
    print(f"STARTING FULL EVALUATION PIPELINE")
    print(f"Topic: {topic}")
    print("="*50)

    # Step 1: Generate Roles
    print("\n[Step 1] Generating Roles...")
    persona_ids = generate_roles(topic, n=num_agents, owner_username=USERNAME)
    if not persona_ids:
        print("Failed to generate roles.")
        return

    # Step 2: Run Standard Forum
    print("\n[Step 2] Running Standard Multi-Agent Forum...")
    std_forum_id = run_standard_forum(topic, persona_ids, duration_minutes=duration)
    if not std_forum_id:
        print("Failed to run standard forum.")
        return

    # Step 3: Generate Baseline
    print("\n[Step 3] Generating Single LLM Baseline...")
    baseline_forum_id = create_baseline_forum(topic, owner_username=USERNAME)
    if not baseline_forum_id:
        print("Failed to generate baseline.")
        return

    # Step 4: Run Ablation Forums
    print("\n[Step 4.1] Running Ablation: No Summary...")
    no_summary_id = run_standard_forum(topic, persona_ids, duration_minutes=duration, ablation_flags={"no_summary": True})
    
    print("\n[Step 4.2] Running Ablation: No Private Memory...")
    no_private_id = run_standard_forum(topic, persona_ids, duration_minutes=duration, ablation_flags={"no_private_memory": True})
    
    print("\n[Step 4.3] Running Ablation: No Shared Memory...")
    no_shared_id = run_standard_forum(topic, persona_ids, duration_minutes=duration, ablation_flags={"no_shared_memory": True})

    # Step 5: Evaluations
    print("\n[Step 5] Running Comparisons...")
    
    # 5.1 Standard vs Baseline (Original request)
    print("\n>>> Standard vs Baseline")
    compare_forums(std_forum_id, baseline_forum_id, "Multi-Agent Discussion vs Single LLM Baseline")
    
    # 5.2 Standard vs No Summary
    if no_summary_id:
        print("\n>>> Standard vs No Summary")
        compare_forums(std_forum_id, no_summary_id, "Standard vs No Periodic Summary")
        
    # 5.3 Standard vs No Private Memory
    if no_private_id:
        print("\n>>> Standard vs No Private Memory")
        compare_forums(std_forum_id, no_private_id, "Standard vs No Private Memory (Stateless Agents)")
        
    # 5.4 Standard vs No Shared Memory
    if no_shared_id:
        print("\n>>> Standard vs No Shared Memory")
        compare_forums(std_forum_id, no_shared_id, "Standard vs No Shared Memory Context")

    print("\n" + "="*50)
    print("EVALUATION PIPELINE COMPLETE")
    print("Check exam/results/ for reports.")
    print("="*50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run full evaluation pipeline.")
    parser.add_argument("--topic", type=str, default="人工智能是否应该拥有人权？", help="Topic for evaluation.")
    parser.add_argument("--agents", type=int, default=3, help="Number of agents.")
    parser.add_argument("--duration", type=int, default=5, help="Duration in minutes.")
    
    args = parser.parse_args()
    
    run_full_evaluation(args.topic, args.agents, args.duration)
