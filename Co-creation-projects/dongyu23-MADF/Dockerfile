# Stage 1: Build the frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy only package files first for better caching
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY frontend/ .

# Build frontend
RUN npm run build

# Stage 2: Final image
FROM python:3.10-slim
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies including Redis server
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Configure pip mirror for faster downloads
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy built frontend assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Copy the rest of the application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose the port
EXPOSE 8000

# Create a startup script to run both Redis and Uvicorn
# Configure Redis to use max 128MB memory and LRU eviction policy
RUN echo '#!/bin/bash\n\
redis-server --daemonize yes --maxmemory 128mb --maxmemory-policy allkeys-lru\n\
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000' > /app/start.sh && chmod +x /app/start.sh

# Default command to run the application
CMD ["/app/start.sh"]
