from typing import List, Optional, Any, Union, Dict
from pydantic import BaseModel, ConfigDict, field_validator
import re
from datetime import datetime
import json

# --- User Schemas ---
class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    role: Optional[str] = "user"

class UserCreate(UserBase):
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
            raise ValueError("请输入有效的邮箱地址")
        return normalized

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- Persona Schemas ---
class PersonaBase(BaseModel):
    name: str
    title: Optional[str] = None
    bio: Optional[str] = None
    theories: Optional[List[str]] = [] 
    stance: Optional[str] = None
    system_prompt: Optional[str] = None
    is_public: bool = False

    @field_validator('name')
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('Persona name must not be blank')
        return value

class PersonaCreate(PersonaBase):
    pass

class PersonaUpdate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    theories: Optional[List[str]] = None
    stance: Optional[str] = None
    system_prompt: Optional[str] = None
    is_public: Optional[bool] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError('Persona name must not be blank')
        return value

class PersonaResponse(PersonaBase):
    id: int
    owner_id: int
    created_at: datetime
    theories: Optional[Union[List[str], str]] = []

    model_config = ConfigDict(from_attributes=True)

    @field_validator('theories', mode='before')
    @classmethod
    def parse_theories(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                return []
            except json.JSONDecodeError:
                return []
        elif v is None:
            return []
        return v

# --- Moderator Schemas ---
class ModeratorBase(BaseModel):
    name: str
    title: Optional[str] = "主持人"
    bio: Optional[str] = None
    system_prompt: Optional[str] = None
    greeting_template: Optional[str] = None
    closing_template: Optional[str] = None
    summary_template: Optional[str] = None

class ModeratorCreate(ModeratorBase):
    pass

class ModeratorUpdate(ModeratorBase):
    pass

class ModeratorResponse(ModeratorBase):
    id: int
    creator_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

from .system_log import SystemLogCreate, SystemLogResponse

# --- Forum Schemas ---
class ForumBase(BaseModel):
    topic: str

    @field_validator('topic')
    @classmethod
    def validate_topic(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('讨论主题不能为空')
        if len(value) > 200:
            raise ValueError('讨论主题不能超过 200 个字符')
        return value

class ForumCreate(ForumBase):
    participant_ids: List[int]
    moderator_id: Optional[int] = None # Optional for backward compatibility (can use default)
    duration_minutes: int = 30

    @field_validator('participant_ids')
    @classmethod
    def validate_participants(cls, value: List[int]) -> List[int]:
        unique_ids = list(dict.fromkeys(value))
        if not unique_ids:
            raise ValueError('请至少选择一位智能体')
        if len(unique_ids) > 5:
            raise ValueError('每个论坛最多选择 5 位智能体')
        if any(persona_id <= 0 for persona_id in unique_ids):
            raise ValueError('智能体编号无效')
        return unique_ids

    @field_validator('duration_minutes')
    @classmethod
    def validate_duration(cls, value: int) -> int:
        if value < 1 or value > 120:
            raise ValueError('论坛时长必须在 1 到 120 分钟之间')
        return value

class ForumParticipantResponse(BaseModel):
    persona_id: int
    thoughts_history: Optional[Union[List[Any], str]] = [] # Changed from List[str] to List[Any] to support dicts
    persona: Optional[PersonaResponse] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator('thoughts_history', mode='before')
    @classmethod
    def parse_thoughts_history(cls, v: Any) -> List[Any]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                # If it's a dict (single thought), wrap in list? Or return empty?
                # Based on log, it seems to be a list of dicts.
                return []
            except json.JSONDecodeError:
                return []
        elif isinstance(v, list):
            return v
        elif v is None:
            return []
        return [v] if v else []

class ForumResponse(ForumBase):
    id: int
    creator_id: int
    moderator_id: Optional[int] = None
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = 30
    summary_history: Optional[Union[List[Any], str]] = [] # Changed to List[Any] for flexibility
    ablation_flags: Optional[Dict[str, bool]] = {}
    participants: Optional[List[ForumParticipantResponse]] = []
    moderator: Optional[ModeratorResponse] = None # Include moderator info

    model_config = ConfigDict(from_attributes=True)

    @field_validator('summary_history', mode='before')
    @classmethod
    def parse_summary_history(cls, v: Any) -> List[Any]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                return []
            except json.JSONDecodeError:
                return []
        elif isinstance(v, list):
            return v
        elif v is None:
            return []
        return [v] if v else []

    @field_validator('ablation_flags', mode='before')
    @classmethod
    def parse_ablation_flags(cls, v: Any) -> Dict[str, bool]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return v if isinstance(v, dict) else {}

# --- Message Schemas ---
class MessageBase(BaseModel):
    speaker_name: str
    content: str
    thought: Optional[str] = None # Added thought field
    turn_count: int = 0

class MessageCreate(MessageBase):
    forum_id: int
    persona_id: Optional[int] = None
    moderator_id: Optional[int] = None

class MessageResponse(MessageBase):
    id: int
    forum_id: int
    persona_id: Optional[int]
    moderator_id: Optional[int] = None
    timestamp: datetime
    thought: Optional[str] = None # Ensure it's in response

    model_config = ConfigDict(from_attributes=True)

class TriggerAgentRequest(BaseModel):
    persona_id: Optional[int] = None

class TriggerModeratorRequest(BaseModel):
    action: str = "auto"  # auto, opening, summary, closing

class GodGenerateRequest(BaseModel):
    prompt: str
    n: int = 1

class ForumStartRequest(BaseModel):
    ablation_flags: Optional[Dict[str, bool]] = None

