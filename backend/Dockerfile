# Backend image — FastAPI + SQLite (local demo).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# Demo data lives on a mounted volume so it survives container restarts.
ENV DATABASE_URL=sqlite:////data/fmcg_sim.db
RUN mkdir -p /data

EXPOSE 8000

# Render (and most PaaS) inject $PORT; fall back to 8000 for local/docker-compose.
# Seed the deterministic offline demo on boot so a fresh deploy shows data
# immediately (DB is ephemeral on free tiers). Seeding never blocks startup.
CMD ["sh", "-c", "python scripts/seed_demo.py --reset-demo || echo 'seed skipped'; uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
