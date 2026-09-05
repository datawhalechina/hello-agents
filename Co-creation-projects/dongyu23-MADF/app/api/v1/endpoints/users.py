from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, Any
from app.db.session import get_db
from app.schemas import UserCreate, UserResponse
from app.crud import get_user_by_username, create_user
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/", response_model=UserResponse)
def create_new_user(user: UserCreate, db: Any = Depends(get_db)):
    db_user = get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return create_user(db=db, user=user.model_copy(update={"role": "user"}))

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: Annotated[Any, Depends(get_current_user)]):
    return current_user

@router.get("/{username}", response_model=UserResponse)
def read_user(username: str, db: Any = Depends(get_db)):
    db_user = get_user_by_username(db, username=username)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user
