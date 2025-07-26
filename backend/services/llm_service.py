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
# Import configuration manager relative to the backend package.  Using
# a relative import ensures the module can be resolved whether the
# package is installed or executed directly.
from ..core.llm_config import LLMManager
# Import the json_repair module.  We use ``json_repair.loads`` to
# repair and decode JSON responses from the LLM.
# Attempt to import the external json_repair library.  If it's not
# available (for example, during local development), fall back to
# our bundled implementation in ``backend.utils.json_repair``.
try:
    import json_repair as _external_json_repair  # type: ignore
    _json_repair = _external_json_repair
except ImportError:
    from ..utils import json_repair as _json_repair  # type: ignore

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        """
        Initialize the LLM service.

        Attempt to load the configuration from environment variables.  If
        a required API key is missing, fall back to a disabled state that
        will never attempt to contact the remote LLM API.  This allows
        the service to operate in a degraded mode using fallback
        heuristics without raising an exception at import time.

        Additionally, prepare a ranked list of free-tier models.  When
        making requests to the Groq API, we will try these models in
        sequence.  If one model fails due to rate limits or other
        errors, the next model in the list will be attempted.  This
        improves resilience when operating with free-tier limits.
        """
        try:
            self.config = LLMManager.get_config_from_env()
        except Exception as e:
            # When no API key is provided, log a warning and disable the LLM.
            logger.warning(
                f"LLM configuration could not be loaded ({e}); operating without an API key."
            )
            self.config = None
        self.session: Optional[aiohttp.ClientSession] = None
        # Build a ranked list of models based on the provider metadata.
        self.models_ranked: List[str] = []
        if self.config is not None:
            provider_info = LLMManager.PROVIDERS.get(self.config.provider, {})
            models_info = provider_info.get("models", {}) if provider_info else {}
            # Define a manual ranking of the available models.  Higher
            # priority models appear first.  If new models are added,
            # include them here with an appropriate ordering.
            preferred_order = [
                "llama3-70b-8192",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
            ]
            # Filter only those models that are present in the provider's
            # metadata and available for free tier usage.  Preserve the
            # preferred order.  If the environment specifies a custom model
            # via LLM_MODEL, ensure it is placed at the front of the list.
            available_models = [m for m in preferred_order if m in models_info]
            env_model = self.config.model if hasattr(self.config, "model") else None
            if env_model and env_model not in available_models and env_model in models_info:
                available_models.insert(0, env_model)
            # Remove duplicates while preserving order
            seen = set()
            self.models_ranked = [m for m in available_models if not (m in seen or seen.add(m))]
            logger.info(
                f"Initialized LLM service with model fallback order: {self.models_ranked}"
            )
        else:
            logger.info(
                "Initialized LLM service in disabled mode (no API key available)"
            )

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def _make_request(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Make a request to the Groq API, trying multiple models if necessary.

        The LLM service maintains a ranked list of models to use.  When
        invoking the API we iterate through this list.  If a request
        fails (for example due to rate limiting or other errors), we log
        the error and attempt the next model.  If all models fail, the
        last error is propagated.
        """
        # If no configuration is available, immediately raise.  This
        # indicates the LLM is disabled and callers should fallback.
        if not self.config or not getattr(self.config, "api_key", None):
            raise Exception("LLM is not configured; cannot make request")

        session = await self._get_session()
        last_error: Optional[Exception] = None
        for model_name in self.models_ranked or [self.config.model]:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_name,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens if self.config else 2048),
                "temperature": kwargs.get("temperature", self.config.temperature if self.config else 0.7),
            }
            if kwargs.get("json_mode", False):
                payload["response_format"] = {"type": "json_object"}
            url = f"{self.config.base_url}/chat/completions"
            try:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        # On success, return the JSON response
                        result = await response.json()
                        return result
                    else:
                        # Capture error text and try next model
                        error_text = await response.text()
                        err_msg = f"LLM API error {response.status}: {error_text}"
                        logger.warning(f"Model {model_name} failed: {err_msg}")
                        last_error = Exception(err_msg)
                        # Try next model
                        continue
            except Exception as e:
                # Network or other error; log and move on
                logger.warning(f"LLM request failed for model {model_name}: {e}")
                last_error = e
                continue
        # If we exit the loop without returning, propagate the last error
        if last_error:
            logger.error(f"All LLM models failed: {last_error}")
            raise last_error
        # Should not reach here; raise generic error
        raise Exception("LLM request failed for all models")

    async def select_news_sources(
        self, 
        topics: List[str], 
        region: str, 
        excluded_sources: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Use LLM to intelligently select the best news sources"""
        excluded_sources = excluded_sources or []

        # If no configuration or API key is available, immediately return fallback sources.
        if not self.config or not getattr(self.config, "api_key", None):
            logger.warning(
                "No LLM API key configured; falling back to default news sources."
            )
            return self._get_fallback_sources(topics, region)

        system_prompt = (
            "You are a news curation expert. Your task is to recommend the best news sources "
            "for given topics and regions.\n\n"
            "Consider these factors:\n"
            "1. Source credibility and reputation\n"
            "2. Coverage quality for the specific topics\n"
            "3. Regional relevance\n"
            "4. Diversity of perspectives\n"
            "5. Timeliness and frequency of updates\n\n"
            "Return a JSON array of 5-8 recommended sources with this structure:\n"
            "{\n"
            "  \"sources\": [\n"
            "    {\n"
            "      \"name\": \"Source Name\",\n"
            "      \"type\": \"newspaper|magazine|news_agency|broadcaster|digital_native\",\n"
            "      \"relevanceScore\": 85,\n"
            "      \"credibilityScore\": 90,\n"
            "      \"reasoning\": \"Brief explanation of why this source is recommended\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        user_prompt = (
            f"Topics: {', '.join(topics)}\n"
            f"Region: {region}\n"
            f"Excluded sources: {', '.join(excluded_sources) if excluded_sources else 'None'}\n\n"
            "Please recommend the best news sources for these topics and region. Avoid the excluded sources.\n"
            "Focus on authoritative, well-established sources with strong coverage in these areas.\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await self._make_request(messages, json_mode=True)
            content = response["choices"][0]["message"]["content"]

            try:
                # Repair and decode the JSON response using json_repair.  This
                # helper fixes common issues and decodes the result into a
                # Python object.  We reference the module via `_json_repair`,
                # which points to either the external library or our fallback.
                result = _json_repair.loads(content)
            except Exception as parse_err:
                logger.warning(
                    f"Failed to parse LLM source recommendation response as JSON: {parse_err}.\n"
                    f"Raw content: {content[:200]}..."
                )
                raise

            sources = result.get("sources", [])
            # Filter out any excluded sources that slipped through
            filtered_sources = [
                src
                for src in sources
                if src.get("name", "").lower() not in [exc.lower() for exc in excluded_sources]
            ]
            logger.info(
                f"Selected {len(filtered_sources)} news sources for topics: {topics}"
            )
            return filtered_sources
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
        # Early exit if we have no articles or no LLM configuration
        if not articles or not topics:
            return self._fallback_scoring(articles, topics)
        if not self.config or not getattr(self.config, "api_key", None):
            logger.warning(
                "No LLM API key configured; falling back to heuristic article scoring."
            )
            return self._fallback_scoring(articles, topics)

        system_prompt = (
            "You are a news analysis expert. Analyze and rank news articles based on:\n\n"
            "1. Relevance to user topics (40%)\n"
            "2. Article quality and depth (25%)\n"
            "3. Timeliness and newsworthiness (20%)\n"
            "4. Source credibility (15%)\n\n"
            "Score each article from 1-100 and provide brief reasoning.\n"
            "Return JSON with ranked articles:\n\n"
            "{\n"
            "  \"articles\": [\n"
            "    {\n"
            "      \"title\": \"Original title\",\n"
            "      \"content\": \"Original content\",\n"
            "      \"url\": \"Original URL\",\n"
            "      \"source\": \"Original source\",\n"
            "      \"topic\": \"Most relevant topic\",\n"
            "      \"ai_score\": 85,\n"
            "      \"published_at\": \"Original date\",\n"
            "      \"reasoning\": \"Brief analysis of why this scored highly\",\n"
            "      \"metadata\": {\"key\": \"value\"}\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        # Summarize up to the first 20 articles to stay within token limits
        articles_summary = []
        for i, article in enumerate(articles[:20]):
            summary_content = article.get("content", "")
            # Truncate content to reduce token usage.  Limiting to 200 characters
            # helps keep the prompt within the free tier token limits.
            if len(summary_content) > 200:
                summary_content = summary_content[:200] + "..."
            articles_summary.append(
                {
                    "id": i,
                    "title": article.get("title", ""),
                    "content": summary_content,
                    "source": article.get("source", ""),
                    "published_at": article.get("published_at", ""),
                }
            )

        user_prompt = (
            f"User topics: {', '.join(topics)}\n"
            f"User region: {preferences.get('region', 'international')}\n"
            f"User preferences: {json.dumps(preferences, indent=2)}\n\n"
            "Articles to analyze:\n"
            f"{json.dumps(articles_summary, indent=2)}\n\n"
            "Please analyze and rank these articles, returning the full article data with AI scores.\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await self._make_request(
                messages, json_mode=True, max_tokens=4000
            )
            content = response["choices"][0]["message"]["content"]
            try:
                # Repair and decode the JSON response using json_repair
                result = _json_repair.loads(content)
            except Exception as parse_err:
                logger.warning(
                    f"Failed to parse LLM article ranking response as JSON: {parse_err}.\n"
                    f"Raw content: {content[:200]}..."
                )
                raise

            ranked_articles = result.get("articles", [])

            final_articles = []
            for ranked in ranked_articles:
                # Match the ranked article with the original by title
                original = next(
                    (a for a in articles if a.get("title") == ranked.get("title")),
                    None,
                )
                if original:
                    # Merge original article fields with AI-provided fields,
                    # giving precedence to the AI-provided values where appropriate.
                    merged = {**original, **ranked}
                    final_articles.append(merged)

            final_articles.sort(
                key=lambda x: x.get("ai_score", 0), reverse=True
            )
            logger.info(
                f"Analyzed and ranked {len(final_articles)} articles"
            )
            return final_articles

        except Exception as e:
            logger.error(f"Error analyzing articles: {e}")
            return self._fallback_scoring(articles, topics)

    async def generate_article_summary(self, content: str) -> str:
        """
        Summarize a news article into a concise bullet point.  This helper
        uses the LLM to condense the article into a single sentence
        capturing the essence of the story.  When the LLM is not
        available, it falls back to returning the first 40 words of the
        content followed by an ellipsis.

        :param content: The full text of the article
        :return: A short summary string
        """
        # If no configuration is available, return a simple truncated
        # summary.  Split on whitespace to avoid cutting words in half.
        if not self.config or not getattr(self.config, "api_key", None):
            words = content.split()
            return " ".join(words[:40]) + ("..." if len(words) > 40 else "")

        prompt = (
            "You are an AI assistant tasked with summarizing news articles. "
            "Generate a single concise sentence that captures the key point "
            "of the following article. Do not include any extraneous details.\n\n"
            f"Article:\n{content[:1500]}"
        )
        messages = [
            {"role": "system", "content": "You summarize news articles succinctly."},
            {"role": "user", "content": prompt},
        ]
        try:
            response = await self._make_request(messages, max_tokens=100, temperature=0.4)
            # The response content is expected to be plain text.  Extract it
            # from the first choice.  If the response is structured as
            # JSON, fall back to the raw content.
            text = response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            # Clean up any leading dashes or bullet markers that the model
            # might include.
            return re.sub(r"^[\-\•\s]+", "", text)
        except Exception as e:
            logger.warning(f"Failed to generate summary with LLM: {e}")
            # Fallback to truncation
            words = content.split()
            return " ".join(words[:40]) + ("..." if len(words) > 40 else "")

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


# Create a module-level singleton instance.  This allows other modules to
# import `llm_service` and use the same configured service.  Without
# instantiating here the import `from services.llm_service import llm_service`
# would fail because no such variable would exist.  By providing this
# instance we preserve backward compatibility with the legacy API.
llm_service = LLMService()
