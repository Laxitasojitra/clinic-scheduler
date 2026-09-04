from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, UserRole

router = APIRouter(tags=["users"])


@router.get("/users/providers")
def list_providers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    providers = db.query(User).filter(User.role == UserRole.provider).all()
    return [{"id": p.id, "full_name": p.full_name} for p in providers]


@router.get("/users/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role.value}
