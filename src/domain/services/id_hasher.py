from __future__ import annotations

import hashlib


def make_id(source: str, url: str) -> str:
    """Hash determinista usado como identidad de `Job` y `RawJob`.

    SHA-1 truncado a 16 hex chars. Idempotente: mismo `(source, url)` siempre
    da el mismo id, lo que permite upserts sin colisión en el pipeline.
    """
    return hashlib.sha1(f"{source}|{url}".encode()).hexdigest()[:16]
