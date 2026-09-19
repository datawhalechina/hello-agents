from app.schemas import UserCreate, PersonaCreate, PersonaUpdate, ForumCreate, MessageCreate
from app.core.hashing import Hasher
from app.db.client import fetch_one, fetch_all, RowObject, db_transaction, db_execute_commit
from app.core.cache import cache_service
import json
import logging
from typing import List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def _normalize_persona(persona):
    if persona and isinstance(getattr(persona, "theories", None), str):
        try:
            theories = json.loads(persona.theories)
            if isinstance(theories, list):
                persona.theories = theories
        except json.JSONDecodeError:
            pass
    return persona

# --- Cache Keys ---
def user_cache_key(username: str): return f"user:{username}"
def persona_cache_key(pid: int): return f"persona:{pid}"
def forum_cache_key(fid: int): return f"forum:{fid}"
def forum_participants_cache_key(fid: int): return f"forum:{fid}:participants"

# --- User ---
def get_user_by_username(db, username: str):
    # Cache Aside: Read
    cache_key = user_cache_key(username)
    cached = cache_service.get_cache(cache_key)
    if cached:
        return RowObject(cached) # Convert dict back to RowObject-like

    rs = db.execute("SELECT * FROM users WHERE username = ?", [username])
    user = fetch_one(rs)
    
    if user:
        cache_service.set_cache(cache_key, user.__dict__, expire=3600)
        
    return user

def create_user(db: Any, user: UserCreate):
    password_bytes = user.password.encode('utf-8')
    if len(password_bytes) > 71:
        password_bytes = password_bytes[:71]
    safe_password = password_bytes.decode('utf-8', 'ignore')
    
    try:
        # Use transaction to ensure commit
        pwd_hash = Hasher.get_password_hash(safe_password)
        created_at = datetime.now()
        rs = db_execute_commit(
            db,
            "INSERT INTO users (username, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?) RETURNING *",
            [user.username, user.email, pwd_hash, user.role, created_at]
        )
        new_user = fetch_one(rs)
            
        if new_user:
             cache_service.set_cache(user_cache_key(new_user.username), new_user.__dict__, expire=3600)
        return new_user
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise

# --- Persona ---
def create_persona(db, persona: PersonaCreate, owner_id: int):
    try:
        theories_json = json.dumps(persona.theories)
        created_at = datetime.now()
        rs = db_execute_commit(
            db,
            """
            INSERT INTO personas (owner_id, name, title, bio, theories, stance, system_prompt, is_public, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            [
                owner_id,
                persona.name,
                persona.title,
                persona.bio,
                theories_json,
                persona.stance,
                persona.system_prompt,
                persona.is_public,
                created_at
            ]
        )
        new_persona = fetch_one(rs)
            
        # Cache Aside: Don't set cache on create. Let the first read populate it.
        # This ensures strict adherence to "DB is source of truth" and lazy loading.
        
        return _normalize_persona(new_persona)
    except Exception as e:
        logger.error(f"Error creating persona: {e}")
        raise

def get_persona(db, persona_id: int):
    cache_key = persona_cache_key(persona_id)
    cached = cache_service.get_cache(cache_key)
    if cached:
        return _normalize_persona(RowObject(cached))

    rs = db.execute("SELECT * FROM personas WHERE id = ?", [persona_id])
    persona = fetch_one(rs)
    persona = _normalize_persona(persona)
    if persona:
        cache_service.set_cache(cache_key, persona.__dict__)
    return persona

def update_persona(db, persona_id: int, updates: PersonaUpdate):
    try:
        update_data = updates.model_dump(exclude_unset=True)
        if not update_data:
            return get_persona(db, persona_id)

        set_clauses = []
        values = []
        for key, value in update_data.items():
            set_clauses.append(f"{key} = ?")
            if key == "theories":
                values.append(json.dumps(value))
            else:
                values.append(value)
        
        values.append(persona_id)
        query = f"UPDATE personas SET {', '.join(set_clauses)} WHERE id = ? RETURNING *"
        
        rs = db_execute_commit(db, query, values)
        updated = fetch_one(rs)
        
        # Sync Strategy: Delete Redis Key on Update
        if updated:
            cache_service.delete_cache(persona_cache_key(persona_id))
            
        return _normalize_persona(updated)
    except Exception as e:
        logger.error(f"Error updating persona: {e}")
        raise

def delete_persona(db, persona_id: int):
    try:
        # Check if exists first to ensure idempotency and clear error
        rs_check = db.execute("SELECT id FROM personas WHERE id = ?", [persona_id])
        if not fetch_one(rs_check):
            return True # Already deleted or not exists

        with db_transaction(db) as tx:
            # Manually set persona_id to NULL in messages to avoid FK violation
            tx.execute("UPDATE messages SET persona_id = NULL WHERE persona_id = ?", [persona_id])
            
            # Cascading deletes should be handled by DB foreign keys, 
            # but let's be explicit if needed or just execute
            rs = tx.execute("DELETE FROM personas WHERE id = ?", [persona_id])
            
            # FORCE COMMIT
            if hasattr(tx, 'commit'):
                tx.commit()
            elif hasattr(db, 'commit'):
                db.commit()
            
        # Sync Strategy: Delete Redis Key on Delete
        cache_service.delete_cache(persona_cache_key(persona_id))
            
        return True
    except Exception as e:
        logger.error(f"Error deleting persona {persona_id}: {e}")
        raise

# --- Forum ---
def create_forum(db, forum: ForumCreate, creator_id: int):
    try:
        with db_transaction(db) as tx:
            rs = tx.execute(
                """
                INSERT INTO forums (topic, creator_id, moderator_id, status, duration_minutes, start_time, summary_history, ablation_flags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                [
                    forum.topic,
                    creator_id,
                    forum.moderator_id,
                    "pending",
                    forum.duration_minutes,
                    None,
                    "[]",
                    "{}"
                ]
            )
            db_forum = fetch_one(rs)

            tx.execute("DELETE FROM messages WHERE forum_id = ?", [db_forum.id])
            tx.execute("DELETE FROM forum_participants WHERE forum_id = ?", [db_forum.id])
            tx.execute("DELETE FROM system_logs WHERE forum_id = ?", [db_forum.id])

            if forum.participant_ids:
                unique_pids = list(dict.fromkeys(int(pid) for pid in forum.participant_ids))
                values = []
                placeholders = []
                for pid in unique_pids:
                    placeholders.append("(?, ?, ?)")
                    values.extend([db_forum.id, pid, "[]"])

                if values:
                    query = f"INSERT INTO forum_participants (forum_id, persona_id, thoughts_history) VALUES {', '.join(placeholders)} ON CONFLICT (forum_id, persona_id) DO NOTHING"
                    tx.execute(query, values)
            
            # FORCE COMMIT
            if hasattr(tx, 'commit'):
                tx.commit()
            elif hasattr(db, 'commit'):
                db.commit()

        # Return full object (will trigger cache set in get_forum)
        return get_forum(db, db_forum.id)
    except Exception as e:
        logger.error(f"Error creating forum: {e}")
        raise

def delete_forum(db, forum_id: int):
    logger.info(f"Attempting to delete forum {forum_id}")
    try:
        with db_transaction(db) as tx:
            tx.execute("DELETE FROM messages WHERE forum_id = ?", [forum_id])
            tx.execute("DELETE FROM forum_participants WHERE forum_id = ?", [forum_id])
            tx.execute("DELETE FROM system_logs WHERE forum_id = ?", [forum_id])
            rs = tx.execute("DELETE FROM forums WHERE id = ?", [forum_id])
            
            affected = rs.rows_affected if hasattr(rs, 'rows_affected') else -1
            logger.info(f"Deleted forum {forum_id}, rows affected: {affected}")
            
            # FORCE COMMIT
            if hasattr(tx, 'commit'):
                tx.commit()
                logger.info("Transaction committed explicitly")
            elif hasattr(db, 'commit'):
                db.commit()
                logger.info("DB committed explicitly")
                
            success = affected > 0 if affected != -1 else True
            
            return success
    except Exception as e:
        logger.error(f"Error deleting forum: {e}")
        raise

def get_forum(db, forum_id: int):
    rs = db.execute("SELECT * FROM forums WHERE id = ?", [forum_id])
    forum = fetch_one(rs)
    if not forum:
        return None
        
    participants = get_forum_participants(db, forum_id)
    setattr(forum, "participants", participants)
    
    if forum.moderator_id:
        mod_rs = db.execute("SELECT * FROM moderators WHERE id = ?", [forum.moderator_id])
        setattr(forum, "moderator", fetch_one(mod_rs))
    else:
        setattr(forum, "moderator", None)
        
    return forum

def update_forum(
    db,
    forum_id: int,
    summary_history: list = None,
    status: str = None,
    start_time: datetime = None,
    ablation_flags: dict = None,
):
    try:
        set_clauses = []
        values = []
        
        if summary_history is not None:
            set_clauses.append("summary_history = ?")
            values.append(json.dumps(summary_history))
            
        if status is not None:
            set_clauses.append("status = ?")
            values.append(status)

        if start_time is not None:
            set_clauses.append("start_time = ?")
            values.append(start_time)

        if ablation_flags is not None:
            set_clauses.append("ablation_flags = ?")
            values.append(json.dumps(ablation_flags))
            
        if not set_clauses:
            return get_forum(db, forum_id)
            
        values.append(forum_id)
        query = f"UPDATE forums SET {', '.join(set_clauses)} WHERE id = ? RETURNING *"
        
        rs = db_execute_commit(db, query, values)
        updated = fetch_one(rs)
        
        return updated
    except Exception as e:
        logger.error(f"Error updating forum: {e}")
        raise

def get_forum_participants(db, forum_id: int):
    query = """
    SELECT fp.*, p.name as persona_name, p.title as persona_title, p.bio as persona_bio, 
           p.theories as persona_theories, p.stance as persona_stance, 
           p.system_prompt as persona_system_prompt, p.owner_id as persona_owner_id,
           p.created_at as persona_created_at
    FROM forum_participants fp
    JOIN personas p ON fp.persona_id = p.id
    WHERE fp.forum_id = ?
    """
    rs = db.execute(query, [forum_id])
    rows = fetch_all(rs)
    
    results = []
    for row in rows:
        persona_data = {
            "id": row.persona_id,
            "name": row.persona_name,
            "title": row.persona_title,
            "bio": row.persona_bio,
            "theories": row.persona_theories,
            "stance": row.persona_stance,
            "system_prompt": row.persona_system_prompt,
            "owner_id": row.persona_owner_id,
            "created_at": row.persona_created_at
        }
        setattr(row, "persona", RowObject(persona_data))
        results.append(row)
    return results

def update_forum_participant(db, forum_id: int, persona_id: int, thoughts_history: list = None):
    try:
        if thoughts_history is None:
            return None
            
        query = "UPDATE forum_participants SET thoughts_history = ? WHERE forum_id = ? AND persona_id = ? RETURNING *"
        rs = db_execute_commit(db, query, [json.dumps(thoughts_history), forum_id, persona_id])
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error updating participant: {e}")
        raise

def create_message(db, message: MessageCreate):
    try:
        timestamp = datetime.now()
        rs = db_execute_commit(
            db,
            """
            INSERT INTO messages (forum_id, persona_id, moderator_id, speaker_name, content, turn_count, thought, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            [
                message.forum_id,
                message.persona_id,
                message.moderator_id,
                message.speaker_name,
                message.content,
                message.turn_count,
                message.thought,
                timestamp
            ]
        )
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error creating message: {e}")
        raise

def get_forum_messages(db, forum_id: int):
    rs = db.execute("SELECT * FROM messages WHERE forum_id = ? ORDER BY timestamp ASC", [forum_id])
    return fetch_all(rs)
