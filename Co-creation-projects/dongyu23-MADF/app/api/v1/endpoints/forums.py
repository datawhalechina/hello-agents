from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Annotated, Any
import json
from app.db.session import get_db
from app.schemas import (
    ForumCreate, 
    ForumResponse, 
    MessageCreate, 
    MessageResponse,
    SystemLogResponse,
    ForumStartRequest
)
from app.crud import get_forum, get_forum_messages, get_forum_participants
from app.crud.crud_system_log import get_system_logs
from app.api.deps import get_current_user
from app.core.websockets import manager
from app.services.forum_service import ForumService
from app.db.client import fetch_all, fetch_one, RowObject
from app.core.cache import cache_service

router = APIRouter()

def get_forum_service(db: Any = Depends(get_db)) -> ForumService:
    return ForumService(db)

def forum_list_cache_key(user_id: int, skip: int, limit: int):
    return f"forums:list:{user_id}:{skip}:{limit}"

def obj_to_dict(obj):
    if isinstance(obj, list):
        return [obj_to_dict(i) for i in obj]
    if hasattr(obj, '__dict__'):
        d = obj.__dict__.copy()
        for k, v in d.items():
            d[k] = obj_to_dict(v)
        return d
    return obj

@router.post("/", response_model=ForumResponse)
def create_new_forum(
    forum: ForumCreate, 
    current_user: Annotated[Any, Depends(get_current_user)],
    service: ForumService = Depends(get_forum_service)
):
    try:
        result = service.create_new_forum(forum, current_user.id)
        
        # Invalidate list cache for this user
        cache_service.delete_keys_pattern(f"forums:list:{current_user.id}:*")
        
        # Ensure result is compatible with ForumResponse
        # If result.summary_history is a string, it might need parsing if Pydantic doesn't handle it
        # But Pydantic validator in ForumResponse should handle it.
        # However, if result is a RowObject, Pydantic's from_attributes=True should handle it.
        
        return result
    except Exception as e:
        # Check if it's a validation error or known exception
        if isinstance(e, HTTPException):
            raise e
        # Log unexpected errors
        import logging
        logging.getLogger(__name__).error(f"Error creating forum: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create forum")

@router.get("/", response_model=List[ForumResponse])
def list_forums(
    db: Any = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: Annotated[Any, Depends(get_current_user)] = None
):
    # Cache Aside
    cache_key = forum_list_cache_key(current_user.id, skip, limit)
    # Increased TTL to 30s to balance responsiveness and DB load
    # Invalidation is handled by create/delete endpoints
    cached_data = cache_service.get_cache(cache_key)
    if cached_data:
        # Reconstruct RowObjects from dicts isn't strictly necessary for Pydantic response,
        # Pydantic can validate from dicts.
        return cached_data

    rs = db.execute(
        "SELECT * FROM forums WHERE creator_id = ? ORDER BY start_time DESC LIMIT ? OFFSET ?",
        [current_user.id, limit, skip]
    )
    
    forums = fetch_all(rs)
    for forum in forums:
        # Populate participants
        participants = get_forum_participants(db, forum.id)
        # Convert participants to dicts for caching immediately? 
        # No, fetch_all returns RowObjects. 
        # We attach RowObjects.
        setattr(forum, "participants", participants)
        
        # Populate moderator
        if forum.moderator_id:
             rs_mod = db.execute("SELECT * FROM moderators WHERE id = ?", [forum.moderator_id])
             mod = fetch_one(rs_mod)
             setattr(forum, "moderator", mod)
        else:
             setattr(forum, "moderator", None)
    
    # Cache Write
    # Serialize to dicts
    forums_data = obj_to_dict(forums)
    cache_service.set_cache(cache_key, forums_data, expire=30) # Increased TTL to 30s
    
    return forums

def _authorized_forum(forum_id: int, db: Any, current_user: Any):
    db_forum = get_forum(db, forum_id=forum_id)
    if db_forum is None:
        raise HTTPException(status_code=404, detail="Forum not found")
    if db_forum.creator_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return db_forum


@router.get("/{forum_id}", response_model=ForumResponse)
def read_forum(
    forum_id: int,
    db: Any = Depends(get_db),
    current_user: Annotated[Any, Depends(get_current_user)] = None,
):
    return _authorized_forum(forum_id, db, current_user)

@router.delete("/{forum_id}")
async def delete_forum_endpoint(
    forum_id: int,
    current_user: Annotated[Any, Depends(get_current_user)],
    service: ForumService = Depends(get_forum_service)
):
    is_admin = current_user.role == 'admin'
    success = await service.delete_forum(forum_id, current_user.id, is_admin)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete forum")
        
    # Invalidate list cache for this user
    cache_service.delete_keys_pattern(f"forums:list:{current_user.id}:*")
    
    return {"message": "Forum deleted successfully"}


@router.post("/{forum_id}/stop")
async def stop_forum_endpoint(
    forum_id: int,
    current_user: Annotated[Any, Depends(get_current_user)],
    service: ForumService = Depends(get_forum_service),
):
    is_admin = current_user.role == "admin"
    return await service.stop_forum(forum_id, current_user.id, is_admin)

@router.post("/{forum_id}/start")
async def start_forum_endpoint(
    forum_id: int,
    request: ForumStartRequest = None,
    current_user: Annotated[Any, Depends(get_current_user)] = None,
    service: ForumService = Depends(get_forum_service)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    is_admin = current_user.role == 'admin'
    ablation_flags = request.ablation_flags if request else None
    return await service.start_forum(forum_id, current_user.id, is_admin, ablation_flags)

@router.post("/{forum_id}/chat", status_code=202)
async def user_chat(
    forum_id: int,
    request: dict,
    db: Any = Depends(get_db),
    current_user: Annotated[Any, Depends(get_current_user)] = None,
):
    """
    Inject a user message into the forum loop.
    Request body: {"speaker": "User", "content": "Hello"}
    """
    _authorized_forum(forum_id, db, current_user)
    speaker = request.get("speaker", "观众")
    content = str(request.get("content", "")).strip()
    
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")
        
    from app.services.forum_scheduler import scheduler
    await scheduler.push_user_message(forum_id, speaker, content)
    return {"status": "queued"}

@router.post("/{forum_id}/messages", response_model=MessageResponse)
async def post_message(
    forum_id: int, 
    message: MessageCreate, 
    service: ForumService = Depends(get_forum_service),
    current_user: Annotated[Any, Depends(get_current_user)] = None,
):
    _authorized_forum(forum_id, service.db, current_user)
    return await service.post_message(forum_id, message)

@router.get("/{forum_id}/messages", response_model=List[MessageResponse])
def get_messages(
    forum_id: int,
    db: Any = Depends(get_db),
    current_user: Annotated[Any, Depends(get_current_user)] = None,
):
    _authorized_forum(forum_id, db, current_user)
    return get_forum_messages(db, forum_id=forum_id)

@router.get("/{forum_id}/logs", response_model=List[SystemLogResponse])
def get_forum_logs(
    forum_id: int,
    db: Any = Depends(get_db),
    current_user: Annotated[Any, Depends(get_current_user)] = None,
):
    _authorized_forum(forum_id, db, current_user)
    return get_system_logs(db, forum_id=forum_id)

@router.websocket("/{forum_id}/ws")
async def websocket_endpoint(websocket: WebSocket, forum_id: int):
    # print(f"WS: Received connection request for forum {forum_id}")
    async def reject_connection():
        # Accept then close so real browser clients observe the policy close
        # code instead of an opaque HTTP handshake rejection.
        await websocket.accept()
        await websocket.close(code=1008)

    token = websocket.query_params.get("token")
    if not token:
        await reject_connection()
        return
    from app.db.session import db_manager
    try:
        db = db_manager.get_connection()
        try:
            from app.core.security import SECRET_KEY, ALGORITHM
            from jose import jwt
            from app.crud import get_user_by_username
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            user = get_user_by_username(db, username) if username else None
            if not user:
                raise ValueError("invalid user")
            _authorized_forum(forum_id, db, user)
        finally:
            db.close()
    except Exception:
        await reject_connection()
        return

    try:
        await manager.connect(websocket, forum_id)
        # print(f"WS: Connection accepted for forum {forum_id}")
    except Exception as e:
        print(f"WS: Connection failed for forum {forum_id}: {e}")
        return

    try:
        while True:
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
            except RuntimeError as e:
                # print(f"WS: RuntimeError in loop for forum {forum_id}: {e}")
                break
            except WebSocketDisconnect:
                # print(f"WS: Client disconnected for forum {forum_id}")
                break
    except Exception as e:
        print(f"WS: Unexpected error for forum {forum_id}: {e}")
    finally:
        # print(f"WS: Cleaning up connection for forum {forum_id}")
        await manager.disconnect(websocket, forum_id)
