# Step 1: Build the frontend
FROM node:18-alpine AS frontend-builder

# Set working dir to project root (since package.json is here)
WORKDIR /app

COPY package*.json ./
RUN npm install --omit=dev

COPY ./client ./client
RUN npm run build --prefix ./client

# Step 2: Build the Python backend
FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Backend dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/client/dist ./dist

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Port and health
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Start app
CMD ["python", "main.py"]
