FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System dependencies for common Python packages and database/client libraries.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        curl \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements*.txt ./
RUN python -m pip install --upgrade pip setuptools wheel \
    && if [ -f requirements.txt ]; then pip install -r requirements.txt; fi \
    && if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi

COPY . .

# ASGI startup for incremental Flask-to-FastAPI migration:
# - Keep the current app behavior intact behind an ASGI adapter.
# - Allows running golden-master contract tests and a parity API layer
#   without changing the database schema or existing route semantics.
# - Individual routes can be cut over slice-by-slice while the container
#   continues to serve the legacy Flask app through ASGI.
EXPOSE 8000

ENV PORT=8000 \
    HOST=0.0.0.0 \
    APP_MODULE=app.main:app \
    ASGI_APP_MODULE=app.asgi:application \
    UVICORN_WORKERS=1

CMD ["sh", "-c", "uvicorn ${ASGI_APP_MODULE:-app.asgi:application} --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --workers ${UVICORN_WORKERS:-1}"]
