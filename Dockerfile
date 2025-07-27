# Build frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/client
COPY client/package*.json ./
RUN npm ci --only=production
COPY client/ ./
RUN npm run build

# Backend
FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y \
    curl && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend code
COPY backend/ ./

# Frontend build
COPY --from=frontend-builder /app/client/dist ./dist

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Run FastAPI app located in backend/utils/main.py
CMD ["uvicorn", "utils.main:app", "--host", "0.0.0.0", "--port", "5000"]
