from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List, Any, Union
import json

# Define SystemLog first or import it
from .system_log import SystemLog

class User(BaseModel):
    id: int
    username: str
    password_hash: str
    role: str = "user"
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class Persona(BaseModel):
    id: int
    owner_id: int
    name: str
    title: Optional[str] = None
    bio: Optional[str] = None
    theories: Optional[Union[List[str], str]] = []
    stance: Optional[str] = None
    system_prompt: Optional[str] = None
    is_public: bool = False
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class Moderator(BaseModel):
    id: int
    name: str
    title: Optional[str] = "主持人"
    bio: Optional[str] = None
    system_prompt: Optional[str] = None
    greeting_template: Optional[str] = None
    closing_template: Optional[str] = None
    summary_template: Optional[str] = None
    creator_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ForumParticipant(BaseModel):
    forum_id: int
    persona_id: int
    thoughts_history: Optional[Union[List[Any], str]] = []
    
    model_config = ConfigDict(from_attributes=True)

class Forum(BaseModel):
    id: int
    topic: str
    creator_id: int
    moderator_id: Optional[int] = None
    status: str = "active"
    summary_history: Optional[Union[List[Any], str]] = []
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: int = 30
    
    # Relationships (Optional, populated manually)
    participants: Optional[List[Any]] = None
    moderator: Optional[Moderator] = None
    
    model_config = ConfigDict(from_attributes=True)

class Message(BaseModel):
    id: int
    forum_id: int
    persona_id: Optional[int] = None
    moderator_id: Optional[int] = None
    speaker_name: str
    content: str
    turn_count: int = 0
    thought: Optional[str] = None # Renamed from thoughts to thought
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)

class Observation(BaseModel):
    id: int
    user_id: int
    forum_id: int
    joined_at: datetime
    left_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class GodLog(BaseModel):
    id: int
    god_user_id: int
    action: str
    details: Optional[str] = None
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)
