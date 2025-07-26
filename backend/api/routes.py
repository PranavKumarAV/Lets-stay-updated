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
from typing import List, Dict, Any
# Import the backward compatible GroqService wrapper.  This wrapper
# delegates to the universal LLM service defined in ``services.llm_service``.
from ..services.groq_service_new import groq_service
from ..services.news_aggregator import news_aggregator
import aiohttp
import asyncio
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
        
        # Step 2: Fetch and validate articles from selected sources.  We
        # attempt to fetch more articles than requested to allow for
        # filtering invalid or off-topic entries.  If we don't obtain
        # enough valid articles after several attempts, we'll use
        # whatever we have collected.  Note: this logic explicitly
        # filters articles to ensure they mention at least one of the
        # user-specified topics in either the title or content.  It
        # also continues to fetch additional batches until the
        # requested number of articles is reached or the maximum
        # number of attempts is exceeded.
        desired_count = request.article_count
        max_attempts = 5
        valid_articles: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()

        async def is_url_valid(url: str) -> bool:
            """Check if a URL returns a successful response."""
            try:
                async with aiohttp.ClientSession() as session:
                    # Try HEAD first; fallback to GET if HEAD is not allowed.
                    try:
                        async with session.head(url, allow_redirects=True, timeout=10) as resp:
                            # Consider status codes < 400 as valid
                            if resp.status < 400:
                                return True
                    except Exception:
                        async with session.get(url, allow_redirects=True, timeout=10) as resp_get:
                            if resp_get.status < 400:
                                return True
            except Exception:
                return False
            return False

        def is_article_relevant(article: Dict[str, Any], topics: List[str]) -> bool:
            """Simple heuristic to check if an article mentions any of the user topics.

            Combines the article title and content into a single lower-case
            string and checks if any topic string (also lower-case)
            appears as a substring.  If no topics are provided, all
            articles are considered relevant.
            """
            if not topics:
                return True
            combined_text = f"{article.get('title', '')} {article.get('content', '')}".lower()
            for t in topics:
                t_lower = t.lower().strip()
                if not t_lower:
                    continue
                if t_lower in combined_text:
                    return True
            return False

        for attempt in range(max_attempts):
            # Stop if we've collected enough articles
            if len(valid_articles) >= desired_count:
                break
            # Determine how many more articles we need.  Always request at
            # least 1 article to avoid zero-length requests.  We add a
            # small buffer by requesting the full desired_count on the
            # first attempt and the remaining count on subsequent tries.
            remaining = desired_count - len(valid_articles)
            fetch_count = desired_count if attempt == 0 else max(1, remaining)
            try:
                raw_articles = await news_aggregator.fetch_articles(
                    topics=request.topics,
                    sources=selected_sources,
                    count=fetch_count
                )
            except Exception as e:
                logger.error(f"Error fetching articles on attempt {attempt+1}: {e}")
                continue
            # Validate each article
            for article in raw_articles:
                # Stop if we've reached our target
                if len(valid_articles) >= desired_count:
                    break
                url = article.get("url", "")
                # Skip duplicate URLs or missing URLs
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                # Filter out articles that do not mention the requested topics
                if not is_article_relevant(article, request.topics):
                    continue
                # Validate the URL asynchronously but sequentially to limit open connections
                try:
                    if await is_url_valid(url):
                        valid_articles.append(article)
                except Exception as e:
                    logger.debug(f"URL validation failed for {url}: {e}")
                    continue

        if not valid_articles:
            raise HTTPException(status_code=404, detail="No valid articles found for the specified criteria")

        # Step 3: AI analyzes and ranks articles
        logger.info(f"Analyzing {len(valid_articles)} articles with AI")
        ranked_articles = await groq_service.analyze_and_rank_articles(
            articles=valid_articles,
            topics=request.topics,
            preferences={
                "region": request.region,
                "country": request.country,
                "excluded_sources": request.excluded_sources or []
            }
        )

        # Step 4: Generate summaries and store top articles in database
        stored_articles = []
        top_articles = ranked_articles[:desired_count]

        for article in top_articles:
            # Generate a concise summary using the LLM service
            summary_text = ""
            try:
                summary_text = await groq_service.client.generate_article_summary(article.get("content", "")) if hasattr(groq_service, 'client') else ""
            except Exception as e:
                logger.warning(f"Failed to generate summary for article '{article.get('title', '')}': {e}")
                summary_text = article.get("content", "")[:200] + ("..." if len(article.get("content", "")) > 200 else "")

            # Store summary in metadata
            metadata = article.get("metadata", {}) or {}
            metadata["summary"] = summary_text

            try:
                stored_article = await db.create_news_article({
                    "title": article["title"],
                    "content": article["content"],
                    "url": article["url"],
                    "source": article["source"],
                    "topic": article.get("topic", request.topics[0]),
                    "ai_score": article.get("ai_score", 70),
                    "published_at": article["published_at"],
                    "metadata": metadata
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