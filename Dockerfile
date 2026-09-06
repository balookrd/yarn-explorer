# ==========================================
# Этап 1: Сборка Frontend (Svelte 5 + Vite)
# ==========================================
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ==========================================
# Этап 2: Финальный образ Backend + Static
# ==========================================
FROM python:3.12-slim

# Системные зависимости для Kerberos и LDAP
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libkrb5-dev \
    krb5-user \
    ldap-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Установка Python зависимостей
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# Копирование исходного кода backend и конфигурации
COPY backend/ ./backend/
COPY config/ ./config/
COPY demo/ ./demo/

# Копирование собранного Frontend из этапа 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Создание непривилегированного пользователя и назначение прав
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appgroup /app

USER appuser

ENV CONFIG_PATH=/app/config/config.yaml \
    PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8080"]
