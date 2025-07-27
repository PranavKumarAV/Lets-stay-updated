# Step 1: Build the frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app

# Copy root package files (includes both frontend + shared deps)
COPY package*.json ./

# Install only production dependencies
RUN npm install --omit=dev

# Copy all source files (frontend inside client/)
COPY . .

# Build client (assuming "build-client" is defined in package.json)
RUN npm run build

# Step 2: Build the Python backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy built frontend
COPY --from=frontend-builder /app/client/dist ./dist

# Add non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose backend port
EXPOSE 5000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Start FastAPI backend
CMD ["python", "utils/main.py"]
