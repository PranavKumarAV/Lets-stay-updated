# Backward compatibility wrapper for the new universal LLM service
import logging
# Use a relative import here.  The ``services`` package is part of the
# backend package, so ``from services.llm_service`` may fail if the
# backend isn't installed as a top-level module.  Using ``.llm_service``
# ensures the import works regardless of how the package is executed.
from .llm_service import llm_service

logger = logging.getLogger(__name__)

class GroqService:
    """
    Legacy wrapper - now delegates to the universal LLM service
    Maintains backward compatibility while supporting multiple LLM providers
    """
    def __init__(self):
        logger.info("GroqService initialized (now using universal LLM service)")
        self.client = llm_service  # Delegate to universal service
    
    async def select_news_sources(self, topics, region, excluded_sources=None):
        """Delegate to universal LLM service"""
        return await llm_service.select_news_sources(topics, region, excluded_sources)
    
    async def analyze_and_rank_articles(self, articles, topics, preferences):
        """Delegate to universal LLM service"""
        return await llm_service.analyze_and_rank_articles(articles, topics, preferences)

# Global instance for backward compatibility
groq_service = GroqService()