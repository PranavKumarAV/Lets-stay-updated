from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
import uvicorn
from contextlib import asynccontextmanager
import logging

from api.routes import router as api_router
from core.config import settings
from core.database import init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up the application...")
    await init_db()
    yield
    # Shutdown
    logger.info("Shutting down the application...")

app = FastAPI(
    title="Let's Stay Updated - AI News Curation",
    description="AI-powered news aggregation and curation platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Service is healthy"}

# Include API routes
app.include_router(api_router, prefix="/api")

# Serve static files in production
if settings.ENVIRONMENT == "production":
    # Mount static files
    static_dir = os.path.join(os.path.dirname(__file__), "..", "dist", "public")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        
        # Serve React app for all other routes
        @app.get("/{full_path:path}")
        async def serve_react_app(full_path: str):
            # Don't serve React app for API routes
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found")
            
            index_file = os.path.join(static_dir, "index.html")
            if os.path.exists(index_file):
                return FileResponse(index_file)
            raise HTTPException(status_code=404, detail="Not found")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )