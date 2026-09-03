from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def require_front_desk(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.front_desk:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Front-desk role required")
    return user


def require_provider(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.provider:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Provider role required")
    return user
