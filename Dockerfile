# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# uv (static binary, pinned)
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /usr/local/bin/uv

WORKDIR /app

# Install deps from uv.lock into a project venv at /opt/venv.
# Cache layer: deps depend only on pyproject.toml + uv.lock, not on source.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Pre-download the sentence-transformers model (BAAI/bge-small-en-v1.5, ~133 MB)
# so the first `embed` run doesn't hit the network and tests stay offline.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

COPY src ./src
COPY tests ./tests

ENV PYTHONPATH=/app

CMD ["pytest", "-v"]
