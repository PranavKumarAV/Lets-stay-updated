import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import aiohttp
from ..core.config import settings

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
            "Reuters": "https://feeds.reuters.com/reuters/topNews",
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

        # Mock article templates and author lists retained for fallback mode
        # (when no NEWS_API_KEY is configured).  These will be used to
        # generate placeholder articles if real news cannot be fetched.
        self.article_templates = {
            "politics": [
                "Breaking: Major Policy Changes Announced in {topic}",
                "Senate Votes on Landmark {topic} Legislation", 
                "Political Analysis: {topic} Impact on Upcoming Elections",
                "International Relations: {topic} Diplomatic Breakthrough",
                "Expert Opinion: {topic} Policy Implications",
                "Government Announces New {topic} Initiative",
                "Opposition Party Criticizes {topic} Decision",
                "Bipartisan Support Growing for {topic} Reform"
            ],
            "sports": [
                "Championship Update: {topic} Tournament Results",
                "Player Transfer News Shakes {topic} World",
                "Record-Breaking Performance in {topic} Competition", 
                "Injury Report: Key {topic} Players Sidelined",
                "Season Analysis: {topic} Team Standings",
                "Olympic Preparation: {topic} Athletes Training Hard",
                "Coach Interview: {topic} Strategy Revealed",
                "Fan Reactions: {topic} Match Generates Buzz"
            ],
            "ai": [
                "AI Breakthrough: Revolutionary {topic} Technology",
                "Tech Giants Invest Billions in {topic} Research",
                "Ethical Concerns Raised Over {topic} Development",
                "Industry Impact: {topic} Transforms Business Operations", 
                "Research Paper: {topic} Advances Published",
                "Startup Announces {topic} Innovation",
                "AI Safety: New {topic} Regulations Proposed",
                "Academic Conference: {topic} Findings Presented"
            ],
            "movies": [
                "Box Office Hit: {topic} Film Breaks Records",
                "Celebrity News: {topic} Stars Announce New Project",
                "Film Festival: {topic} Movies Win Critical Acclaim",
                "Industry Insider: {topic} Production Updates",
                "Review: {topic} Film Receives Mixed Reception",
                "Director Interview: {topic} Vision Explained",
                "Behind the Scenes: {topic} Movie Magic",
                "Awards Season: {topic} Nominations Announced"
            ]
        }

        self.authors = {
            "reddit": [
                "u/newsreporter",
                "u/politicsexpert",
                "u/sportswriter",
                "u/techguru"
            ],
            "substack": [
                "Sarah Chen",
                "David Rodriguez",
                "Emily Watson",
                "Michael Thompson",
                "Lisa Chang"
            ],
            "traditional": [
                "Reuters Staff",
                "AP Reporter",
                "BBC Correspondent",
                "Guardian Writer",
                "NPR Correspondent"
            ],
            "newspaper": [
                "Guardian Reporter",
                "Independent Journalist",
                "Digital Correspondent"
            ],
        }

        # Track whether the NewsAPI has responded with a rate‑limit error.
        # When this flag is true, subsequent requests to the NewsAPI will be
        # skipped for the remainder of the process to avoid repeated 429
        # responses.  The flag resets when the application restarts.
        self.newsapi_rate_limited: bool = False
    
    async def fetch_articles(self, topics: List[str], sources: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
        """
        Orchestrate fetching of news articles for the given topics and sources.

        This method first consults the NewsAPI for each requested source.  If a
        source is not present in the built‑in mapping, it attempts to discover
        the corresponding NewsAPI identifier using the ``discover_api_for_source``
        helper.  Any discovered identifiers are cached for future use.  The
        aggregator then attempts to fetch articles from the NewsAPI, followed
        by RSS feeds for the user‑selected sources.  If those calls yield
        fewer than the requested number of articles, additional RSS feeds
        from all known sources are queried to top up the result.  Duplicate
        articles (based on URL) are removed and the combined list is
        truncated to twice the requested count to give the AI extra context.

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

        # Fetch from RSS feeds for the user‑selected sources
        try:
            rss_articles = await self._fetch_rss_articles(topics, sources, count)
            if rss_articles:
                collected.extend(rss_articles)
            else:
                logger.warning(
                    "RSS feeds returned no articles for topics %s and sources %s.",
                    topics,
                    [s.get("name") for s in sources],
                )
        except Exception as e:
            logger.error(f"Error fetching RSS articles: {e}.")

        # If we still don't have enough articles, fetch from additional RSS feeds
        # one by one until we collect at least ``count`` articles.  This
        # incremental approach avoids fetching large batches from all feeds
        # when only a few additional articles are needed.
        if len(collected) < count:
            selected_names = {s.get("name") for s in sources if s.get("name")}
            for name in self.rss_feed_map.keys():
                if name in selected_names:
                    continue
                remaining = count - len(collected)
                if remaining <= 0:
                    break
                try:
                    extra = await self._fetch_rss_articles(topics, [{"name": name}], remaining)
                    if extra:
                        collected.extend(extra)
                except Exception as e:
                    logger.error(f"Error fetching RSS articles from additional source {name}: {e}.")

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

        # Return up to twice the requested count to give AI more context
        return unique_articles[: count * 2]

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
        method does not require an API key.  It filters articles whose
        titles or descriptions mention any of the topics.

        :param topics: List of user topics
        :param sources: List of source dicts
        :param count: Desired article count
        :return: List of articles
        """
        import feedparser  # Local import to avoid dependency if unused
        articles: List[Dict[str, Any]] = []
        max_per_source = max(1, count // max(1, len(sources)))
        topic_keywords = [t.lower() for t in topics]
        for source in sources:
            name = source.get("name")
            feed_url = self.rss_feed_map.get(name)
            if not feed_url:
                continue
            # Fetch the RSS feed content over HTTP.  Some feeds block
            # default user agents, so specify a browser‑like agent.  If
            # network access is unavailable the request will fail and the
            # feed will be skipped.
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(feed_url, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                        if resp.status != 200:
                            logger.warning(f"Failed to fetch RSS feed for {name}: HTTP {resp.status}")
                            continue
                        content = await resp.read()
            except Exception as e:
                logger.warning(f"Failed to fetch RSS feed for {name}: {e}")
                continue
            # Parse the feed from the downloaded content.  Use feedparser
            # directly on the bytes to avoid additional network calls.
            feed = feedparser.parse(content)
            if feed.bozo:
                logger.warning(f"Failed to parse RSS feed for {name}: {feed.bozo_exception}")
                continue
            for entry in feed.entries[: max_per_source * 2]:
                title = entry.get("title", "")
                description = entry.get("summary", "") or entry.get("description", "")
                text = f"{title} {description}".lower()
                if not any(kw in text for kw in topic_keywords):
                    continue
                published = entry.get("published") or entry.get("updated") or datetime.utcnow().isoformat()
                # Convert RSS published date to datetime object if possible
                try:
                    published_dt = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') and entry.published_parsed else datetime.fromisoformat(published)
                except Exception:
                    try:
                        published_dt = datetime.fromisoformat(published)
                    except Exception:
                        published_dt = datetime.utcnow()
                # Skip entries older than seven days
                if published_dt < datetime.utcnow() - timedelta(days=7):
                    continue
                # Ensure the URL is absolute.  Some feeds return relative
                # links; urljoin will resolve them against a sensible base.
                # Compute a base URL from the feed (scheme + host) to
                # handle feeds where the feed URL includes a path.  Fallback
                # to the feed URL itself if parsing fails.
                from urllib.parse import urljoin, urlparse
                link = entry.get("link", "") or ""
                try:
                    parsed_feed = urlparse(feed_url)
                    base = f"{parsed_feed.scheme}://{parsed_feed.netloc}"
                    absolute_link = urljoin(base + "/", link)
                except Exception:
                    absolute_link = urljoin(feed_url, link)
                articles.append({
                    "title": title,
                    "content": description,
                    "url": absolute_link,
                    "source": name,
                    "published_at": published_dt.isoformat(),
                    "metadata": {
                        "rss": True,
                    },
                })
        # Sort by published date descending
        articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)
        return articles[: count * 2]

    def _generate_mock_articles(self, topics: List[str], sources: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
        """Generate mock articles when no NEWS_API_KEY is available."""
        articles = []
        source_names = [source['name'] for source in sources]
        articles_per_combination = max(1, count // (len(topics) * len(source_names)))
        for topic in topics:
            for source_name in source_names:
                for _ in range(articles_per_combination + 1):
                    article = self._generate_mock_article(topic, source_name)
                    articles.append(article)
        random.shuffle(articles)
        return articles[: count * 2]
    
    def _generate_mock_article(self, topic: str, source: str) -> Dict[str, Any]:
        """Generate a realistic mock article"""
        # Determine topic category for templates
        topic_key = self._get_topic_category(topic)
        templates = self.article_templates.get(topic_key, self.article_templates["politics"])
        
        # Generate title
        title_template = random.choice(templates)
        title = title_template.format(topic=topic)
        
        # Generate content
        content = self._generate_article_content(topic, title)
        
        # Generate URL
        url_slug = title.lower().replace(" ", "-").replace(":", "")[:50]
        url = f"https://example.com/{topic.lower().replace(' ', '-')}/{url_slug}"
        
        # Generate published time within the last 7 days.  When summarizing
        # weekly highlights we want articles from the past week rather than
        # only the last 24 hours.  Choose a random time within the last
        # 7×24 hours (7 days) to simulate realistic publication dates.
        published_at = datetime.now() - timedelta(hours=random.randint(1, 7 * 24))
        
        # Generate metadata based on source type
        metadata = self._generate_metadata(source)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "source": source,
            "published_at": published_at.isoformat(),
            "metadata": metadata
        }
    
    def _get_topic_category(self, topic: str) -> str:
        """Categorize topic for template selection"""
        topic_lower = topic.lower()
        if any(word in topic_lower for word in ["politics", "government", "election", "policy", "trump", "biden"]):
            return "politics"
        elif any(word in topic_lower for word in ["sports", "football", "basketball", "soccer", "tennis", "olympics"]):
            return "sports"
        elif any(word in topic_lower for word in ["ai", "artificial intelligence", "machine learning", "technology", "tech"]):
            return "ai"
        elif any(word in topic_lower for word in ["movies", "film", "cinema", "hollywood", "entertainment"]):
            return "movies"
        else:
            return "politics"  # Default
    
    def _generate_article_content(self, topic: str, title: str) -> str:
        """Generate realistic article content"""
        base_content = f"""
        Recent developments in {topic} have captured significant attention from experts and stakeholders worldwide. 
        The implications of these changes are expected to have far-reaching consequences across multiple sectors.
        
        Industry analysts suggest that this trend represents a fundamental shift in how {topic} is approached, 
        with new methodologies and strategies being adopted by organizations globally. The response from key 
        stakeholders has been largely positive, though some concerns remain about long-term sustainability.
        
        Key findings from recent studies indicate that the current trajectory in {topic} will likely continue 
        for the foreseeable future, with emerging technologies and changing consumer preferences driving innovation.
        
        Experts recommend that organizations closely monitor these developments and adapt their strategies accordingly 
        to remain competitive in this evolving landscape. The next few months will be crucial in determining 
        the long-term impact of these changes on the {topic} sector.
        """.strip()
        
        return base_content
    
    def _generate_metadata(self, source: str) -> Dict[str, Any]:
        """Generate realistic metadata based on source type"""
        source_lower = source.lower()
        
        if "reddit" in source_lower:
            return {
                "views": random.randint(1000, 50000),
                "comments": random.randint(50, 1000),
                "upvotes": random.randint(100, 5000),
                "author": random.choice(self.authors["reddit"])
            }
        # We intentionally skip generating Twitter/X style metadata because that
        # platform is excluded from our news sources.
        elif "substack" in source_lower:
            return {
                "author": random.choice(self.authors["substack"]),
                "read_time": f"{random.randint(3, 15)} min read",
                "subscribers": random.randint(1000, 50000),
                "likes": random.randint(50, 500)
            }
        else:  # Traditional media
            return {
                "views": random.randint(5000, 100000),
                "author": random.choice(self.authors["traditional"]),
                "published_outlet": source,
                "word_count": random.randint(500, 2000)
            }

# Global aggregator instance
news_aggregator = NewsAggregator()