import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import aiohttp
from ..core.config import settings
import re

logger = logging.getLogger(__name__)

class NewsAggregator:
    """
    Mock news aggregator that simulates fetching articles from various sources.
    In a real implementation, this would integrate with actual news APIs.
    """
    
    def __init__(self):
        # Map human-readable source names (as returned by the LLM) to
        # NewsAPI source identifiers.  Only sources present in this
        # mapping will be used for real article fetching.  You can extend
        # this mapping with additional providers supported by your news
        # service.  See https://newsapi.org/sources for a list of IDs.
        self.newsapi_source_map = {
            "Reuters": "reuters",
            "Associated Press": "associated-press",
            "BBC News": "bbc-news",
            "NPR": "npr",
            "The Guardian": "the-guardian-uk",
            # Add other known sources here as needed
        }

        # RSS feed URLs for each source.  These feeds can be used to fetch
        # headlines without requiring an API key.  Not all outlets provide
        # straightforward RSS feeds; some may require scraping or are omitted.
        #
        # This mapping has been extended to include several entertainment
        # outlets commonly suggested by the language model.  Where possible
        # official feeds were used; however, some sites do not expose
        # first‑party RSS feeds.  For those, the entry is left absent and the
        # outlet will simply be skipped during RSS fetching.
        self.rss_feed_map = {
            # Use HTTPS for Reuters to avoid connection errors in environments
            # that disallow plain HTTP connections
            "Reuters": "https://news.google.com/rss/search?q=site:reuters.com&hl=en-US&gl=US&ceid=US:en",
            "BBC News": "http://feeds.bbci.co.uk/news/rss.xml",
            "NPR": "https://feeds.npr.org/1001/rss.xml",
            "The Guardian": "https://www.theguardian.com/world/rss",
            # Entertainment outlets
            "The Hollywood Reporter": "https://www.hollywoodreporter.com/feed",
            "Variety": "https://variety.com/feed",
            "Los Angeles Times": "https://www.latimes.com/world-nation/rss2.0.xml",
            "Rolling Stone": "https://www.rollingstone.com/feed",
            "Deadline Hollywood": "https://deadline.com/feed",
            "IndieWire": "https://www.indiewire.com/feed",
            "Screen International": "https://screendaily.com/45202.rss",

            # Additional entertainment and general outlets
            "E! News": "https://www.eonline.com/syndication/feeds/rssfeeds/topstories.xml",

            # Business outlets
            "CNBC": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
            "Forbes": "https://www.forbes.com/business/feed",
            "Financial Times": "https://www.ft.com/?edition=international&format=rss",

            # General news outlets
            "CNN": "http://rss.cnn.com/rss/edition.rss",
            "Al Jazeera English": "https://www.aljazeera.com/xml/rss/all.xml",
            "The New York Times": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
            "The Washington Post": "http://feeds.washingtonpost.com/rss/world",

            # Sports outlets
            "ESPN": "https://www.espn.com/espn/rss/news",
            "Sky Sports": "https://www.skysports.com/rss/12040",
            "CBS Sports": "https://www.cbssports.com/rss/headlines/",
            "BBC Sport": "http://feeds.bbci.co.uk/sport/rss.xml",

            # Health outlets

            # Technology and science outlets
            # These feeds were sourced from publicly available RSS listings.
            # The Verge: general technology and culture feed
            "The Verge": "https://www.theverge.com/rss/index.xml",
            # MIT Technology Review: top news feed
            "MIT Technology Review": "https://www.technologyreview.com/topnews.rss",
            # Wired: main RSS feed
            "Wired": "https://www.wired.com/feed/rss",
            # New Scientist: home page feed
            "New Scientist": "https://www.newscientist.com/feed/home",
            # IEEE Spectrum: full‑text feed
            "IEEE Spectrum": "https://spectrum.ieee.org/rss/fulltext",
            # Nature: research and news feed (science)
            "Nature": "http://feeds.nature.com/nature/rss/current",
            # Science Magazine: news from science
            "Science Magazine": "https://www.sciencemag.org/rss/news_current.xml",
        }

        # Track whether the NewsAPI has responded with a rate‑limit error.
        # When this flag is true, subsequent requests to the NewsAPI will be
        # skipped for the remainder of the process to avoid repeated 429
        # responses.  The flag resets when the application restarts.
        self.newsapi_rate_limited: bool = False

        # Collect all available NewsAPI keys for quota rotation.  Attempt
        # to pull from multiple environment variables to be robust to
        # different deployment naming conventions (e.g. NEWS_API_KEY vs
        # NEWS_API).  The primary key is always considered first.  Keys
        # ending in _1, or _2 allow simple rotation when the free
        # quota is exhausted.
        self.newsapi_keys: List[str] = []
        # Pull keys from the Settings dataclass when defined
        if settings.NEWS_API_KEY:
            self.newsapi_keys.append(settings.NEWS_API_KEY)
        for i in range(1, 3):
            key_attr = f"NEWS_API_KEY_{i}"
            try:
                key_val = getattr(settings, key_attr)
            except AttributeError:
                key_val = None
            if key_val:
                self.newsapi_keys.append(key_val)
        # Fallback: also check for alternative environment variable names
        # like NEWS_API, NEWS_API_1, NEWS_API_2. Some
        # deployments may define API keys using these names.  We use
        # os.getenv directly here to avoid adding more fields to settings.
        import os
        for fallback_name in ["NEWS_API", "NEWS_API_1", "NEWS_API_2"]:
            val = os.getenv(fallback_name)
            if val and val not in self.newsapi_keys:
                self.newsapi_keys.append(val)

        # Index used to track which key is currently active when
        # sequentially iterating through multiple keys.  This is not
        # currently used directly but retained for future enhancement.
        self._api_key_index: int = 0
    
    async def _legacy_fetch_articles(self, topics: List[str], sources: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
        """
        Legacy article fetching pipeline used prior to the introduction of
        global/local modes.  This method consults the NewsAPI (using the
        mapped source identifiers) and then falls back to RSS feeds for the
        selected sources.  It is retained for backwards compatibility with
        older callers that supply a list of topics and explicit sources.

        :param topics: List of user topics
        :param sources: List of source dicts containing at least a ``name`` key
        :param count: The desired minimum number of articles
        :return: A list of news articles (possibly empty)
        """
        # Build a list of valid NewsAPI source identifiers.  Attempt to
        # discover unknown identifiers when possible and cache new mappings.
        valid_source_ids: List[tuple[str, str]] = []
        for source in sources:
            name = source.get("name")
            if not name:
                continue
            source_id = self.newsapi_source_map.get(name)
            if not source_id:
                # Skip API discovery if we have already hit the NewsAPI rate limit.
                if not self.newsapi_rate_limited:
                    try:
                        # Attempt to discover the API ID via NewsAPI sources
                        discovered = await self.discover_api_for_source(name)
                        if discovered:
                            self.newsapi_source_map[name] = discovered
                            source_id = discovered
                            # Persist the new mapping to disk for future reuse
                            try:
                                import json, os
                                cache_path = os.path.join(os.path.dirname(__file__), "newsapi_source_map.json")
                                # Load existing cache if present
                                cached_map: Dict[str, str] = {}
                                if os.path.exists(cache_path):
                                    with open(cache_path, "r", encoding="utf-8") as f:
                                        try:
                                            cached_map = json.load(f) or {}
                                        except Exception:
                                            cached_map = {}
                                cached_map[name] = discovered
                                with open(cache_path, "w", encoding="utf-8") as f:
                                    json.dump(cached_map, f, indent=2)
                            except Exception as e:
                                logger.warning(f"Failed to persist discovered API mapping for {name}: {e}")
                    except Exception as e:
                        logger.warning(f"Error discovering API ID for source '{name}': {e}")
            if source_id:
                valid_source_ids.append((name, source_id))

        collected: List[Dict[str, Any]] = []

        # Attempt to fetch from NewsAPI if credentials and valid sources exist.
        # Only one attempt is made; if it fails to return sufficient articles or
        # raises a rate‑limit error, the aggregator will fall back entirely to
        # RSS feeds.  Skip this call altogether if we have already hit a
        # rate limit earlier.
        if settings.NEWS_API_KEY and valid_source_ids and not self.newsapi_rate_limited:
            try:
                real_articles = await self._fetch_real_articles(topics, sources, count)
                if real_articles:
                    collected.extend(real_articles)
                else:
                    logger.warning(
                        "NewsAPI returned no articles for topics %s and sources %s.",
                        topics,
                        [s.get("name") for s in sources],
                    )
            except Exception as e:
                logger.error(f"Error fetching real articles: {e}.")

        # RSS fetching has been removed.  Previously, when no real articles
        # were found for the selected sources, the aggregator would fall back
        # to RSS feeds.  Since the application now relies solely on the
        # NewsAPI, this section has been intentionally left blank.  If no
        # articles are obtained from the NewsAPI, the collected list will
        # remain empty and downstream handlers will handle the situation.

        # Deduplicate by URL
        unique_articles: List[Dict[str, Any]] = []
        seen_urls = set()
        seen_titles = set()
        for article in collected:
            url = article.get("url")
            title = (article.get("title") or "").strip().lower()
            # Skip if URL or title is missing or we've seen it already
            if not url or url in seen_urls or (title and title in seen_titles):
                continue
            seen_urls.add(url)
            if title:
                seen_titles.add(title)
            unique_articles.append(article)

        # Sort by published date descending if available
        unique_articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)

        # Return an empty list if no articles were collected.  Downstream
        # handlers can decide how to handle the absence of content (e.g., by
        # returning a friendly message to the user).
        if not unique_articles:
            return []

        # Return up to twice the requested count to give AI more context
        return unique_articles[: count * 2]

    async def _fetch_global_articles(self, topic: str, count: int, page: int = 1, language: str = "en") -> List[Dict[str, Any]]:
        """
        Fetch a list of articles for a given topic from the NewsAPI ``/v2/everything``
        endpoint.  This helper always sorts results by popularity and restricts
        the time window to the past seven days.  It returns up to ``count``
        articles (possibly more if duplicates are removed).

        :param topic: Search keyword or topic
        :param count: Desired number of articles to return
        :param language: ISO language code (e.g. "en")
        :return: List of article dicts
        """
        # Skip if we've already marked the API as rate-limited
        if self.newsapi_rate_limited:
            return []
        # Compute the date range for the past seven days
        from_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        page_size = max(1, min(count * 2, 100))
        all_articles: List[Dict[str, Any]] = []
        # Track whether we encountered a 429 across all keys
        encountered_rate_limit = True
        # Iterate through all available API keys until we get a successful response
        for key in self.newsapi_keys:
            if not key:
                continue
            url = (
                "https://newsapi.org/v2/everything"
                f"?q={aiohttp.helpers.quote(topic)}"
                f"&language={language}"
                f"&from={from_date}"
                f"&sortBy=popularity"
                f"&pageSize={page_size}"
                f"&page={page}"
                f"&apiKey={key}"
            )
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 429:
                            # Try the next key if available
                            text = await resp.text()
                            logger.warning(f"NewsAPI key exhausted (429): {text}")
                            continue
                        encountered_rate_limit = False
                        if resp.status != 200:
                            text = await resp.text()
                            logger.warning(f"NewsAPI /v2/everything responded with status {resp.status}: {text}")
                            break
                        data = await resp.json()
                        for item in data.get("articles", []):
                            published_at = item.get("publishedAt") or datetime.utcnow().isoformat()
                            try:
                                published_dt = datetime.fromisoformat(published_at.rstrip("Z"))
                            except Exception:
                                published_dt = datetime.utcnow()
                            if published_dt < datetime.utcnow() - timedelta(days=7):
                                continue
                            all_articles.append({
                                "title": item.get("title", ""),
                                "content": item.get("description") or item.get("content") or "",
                                "url": item.get("url", ""),
                                "source": item.get("source", {}).get("name", ""),
                                "published_at": published_at,
                                "metadata": {
                                    "author": item.get("author"),
                                    "source_name": item.get("source", {}).get("name"),
                                },
                            })
                        # Successful fetch; break the loop
                        break
            except Exception as e:
                logger.error(f"Error fetching global articles with key {key}: {e}")
                continue
        # If all keys resulted in 429, mark the service as rate limited
        if encountered_rate_limit:
            self.newsapi_rate_limited = True
            return []
        # Deduplicate and sort
        unique: List[Dict[str, Any]] = []
        seen = set()
        for art in all_articles:
            url = art.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            unique.append(art)
        unique.sort(key=lambda x: x.get("published_at", ""), reverse=True)
        return unique[:count]

    async def _fetch_local_headlines(self, topic: str, count: int, page: int = 1, country: Optional[str] = None, language: str = "en") -> List[Dict[str, Any]]:
        """
        Fetch top headlines for a given topic from the NewsAPI ``/v2/top-headlines``
        endpoint.  Results are filtered by the supplied country code and
        optionally by a category derived from the topic.  If no country is
        provided, an empty list is returned.  Up to ``count`` articles are
        returned.

        :param topic: Search keyword or topic
        :param count: Desired number of articles to return
        :param country: Two‑letter ISO country code (e.g. "US")
        :param language: ISO language code
        :return: List of article dicts
        """
        if self.newsapi_rate_limited or not country:
            return []
        # Derive a NewsAPI category from the topic using the existing helper.
        derived_category = self._get_topic_category(topic)
        valid_categories = {"business", "entertainment", "general", "health", "science", "sports", "technology"}
        category_param = ""
        if derived_category.lower() in valid_categories:
            category_param = f"&category={aiohttp.helpers.quote(derived_category.lower())}"
        page_size = max(1, min(count * 2, 100))
        all_articles: List[Dict[str, Any]] = []
        encountered_rate_limit = True
        for key in self.newsapi_keys:
            if not key:
                continue
            url = (
                "https://newsapi.org/v2/top-headlines"
                f"?country={country.upper()}"
                f"&language=en"
                f"&pageSize={page_size}"
                f"&page={page}"
                f"{category_param}"
                f"&apiKey={key}"
            )
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 429:
                            text = await resp.text()
                            logger.warning(f"NewsAPI key exhausted (429): {text}")
                            continue
                        encountered_rate_limit = False
                        if resp.status != 200:
                            text = await resp.text()
                            logger.warning(f"NewsAPI /v2/top-headlines responded with status {resp.status}: {text}")
                            break
                        data = await resp.json()
                        for item in data.get("articles", []):
                            published_at = item.get("publishedAt") or datetime.utcnow().isoformat()
                            try:
                                published_dt = datetime.fromisoformat(published_at.rstrip("Z"))
                            except Exception:
                                published_dt = datetime.utcnow()
                            if published_dt < datetime.utcnow() - timedelta(days=7):
                                continue
                            all_articles.append({
                                "title": item.get("title", ""),
                                "content": item.get("description") or item.get("content") or "",
                                "url": item.get("url", ""),
                                "source": item.get("source", {}).get("name", ""),
                                "published_at": published_at,
                                "metadata": {
                                    "author": item.get("author"),
                                    "source_name": item.get("source", {}).get("name"),
                                },
                            })
                        break
            except Exception as e:
                logger.error(f"Error fetching local headlines with key {key}: {e}")
                continue
        if encountered_rate_limit:
            self.newsapi_rate_limited = True
            return []
        # Deduplicate and sort
        unique: List[Dict[str, Any]] = []
        seen = set()
        for art in all_articles:
            url = art.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            unique.append(art)
        unique.sort(key=lambda x: x.get("published_at", ""), reverse=True)
        return unique[:count]

    async def fetch_articles(self,
        topic: Any,
        count: int = 10,
        page: int = 1,
        mode: str = "global",
        language: str = "en",
        country: Optional[str] = None,
        sources: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Unified entry point for fetching news articles.  When a ``mode`` is
        provided (either ``global`` or ``local``), this method routes the
        request to the appropriate helper.  If ``sources`` are supplied and
        no mode is given, the legacy pipeline will be used for backwards
        compatibility.

        :param topic: Either a single topic string or a list of topics
        :param count: Number of articles requested
        :param mode: ``global`` to fetch from /v2/everything or ``local`` to
                     fetch from /v2/top-headlines.  Any other value (or ``None``)
                     triggers the legacy behaviour if ``sources`` are provided.
        :param language: Language code used for filtering results
        :param country: Country code used for local headlines (ignored for
                        global mode)
        :param sources: Optional list of source dicts (legacy only)
        :return: List of articles
        """
        # Determine if we should use the legacy code path.  If ``sources``
        # are provided and the caller did not explicitly specify a mode, fall
        # back to the original implementation.  This preserves behaviour
        # for older API routes that still supply topics and sources.
        if sources is not None and (mode is None or mode not in {"global", "local"}):
            # Ensure topic is a list when using legacy fetch
            topics_list = topic if isinstance(topic, list) else [str(topic)]
            return await self._legacy_fetch_articles(topics_list, sources, count)

        # Normalize topics into a list for iteration
        topics_list: List[str] = topic if isinstance(topic, list) else [str(topic)]

        collected: List[Dict[str, Any]] = []
        for t in topics_list:
            if mode == "local":
                # For local mode we must have a country; skip if not provided
                if not country:
                    continue
                fetched = await self._fetch_local_headlines(t, count, page=page, country=country, language=language)
            else:
                fetched = await self._fetch_global_articles(t, count, page=page, language=language)
            collected.extend(fetched)

        # Remove duplicates by URL
        unique_articles: List[Dict[str, Any]] = []
        seen_urls = set()
        for article in collected:
            url = article.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            unique_articles.append(article)

        # Sort by published date descending
        unique_articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)

        # If we didn't collect any articles from the NewsAPI and a fallback is
        # available, attempt to gather articles from RSS feeds.  We build a
        # list of source dicts using the keys of ``rss_feed_map``.  The
        # resulting articles will still be filtered by topics_list and
        # deduplicated.  RSS parsing may be slower, so this block is
        # executed only when the API yields no content.
        if not unique_articles and mode == 'global':    # Current RSS not valid for local search
            try:
                # Build a generic sources list for RSS based on all known feeds
                rss_sources = [{"name": name} for name in self.rss_feed_map.keys()]
                rss_articles: List[Dict[str, Any]] = []
                # Fetch RSS articles for each topic; the helper already handles
                # per-source filtering and deduplication.  We request count
                # articles per topic to over‑fetch and allow downstream ranking.
                for t in topics_list:
                    fetched = await self._fetch_rss_articles([t], rss_sources, count)
                    rss_articles.extend(fetched)
                # Deduplicate and sort RSS articles by published_at descending
                seen_rss = set()
                deduped_rss: List[Dict[str, Any]] = []
                for art in rss_articles:
                    url = art.get("link")
                    if not url or url in seen_rss:
                        continue
                    seen_rss.add(url)
                    deduped_rss.append(art)
                deduped_rss.sort(key=lambda x: x.get("published_at", ""), reverse=True)
                # Return up to 2× count to allow AI ranking later
                return deduped_rss[: max(1, count * 2)]
            except Exception as e:
                logger.error(f"Error fetching RSS fallback articles: {e}")
                # Return empty list; upstream will handle with 404
                return []
        # Return up to the requested count * 2 to give the AI additional context
        return unique_articles[: max(1, count * 2)]

    async def discover_api_for_source(self, source_name: str) -> Optional[str]:
        """
        Attempt to discover the NewsAPI source identifier for a human‑readable
        source name.

        This implementation queries the NewsAPI ``/v2/sources`` endpoint using
        the provided ``NEWS_API_KEY`` and searches the returned list of
        sources for one whose name contains the requested source_name.  If a
        matching source is found, its ``id`` is returned.  When no API key
        is available or no match exists, ``None`` is returned.

        :param source_name: Human‑readable news outlet name (e.g. "BBC News")
        :return: A NewsAPI source ID if discovered, otherwise None
        """
        # Without an API key we cannot query the NewsAPI for sources
        api_key = settings.NEWS_API_KEY
        if not api_key:
            return None
        # Normalize the search term for comparison
        search_term = source_name.lower()
        url = f"https://newsapi.org/v2/sources?apiKey={api_key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    # If a rate limit (HTTP 429) response is returned, set the
                    # newsapi_rate_limited flag so future NewsAPI requests can be
                    # skipped.  This prevents repeated queries once the free
                    # quota has been exhausted.
                    if resp.status == 429:
                        self.newsapi_rate_limited = True
                    try:
                        text = await resp.text()
                    except Exception:
                        text = ""
                    logger.warning(f"NewsAPI sources request failed with status {resp.status}: {text}")
                    return None
                data = await resp.json()
                for src in data.get("sources", []):
                    name = src.get("name", "")
                    if search_term in name.lower():
                        return src.get("id")
        return None

    async def _fetch_real_articles(self, topics: List[str], sources: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
        """
        Fetch articles from a real news API (e.g. NewsAPI.org).  The number of
        articles returned is limited by ``count`` times the number of topics
        and sources.  Only sources present in ``self.newsapi_source_map``
        will be queried.

        :param topics: List of topics provided by the user
        :param sources: List of source dicts (with at least a 'name' key)
        :param count: Desired number of articles per user request
        :return: List of articles in the expected format
        """
        api_key = settings.NEWS_API_KEY
        real_articles: List[Dict[str, Any]] = []
        max_per_request = max(1, count // max(1, len(topics) * len(sources)))
        async with aiohttp.ClientSession() as session:
            # Compute the date range for the past seven days.  The NewsAPI
            # accepts a `from` parameter specifying the earliest publication
            # time; omit the `to` parameter to default to the current time.
            from_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
            for topic in topics:
                for source in sources:
                    source_name = source.get("name")
                    source_id = self.newsapi_source_map.get(source_name)
                    if not source_id:
                        continue  # skip sources we don't have an ID for
                    url = (
                        "https://newsapi.org/v2/everything"
                        f"?q={topic}&sources={source_id}&pageSize={max_per_request}"
                        "&sortBy=publishedAt"
                        f"&from={from_date}"
                        f"&apiKey={api_key}"
                    )
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            # If the NewsAPI request returns a rate limit error
                            # (HTTP 429), mark the aggregator so that future
                            # NewsAPI calls are skipped.  Otherwise just log the
                            # error and continue.  Note that we still read
                            # the response text to aid debugging.
                            if resp.status == 429:
                                self.newsapi_rate_limited = True
                            text = await resp.text()
                            logger.warning(f"NewsAPI responded with status {resp.status}: {text}")
                            continue
                        data = await resp.json()
                        for item in data.get("articles", []):
                            # Skip articles published more than seven days ago
                            published_at = item.get("publishedAt") or datetime.utcnow().isoformat()
                            try:
                                published_dt = datetime.fromisoformat(published_at.rstrip("Z"))
                            except Exception:
                                published_dt = datetime.utcnow()
                            if published_dt < datetime.utcnow() - timedelta(days=7):
                                continue
                            real_articles.append({
                                "title": item.get("title", ""),
                                "content": item.get("description") or item.get("content") or "",
                                "url": item.get("url", ""),
                                "source": source_name,
                                "published_at": published_at,
                                "metadata": {
                                    "author": item.get("author"),
                                    "source_name": item.get("source", {}).get("name"),
                                },
                            })
        # Sort articles by publication date descending and limit output
        real_articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)
        # Return more articles than requested so AI can filter
        return real_articles[: count * 2]

    async def _fetch_rss_articles(self, topics: List[str], sources: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
        """
        Fetch articles from RSS feeds for the given sources and topics.  This
        implementation relies on feedparser to download and parse the feed
        directly, mirroring the behaviour found in the semi‑stable reference
        version of the project.  It filters entries to only include those
        mentioning one of the user‑provided topics and ignores articles older
        than one week.

        :param topics: List of user topics
        :param sources: List of source dicts
        :param count: Desired article count
        :return: List of articles
        """
        articles: List[Dict[str, Any]] = []
        # Determine how many articles to retrieve from each feed.  We fetch
        # twice the per‑source count to allow for filtering below.
        max_per_source = max(1, count // max(1, len(sources)))
        topic_keywords = [t.lower() for t in topics]

        # Attempt to import feedparser once.  If unavailable, we'll fall
        # back to a manual RSS parser below.
        try:
            import feedparser  # type: ignore
            feedparser_available = True
        except ImportError:
            feedparser_available = False

        for source in sources:
            name = source.get("name")
            if not name:
                continue
            feed_url = self.rss_feed_map.get(name)
            if not feed_url:
                continue
            entries: List[Any] = []
            # Primary path: use feedparser if it's available to fetch and parse
            if feedparser_available:
                try:
                    # Use feedparser to fetch and parse the RSS feed.  Pass a
                    # browser‑like User‑Agent header to reduce the chance of being
                    # blocked by some servers.  Feedparser accepts a
                    # ``request_headers`` argument for this purpose.
                    feed = feedparser.parse(feed_url, request_headers={"User-Agent": "Mozilla/5.0"})  # type: ignore
                    # Skip malformed feeds
                    if getattr(feed, "bozo", False):
                        exc = getattr(feed, "bozo_exception", None)
                        logger.warning(f"Failed to parse RSS feed for {name}: {exc}")
                        continue
                    entries = feed.entries
                except Exception as e:
                    logger.warning(f"Failed to fetch or parse RSS feed for {name}: {e}")
                    # Fall through to manual parsing
            # Fallback path: manually fetch and parse the RSS feed if feedparser
            # is not available or failed above.
            if not entries:
                try:
                    from aiohttp import ClientSession
                    from xml.etree import ElementTree as ET
                    from email.utils import parsedate_to_datetime
                    async with ClientSession() as session:
                        async with session.get(feed_url, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                            if resp.status != 200:
                                logger.warning(f"Failed to fetch RSS feed for {name}: HTTP {resp.status}")
                                continue
                            content = await resp.read()
                    # Parse XML
                    try:
                        root = ET.fromstring(content)
                    except Exception as e:
                        logger.warning(f"Failed to parse RSS XML for {name}: {e}")
                        continue
                    # RSS 2.0 items are under channel/item; Atom entries under feed/entry
                    items = root.findall('.//item')
                    if not items:
                        items = root.findall('.//entry')
                    for item in items:
                        title = (item.findtext('title') or '').strip()
                        description = (item.findtext('description') or item.findtext('summary') or '').strip()
                        # Some Atom feeds use <content> for full description
                        if not description:
                            desc_elem = item.find('content')
                            description = (desc_elem.text or '').strip() if desc_elem is not None else ''
                        pub_str = item.findtext('pubDate') or item.findtext('published') or item.findtext('updated')
                        # Attempt to parse publication date using email.utils helper
                        if pub_str:
                            try:
                                pub_dt = parsedate_to_datetime(pub_str)
                                # Remove timezone info for comparison if present
                                published_dt = pub_dt.replace(tzinfo=None)
                            except Exception:
                                published_dt = datetime.utcnow()
                        else:
                            published_dt = datetime.utcnow()
                        entries.append({
                            'title': title,
                            'description': description,
                            'summary': description,
                            'link': None,  # placeholder
                            'published_dt': published_dt
                        })
                    # Extract link separately because <link> structure can vary
                    for idx, item in enumerate(items):
                        link = ''
                        link_elem = item.find('link')
                        if link_elem is not None:
                            # Atom format: <link href="..."/>
                            href = link_elem.get('href')
                            if href and href.strip().startswith("http"):
                                link = href.strip()
                            elif link_elem.text and link_elem.text.strip().startswith("http"):
                                # RSS 2.0 format: <link>https://...</link>
                                link = link_elem.text.strip()
                        if not link:
                            logger.warning(f"Skipping article due to missing or invalid link in source '{name}'")
                            continue
                        entries[idx]['link'] = link
                except Exception as e:
                    logger.warning(f"Error fetching/parsing RSS feed for {name}: {e}")
                    continue
            # Process each entry (from either feedparser or manual parsing)
            for entry in entries[: max_per_source * 2]:
                # When using manual parsing, entry is a dict we created above
                # otherwise it's a feedparser entry object.  Normalize fields.
                if isinstance(entry, dict):
                    title = entry.get('title', '')
                    description = entry.get('description', '') or entry.get('summary', '')
                    published_dt = entry.get('published_dt') or datetime.utcnow()
                    link = entry.get('link', '') or ''
                else:
                    title = entry.get("title", "")
                    description = entry.get("summary", "") or entry.get("description", "")
                    published_raw = entry.get("published") or entry.get("updated")
                    # Parse date using feedparser's structured tuple if available
                    try:
                        if hasattr(entry, "published_parsed") and entry.published_parsed:
                            published_dt = datetime(*entry.published_parsed[:6])
                        elif published_raw:
                            published_dt = datetime.fromisoformat(published_raw)
                        else:
                            published_dt = datetime.utcnow()
                    except Exception:
                        published_dt = datetime.utcnow()
                    link = entry.get("link", "") or ""
                # Filter by topics if specified
                text = f"{title} {description}".lower()
                if topic_keywords and not any(kw in text for kw in topic_keywords):
                    continue
                # Skip articles older than seven days
                if published_dt < datetime.utcnow() - timedelta(days=7):
                    continue
                articles.append({
                    "title": title,
                    "content": description,
                    "url": link,
                    "source": name,
                    "published_at": published_dt.isoformat(),
                    "metadata": {
                        "rss": True,
                    },
                })

        # Sort by published date descending
        articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)
        # Return twice the requested count to allow for downstream ranking
        return articles[: count * 2]
    
    def _get_topic_category(self, topic: str) -> str:
        """
        Map a free‑form topic to a NewsAPI category using keyword heuristics.
        If no category matches, return the topic itself.  This helper is used
        when fetching local headlines to derive a ``category`` parameter.  It
        now recognizes the seven canonical NewsAPI categories (business,
        entertainment, general, health, science, sports and technology) and
        includes a wider set of synonyms for each.  If the topic matches
        multiple categories, the first match in the defined order is used.
        """
        topic_lower = topic.lower().strip()
        categories: dict[str, list[str]] = {
            "business": [
                "business", "finance", "economy", "economic", "stock", "stocks", "markets", "company", "companies"
            ],
            "entertainment": [
                "entertainment", "movie", "movies", "film", "cinema", "hollywood", "music", "celebrity", "celebrities"
            ],
            "general": [
                "general", "news", "top stories", "headlines", "current events"
            ],
            "health": [
                "health", "healthcare", "medicine", "medical", "wellness", "fitness", "covid", "pandemic"
            ],
            "science": [
                "science", "research", "physics", "chemistry", "biology", "space", "astronomy", "quantum"
            ],
            "sports": [
                "sports", "sport", "football", "soccer", "basketball", "baseball", "tennis", "golf", "olympics"
            ],
            "technology": [
                "technology", "tech", "gadget", "gadgets", "ai", "artificial intelligence", "machine learning", "computing", "software"
            ],
        }
        for category, keywords in categories.items():
            for keyword in keywords:
                if re.search(rf"\b{re.escape(keyword)}\b", topic_lower):
                    return category
        return topic_lower
        
# Global aggregator instance
news_aggregator = NewsAggregator()