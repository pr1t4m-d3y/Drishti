# syntax=docker/dockerfile:1
# Stage 1: build wheels so the runtime image carries no compiler or pip cache.
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# Stage 2: minimal runtime, non-root.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PORT=8080
RUN useradd --create-home --uid 10001 drishti
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* && rm -rf /wheels
COPY --chown=drishti:drishti drishti ./drishti
COPY --chown=drishti:drishti ingest ./ingest
COPY --chown=drishti:drishti evals ./evals
COPY --chown=drishti:drishti models ./models
COPY --chown=drishti:drishti data/policies ./data/policies
USER drishti
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health')" || exit 1
CMD ["sh", "-c", "uvicorn drishti.api.main:app --host 0.0.0.0 --port ${PORT}"]
