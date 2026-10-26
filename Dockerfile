# API image: FastAPI + the ingest code it calls at signup.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api ./api
COPY ingest ./ingest
COPY sql ./sql
COPY data ./data

RUN useradd --create-home app
USER app

EXPOSE 8000
# Render and similar hosts set PORT; locally it defaults to 8000.
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-server-header"]
