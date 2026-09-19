from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas import ModeratorCreate, ModeratorResponse
from app.crud.crud_moderator import get_moderators, create_moderator, get_moderator, delete_moderator
from app.api.deps import get_current_user
from app.models import User

router = APIRouter()

@router.get("/", response_model=List[ModeratorResponse])
def read_moderators(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    moderators = get_moderators(db, skip=skip, limit=limit, creator_id=current_user.id)
    return moderators

@router.post("/", response_model=ModeratorResponse)
def create_new_moderator(
    moderator: ModeratorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return create_moderator(db=db, moderator=moderator, creator_id=current_user.id)

@router.get("/{moderator_id}", response_model=ModeratorResponse)
def read_moderator(
    moderator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_moderator = get_moderator(db, moderator_id=moderator_id)
    if db_moderator is None:
        raise HTTPException(status_code=404, detail="Moderator not found")
    if db_moderator.creator_id != current_user.id and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return db_moderator

@router.delete("/{moderator_id}", response_model=ModeratorResponse)
def delete_existing_moderator(
    moderator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_moderator = get_moderator(db, moderator_id=moderator_id)
    if db_moderator is None:
        raise HTTPException(status_code=404, detail="Moderator not found")
    if db_moderator.creator_id != current_user.id and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return delete_moderator(db=db, moderator_id=moderator_id)
