from __future__ import annotations

from sentence_transformers import SentenceTransformer

from src.domain.ports.embedder import Embedder
from src.infrastructure.config import settings


class SentenceTransformersEmbedder(Embedder):
    """Implementación de `Embedder` sobre `sentence-transformers`.

    Modelo por defecto: `BAAI/bge-small-en-v1.5` (384 dims, ~133 MB, CPU).
    Pre-descargado en la imagen Docker (ver `Dockerfile`) para que `embed`
    no haga red en el primer uso.

    Salidas normalizadas L2 — pgvector cosine asume vectores normalizados
    para que `1 - cosine_distance` quede en el rango [0, 1].
    """

    def __init__(self, *, model: str | None = None):
        self._model_name = model or settings.embedding_model
        self._model: SentenceTransformer | None = None

    def _ensure_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vecs = self._ensure_model().encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vecs.tolist()
