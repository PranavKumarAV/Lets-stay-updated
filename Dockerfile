# Step 1: Build the frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install --omit=dev

# Copy all source files and build frontend
COPY . .
RUN npm run build  # Creates /app/dist

# Step 2: Build the Python backend
FROM python:3.11-slim

WORKDIR /app

# Install OS dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire backend source
COPY backend/ ./  # includes main.py, utils/, etc.

# Copy frontend build output
COPY --from=frontend-builder /app/dist ./dist

# Add a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Corrected CMD path
CMD ["python", "main.py"]
