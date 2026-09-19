import sys
import os
import json
import argparse
from datetime import datetime

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.crud import create_forum, create_persona, create_message, get_user_by_username
from app.schemas import ForumCreate, PersonaCreate, MessageCreate
from app.agent.agent import run_simple_agent

def create_baseline_forum(topic: str, owner_username: str = "admin"):
    """
    Generate a baseline single-LLM response and save it as a forum.
    """
    db = SessionLocal()
    try:
        user = get_user_by_username(db, owner_username)
        if not user:
            print(f"User {owner_username} not found.")
            return

        # 1. Ensure Baseline Persona exists
        baseline_persona_name = "Baseline Model"
        
        # Direct DB query for simplicity
        from app.models import Persona
        baseline_persona = db.query(Persona).filter(Persona.name == baseline_persona_name).first()
        
        if not baseline_persona:
            print("Creating Baseline Persona...")
            p_create = PersonaCreate(
                name=baseline_persona_name,
                title="AI Assistant",
                bio="A standard large language model providing direct, comprehensive answers.",
                theories=[],
                stance="Neutral, Objective, Comprehensive",
                system_prompt="You are a helpful AI assistant. Provide a comprehensive and detailed answer to the user's topic.",
                is_public=True
            )
            baseline_persona = create_persona(db, p_create, user.id)
        
        print(f"Using Baseline Persona ID: {baseline_persona.id}")

        # 2. Create Baseline Forum
        print(f"Creating Baseline Forum for topic: '{topic}'...")
        f_create = ForumCreate(
            topic=topic,
            moderator_id=baseline_persona.id, # Baseline acts as moderator too? Or no moderator.
            participant_ids=[baseline_persona.id],
            duration_minutes=10
        )
        # Assuming create_forum handles moderator_id. Actually moderator is usually separate.
        # Let's use the baseline persona as moderator for simplicity or a system moderator.
        # If moderator_id is required... let's check ForumCreate schema.
        # It seems moderator_id is required. Let's use the baseline persona.
        
        forum = create_forum(db, f_create, user.id)
        print(f"Created Forum ID: {forum.id}")

        # 3. Generate Baseline Response
        print("Generating Baseline Response...")
        prompt = f"""
        你是一个知识渊博的专家。请针对以下议题，发表一篇深度、全面、逻辑严密的论述。
        
        【议题】：{topic}
        
        要求：
        1. 观点明确，论证充分。
        2. 结构清晰，包含引言、正文（多角度分析）和结语。
        3. 字数在 800 字左右。
        4. 保持客观、理性的学术风格。
        """
        
        content = run_simple_agent(
            "BaselineEvaluationAgent",
            "你是一个知识渊博、客观严谨的议题分析专家。",
            prompt,
        )
        
        if not content:
            print("Failed to generate response.")
            return
        print("Response generated.")

        # 4. Save Message
        msg_create = MessageCreate(
            forum_id=forum.id,
            persona_id=baseline_persona.id,
            moderator_id=baseline_persona.id, # Self-moderated
            speaker_name=baseline_persona.name,
            content=content,
            turn_count=1
        )
        create_message(db, msg_create)
        print("Message saved.")
        
        # Mark as completed
        from app.models import Forum
        db_forum = db.query(Forum).filter(Forum.id == forum.id).first()
        db_forum.status = "completed"
        db.commit()
        
        print(f"\nBaseline Forum Ready! ID: {forum.id}")
        return forum.id

    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a baseline forum with a single LLM response.")
    parser.add_argument("topic", type=str, help="The topic for the baseline.")
    parser.add_argument("--owner", type=str, default="admin", help="Username of the owner.")
    
    args = parser.parse_args()
    create_baseline_forum(args.topic, args.owner)
