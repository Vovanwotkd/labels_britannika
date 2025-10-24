# Backend Dockerfile
# Python 3.11 + FastAPI + SQLite

FROM python:3.11-slim

# Рабочая директория
WORKDIR /app

# Установка системных зависимостей и шрифтов
RUN apt-get update && apt-get install -y \
    gcc \
    cups-client \
    wget \
    unzip \
    fonts-dejavu-core \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Установка Roboto шрифтов с разными весами (100-900)
RUN mkdir -p /usr/share/fonts/truetype/roboto && \
    cd /tmp && \
    wget -q https://github.com/google/roboto/releases/download/v2.138/roboto-unhinted.zip && \
    unzip -q roboto-unhinted.zip -d roboto && \
    cp roboto/*.ttf /usr/share/fonts/truetype/roboto/ && \
    rm -rf roboto roboto-unhinted.zip && \
    fc-cache -f -v

# Копируем requirements
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаём директории для данных
RUN mkdir -p /app/data

# Переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_URL=sqlite:///./data/britannica_labels.db

# Порт приложения
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Инициализация БД и запуск
CMD python scripts/init_db.py && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000
