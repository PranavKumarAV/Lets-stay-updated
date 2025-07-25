from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import time
import logging
from datetime import datetime

from ..models.schemas import (
    GenerateNewsRequest, GenerateNewsResponse, 
    GetSourcesRequest, GetSourcesResponse,
    HealthResponse, ErrorResponse
)
# Import the backward compatible GroqService wrapper.  This wrapper
# delegates to the universal LLM service defined in ``services.llm_service``.
from ..services.groq_service_new import groq_service
from ..services.news_aggregator import news_aggregator
from ..core.database import db
from ..core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/news/generate", response_model=GenerateNewsResponse)
async def generate_news(request: GenerateNewsRequest, background_tasks: BackgroundTasks):
    """Generate curated news feed using AI"""
    start_time = time.time()
    
    try:
        # Step 1: AI selects best news sources
        logger.info(f"Selecting sources for topics: {request.topics}")
        selected_sources = await groq_service.select_news_sources(
            topics=request.topics,
            region=request.region,
            excluded_sources=request.excluded_sources or []
        )
        
        if not selected_sources:
            raise HTTPException(status_code=400, detail="No suitable news sources found")
        
        logger.info(f"Selected {len(selected_sources)} sources: {[s['name'] for s in selected_sources]}")
        
        # Step 2: Fetch articles from selected sources
        mock_articles = await news_aggregator.fetch_articles(
            topics=request.topics,
            sources=selected_sources,
            count=request.article_count
        )
        
        if not mock_articles:
            raise HTTPException(status_code=404, detail="No articles found for the specified criteria")
        
        # Step 3: AI analyzes and ranks articles
        logger.info(f"Analyzing {len(mock_articles)} articles with AI")
        ranked_articles = await groq_service.analyze_and_rank_articles(
            articles=mock_articles,
            topics=request.topics,
            preferences={
                "region": request.region,
                "country": request.country,
                "excluded_sources": request.excluded_sources or []
            }
        )
        
        # Step 4: Store top articles in database
        stored_articles = []
        top_articles = ranked_articles[:request.article_count]
        
        for article in top_articles:
            try:
                stored_article = await db.create_news_article({
                    "title": article["title"],
                    "content": article["content"],
                    "url": article["url"],
                    "source": article["source"],
                    "topic": article.get("topic", request.topics[0]),
                    "ai_score": article.get("ai_score", 70),
                    "published_at": article["published_at"],
                    "metadata": article.get("metadata", {})
                })
                stored_articles.append(stored_article)
            except Exception as e:
                logger.error(f"Error storing article: {e}")
                continue
        
        # Schedule cleanup of old articles
        background_tasks.add_task(db.clear_old_articles)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return GenerateNewsResponse(
            articles=stored_articles,
            total_count=len(stored_articles),
            generated_at=datetime.now().isoformat(),
            processing_time_ms=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating news: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate news feed")

@router.post("/news/sources", response_model=GetSourcesResponse)
async def get_news_sources(request: GetSourcesRequest):
    """Get recommended news sources for topics"""
    try:
        sources = await groq_service.select_news_sources(
            topics=request.topics,
            region=request.region,
            excluded_sources=request.excluded_sources or []
        )
        
        return GetSourcesResponse(sources=sources)
        
    except Exception as e:
        logger.error(f"Error getting sources: {e}")
        raise HTTPException(status_code=500, detail="Failed to get news sources")

@router.get("/news/articles")
async def get_cached_articles(
    topics: str = None,
    source: str = None,
    min_ai_score: int = None,
    limit: int = 20
):
    """Get cached articles with optional filtering"""
    try:
        topic_list = topics.split(',') if topics else None
        
        articles = await db.get_news_articles(
            topics=topic_list,
            source=source,
            min_ai_score=min_ai_score,
            limit=limit
        )
        
        return {"articles": articles, "count": len(articles)}
        
    except Exception as e:
        logger.error(f"Error getting articles: {e}")
        raise HTTPException(status_code=500, detail="Failed to get articles")

@router.post("/news/cleanup")
async def cleanup_old_articles():
    """Clean up old articles (maintenance endpoint)"""
    try:
        deleted_count = await db.clear_old_articles()
        return {"message": f"Cleaned up {deleted_count} old articles"}
        
    except Exception as e:
        logger.error(f"Error cleaning up articles: {e}")
        raise HTTPException(status_code=500, detail="Failed to clean up articles")

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Enhanced health check with service status"""
    try:
        # Check if Groq is available
        groq_available = bool(settings.GROQ_API_KEY and groq_service.client)
        
        return HealthResponse(
            status="ok",
            message="Service is healthy",
            timestamp=datetime.now().isoformat(),
            groq_available=groq_available
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "message": str(e)}
        )