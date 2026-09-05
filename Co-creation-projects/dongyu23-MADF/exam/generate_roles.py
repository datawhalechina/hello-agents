import sys
import os
import json
import argparse
from typing import List

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.agent.real_god import RealGodAgent
from app.crud import create_persona, get_user_by_username
from app.schemas import PersonaCreate

def generate_roles(topic: str, n: int = 3, owner_username: str = "admin"):
    """
    Generate roles using RealGodAgent and save to DB.
    """
    db = SessionLocal()
    try:
        # Get owner (admin)
        user = get_user_by_username(db, owner_username)
        if not user:
            print(f"User {owner_username} not found. Please create it first.")
            return []

        print(f"Generating {n} roles for topic: '{topic}'...")
        agent = RealGodAgent()
        generated_names = []
        created_persona_ids = []

        for i in range(n):
            print(f"Generating role {i+1}/{n}...")
            
            # Run agent for 1 persona
            # We collect the result from the generator
            for event in agent.run(topic, n=1, generated_names=generated_names):
                if event["type"] == "result":
                    personas_data = event["content"]
                    
                    for p_data in personas_data:
                        name = p_data.get('name')
                        if name:
                            generated_names.append(name)
                        
                        try:
                            # Handle theories field
                            if isinstance(p_data.get('theories'), str):
                                try:
                                    p_data['theories'] = json.loads(p_data['theories'])
                                except:
                                    p_data['theories'] = []
                            
                            # Create Schema
                            persona_create = PersonaCreate(**p_data)
                            persona_create.is_public = True # Make them public for experiments
                            
                            # Save to DB
                            db_persona = create_persona(db=db, persona=persona_create, owner_id=user.id)
                            created_persona_ids.append(db_persona.id)
                            print(f"  -> Created persona: {db_persona.name} (ID: {db_persona.id})")
                            
                        except Exception as e:
                            print(f"  -> Error saving persona: {e}")
                
                elif event["type"] == "thought":
                    print(f"  [Thought]: {event['content']}")
                elif event["type"] == "action":
                    print(f"  [Action]: {event['content']}")
                elif event["type"] == "observation":
                    print(f"  [Observation]: {event['content'][:100]}...")
                elif event["type"] == "error":
                    print(f"  [Error]: {event['content']}")

        print(f"\nGeneration Complete. Created Persona IDs: {created_persona_ids}")
        return created_persona_ids

    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate roles for a forum topic.")
    parser.add_argument("topic", type=str, help="The topic/theme for the roles.")
    parser.add_argument("--n", type=int, default=3, help="Number of roles to generate.")
    parser.add_argument("--owner", type=str, default="admin", help="Username of the owner.")
    
    args = parser.parse_args()
    generate_roles(args.topic, args.n, args.owner)
