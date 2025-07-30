from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import time
import logging
from datetime import datetime, timedelta, timezone

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
        # Step 1: Normalize topics.  Replace short forms (e.g. "ai") with
        # descriptive equivalents to improve NewsAPI search relevance.
        transformed_topics = [
            ("artificial intelligence" if t.lower().strip() == "ai" else t)
            for t in request.topics
        ]
        logger.info(f"Fetching articles for topics: {transformed_topics}")

        # Step 2: Fetch and validate articles from the NewsAPI (with fallback to RSS).  We no longer
        # ask the LLM to select sources.  Instead we rely solely on the
        # NewsAPI, rotating through multiple API keys.  If the NewsAPI
        # cannot return any articles due to quota exhaustion or missing
        # results, the aggregator will automatically fall back to RSS feeds.
        desired_count = request.article_count
        max_attempts = 5
        valid_articles: List[Dict[str, Any]] = []

        async def is_url_valid(url: str) -> bool:
            """
            Perform a lightweight HTTP HEAD request to verify that a URL is reachable
            and returns a 200 OK or other valid response code.
            """
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.head(url, allow_redirects=True, timeout=5) as response:
                        return response.status < 400
            except Exception as e:
                # Could log e here if needed
                return False

        def is_article_relevant(article: Dict[str, Any], topics: List[str]) -> bool:
            """Check if an article mentions any of the user topics or their synonyms.

            The function concatenates the article title and content into a
            lower‑case string and checks for the presence of each topic
            string or its known synonyms.  If the topics list is empty,
            all articles are considered relevant.  Synonyms are used to
            improve recall for terms like "artificial intelligence" which may
            appear as "AI" or "machine learning" in headlines.
            """
            if not topics:
                return True
            combined_text = f"{article.get('title', '')} {article.get('content', '')}".lower()
            # Define simple synonyms for select topics
            synonym_map = {
                "artificial intelligence": ["artificial intelligence", "ai", "machine learning", "ml"],
                "ai": ["artificial intelligence", "ai", "machine learning", "ml"],
            }
            for t in topics:
                t_lower = t.lower().strip()
                if not t_lower:
                    continue
                # Expand synonyms if available
                synonyms = synonym_map.get(t_lower, [t_lower])
                for syn in synonyms:
                    if syn in combined_text:
                        return True
            return False

        def is_recent_article(article: Dict[str, Any]) -> bool:
            """Return True if the article was published within the last 7 days."""
            published = article.get("published_at")
            if not published:
                return False
            try:
                # Parse ISO datetime and convert to UTC-aware datetime
                dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                return dt >= now - timedelta(days=7)
            except Exception:
                return False

        # Determine which fetching mode to use based on the user's region
        mode = "global" if request.region == "international" else "local"
        # Default language for filtering; this could be extended to support
        # user-specified languages in the future.  For now, use English.
        language = "en"

        # We'll loop a fixed number of times to accumulate enough articles.
        seen_urls = set()
        page = 1

        for attempt in range(max_attempts):
            if len(valid_articles) >= desired_count:
                break

            remaining = desired_count - len(valid_articles)
            fetch_count = max(1, desired_count * 3) if attempt == 0 else max(1, remaining * 2)

            try:
                raw_articles = await news_aggregator.fetch_articles(
                    transformed_topics,
                    count=fetch_count,
                    page=page,
                    mode=mode,
                    language=language,
                    country=request.country
                )
                page += 1  # next page on next attempt

                for article in raw_articles:
                    if len(valid_articles) >= desired_count:
                        break
                    url = article.get("url", "")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    if not is_article_relevant(article, transformed_topics):
                        continue
                    if not is_recent_article(article):
                        continue
                    if await is_url_valid(url):
                        valid_articles.append(article)
            except Exception as e:
                logger.error(f"Error fetching articles on attempt {attempt+1}: {e}")
                continue

        if not valid_articles:
            # No articles were collected even after exhausting the NewsAPI and RSS fallback.
            # Return an empty result with total_count 0.  The frontend will display
            # a user‑friendly message about the free tier limit.
            processing_time = int((time.time() - start_time) * 1000)
            return GenerateNewsResponse(
                articles=[],
                total_count=0,
                generated_at=datetime.now().isoformat(),
                processing_time_ms=processing_time
            )

        # Step 3: AI analyzes and ranks articles
        logger.info(f"Analyzing {len(valid_articles)} articles with AI")
        ranked_articles = await groq_service.analyze_and_rank_articles(
            articles=valid_articles,
            topics=request.topics,
            preferences={
                "region": request.region,
                "country": request.country,
            }
        )

        # Step 4: Generate summaries and store top articles in database
        stored_articles = []
        top_articles = ranked_articles[:desired_count]

        for article in top_articles:
            # Generate a concise summary using the LLM service
            summary_text = ""
            try:
                content = article.get("content", "")
                if len(content) < 100:
                    summary_text = content
                else:
                    summary_text = await groq_service.client.generate_article_summary(content)

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
        )
        
        return GetSourcesResponse(sources=sources)
        
    except Exception as e:
        logger.error(f"Error getting sources: {e}")
        raise HTTPException(status_code=500, detail="Failed to get news sources")

@router.get("/news/articles")
async def get_cached_articles(
    topics: str = None,
    source: str = None,
    min_ai_score: float = None,
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