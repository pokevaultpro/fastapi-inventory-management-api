from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from app.database import SessionLocal
from app.models import Users
from app.routers.auth import get_current_user


router = APIRouter(prefix="/admin-bootstrap", tags=["admin-bootstrap"])


class PromoteMeRequest(BaseModel):
    setup_token: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def read_current_user_id(user: dict) -> int:
    user_id = user.get("id") or user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: missing user id")
    return int(user_id)


@router.get("/status")
def bootstrap_status(user: user_dependency, db: db_dependency):
    """
    Checks whether bootstrap is configured and shows the current logged user's role.
    Does not expose the secret token.
    """
    user_id = read_current_user_id(user)
    db_user = db.query(Users).filter(Users.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {
        "configured": bool(os.getenv("ADMIN_BOOTSTRAP_TOKEN")),
        "user_id": db_user.id,
        "username": db_user.username,
        "email": db_user.email,
        "role": db_user.role,
        "is_admin": db_user.role == "admin",
    }


@router.post("/promote-me")
def promote_current_user_to_admin(request: PromoteMeRequest, user: user_dependency, db: db_dependency):
    """
    One-time style online bootstrap endpoint.

    How to use:
    1. Set ADMIN_BOOTSTRAP_TOKEN in Render environment variables.
    2. Login normally in the app.
    3. Authorize Swagger with the logged-in JWT.
    4. POST the same setup_token here.
    5. Logout/login again so the new token contains role=admin.
    """
    expected = os.getenv("ADMIN_BOOTSTRAP_TOKEN")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ADMIN_BOOTSTRAP_TOKEN is not configured on the server.",
        )

    if request.setup_token != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid setup token")

    user_id = read_current_user_id(user)
    db_user = db.query(Users).filter(Users.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    old_role = db_user.role
    db_user.role = "admin"
    db.commit()
    db.refresh(db_user)

    return {
        "ok": True,
        "message": "Current user promoted to admin. Logout and login again.",
        "user_id": db_user.id,
        "username": db_user.username,
        "email": db_user.email,
        "old_role": old_role,
        "new_role": db_user.role,
    }
