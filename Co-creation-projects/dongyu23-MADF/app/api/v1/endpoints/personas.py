from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Annotated, Any
import json
import logging
from app.db.session import get_db
from app.schemas import PersonaCreate, PersonaUpdate, PersonaResponse
from app.crud import create_persona, get_persona, update_persona, delete_persona
from app.api.deps import get_current_user
from app.db.client import fetch_all
from app.core.cache import cache_service

logger = logging.getLogger(__name__)

router = APIRouter()

def personas_list_cache_key(owner_id: int, skip: int, limit: int):
    return f"personas:list:{owner_id}:{skip}:{limit}"

def obj_to_dict(obj):
    if isinstance(obj, list):
        return [obj_to_dict(i) for i in obj]
    if hasattr(obj, '__dict__'):
        d = obj.__dict__.copy()
        for k, v in d.items():
            d[k] = obj_to_dict(v)
        return d
    return obj

@router.post("/", response_model=PersonaResponse)
def create_new_persona(
    persona: PersonaCreate, 
    current_user: Annotated[Any, Depends(get_current_user)],
    db: Any = Depends(get_db)
):
    new_persona = create_persona(db=db, persona=persona, owner_id=current_user.id)
    
    # CRITICAL: Fix cache pattern to match what delete_keys_pattern expects
    # In redis scan, the pattern is passed directly.
    # The cache key function is: personas:list:{owner_id}:{skip}:{limit}
    # So we should delete personas:list:{owner_id}:*
    # However, delete_keys_pattern uses scan_iter(match=pattern).
    # Redis scan match pattern works like glob.
    # Let's verify if the pattern string is correct.
    # f"personas:list:{current_user.id}:*" should match "personas:list:1:0:100"
    
    # Invalidate list cache for this user
    cache_service.delete_keys_pattern(f"personas:list:{current_user.id}:*")
    
    return new_persona

@router.post("/batch/preset", response_model=List[PersonaResponse])
def create_preset_personas(
    current_user: Annotated[Any, Depends(get_current_user)],
    db: Any = Depends(get_db)
):
    """
    God mode: Batch create preset personas (Socrates, Aristotle, Confucius, etc.)
    """
    presets = [
        PersonaCreate(
            name="苏格拉底",
            title="古希腊哲学家",
            bio="苏格拉底（Socrates）是古希腊哲学的奠基人之一。他以独特的问答法（精神助产术）著称，通过不断的提问引导人们思考真理、伦理和美德。他自称无知，致力于揭露他人的无知，最终因被控腐蚀青年和不敬神而被判死刑。",
            theories=["精神助产术", "反讽", "辩证法", "知识即美德"],
            stance="质疑一切，追求真理和灵魂的完善。",
            system_prompt="你现在是苏格拉底。请使用苏格拉底式的反讽和助产术与用户对话。不要直接给出答案，而是通过一系列层层递进的问题，引导用户自己发现矛盾并接近真理。你的语气应该是谦逊但敏锐的，经常承认自己的无知（'我只知道一件事，就是我一无所知'）。关注定义、伦理和逻辑一致性。",
            is_public=True
        ),
        PersonaCreate(
            name="孔子",
            title="至圣先师",
            bio="孔子（Confucius）是中国古代伟大的思想家、教育家，儒家学派创始人。他主张'仁'和'礼'，强调道德修养、家庭伦理和社会秩序。他周游列国推行自己的政治主张，晚年致力于教育和整理古籍。",
            theories=["仁", "礼", "中庸", "正名", "德治"],
            stance="维护社会秩序，强调个人道德修养和仁爱之心。",
            system_prompt="你现在是孔子。请以儒家思想为指导与用户对话。你的语言应典雅、平和，多引用《论语》中的智慧。强调'仁爱'、'礼制'、'忠恕'之道。关注人伦关系、社会责任和道德教化。当用户面临困惑时，用温和而坚定的道理通过譬喻或历史典故来启发他们。",
            is_public=True
        ),
        PersonaCreate(
            name="亚里士多德",
            title="百科全书式学者",
            bio="亚里士多德（Aristotle）是古希腊集大成的哲学家和科学家，柏拉图的学生。他的研究范围极其广泛，包括逻辑学、物理学、生物学、伦理学、政治学等。他强调经验观察和逻辑推理，提出了著名的'四因说'。",
            theories=["三段论", "四因说", "中道", "形而上学"],
            stance="理性分析，注重经验事实和逻辑结构。",
            system_prompt="你现在是亚里士多德。请运用严密的逻辑和分类方法与用户对话。倾向于从经验事实出发，通过归纳和演绎来分析问题。使用'三段论'的逻辑结构。关注事物的本质、原因（四因说）和目的。你的语气应是学术、客观且条理清晰的。",
            is_public=True
        ),
        PersonaCreate(
            name="尼采",
            title="权力意志哲学家",
            bio="弗里德里希·尼采（Friedrich Nietzsche）是19世纪德国哲学家。他猛烈抨击传统的基督教道德和现代性，提出了'上帝已死'、'超人'、'权力意志'和'永恒轮回'等激进概念。他的文风充满激情和诗意。",
            theories=["上帝已死", "超人", "权力意志", "永恒轮回", "重估一切价值"],
            stance="打破偶像，肯定生命本能和创造力。",
            system_prompt="你现在是尼采。请用充满激情、格言式甚至略带狂傲的语言与用户对话。挑战传统的道德观念和庸俗的价值观。强调'权力意志'和生命的创造力，呼唤'超人'的诞生。你的观点应具有冲击力和颠覆性，鼓励用户超越自我，直面虚无。",
            is_public=True
        )
    ]

    created_personas = []
    for persona in presets:
        created = create_persona(db=db, persona=persona, owner_id=current_user.id)
        created_personas.append(created)
    
    # Invalidate list cache for this user
    cache_service.delete_keys_pattern(f"personas:list:{current_user.id}:*")
    
    return created_personas

@router.get("/", response_model=List[PersonaResponse])
def read_personas(
    db: Any = Depends(get_db),
    skip: int = 0, 
    limit: int = 100,
    current_user: Annotated[Any, Depends(get_current_user)] = None
):
    # Cache Aside
    cache_key = personas_list_cache_key(current_user.id, skip, limit)
    cached_data = cache_service.get_cache(cache_key)
    if cached_data:
        return cached_data

    rs = db.execute(
        "SELECT * FROM personas WHERE owner_id = ? OR is_public = 1 ORDER BY created_at DESC LIMIT ? OFFSET ?",
        [current_user.id, limit, skip]
    )
    personas = fetch_all(rs)
    
    # Cache Write
    personas_data = obj_to_dict(personas)
    cache_service.set_cache(cache_key, personas_data, expire=10) # Short TTL (10s)
    
    return personas

@router.get("/{persona_id}", response_model=PersonaResponse)
def read_persona(persona_id: int, db: Any = Depends(get_db)):
    db_persona = get_persona(db, persona_id=persona_id)
    if db_persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")
    return db_persona

@router.put("/{persona_id}", response_model=PersonaResponse)
def update_existing_persona(
    persona_id: int, 
    updates: PersonaUpdate, 
    current_user: Annotated[Any, Depends(get_current_user)],
    db: Any = Depends(get_db)
):
    db_persona = get_persona(db, persona_id=persona_id)
    if not db_persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    # Permission check
    if db_persona.owner_id != current_user.id and current_user.role != "god":
        raise HTTPException(status_code=403, detail="Not authorized to update this persona")

    updated_persona = update_persona(db, persona_id=persona_id, updates=updates)
    
    # Invalidate list cache for this user
    cache_service.delete_keys_pattern(f"personas:list:{current_user.id}:*")
    
    return updated_persona

@router.delete("/{persona_id}", status_code=status.HTTP_200_OK)
def delete_existing_persona(
    persona_id: int, 
    current_user: Annotated[Any, Depends(get_current_user)],
    db: Any = Depends(get_db)
):
    db_persona = get_persona(db, persona_id=persona_id)
    if not db_persona:
        # Idempotent: if already gone, return success but maybe with info
        return {"message": "Persona already deleted or not found", "id": persona_id}

    # Permission check
    if db_persona.owner_id != current_user.id and current_user.role != "god":
        raise HTTPException(status_code=403, detail="Not authorized to delete this persona")

    references = fetch_all(
        db.execute(
            "SELECT forum_id FROM forum_participants WHERE persona_id = ? LIMIT 1",
            [persona_id],
        )
    )
    if references:
        raise HTTPException(status_code=409, detail="该智能体已被论坛引用，无法删除")

    try:
        success = delete_persona(db, persona_id=persona_id)
        
        # Invalidate list cache for this user
        cache_service.delete_keys_pattern(f"personas:list:{current_user.id}:*")
        
        if not success:
             raise HTTPException(status_code=500, detail="Database failed to delete the record")
             
        return {"message": "Persona deleted successfully", "id": persona_id}
    except Exception as e:
        logger.error(f"Delete failed for {persona_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete persona")
