# KaamPilot backend. xhtml2pdf is pure Python, so no system PDF libraries are needed (D-021).
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    KP_STORAGE_DIR=/data

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY evals ./evals
COPY scripts ./scripts
RUN pip install ".[google,openai]"

RUN useradd --create-home --uid 1000 kaampilot && mkdir -p /data && chown kaampilot /data
USER kaampilot
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# One worker: the follow-up scheduler must run in exactly one process (D-013).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
