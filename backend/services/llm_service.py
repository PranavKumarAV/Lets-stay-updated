"""
Universal LLM Service - Groq only (OpenAI-compatible)
"""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import aiohttp

from ..core.llm_config import LLMManager

try:
    import json_repair as _external_json_repair  # type: ignore
    _json_repair = _external_json_repair
except ImportError:
    from ..utils import json_repair as _json_repair  # type: ignore

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        try:
            self.config = LLMManager.get_config_from_env()
        except Exception as e:
            logger.warning(f"LLM config load failed: {e}; running in disabled mode.")
            self.config = None

        self.session: Optional[aiohttp.ClientSession] = None
        self.models_ranked: List[str] = []

        if self.config:
            provider_info = LLMManager.PROVIDERS.get(self.config.provider, {})
            models_info = provider_info.get("models", {}) if provider_info else {}

            preferred_order = [
                "llama3-70b-8192",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
            ]
            available_models = [m for m in preferred_order if m in models_info]
            env_model = self.config.model
            if env_model and env_model not in available_models and env_model in models_info:
                available_models.insert(0, env_model)

            seen = set()
            self.models_ranked = [m for m in available_models if not (m in seen or seen.add(m))]

            logger.info(f"LLM initialized with model fallback order: {self.models_ranked}")
        else:
            logger.info("LLM initialized in disabled mode.")

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def _make_request(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        if not self.config or not self.config.api_key:
            raise Exception("LLM is not configured.")

        session = await self._get_session()
        last_error: Optional[Exception] = None

        for model_name in self.models_ranked or [self.config.model]:
            # Skip models in cooldown
            if model_name in LLMManager._exhausted_models:
                if datetime.utcnow().timestamp() < LLMManager._exhausted_models[model_name]:
                    continue
                else:
                    del LLMManager._exhausted_models[model_name]

            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model_name,
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
                        logger.warning(f"{model_name} failed [{response.status}]: {error_text}")
                        if response.status == 429 or "quota" in error_text.lower():
                            LLMManager._exhausted_models[model_name] = datetime.utcnow().timestamp() + 300
                        last_error = Exception(f"LLM error {response.status}: {error_text}")
            except Exception as e:
                logger.warning(f"{model_name} request failed: {e}")
                last_error = e

        logger.error(f"All LLM models failed: {last_error}")
        raise last_error or Exception("All LLM requests failed.")

    # ------------------------------------------------------------

    async def select_news_sources(self, topics: List[str], region: str) -> List[Dict[str, Any]]:
        if not self.config or not self.config.api_key:
            logger.warning("No API key: falling back to default news sources.")
            return self._get_fallback_sources(topics, region)

        system_prompt = (
            "You are a news curation expert. Recommend 5-8 top news sources for given topics and regions, "
            "considering credibility, coverage, timeliness, and diversity. Output JSON as:\n"
            "{\n"
            "  \"sources\": [\n"
            "    {\"name\": ..., \"type\": ..., \"relevanceScore\": ..., \"credibilityScore\": ..., \"reasoning\": ...}\n"
            "  ]\n"
            "}"
        )
        user_prompt = (
            f"Topics: {', '.join(topics)}\nRegion: {region}\n"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await self._make_request(messages, json_mode=True)
            content = response["choices"][0]["message"]["content"]
            result = _json_repair.loads(content)
            return result.get("sources", [])
        except Exception as e:
            logger.error(f"Failed to select sources: {e}")
            return self._get_fallback_sources(topics, region)

    async def analyze_and_rank_articles(self, articles: List[Dict[str, Any]], topics: List[str], preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not articles or not topics:
            return self._fallback_scoring(articles, topics)
        if not self.config or not self.config.api_key:
            logger.warning("No API key: falling back to heuristic article ranking.")
            return self._fallback_scoring(articles, topics)

        system_prompt = (
            "You are a news expert. Rank articles based on relevance, quality, timeliness, and source credibility.\n"
            "Return: {\"articles\": [{title, content, url, source, topic, ai_score, published_at, reasoning, metadata}]}"
        )

        summary_articles = []
        for i, a in enumerate(articles[:20]):
            summary = a.get("content", "")[:200] + "..." if len(a.get("content", "")) > 200 else a.get("content", "")
            summary_articles.append({
                "id": i,
                "title": a.get("title", ""),
                "content": summary,
                "source": a.get("source", ""),
                "published_at": a.get("published_at", "")
            })

        user_prompt = (
            f"Topics: {', '.join(topics)}\n"
            f"Region: {preferences.get('region', '')}\n"
            f"Preferences: {json.dumps(preferences, indent=2)}\n"
            f"Articles:\n{json.dumps(summary_articles, indent=2)}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await self._make_request(messages, json_mode=True, max_tokens=4000)
            content = response["choices"][0]["message"]["content"]
            result = _json_repair.loads(content)
            ranked = result.get("articles", [])

            final = []
            for r in ranked:
                original = next((a for a in articles if a.get("title") == r.get("title")), None)
                if original:
                    merged = {**original, **r}
                    final.append(merged)
            return sorted(final, key=lambda x: x.get("ai_score", 0), reverse=True)
        except Exception as e:
            logger.error(f"LLM failed to rank articles: {e}")
            return self._fallback_scoring(articles, topics)

    async def generate_article_summary(self, content: str) -> str:
        if not self.config or not self.config.api_key:
            return " ".join(content.split()[:40]) + ("..." if len(content.split()) > 40 else "")

        prompt = (
            "Summarize this news article in one sentence:\n\n"
            f"{content[:1500]}"
        )
        messages = [
            {"role": "system", "content": "You summarize news articles succinctly."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = await self._make_request(messages, max_tokens=100, temperature=0.4)
            text = response["choices"][0]["message"]["content"].strip()
            return re.sub(r"^[\-\•\s]+", "", text)
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            return " ".join(content.split()[:40]) + ("..." if len(content.split()) > 40 else "")

    def _get_fallback_sources(self, topics: List[str], region: str) -> List[Dict[str, Any]]:
        base = [
            {"name": "Reuters", "type": "news_agency", "relevanceScore": 95, "credibilityScore": 98, "reasoning": "Global credibility"},
            {"name": "Associated Press", "type": "news_agency", "relevanceScore": 90, "credibilityScore": 95, "reasoning": "International scope"},
            {"name": "BBC News", "type": "broadcaster", "relevanceScore": 88, "credibilityScore": 92, "reasoning": "Reliable reporting"},
            {"name": "NPR", "type": "broadcaster", "relevanceScore": 86, "credibilityScore": 91, "reasoning": "Depth of analysis"},
            {"name": "The Guardian", "type": "newspaper", "relevanceScore": 84, "credibilityScore": 89, "reasoning": "Investigative strength"},
            {"name": "Substack", "type": "newsletter_platform", "relevanceScore": 82, "credibilityScore": 85, "reasoning": "Expert opinions"},
        ]
        if region != "international":
            base.append({
                "name": f"Local News in {region}",
                "type": "digital_native",
                "relevanceScore": 80,
                "credibilityScore": 75,
                "reasoning": "Regional specificity"
            })
        return base

    def _fallback_scoring(self, articles: List[Dict[str, Any]], topics: List[str]) -> List[Dict[str, Any]]:
        for a in articles:
            score = 50
            combined = (a.get("title", "") + " " + a.get("content", "")).lower()
            for t in topics:
                if t.lower() in combined:
                    score += 10
            a["ai_score"] = min(score, 90)
            a["reasoning"] = "Keyword match fallback scoring"
        return sorted(articles, key=lambda x: x["ai_score"], reverse=True)


# Global instance
llm_service = LLMService()
