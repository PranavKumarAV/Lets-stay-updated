from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import uvicorn
from contextlib import asynccontextmanager
import logging

# Import submodules relative to the backend package.  When this module
# is executed as part of the ``backend`` package (e.g. via
# ``python -m backend.main`` or ``uvicorn backend.main:app``), these
# relative imports resolve correctly.  Avoid absolute imports like
# ``from api.routes`` to prevent "attempted relative import beyond
# top-level package" errors when the code is packaged.
from .api.routes import router as api_router
from .core.config import settings
from .core.database import init_db
from .services.llm_service import llm_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic for the FastAPI app."""
    logger.info("🚀 Starting up the application...")
    await init_db()
    try:
        yield
    finally:
        # Ensure the LLM service session is closed on shutdown to avoid
        # unclosed aiohttp client warnings.
        try:
            await llm_service.close()
        except Exception as e:
            logger.warning(f"Error closing LLM service session: {e}")
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

# Serve frontend static files for the React SPA.
#
# The compiled frontend assets are placed in ``dist/public`` by the Vite
# build.  We mount this directory as a static file application at the
# root path so that visiting ``/`` returns the ``index.html`` file and
# any nested routes are handled client-side.  API routes defined above
# (under the ``/api`` prefix) take precedence over this mounted
# application, ensuring that ``/api`` still serves JSON.
static_dir = os.path.join(os.path.dirname(__file__), "..", "dist", "public")
if os.path.exists(static_dir):
    # ``html=True`` tells FastAPI to serve ``index.html`` when the root
    # path is requested or when a non-existent file is requested,
    # enabling client-side routing in the React SPA.
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    logger.warning("Static directory %s does not exist; the frontend may not be served.", static_dir)

# Dev entry point
if __name__ == "__main__":
    # When running this module directly, use uvicorn and reference the
    # application via the ``backend.main:app`` module path.  This
    # ensures that uvicorn imports the module within the package
    # namespace, enabling relative imports to work correctly.  The
    # ``reload`` flag is enabled automatically in development mode.
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )
