"""
Universal LLM Service - Groq only (OpenAI-compatible)
"""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiohttp
from core.llm_config import LLMManager

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.config = LLMManager.get_config_from_env()
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"Initialized LLM service with Groq model: {self.config.model}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def _make_request(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Make request to Groq (OpenAI-compatible) API"""
        session = await self._get_session()

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }

        if kwargs.get("json_mode", False):
            payload["response_format"] = {"type": "json_object"}

        url = f"{self.config.base_url}/chat/completions"

        try:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"LLM API error {response.status}: {error_text}")
                    raise Exception(f"LLM API error: {response.status} - {error_text}")

        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            raise

    async def select_news_sources(
        self, 
        topics: List[str], 
        region: str, 
        excluded_sources: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Use LLM to intelligently select the best news sources"""
        excluded_sources = excluded_sources or []
        
        system_prompt = """You are a news curation expert. Your task is to recommend the best news sources for given topics and regions.

Consider these factors:
1. Source credibility and reputation
2. Coverage quality for the specific topics
3. Regional relevance
4. Diversity of perspectives
5. Timeliness and frequency of updates

Return a JSON array of 5-8 recommended sources with this structure:
{
  "sources": [
    {
      "name": "Source Name",
      "type": "newspaper|magazine|news_agency|broadcaster|digital_native",
      "relevanceScore": 85,
      "credibilityScore": 90,
      "reasoning": "Brief explanation of why this source is recommended"
    }
  ]
}"""

        user_prompt = f"""
Topics: {', '.join(topics)}
Region: {region}
Excluded sources: {', '.join(excluded_sources) if excluded_sources else 'None'}

Please recommend the best news sources for these topics and region. Avoid the excluded sources.
Focus on authoritative, well-established sources with strong coverage in these areas.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = await self._make_request(messages, json_mode=True)
            content = response["choices"][0]["message"]["content"]
            result = json.loads(content)
            sources = result.get("sources", [])
            logger.info(f"Selected {len(sources)} news sources for topics: {topics}")
            return sources
            
        except Exception as e:
            logger.error(f"Error selecting news sources: {e}")
            return self._get_fallback_sources(topics, region)

    async def analyze_and_rank_articles(
        self,
        articles: List[Dict[str, Any]],
        topics: List[str],
        preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Use LLM to analyze and rank articles by relevance and quality"""

        system_prompt = """You are a news analysis expert. Analyze and rank news articles based on:

1. Relevance to user topics (40%)
2. Article quality and depth (25%)
3. Timeliness and newsworthiness (20%)
4. Source credibility (15%)

Score each article from 1-100 and provide brief reasoning.
Return JSON with ranked articles:

{
  "articles": [
    {
      "title": "Original title",
      "content": "Original content",
      "url": "Original URL",
      "source": "Original source",
      "topic": "Most relevant topic",
      "ai_score": 85,
      "published_at": "Original date",
      "reasoning": "Brief analysis of why this scored highly",
      "metadata": {"key": "value"}
    }
  ]
}"""

        articles_summary = []
        for i, article in enumerate(articles[:20]):
            articles_summary.append({
                "id": i,
                "title": article["title"],
                "content": article["content"][:500] + "..." if len(article["content"]) > 500 else article["content"],
                "source": article["source"],
                "published_at": article["published_at"]
            })

        user_prompt = f"""
User topics: {', '.join(topics)}
User region: {preferences.get('region', 'international')}
User preferences: {json.dumps(preferences, indent=2)}

Articles to analyze:
{json.dumps(articles_summary, indent=2)}

Please analyze and rank these articles, returning the full article data with AI scores.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await self._make_request(messages, json_mode=True, max_tokens=4000)
            content = response["choices"][0]["message"]["content"]
            result = json.loads(content)
            ranked_articles = result.get("articles", [])

            final_articles = []
            for ranked in ranked_articles:
                original = next((a for a in articles if a["title"] == ranked["title"]), None)
                if original:
                    final_article = {**original, **ranked}
                    final_articles.append(final_article)

            final_articles.sort(key=lambda x: x.get("ai_score", 0), reverse=True)
            logger.info(f"Analyzed and ranked {len(final_articles)} articles")
            return final_articles
            
        except Exception as e:
            logger.error(f"Error analyzing articles: {e}")
            return self._fallback_scoring(articles, topics)

    def _get_fallback_sources(self, topics: List[str], region: str) -> List[Dict[str, Any]]:
        fallback_sources = [
            {
                "name": "Reuters",
                "type": "news_agency",
                "relevanceScore": 95,
                "credibilityScore": 98,
                "reasoning": "Global news agency with exceptional credibility and comprehensive coverage"
            },
            {
                "name": "Associated Press",
                "type": "news_agency", 
                "relevanceScore": 90,
                "credibilityScore": 95,
                "reasoning": "Reliable international news coverage with fact-checking standards"
            },
            {
                "name": "BBC News",
                "type": "broadcaster",
                "relevanceScore": 88,
                "credibilityScore": 92,
                "reasoning": "Comprehensive global news coverage with editorial standards"
            },
            {
                "name": "NPR",
                "type": "broadcaster",
                "relevanceScore": 86,
                "credibilityScore": 91,
                "reasoning": "High-quality journalism with in-depth analysis"
            },
            {
                "name": "The Guardian",
                "type": "newspaper",
                "relevanceScore": 84,
                "credibilityScore": 89,
                "reasoning": "Strong digital presence with investigative journalism"
            },
            {
                "name": "Substack",
                "type": "newsletter_platform",
                "relevanceScore": 82,
                "credibilityScore": 85,
                "reasoning": "Independent journalists and expert newsletters on specialized topics"
            }
        ]
        
        if region != "international":
            fallback_sources.append({
                "name": "Local News Network",
                "type": "digital_native",
                "relevanceScore": 85,
                "credibilityScore": 80,
                "reasoning": f"Regional coverage for {region}"
            })
        
        return fallback_sources

    def _fallback_scoring(self, articles: List[Dict[str, Any]], topics: List[str]) -> List[Dict[str, Any]]:
        for i, article in enumerate(articles):
            score = 50
            text = f"{article['title']} {article['content']}".lower()
            for topic in topics:
                if topic.lower() in text:
                    score += 10
            score = min(score, 90)
            article["ai_score"] = score
            article["reasoning"] = "Fallback score based on topic keyword match"
        return sorted(articles, key=lambda x: x["ai_score"], reverse=True)
