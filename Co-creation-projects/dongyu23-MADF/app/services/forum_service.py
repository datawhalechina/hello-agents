from typing import Any
from datetime import datetime, timezone
from app.crud import (
    create_forum, 
    get_forum, 
    create_message, 
    get_forum_messages, 
    get_persona,
    delete_forum,
    get_forum_participants,
    update_forum,
)
from app.schemas import ForumCreate, MessageCreate
from app.core.websockets import manager
from app.services.forum_scheduler import scheduler
from app.agent.agent import ParticipantAgent
from fastapi import HTTPException

class ForumService:
    def __init__(self, db: Any):
        self.db = db

    def create_new_forum(self, forum_in: ForumCreate, creator_id: int):
        forum_in.participant_ids = list(dict.fromkeys(int(pid) for pid in forum_in.participant_ids))

        if forum_in.participant_ids:
            for pid in forum_in.participant_ids:
                p = get_persona(self.db, pid)
                if not p:
                    raise HTTPException(status_code=404, detail=f"Persona {pid} not found")
                if p.owner_id != creator_id and not p.is_public:
                    raise HTTPException(status_code=403, detail="不能邀请其他用户的私有智能体")

        if forum_in.moderator_id:
            rs = self.db.execute("SELECT 1 FROM moderators WHERE id = ?", [forum_in.moderator_id])
            # Check if any row is returned
            # LibSQL sync client result object has rows property which is a list of tuples
            # Or fetchone method if wrapped
            from app.db.client import fetch_one
            if not fetch_one(rs):
                raise HTTPException(status_code=404, detail=f"Moderator {forum_in.moderator_id} not found")

        return create_forum(self.db, forum_in, creator_id)

    async def start_forum(self, forum_id: int, user_id: int, is_admin: bool = False, ablation_flags: dict = None):
        forum = get_forum(self.db, forum_id)
        if not forum:
            raise HTTPException(status_code=404, detail="Forum not found")
            
        if forum.creator_id != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="Not authorized")
            
        if forum.status == "running":
            return {
                "status": "already_running",
                "ablation_flags": ablation_flags or {},
                "start_time": forum.start_time,
                "duration_minutes": forum.duration_minutes or 30,
            }
            
        flags = ablation_flags or {}
        # A non-running forum always starts a fresh session. This also repairs
        # legacy pending rows whose creation timestamp was stored as start_time.
        started_at = datetime.now(timezone.utc)
        update_forum(self.db, forum_id, status="running", start_time=started_at, ablation_flags=flags)
        await scheduler.start_forum(forum_id, flags)
        return {"status": "started", "ablation_flags": flags, "start_time": started_at, "duration_minutes": forum.duration_minutes or 30}

    async def delete_forum(self, forum_id: int, user_id: int, is_admin: bool = False):
        forum = get_forum(self.db, forum_id)
        if not forum:
            # If not found, maybe already deleted, return True to be idempotent
            return True
            
        if forum.creator_id != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Stop any running tasks for this forum first
        try:
            await scheduler.stop_forum(forum_id)
        except Exception as e:
            # Log error but proceed with deletion
            import logging
            logging.getLogger(__name__).error(f"Error stopping forum {forum_id} before delete: {e}")
            
        # Clear cache related to this forum
        try:
            from app.core.cache import cache_service
            cache_service.delete_keys_pattern(f"forums:list:{user_id}:*")
            # If forum has participants, clear their cache if needed? No, participant list cache isn't global.
        except:
            pass
        
        # Ensure we use a new transaction/connection for deletion if needed, 
        # but self.db is injected.
        return delete_forum(self.db, forum_id)

    async def stop_forum(self, forum_id: int, user_id: int, is_admin: bool = False):
        forum = get_forum(self.db, forum_id)
        if not forum:
            raise HTTPException(status_code=404, detail="Forum not found")
        if forum.creator_id != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="Not authorized")
        if forum.status in {"closed", "finished"}:
            return {"status": "closed"}
        await scheduler.stop_forum(forum_id)
        return {"status": "closed"}

    async def post_message(self, forum_id: int, msg_in: MessageCreate):
        if msg_in.forum_id != forum_id:
            raise HTTPException(status_code=400, detail="Forum ID mismatch")
            
        forum = get_forum(self.db, forum_id)
        if not forum:
            raise HTTPException(status_code=404, detail="Forum not found")
            
        if msg_in.persona_id:
            p = get_persona(self.db, msg_in.persona_id)
            if not p:
                raise HTTPException(status_code=404, detail="Persona not found")
        
        # Calculate turn count if not provided? 
        # Current logic trusts frontend, but better to count from DB.
        # messages = get_forum_messages(self.db, forum_id)
        # msg_in.turn_count = len(messages) + 1
        
        new_msg = create_message(self.db, msg_in)
        
        # RowObject or dict doesn't have .isoformat() if timestamp is string
        # libsql returns DATETIME as string usually.
        # We need to handle this.
        # If new_msg is RowObject, timestamp is likely a string "YYYY-MM-DD HH:MM:SS"
        ts = new_msg.timestamp
        # Check if ts is string
        if not isinstance(ts, str) and hasattr(ts, 'isoformat'):
            ts = ts.isoformat()
        
        await manager.broadcast(forum_id, {
            "type": "new_message",
            "data": {
                "id": new_msg.id,
                "forum_id": forum_id,
                "speaker_name": new_msg.speaker_name,
                "content": new_msg.content,
                "persona_id": new_msg.persona_id,
                "timestamp": ts
            }
        })
        
        return new_msg
