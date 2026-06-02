# syntax=docker/dockerfile:1

# --- Build dependencies into a project-local venv ---
FROM python:3.13-slim AS builder

ENV PDM_CHECK_UPDATE=false \
    PDM_VENV_IN_PROJECT=true \
    PDM_IGNORE_STORED_PYTHON=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir pdm

COPY pyproject.toml pdm.lock ./

RUN pdm install --prod --no-editable


# --- Production runtime ---
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/app/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=core.settings

WORKDIR /app

# Pillow and other binary wheels need these at runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        libpng16-16 \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home --home-dir /home/appuser appuser

COPY --from=builder /app/.venv /app/.venv

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod 755 /docker-entrypoint.sh

COPY --chown=appuser:appuser . .

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/', timeout=5)"

ENTRYPOINT ["/docker-entrypoint.sh"]
