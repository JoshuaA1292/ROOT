# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir hatch

COPY pyproject.toml .
RUN pip install --no-cache-dir "." --target=/deps

COPY app/ ./app/

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Non-root user for Cloud Run security
RUN addgroup --system app && adduser --system --group app

COPY --from=builder /deps /usr/local/lib/python3.11/site-packages
COPY --from=builder /build/app ./app

USER app

ENV PORT=8000
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
