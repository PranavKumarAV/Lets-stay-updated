# Multi-stage build: First build the frontend
FROM node:18-alpine AS frontend-builder

# The frontend is built using the root package.json.  We set the working
# directory to /app, install the production dependencies defined in the
# root package.json, copy the entire repository, and run the build script.
WORKDIR /app

# Copy package manifests and install dependencies.  We use `npm install`
# instead of `npm ci` because a package-lock.json is not provided in
# this repository.  Installing all dependencies is acceptable here
# because the production-only flag would otherwise require a lock file.
COPY package*.json ./
RUN npm install

# Copy the rest of the source code.  This includes the client/ directory,
# shared code, and the Vite configuration needed for the build.
COPY . .

# Execute the build script defined in package.json.  This will run
# `vite build` and output the static assets to dist/public.
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
COPY --from=frontend-builder /app/dist ./dist

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
# Start the FastAPI application using uvicorn.  Running the app via
# uvicorn ensures that the ``backend`` package is imported correctly
# and relative imports inside the package work as expected.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "5000"]