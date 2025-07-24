from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
    """Startup and shutdown logic for the FastAPI app."""
    logger.info("🚀 Starting up the application...")
    await init_db()
    yield
    logger.info("🛑 Shutting down the application...")

# Initialize FastAPI app
app = FastAPI(
    title="Let's Stay Updated - AI News Curation",
    description="AI-powered news aggregation and curation platform using Groq",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware (adjust for production security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 🔒 Replace with specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Service is healthy"}

# Mount all API routes
app.include_router(api_router, prefix="/api")

# Serve frontend static files if in production mode
if settings.ENVIRONMENT == "production":
    static_dir = os.path.join(os.path.dirname(__file__), "..", "dist", "public")
    
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        
        @app.get("/{full_path:path}")
        async def serve_react_app(full_path: str):
            """Serve index.html for non-API routes (React SPA)"""
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found")
            
            index_file = os.path.join(static_dir, "index.html")
            if os.path.exists(index_file):
                return FileResponse(index_file)
            raise HTTPException(status_code=404, detail="Not found")

# Dev entry point
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )
