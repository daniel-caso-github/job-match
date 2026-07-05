from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from src.domain.entities.profile import Profile
from src.domain.ports.profile_repository import ProfileRepository
from src.domain.value_objects.profile_form import ProfileForm
from src.infrastructure.persistence import mappers
from src.infrastructure.persistence.orm_models import (
    ProfileModel,
    ProfileSkillModel,
    SkillModel,
)


class SqlAlchemyProfileRepository(ProfileRepository):
    def __init__(self, session: Session):
        self._session = session

    def upsert(self, form: ProfileForm, password_hash: str | None = None) -> str:
        """Upsert por `username`. El RETURNING devuelve el id (UUID) tanto en la
        rama insert como en la update — no cambiar a `on_conflict_do_nothing`,
        que devolvería vacío en conflicto.

        `password_hash` solo se incluye en el set cuando se pasa explícitamente;
        así un re-score no sobreescribe el hash existente.
        """
        values: dict = {
            "username": form.username,
            "first_name": form.first_name,
            "last_name": form.last_name,
            "email": form.email,
            "seniority": form.seniority.value,
            "english_level": form.english_level.value,
            "location": form.location,
            "willing_to_relocate": form.willing_to_relocate,
            "modality": form.modality,
            "salary_min": form.salary_min,
            "salary_max": form.salary_max,
            "salary_currency": form.salary_currency,
            "summary": form.summary,
        }
        if password_hash is not None:
            values["password_hash"] = password_hash
        stmt = pg_insert(ProfileModel).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["username"],
            set_={k: getattr(stmt.excluded, k) for k in values if k != "username"},
        ).returning(ProfileModel.id)
        profile_id = self._session.execute(stmt).scalar_one()
        self._replace_skills(profile_id, form)
        return profile_id

    def _replace_skills(self, profile_id: str, form: ProfileForm) -> None:
        skill_ids: dict[str, int] = {}
        if form.stack:
            names = [t.name for t in form.stack]
            insert_skills = pg_insert(SkillModel).values([{"name": n} for n in names])
            self._session.execute(insert_skills.on_conflict_do_nothing(index_elements=["name"]))
            rows = self._session.execute(
                select(SkillModel.id, SkillModel.name).where(SkillModel.name.in_(names))
            ).all()
            skill_ids = {name: skill_id for skill_id, name in rows}

        self._session.execute(
            delete(ProfileSkillModel).where(ProfileSkillModel.profile_id == profile_id)
        )
        if form.stack:
            self._session.execute(
                pg_insert(ProfileSkillModel).values(
                    [
                        {
                            "profile_id": profile_id,
                            "skill_id": skill_ids[t.name],
                            "years": t.years,
                        }
                        for t in form.stack
                    ]
                )
            )

    def update_embedding(self, profile_id: str, vec: list[float]) -> None:
        model = self._session.get(ProfileModel, profile_id)
        if model is None:
            raise LookupError(f"Profile {profile_id} not found")
        model.embedding = vec

    def get(self, profile_id: str) -> Profile | None:
        model = self._session.get(
            ProfileModel,
            profile_id,
            options=[selectinload(ProfileModel.skills).selectinload(ProfileSkillModel.skill)],
        )
        return mappers.profile_model_to_domain(model) if model else None

    def get_by_username(self, username: str) -> Profile | None:
        model = self._session.scalars(
            select(ProfileModel)
            .where(ProfileModel.username == username)
            .options(
                selectinload(ProfileModel.skills).selectinload(ProfileSkillModel.skill)
            )
        ).one_or_none()
        return mappers.profile_model_to_domain(model) if model else None

    def get_by_email(self, email: str) -> Profile | None:
        model = self._session.scalars(
            select(ProfileModel)
            .where(ProfileModel.email == email)
            .options(
                selectinload(ProfileModel.skills).selectinload(ProfileSkillModel.skill)
            )
        ).one_or_none()
        return mappers.profile_model_to_domain(model) if model else None

    def list_all(self) -> list[Profile]:
        models = self._session.scalars(
            select(ProfileModel).options(
                selectinload(ProfileModel.skills).selectinload(ProfileSkillModel.skill)
            )
        ).all()
        return [mappers.profile_model_to_domain(m) for m in models]
