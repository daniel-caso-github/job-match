from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from src.interfaces.api.dependencies import _embedder_singleton
from src.interfaces.api.routers import auth, health, jobs, matches, profile


@asynccontextmanager
async def lifespan(app: FastAPI):
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(matches.router)
app.include_router(profile.router)
app.include_router(jobs.router)

Instrumentator().instrument(app).expose(app)
