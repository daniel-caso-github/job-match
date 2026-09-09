from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, status
from pydantic import BaseModel, Field, field_validator

from src.application.use_cases.score_profile import ScoreProfileUseCase
from src.domain.value_objects.cv_extraction import CvExtraction
from src.domain.value_objects.job_requirements import EnglishLevel, Seniority
from src.domain.value_objects.profile_form import _EMAIL_RE, ProfileForm
from src.infrastructure.config import settings
from src.infrastructure.llm.gemini_scorer import GeminiScorer
from src.infrastructure.persistence.database import session_scope
from src.infrastructure.persistence.sqlalchemy_job_repository import (
    SqlAlchemyJobRepository,
)
from src.infrastructure.persistence.sqlalchemy_match_repository import (
    SqlAlchemyMatchRepository,
)
from src.infrastructure.persistence.sqlalchemy_profile_repository import (
    SqlAlchemyProfileRepository,
)
from src.infrastructure.security import hash_password
from src.interfaces.api.dependencies import (
    CurrentProfileDep,
    CvExtractorDep,
    ProfileRepositoryDep,
    SessionDep,
    _embedder_singleton,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["profile"])


class RegisterRequest(BaseModel):
    """Body de POST /profile. Datos de cuenta — el perfil profesional se crea con defaults."""

    username: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    email: str = Field(min_length=3, max_length=254)
    first_name: str | None = Field(default=None, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)
    password: str = Field(min_length=6)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, v: object) -> object:
        return v.strip().lower() if isinstance(v, str) else v

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v: object) -> object:
        if not isinstance(v, str):
            return v
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("email inválido")
        return v


def _run_scoring(form: ProfileForm) -> None:
    """Background task: runs ScoreProfileUseCase in its own transaction.

    The request session is gone by the time this runs, so we open a fresh
    `session_scope()` and instantiate concrete adapters here. The embedder is
    a process-wide singleton (heavy to load); the scorer is cheap to create
    per-call."""
    try:
        with session_scope() as session:
            use_case = ScoreProfileUseCase(
                embedder=_embedder_singleton(),
                llm_scorer=GeminiScorer(),
                profile_repository=SqlAlchemyProfileRepository(session),
                job_repository=SqlAlchemyJobRepository(session),
                match_repository=SqlAlchemyMatchRepository(session),
            )
            n = use_case.execute(form)
        logger.info("Background scoring finished for profile %s: %d matches", form.username, n)
    except Exception:
        logger.exception("Background scoring failed for profile %s", form.username)


@router.post("", status_code=status.HTTP_201_CREATED)
def register_profile(
    body: RegisterRequest,
    bg: BackgroundTasks,
    repo: ProfileRepositoryDep,
    session: SessionDep,
) -> dict:
    username = body.username.strip().lower()
    email = body.email.strip().lower()
    if repo.get_by_username(username) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username ya existe")
    if repo.get_by_email(email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email ya existe")
    form = ProfileForm(
        username=username,
        first_name=body.first_name,
        last_name=body.last_name,
        email=email,
        seniority=Seniority.junior,
        english_level=EnglishLevel.b1,
        location="US",
        modality="remote",
    )
    hashed = hash_password(body.password)
    profile_id = repo.upsert(form, password_hash=hashed)
    session.commit()
    bg.add_task(_run_scoring, form)
    return {"profile_id": profile_id, "username": username, "matching": "scheduled"}


@router.post("/parse-cv")
async def parse_cv(
    extractor: CvExtractorDep,
    current: CurrentProfileDep,
    file: UploadFile,
) -> dict:
    """Extrae una `CvExtraction` propuesta a partir de un CV en PDF.

    Requiere sesión activa (evita pegar a Gemini sin autenticación). No
    persiste nada: el resultado es una propuesta para que el usuario la
    revise/edite en el frontend y confirme el alta/edición vía POST/PUT
    /profile con el ProfileForm resultante.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="solo se acepta PDF (application/pdf)",
        )
    pdf_bytes = await file.read()
    if len(pdf_bytes) > settings.cv_max_pdf_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"el PDF supera el máximo de {settings.cv_max_pdf_bytes} bytes",
        )
    extraction: CvExtraction = extractor.extract(pdf_bytes)
    return extraction.model_dump(mode="json")


@router.get("/{profile_id}")
def get_profile(
    profile_id: str,
    repo: ProfileRepositoryDep,
    current: CurrentProfileDep,
) -> dict:
    if profile_id != current.profile_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="acceso denegado")
    profile = repo.get(profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile not found")
    return profile.form.model_dump(mode="json")


@router.put("/{profile_id}", status_code=status.HTTP_200_OK)
def update_profile(
    profile_id: str,
    form: ProfileForm,
    bg: BackgroundTasks,
    repo: ProfileRepositoryDep,
    session: SessionDep,
    current: CurrentProfileDep,
) -> dict:
    if profile_id != current.profile_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="acceso denegado")
    # Username es inmutable post-registro; forzar el del token para evitar IDOR.
    form = form.model_copy(update={"username": current.username})
    if form.email is not None:
        existing = repo.get_by_email(form.email)
        if existing is not None and existing.id != profile_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email ya existe")
    repo.upsert(form)
    session.commit()
    bg.add_task(_run_scoring, form)
    return {"profile_id": profile_id, "username": form.username, "matching": "scheduled"}
