FROM node:24-alpine AS ui
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 WORKFLOW_ROOT=/app WORKFLOW_DATABASE_PATH=/app/data/workflow.db
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY requirements.lock pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.lock
COPY backend/ backend/
RUN pip install --no-cache-dir --no-deps .
COPY data/fixtures/ data/fixtures/
COPY --from=ui /ui/dist frontend/dist/
RUN useradd --create-home workflow && mkdir -p /app/data && chown -R workflow:workflow /app
USER workflow
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)"
CMD ["python", "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
