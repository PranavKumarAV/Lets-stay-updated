# Multi-stage build: First build the frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/client
COPY client/package*.json ./
RUN npm ci --only=production
COPY client/ ./
RUN npm run build

# Now build the Python backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code into a dedicated subdirectory.  Keeping the package
# structure intact ensures that relative imports (e.g. ``from ..models``)
# resolve correctly when running ``python backend/main.py``.  We avoid
# flattening the backend into the root of the container.
COPY backend/ ./backend/

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/client/dist ./dist

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Start the FastAPI application from within the backend package.  Using
# ``backend/main.py`` preserves the package structure and prevents
# relative import errors (e.g. "attempted relative import beyond
# top-level package").
CMD ["python", "backend/main.py"]