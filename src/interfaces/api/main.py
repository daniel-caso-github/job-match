from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.interfaces.api.dependencies import _embedder_singleton
from src.interfaces.api.routers import health, jobs, matches, profile


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Precarga el embedder (sentence-transformers) para evitar el cold-start
    # en la primera request que dispare scoring.
    _embedder_singleton()
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

# CORS abierto: la API se bindea a 127.0.0.1, sin auth, uso personal.
# Si en algún momento se publica, restringir orígenes.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(matches.router)
app.include_router(profile.router)
app.include_router(jobs.router)
