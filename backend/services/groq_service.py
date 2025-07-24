
import json
import re

def extract_json_from_text(text: str):
    try:
        json_matches = re.findall(r'{.*?}', text, re.DOTALL)
        if json_matches:
            return json.loads(json_matches[0])
    except json.JSONDecodeError as e:
        print("extract_json_from_text error:", e)
    return None

from groq import Groq
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random

from core.config import settings

logger = logging.getLogger(__name__)

class GroqService:
    def __init__(self):
        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY not provided. AI features will use fallback responses.")
            self.client = None
        else:
            self.client = Groq(api_key=settings.GROQ_API_KEY)
    
    async def select_news_sources(self, topics: List[str], region: str, excluded_sources: List[str] = None) -> List[Dict[str, Any]]:
        """Select optimal news sources using Groq AI"""
        if excluded_sources is None:
            excluded_sources = []
            
        if not self.client:
            return self._get_fallback_sources(topics, excluded_sources)
        
        try:
            prompt = f"""You are an AI news curation expert. Select the best news sources for these topics and region.

TOPICS: {', '.join(topics)}
REGION: {region}
EXCLUDED SOURCES: {', '.join(excluded_sources) if excluded_sources else 'None'}

Consider these source types:
- Reddit (community discussions, real-time reactions)
- Twitter/X (breaking news, expert opinions) 
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
            result = json.loads(content)
            sources = result.get('sources', [])
            
            # Filter out excluded sources
            filtered_sources = [
                source for source in sources 
                if source['name'].lower() not in [exc.lower() for exc in excluded_sources]
            ]
            
            return filtered_sources[:12]  # Limit to 12 sources
            
        except Exception as e:
            logger.error(f"Error selecting news sources with Groq: {e}")
            return self._get_fallback_sources(topics, excluded_sources)
    
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
    'content': article['content'][:300] + '...',
    'source': article['source'],
    'topic': article.get('topic', topics[0])
} for idx, article in enumerate(batch)], indent=2)}

For each article, provide:
- originalIndex: the index from the input
- aiScore: 1-100 relevance and quality score
- reasoning: why this score was assigned
- topicMatch: which user topic this best matches

Consider factors:
- Relevance to user topics
- Article recency and timeliness
- Source credibility
- Content quality and depth
- Factual accuracy indicators

Return JSON format:
{{"rankedArticles": [{{"originalIndex": 0, "aiScore": 95, "reasoning": "explanation", "topicMatch": "topic name"}}]}}"""

                response = self.client.chat.completions.create(
                    model=settings.DEFAULT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=settings.MAX_TOKENS,
                    temperature=settings.TEMPERATURE
                )
                
                content = response.choices[0].message.content
                result = json.loads(content)
                
                # Apply AI scores to batch
                for analysis in result.get('rankedArticles', []):
                    if analysis['originalIndex'] < len(batch):
                        article = batch[analysis['originalIndex']].copy()
                        article['ai_score'] = analysis.get('aiScore', 70)
                        article['topic'] = analysis.get('topicMatch', topics[0])
                        article['ai_reasoning'] = analysis.get('reasoning', '')
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
    
    def _get_fallback_sources(self, topics: List[str], excluded_sources: List[str] = None) -> List[Dict[str, Any]]:
        """Fallback news sources when AI is unavailable"""
        if excluded_sources is None:
            excluded_sources = []
        
        all_sources = [
            {"name": "Reddit", "type": "Social Media", "relevanceScore": 85, "credibilityScore": 70, "reasoning": "Community discussions and diverse perspectives"},
            {"name": "X (Twitter)", "type": "Social Media", "relevanceScore": 90, "credibilityScore": 65, "reasoning": "Real-time breaking news and expert opinions"},
            {"name": "Substack", "type": "Newsletter Platform", "relevanceScore": 80, "credibilityScore": 85, "reasoning": "In-depth analysis from subject matter experts"},
            {"name": "Reuters", "type": "Traditional Media", "relevanceScore": 85, "credibilityScore": 95, "reasoning": "Factual reporting with global reach"},
            {"name": "Associated Press", "type": "Traditional Media", "relevanceScore": 85, "credibilityScore": 95, "reasoning": "Reliable wire service with comprehensive coverage"},
            {"name": "BBC News", "type": "Traditional Media", "relevanceScore": 80, "credibilityScore": 90, "reasoning": "International perspective with credible reporting"},
            {"name": "The Guardian", "type": "Traditional Media", "relevanceScore": 75, "credibilityScore": 85, "reasoning": "Progressive perspective with investigative journalism"},
            {"name": "Hacker News", "type": "Tech Community", "relevanceScore": 70, "credibilityScore": 80, "reasoning": "Tech-focused discussions and startup news"},
        ]
        
        # Filter out excluded sources
        filtered_sources = [
            source for source in all_sources 
            if source['name'].lower() not in [exc.lower() for exc in excluded_sources]
        ]
        
        return filtered_sources
    
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