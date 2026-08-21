# syntax=docker/dockerfile:1
# Контекст сборки — корень репозитория (см. docker-compose.prod.yml).

# --- стадия 1: сборка фронтенда ------------------------------------------
FROM node:22-alpine AS frontend
WORKDIR /build

COPY frontend/package.json frontend/package-lock.json* ./frontend/
RUN cd frontend && npm ci

COPY frontend ./frontend
# vite.config.ts пишет результат в ../backend/frontend_dist
RUN cd frontend && npm run build


# --- стадия 2: рантайм Django --------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# libpq нужен psycopg, остальное — для Pillow (обработка фото собак)
RUN apt-get update && apt-get install --no-install-recommends -y \
        libpq5 libjpeg62-turbo zlib1g curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/ ./
# собранный бандл и манифест Vite из первой стадии
COPY --from=frontend /build/backend/frontend_dist ./frontend_dist

COPY backend/docker-entrypoint.sh /usr/local/bin/entrypoint
RUN chmod +x /usr/local/bin/entrypoint \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /var/app/static /var/app/media \
    && chown -R app:app /app /var/app

USER app

EXPOSE 8000
ENTRYPOINT ["entrypoint"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
