from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List, Annotated, Any
import json
import logging

from app.db.session import get_db
from app.schemas import PersonaResponse, GodGenerateRequest, PersonaCreate
from app.crud import create_persona
from app.api.deps import get_current_user
# from app.agent.god import God  # Deprecated
from app.agent.real_god import RealGodAgent
from app.core.async_utils import async_generator_wrapper
from app.core.cache import cache_service
from app.services.persona_service import persona_service
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()
# god = God() # Deprecated

# @router.post("/generate", response_model=List[PersonaResponse])
# def generate_personas(
#     request: GodGenerateRequest,
#     current_user: Annotated[Any, Depends(get_current_user)],
#     db: Any = Depends(get_db)
# ):
#     """
#     Generate personas based on natural language prompt using the God agent.
#     DEPRECATED: Use /generate_real instead.
#     """
#     raise HTTPException(status_code=410, detail="This endpoint is deprecated. Use RealGodAgent.")

@router.post("/generate_real")
async def generate_real_personas(
    request: GodGenerateRequest,
    current_user: Annotated[Any, Depends(get_current_user)],
    db: Any = Depends(get_db)
):
    """
    Generate personas using RealGodAgent with internet search capabilities.
    Each persona is generated sequentially to ensure high quality and deep research.
    Returns a StreamingResponse with SSE events.
    """
    if not settings.has_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="模型服务尚未配置，暂时无法生成角色。请联系管理员配置 API Key。",
        )

    agent = RealGodAgent()
    user_id = current_user.id
    
    # 1. Fetch all existing persona names from DB for global deduplication
    try:
        rs = db.execute("SELECT name FROM personas")
        # rs.fetchall() returns list of Row objects or tuples?
        # fetch_all returns list of RowObject
        from app.db.client import fetch_all
        rows = fetch_all(rs)
        db_existing_names = [r.name for r in rows if hasattr(r, 'name')]
    except Exception as e:
        logger.error(f"Error fetching existing names: {e}")
        db_existing_names = []

    async def event_generator():
        try:
            generated_names_in_session = []
            saved_persona_count = 0
            
            # Use n=None to allow the agent to auto-detect count from prompt
            target_n = request.n if request.n > 1 else None
            
            async for event in async_generator_wrapper(agent.run(request.prompt, n=target_n, generated_names=generated_names_in_session, db_existing_names=db_existing_names)):
                if event.get("type") == "error":
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    return
                
                # If result, save to DB
                if event["type"] == "result":
                    personas_data = event["content"]
                    saved_personas_dicts = []
                    
                    # Ensure it's a list
                    if isinstance(personas_data, dict):
                        personas_data = [personas_data]
                        
                    for p_data in personas_data:
                        # Add name to session list
                        # Safe check for name
                        if isinstance(p_data, dict) and p_data.get('name'):
                            generated_names_in_session.append(p_data['name'])
                        
                        # Use unified service
                        try:
                            if not isinstance(p_data, dict):
                                logger.error(f"Invalid persona data format: {p_data}")
                                continue
                                
                            # Log debug info
                            msg_content = f"正在保存角色: {p_data.get('name', 'Unknown')}..."
                            yield f"data: {json.dumps({'type': 'status', 'content': msg_content}, ensure_ascii=False)}\n\n"
                            
                            saved_p = persona_service.save_generated_persona(user_id, p_data, db=db)
                            
                            if saved_p:
                                # Parse theories from JSON string to List if needed
                                theories_val = saved_p.theories
                                if isinstance(theories_val, str):
                                    try:
                                        theories_val = json.loads(theories_val)
                                    except:
                                        theories_val = []

                                # Convert to dict for JSON serialization
                                saved_dict = {
                                    "id": saved_p.id,
                                    "name": saved_p.name,
                                    "title": saved_p.title,
                                    "bio": saved_p.bio,
                                    "theories": theories_val,
                                    "stance": saved_p.stance,
                                    "system_prompt": saved_p.system_prompt,
                                    "is_public": saved_p.is_public
                                }
                                saved_personas_dicts.append(saved_dict)
                                saved_persona_count += 1
                                success_msg = f"✅ 角色 {saved_p.name} 保存成功 (ID: {saved_p.id})"
                                yield f"data: {json.dumps({'type': 'status', 'content': success_msg}, ensure_ascii=False)}\n\n"
                                
                                # CRITICAL: Ensure cache is invalidated for the list view
                                cache_service.delete_keys_pattern(f"personas:list:{user_id}:*")
                            else:
                                fail_msg = f"角色 {p_data.get('name')} 保存失败，请查看后台日志"
                                yield f"data: {json.dumps({'type': 'error', 'content': fail_msg}, ensure_ascii=False)}\n\n"
                                return
                                
                        except Exception as e:
                            logger.error(f"Error saving real persona: {e}")
                            err_msg = "角色保存失败，请稍后重试"
                            yield f"data: {json.dumps({'type': 'error', 'content': err_msg}, ensure_ascii=False)}\n\n"
                            return
                    
                    # Update content with saved personas (including IDs)
                    event["content"] = saved_personas_dicts
                
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            if saved_persona_count:
                final_msg = "✅ 所有智能体角色已生成并保存完毕。已停止生成。"
                yield f"data: {json.dumps({'type': 'thought', 'content': final_msg}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'content': '未能生成可保存的角色，请稍后重试'}, ensure_ascii=False)}\n\n"
                    
        except Exception as e:
            logger.error(f"RealGod stream error: {e}")
            err_msg = "角色生成失败，请稍后重试"
            yield f"data: {json.dumps({'type': 'error', 'content': err_msg}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
