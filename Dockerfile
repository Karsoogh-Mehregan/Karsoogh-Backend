FROM python:3.12 AS builder

WORKDIR /app

RUN pip install pdm

# Copy the project definition and the lock file
# This is done first to leverage Docker's layer caching
COPY pyproject.toml pdm.lock ./

# Install ONLY production dependencies using the lock file for a reproducible build
# --prod flag ignores dev dependencies
# --no-self ensures the project itself isn't installed in editable mode
RUN pdm install --prod --no-self



FROM python:3.12-slim


WORKDIR /app

# Copy the entire virtual environment created by PDM from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy the application source code
COPY . .

# Activate the virtual environment by adding it to the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Create a non-root user for security
RUN useradd --create-home appuser

# Copy and set permissions for the entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh && chown -R appuser:appuser /app


USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; req = urllib.request.Request('http://localhost:8000/health/', headers={'X-Forwarded-Proto': 'https'}); urllib.request.urlopen(req, timeout=5).read()" || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]