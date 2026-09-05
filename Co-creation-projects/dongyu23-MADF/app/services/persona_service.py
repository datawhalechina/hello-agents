from typing import List, Dict, Any, Optional
from app.schemas import PersonaCreate
from app.crud import create_persona
from app.core.cache import cache_service
from app.db.session import db_manager
import json
import logging

logger = logging.getLogger(__name__)

class PersonaService:
    @staticmethod
    def save_generated_persona(user_id: int, persona_data: Dict[str, Any], db=None) -> Optional[Any]:
        """
        Unified method to save a generated persona to the database.
        Handles data validation, JSON parsing, DB insertion, and cache invalidation.
        """
        try:
            # 1. Ensure 'theories' is a list
            if isinstance(persona_data.get('theories'), str):
                try:
                    persona_data['theories'] = json.loads(persona_data['theories'])
                except:
                    persona_data['theories'] = []
            
            # 2. Create Pydantic Model
            # Set default is_public to False for generated personas
            if 'is_public' not in persona_data:
                persona_data['is_public'] = False
                
            persona_create = PersonaCreate(**persona_data)
            
            # 3. Get DB Connection if not provided
            should_close = False
            if db is None:
                db = db_manager.get_connection()
                should_close = True
                
            try:
                # 4. Save to DB
                # This uses the underlying create_persona CRUD which is now transaction-safe via RetryingTransaction
                db_persona = create_persona(db=db, persona=persona_create, owner_id=user_id)
                
                # 5. Invalidate Cache
                # Crucial step to ensure frontend sees the new persona immediately
                cache_service.delete_keys_pattern(f"personas:list:{user_id}:*")
                
                logger.info(f"Successfully saved persona '{db_persona.name}' (ID: {db_persona.id}) for user {user_id}")
                return db_persona
                
            finally:
                if should_close:
                    db.close()
                    
        except Exception as e:
            logger.error(f"Failed to save generated persona: {e}")
            # Re-raise or return None? Let's log and return None so caller can handle gracefully
            print(f"[PersonaService] Error saving persona: {e}")
            return None

persona_service = PersonaService()
