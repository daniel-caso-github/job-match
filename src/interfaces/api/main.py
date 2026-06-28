from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.interfaces.api.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Placeholder. Cuando llegue fase 3, aquí precargamos el embedder
    # (sentence-transformers) para evitar el cold-start en la primera request.
    yield


app = FastAPI(
    title="Job Match Pipeline",
    description=(
        "Pipeline de recolección + extracción + scoring de ofertas vs. perfil. "
        "Uso personal. Atribución de fuentes incluida en cada response de matches."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
