from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.infrastructure.security import create_access_token, verify_password
from src.interfaces.api.dependencies import ProfileRepositoryDep

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1)


@router.post("/login")
def login(request: LoginRequest, repo: ProfileRepositoryDep) -> dict:
    profile = repo.get_by_username(request.username.strip().lower())
    # 401 en ambos casos para no filtrar existencia de usuarios.
    if profile is None or profile.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="credenciales incorrectas",
        )
    if not verify_password(request.password, profile.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="credenciales incorrectas",
        )
    token = create_access_token(profile.id, profile.form.username)
    return {
        "access_token": token,
        "token_type": "bearer",
        "profile_id": profile.id,
        "username": profile.form.username,
    }
