from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Users
from app.routers.auth import get_current_user


router = APIRouter(
    prefix="/profile",
    tags=["profile"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.get("/role")
def get_profile_role(user: user_dependency, db: db_dependency):
    """
    Returns the current user's role.

    Useful because the JWT token can become stale after an admin changes
    the role. This endpoint reads the current value from the database.
    """
    user_id = user.get("id") or user.get("user_id")
    db_user = db.query(Users).filter(Users.id == user_id).first() if user_id else None

    db_role = getattr(db_user, "role", None) if db_user else None
    token_role = user.get("user_role") or user.get("role")

    return {
        "user_id": user_id,
        "username": getattr(db_user, "username", None) if db_user else user.get("username"),
        "email": getattr(db_user, "email", None) if db_user else user.get("email"),
        "role": db_role or token_role or "user",
        "token_role": token_role,
        "db_role": db_role,
        "is_admin": (db_role or token_role) == "admin",
    }
