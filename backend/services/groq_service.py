
import json
import re

# Import the minimal JSON repair utility from the local utils.  This helper
# cleans up common issues such as single quotes and trailing commas before
# passing the string to ``json.loads``.  By using this helper instead of
# ad‑hoc regex extraction we ensure consistent handling of malformed
# language‑model outputs.
# Prefer the external json_repair library if available.  This library
# provides robust repair functions for malformed JSON.  If it is not
# installed, fall back to our local implementation in utils.json_repair.
try:
    import json_repair as _external_json_repair  # type: ignore
    _json_repair = _external_json_repair
except ImportError:
    from ..utils import json_repair as _json_repair  # type: ignore

def extract_json_from_text(text: str):
    """Deprecated: use ``json_repair.loads`` instead.

    This function remains for backward compatibility but now delegates
    directly to ``json_repair.loads``, which repairs and decodes the
    provided string.  The actual implementation used depends on whether
    the external ``json_repair`` library is available.
    """
    try:
        return _json_repair.loads(text)
    except Exception:
        return None

from groq import Groq
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random

# Import the settings relative to the backend package.  A direct
# ``from core.config`` import assumes ``core`` is a top-level package,
# which isn't the case when executing the backend in a local context.
from ..core.config import settings

logger = logging.getLogger(__name__)

class GroqService:
    def __init__(self):
        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY not provided. AI features will use fallback responses.")
            self.client = None
        else:
            self.client = Groq(api_key=settings.GROQ_API_KEY)
    
    async def select_news_sources(self, topics: List[str], region: str) -> List[Dict[str, Any]]:
        """Select optimal news sources using Groq AI"""
            
        if not self.client:
            return self._get_fallback_sources(topics)
        
        try:
            prompt = f"""You are an AI news curation expert. Select the best news sources for these topics and region.

TOPICS: {', '.join(topics)}
REGION: {region}

        Consider these source types:
        - Reddit (community discussions, real-time reactions)
        - Substack (in-depth analysis, expert newsletters)
        - Traditional Media (Reuters, AP, BBC, etc.)
        - Specialized Publications (industry-specific sources)

For each recommended source, provide:
- name: source name
- type: source category
- relevanceScore: 1-100 relevance for these topics
- credibilityScore: 1-100 credibility rating
- reasoning: why this source is good

Return exactly 8-12 diverse sources as JSON:
{{"sources": [{{"name": "source name", "type": "source type", "relevanceScore": 95, "credibilityScore": 90, "reasoning": "explanation"}}]}}"""

            response = self.client.chat.completions.create(
                model=settings.DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=settings.MAX_TOKENS,
                temperature=settings.TEMPERATURE
            )

            content = response.choices[0].message.content
            # Repair and decode the JSON response using json_repair.  Use
            # the external implementation if available, otherwise fall back
            # to our bundled version.
            result = _json_repair.loads(content)
            sources = result.get('sources', [])
                        
            return sources[:10]  # Limit to 10 sources
            
        except Exception as e:
            logger.error(f"Error selecting news sources with Groq: {e}")
            return self._get_fallback_sources(topics)
    
    async def analyze_and_rank_articles(self, articles: List[Dict[str, Any]], topics: List[str], preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze and rank articles using Groq AI"""
        if not self.client or not articles:
            return self._apply_fallback_ranking(articles, topics)
        
        try:
            # Process articles in batches to avoid token limits
            batch_size = 10
            ranked_articles = []
            
            for i in range(0, len(articles), batch_size):
                batch = articles[i:i + batch_size]
                
                prompt = f"""You are an AI news analyst. Analyze and rank these articles based on relevance, credibility, and user preferences.

USER TOPICS: {', '.join(topics)}
USER PREFERENCES: {json.dumps(preferences)}

ARTICLES TO ANALYZE:
{json.dumps([{
    'index': idx,
    'title': article['title'],
    'content': (article.get('content') or '')[:300] + '...',
    'source': article['source'],
    'url': article.get('url', 'N/A'),
    'topic': article.get('topic', topics[0])
} for idx, article in enumerate(articles[i:i + batch_size], start=i)], indent=2)}

For each article, provide:
- originalIndex: the index from the input
- aiScore: 1-100 relevance and quality score
- reasoning: why this score was assigned
- topicMatch: which user topic this best matches

Consider factors:
- Relevance to user topics
- Article recency and timeliness
- Source credibility (e.g., based on domain in URL)
- Content quality and depth
- Factual accuracy indicators

Return JSON format:
{{"rankedArticles": [{{"originalIndex": index from input, "aiScore": measured score, "reasoning": "explanation", "topicMatch": "topic name"}}]}}"""

                response = self.client.chat.completions.create(
                    model=settings.DEFAULT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=settings.MAX_TOKENS,
                    temperature=settings.TEMPERATURE
                )

                content = response.choices[0].message.content
                # Repair and decode the JSON returned by the model
                result = _json_repair.loads(content)
                
                # Apply AI scores to batch
                for analysis in result.get('rankedArticles', []):
                    if analysis['originalIndex'] < len(batch):
                        article = batch[analysis['originalIndex']].copy()
                        article['ai_score'] = analysis.get('aiScore', 70)
                        article['topic'] = analysis.get('topicMatch', topics[0])
                        article['ai_reasoning'] = analysis.get('reasoning', '')
                        article['url'] = batch[analysis['originalIndex']].get('url', 'N/A')
                        ranked_articles.append(article)
            
            # Sort by AI score
            ranked_articles.sort(key=lambda x: x.get('ai_score', 0), reverse=True)
            return ranked_articles
            
        except Exception as e:
            logger.error(f"Error analyzing articles with Groq: {e}")
            return self._apply_fallback_ranking(articles, topics)
    
    async def generate_article_summary(self, content: str) -> str:
        """Generate article summary using Groq AI"""
        if not self.client:
            return content[:200] + "..."
        
        try:
            prompt = f"""Summarize this news article in 2-3 sentences, maintaining key facts and context:

{content[:1500]}"""

            response = self.client.chat.completions.create(
                model=settings.DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating summary with Groq: {e}")
            return content[:200] + "..."
    
    def _get_fallback_sources(self, topics: List[str]) -> List[Dict[str, Any]]:
        """Fallback news sources when AI is unavailable"""
        
        # Predefined fallback sources.  The list intentionally omits Twitter/X to
        # avoid relying on that platform as a news source.
        all_sources = [
            {
                "name": "Reddit",
                "type": "Social Media",
                "relevanceScore": 85,
                "credibilityScore": 70,
                "reasoning": "Community discussions and diverse perspectives",
            },
            {
                "name": "Substack",
                "type": "Newsletter Platform",
                "relevanceScore": 80,
                "credibilityScore": 85,
                "reasoning": "In-depth analysis from subject matter experts",
            },
            {
                "name": "Reuters",
                "type": "Traditional Media",
                "relevanceScore": 85,
                "credibilityScore": 95,
                "reasoning": "Factual reporting with global reach",
            },
            {
                "name": "Associated Press",
                "type": "Traditional Media",
                "relevanceScore": 85,
                "credibilityScore": 95,
                "reasoning": "Reliable wire service with comprehensive coverage",
            },
            {
                "name": "BBC News",
                "type": "Traditional Media",
                "relevanceScore": 80,
                "credibilityScore": 90,
                "reasoning": "International perspective with credible reporting",
            },
            {
                "name": "The Guardian",
                "type": "Traditional Media",
                "relevanceScore": 75,
                "credibilityScore": 85,
                "reasoning": "Progressive perspective with investigative journalism",
            },
            {
                "name": "Hacker News",
                "type": "Tech Community",
                "relevanceScore": 70,
                "credibilityScore": 80,
                "reasoning": "Tech-focused discussions and startup news",
            },
        ]
             
        return all_sources
    
    def _apply_fallback_ranking(self, articles: List[Dict[str, Any]], topics: List[str]) -> List[Dict[str, Any]]:
        """Apply fallback ranking when AI is unavailable"""
        for article in articles:
            # Simple scoring based on title relevance and recency
            score = 60  # Base score
            
            # Boost score if title contains topic keywords
            title_lower = article.get('title', '').lower()
            for topic in topics:
                if topic.lower() in title_lower:
                    score += 20
                    break
            
            # Add some randomness to simulate AI variation
            score += random.randint(-10, 10)
            score = max(1, min(100, score))  # Clamp between 1-100
            
            article['ai_score'] = score
            article['topic'] = topics[0] if topics else 'general'
        
        # Sort by score
        articles.sort(key=lambda x: x.get('ai_score', 0), reverse=True)
        return articles

# Global service instance
groq_service = GroqService()