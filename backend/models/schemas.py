from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class GenerateNewsRequest(BaseModel):
    region: str = Field(..., description="Preferred news region: 'international' or specific country context")
    country: Optional[str] = Field(None, description="Country code (e.g. 'us', 'in') for region-specific results")
    topics: List[str] = Field(..., min_items=1, description="List of topics to fetch news for")
    article_count: int = Field(5, ge=5, le=15, description="Number of articles to generate (5-15)")

class NewsSourceResponse(BaseModel):
    name: str = Field(..., description="Source name")
    type: str = Field(..., description="Source type (e.g. blog, news agency)")
    relevanceScore: int = Field(..., ge=1, le=100, description="Relevance score (1-100)")
    credibilityScore: int = Field(..., ge=1, le=100, description="Credibility score (1-100)")
    reasoning: str = Field(..., description="Reason for selection or exclusion")

class GetSourcesRequest(BaseModel):
    topics: List[str] = Field(..., min_items=1, description="Topics for which sources are requested")
    region: str = Field(..., description="Region of interest (e.g. 'international', 'us')")

class GetSourcesResponse(BaseModel):
    sources: List[NewsSourceResponse] = Field(..., description="List of suggested news sources")

class NewsArticleResponse(BaseModel):
    id: int = Field(..., description="Unique article ID")
    title: str = Field(..., description="Article title")
    content: str = Field(..., description="Full article content")
    url: str = Field(..., description="Canonical article URL")
    source: str = Field(..., description="Source or publication name")
    topic: str = Field(..., description="Matched topic for the article")
    ai_score: int = Field(..., ge=1, le=100, description="AI relevance score (1-100)")
    published_at: datetime = Field(..., description="Datetime when the article was published (UTC)")
    fetched_at: datetime = Field(..., description="Datetime when the article was fetched (UTC)")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional structured metadata")
    summary: Optional[str] = Field(default=None, description="LLM-generated summary (if available)")

class GenerateNewsResponse(BaseModel):
    articles: List[NewsArticleResponse] = Field(..., description="Final list of AI-ranked and summarized articles")
    total_count: int = Field(..., description="Total number of articles returned")
    generated_at: datetime = Field(..., description="Timestamp of news generation (UTC)")
    processing_time_ms: int = Field(..., description="Time taken to generate response (in milliseconds)")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall API status ('ok' or 'unhealthy')")
    message: str = Field(..., description="Descriptive health message")
    timestamp: datetime = Field(..., description="Timestamp of health check (UTC)")
    groq_available: bool = Field(..., description="True if LLM summarizer is available")

class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message returned from the server")
