from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.application.use_cases.confirm_password_reset import ConfirmPasswordResetUseCase
from src.application.use_cases.request_password_reset import RequestPasswordResetUseCase
from src.infrastructure.security import create_access_token, verify_password
from src.interfaces.api.dependencies import EmailSenderDep, ProfileRepositoryDep, SessionDep

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


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=1, max_length=254)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


@router.post("/forgot-password", status_code=200)
def forgot_password(
    request: ForgotPasswordRequest,
    repo: ProfileRepositoryDep,
    email_sender: EmailSenderDep,
    session: SessionDep,
) -> dict:
    RequestPasswordResetUseCase(repo, email_sender).execute(request.email)
    session.commit()
    return {"detail": "Si el email está registrado, recibirás las instrucciones."}


@router.post("/reset-password", status_code=200)
def reset_password(
    request: ResetPasswordRequest, repo: ProfileRepositoryDep, session: SessionDep
) -> dict:
    ok = ConfirmPasswordResetUseCase(repo).execute(request.token, request.new_password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido o expirado."
        )
    session.commit()
    return {"detail": "Contraseña actualizada."}
