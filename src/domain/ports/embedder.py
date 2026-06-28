from __future__ import annotations

from abc import ABC, abstractmethod


class Embedder(ABC):
    """Port: vectoriza textos a embeddings densos.

    Implementación por defecto en
    `src/infrastructure/embedding/sentence_transformers_embedder.py`.

    Contrato:
    - Recibe una lista de textos y devuelve una lista paralela de vectores
      (list[list[float]]). Cada vector debe estar normalizado L2 — el operador
      cosine de pgvector lo asume.
    - Determinista para un mismo input + mismo modelo.
    """

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...
