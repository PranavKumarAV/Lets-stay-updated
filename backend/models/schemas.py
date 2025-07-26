from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class NewsPreferencesCreate(BaseModel):
    region: str = Field(..., description="Region preference: 'international' or 'country'")
    country: Optional[str] = Field(None, description="Specific country if region is 'country'")
    topics: List[str] = Field(..., min_items=1, description="List of topics of interest")
    article_count: int = Field(10, ge=5, le=50, description="Number of articles to return")
    excluded_sources: Optional[List[str]] = Field(default=[], description="Sources to exclude")

class NewsPreferencesResponse(BaseModel):
    id: int
    region: str
    country: Optional[str]
    topics: List[str]
    article_count: int
    excluded_sources: List[str]
    created_at: str

class NewsArticleResponse(BaseModel):
    id: int
    title: str
    content: str
    url: str
    source: str
    topic: str
    ai_score: int = Field(..., ge=1, le=100, description="AI relevance score")
    published_at: str
    fetched_at: str
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional article metadata")
    summary: Optional[str] = Field(default=None, description="Concise summary of the article")

class NewsSourceResponse(BaseModel):
    name: str
    type: str
    relevanceScore: int = Field(..., ge=1, le=100)
    credibilityScore: int = Field(..., ge=1, le=100)
    reasoning: str

class GenerateNewsRequest(BaseModel):
    region: str
    country: Optional[str] = None
    topics: List[str] = Field(..., min_items=1)
    article_count: int = Field(10, ge=5, le=50)
    excluded_sources: Optional[List[str]] = Field(default=[])

class GenerateNewsResponse(BaseModel):
    articles: List[NewsArticleResponse]
    total_count: int
    generated_at: str
    processing_time_ms: Optional[int] = None

class GetSourcesRequest(BaseModel):
    topics: List[str]
    region: str
    excluded_sources: Optional[List[str]] = Field(default=[])

class GetSourcesResponse(BaseModel):
    sources: List[NewsSourceResponse]

class HealthResponse(BaseModel):
    status: str = "ok"
    message: str = "Service is healthy"
    timestamp: Optional[str] = None
    groq_available: bool = False

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: str