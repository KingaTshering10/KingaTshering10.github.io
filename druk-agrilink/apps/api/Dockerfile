FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/api

RUN addgroup --system druk && adduser --system --ingroup druk druk

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
      "fastapi==0.115.12" "uvicorn[standard]==0.34.2" "pydantic==2.11.4" \
      "pydantic-settings==2.9.1" "SQLAlchemy==2.0.41" "alembic==1.15.2" \
      "psycopg[binary]==3.2.9" "passlib==1.7.4" "PyJWT==2.10.1" \
      "python-multipart==0.0.20"

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

RUN mkdir -p var/uploads && chown -R druk:druk /srv/api
USER druk

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
