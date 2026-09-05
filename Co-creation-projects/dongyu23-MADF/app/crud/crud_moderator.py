from typing import List, Optional
from app.schemas import ModeratorCreate, ModeratorUpdate
from app.db.client import fetch_one, fetch_all, RowObject, db_execute_commit
from app.core.cache import cache_service
from datetime import datetime
import json

def moderator_cache_key(mod_id: int): return f"moderator:{mod_id}"
def moderators_list_cache_key(skip: int, limit: int, creator_id: Optional[int]):
    return f"moderators:list:{skip}:{limit}:{creator_id}"

def get_moderator(db, moderator_id: int):
    # Cache Aside: Read
    cache_key = moderator_cache_key(moderator_id)
    cached = cache_service.get_cache(cache_key)
    if cached:
        return RowObject(cached)

    rs = db.execute("SELECT * FROM moderators WHERE id = ?", [moderator_id])
    mod = fetch_one(rs)
    if mod:
        cache_service.set_cache(cache_key, mod.__dict__, expire=3600)
    return mod

def get_moderators(db, skip: int = 0, limit: int = 100, creator_id: Optional[int] = None):
    # Cache Aside: List
    # Only cache if creator_id is None or provided, but with short TTL because list changes
    cache_key = moderators_list_cache_key(skip, limit, creator_id)
    cached_list = cache_service.get_cache(cache_key)
    if cached_list:
        return [RowObject(item) for item in cached_list]

    params = []
    query = "SELECT * FROM moderators"
    
    if creator_id:
        query += " WHERE creator_id = ?"
        params.append(creator_id)
        
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, skip])
    
    rs = db.execute(query, params)
    mods = fetch_all(rs)
    
    # Cache Write
    if mods:
        # Serialize list of RowObjects to list of dicts
        mods_data = [m.__dict__ for m in mods]
        cache_service.set_cache(cache_key, mods_data, expire=300) # Increased TTL to 5 minutes
        
    return mods

def create_moderator(db, moderator: ModeratorCreate, creator_id: int):
    data = moderator.model_dump()
    data['creator_id'] = creator_id
    data['created_at'] = datetime.now()
    
    columns = list(data.keys())
    placeholders = ["?"] * len(columns)
    values = list(data.values())
    
    query = f"""
    INSERT INTO moderators ({', '.join(columns)})
    VALUES ({', '.join(placeholders)})
    RETURNING *
    """
    
    rs = db_execute_commit(db, query, values)
    new_mod = fetch_one(rs)
    
    if new_mod:
        # Update specific cache
        cache_service.set_cache(moderator_cache_key(new_mod.id), new_mod.__dict__, expire=3600)
        # Invalidate list cache
        cache_service.delete_keys_pattern("moderators:list:*")
        
    return new_mod

def delete_moderator(db, moderator_id: int):
    # First get it to return it (matching old behavior)
    mod = get_moderator(db, moderator_id) # This might use cache, which is fine
    if mod:
        db_execute_commit(db, "DELETE FROM moderators WHERE id = ?", [moderator_id])
        # Invalidate specific and list cache
        cache_service.delete_cache(moderator_cache_key(moderator_id))
        cache_service.delete_keys_pattern("moderators:list:*")
    return mod
