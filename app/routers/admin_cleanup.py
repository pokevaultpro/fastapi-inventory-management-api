from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import engine
from app.routers.auth import get_current_user
from app.services.conad_flyer_cleanup import execute_cleanup, preview_cleanup


router = APIRouter(prefix="/admin/cleanup", tags=["admin-cleanup"])


user_dependency = Annotated[dict, Depends(get_current_user)]


def require_admin(user: dict) -> None:
    if not user or user.get("user_role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


class ConadCleanupRequest(BaseModel):
    valid_from: str = "2026-06-15"
    valid_to: str = "2026-06-27"
    delete_images: bool = False
    confirm: bool = False


@router.get("/conad-flyer-products/preview")
def conad_cleanup_preview(
    user: user_dependency,
    valid_from: str = "2026-06-15",
    valid_to: str = "2026-06-27",
):
    require_admin(user)
    try:
        return preview_cleanup(engine, valid_from=valid_from, valid_to=valid_to)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/conad-flyer-products/execute")
def conad_cleanup_execute(user: user_dependency, request: ConadCleanupRequest):
    require_admin(user)
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to execute cleanup.")

    try:
        return execute_cleanup(
            engine,
            valid_from=request.valid_from,
            valid_to=request.valid_to,
            delete_images=request.delete_images,
            project_root=Path.cwd(),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
