from __future__ import annotations

from src.domain.entities.job import Job
from src.domain.value_objects.profile_form import ProfileForm

_RAW_TEXT_CAP = 1500


def job_text_for_embedding(job: Job) -> str:
    """Texto a embeber para una oferta. Concatena los campos más informativos
    y trunca el `raw_text` para mantener el embedding focalizado.

    Si `job.requirements` ya está extraído, lo prepende como hint estructurado
    (mejora la separación semántica entre roles con stacks distintos)."""
    parts: list[str] = [job.title]
    if job.company:
        parts.append(job.company)

    req = job.requirements
    if req is not None:
        if req.stack:
            parts.append("Stack: " + ", ".join(req.stack))
        if req.seniority is not None:
            parts.append(f"Seniority: {req.seniority.value}")

    if job.raw_text:
        parts.append(job.raw_text[:_RAW_TEXT_CAP])

    return "\n".join(p for p in parts if p)


def profile_text_for_embedding(form: ProfileForm) -> str:
    """Texto a embeber para el perfil. Espejo estructural del de jobs."""
    stack_str = ", ".join(f"{t.name} ({t.years:g}y)" for t in form.stack)
    parts = [
        f"Stack: {stack_str}" if stack_str else "Stack: (unspecified)",
        f"Seniority: {form.seniority.value}",
        f"English: {form.english_level.value}",
        f"Location: {form.location}",
        f"Modality: {form.modality}",
    ]
    if form.summary:
        parts.append(form.summary)
    return "\n".join(parts)
