#!/bin/bash

# Deployment script for Render.com
echo "Starting deployment process..."

# Check if required environment variables are set
if [ -z "$GROQ_API_KEY" ]; then
    echo "Error: GROQ_API_KEY environment variable is required"
    exit 1
fi

# Set NODE_ENV to production if not already set
export NODE_ENV=${NODE_ENV:-production}

echo "Environment: $NODE_ENV"
echo "Port: ${PORT:-5000}"

# Install dependencies
echo "Installing dependencies..."
npm ci --prefer-offline --no-audit

# Type check
echo "Running type check..."
npm run check

# Build the application
echo "Building application..."
npm run build

# Verify build output
if [ ! -f "dist/index.js" ]; then
    echo "Error: Build failed - dist/index.js not found"
    exit 1
fi

if [ ! -d "dist/public" ]; then
    echo "Error: Build failed - dist/public directory not found"
    exit 1
fi

echo "Build completed successfully!"
echo "Ready to start with: npm start"

# Test the health endpoint (optional)
if [ "$NODE_ENV" = "development" ]; then
    echo "Testing health endpoint..."
    timeout 10s npm start &
    SERVER_PID=$!
    sleep 3
    
    if curl -f http://localhost:${PORT:-5000}/health > /dev/null 2>&1; then
        echo "Health check passed!"
    else
        echo "Warning: Health check failed"
    fi
    
    kill $SERVER_PID 2>/dev/null || true
fi

echo "Deployment preparation complete!"