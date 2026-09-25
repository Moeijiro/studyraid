FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt asyncpg

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

RUN useradd --create-home --uid 1000 raid && chown -R raid /app
USER raid

EXPOSE 8000
# Migrate, seed the demo world into an empty database, then serve.
CMD ["sh", "-c", "python -m app.seed --if-empty && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
