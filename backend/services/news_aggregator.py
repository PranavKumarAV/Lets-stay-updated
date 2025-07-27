import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import aiohttp
import os
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
            # Extend the mapping with additional well-known outlets and
            # sports sources.  These identifiers correspond to the
            # ``sources`` parameter accepted by the NewsAPI "everything"
            # endpoint.  Adding them here prevents invalid sources from
            # being requested and triggering API errors.
            "ESPN": "espn",
            "BBC Sport": "bbc-sport",
            "Reuters Sports": "reuters",  # reuse Reuters ID for sports
            "Sports Illustrated": "sports-illustrated",
            # Al Jazeera has a general English feed; no dedicated sports feed
            "Al Jazeera": "al-jazeera-english",
            "Al Jazeera English": "al-jazeera-english",
            # Additional mainstream outlets used by the LLM for recommendations
            "The New York Times": "the-new-york-times",
            "The Washington Post": "the-washington-post",
            "Wired": "wired",
            "MIT Technology Review": "mit-technology-review",
            "Reuters Sports": "reuters",  # alias for Reuters
        }

        # Attempt to load any previously discovered API identifiers from a
        # JSON file.  This allows the service to cache new source-to-ID
        # mappings discovered at runtime.  If the file does not exist or
        # cannot be parsed, silently ignore and proceed with the static
        # mapping defined above.  The file is expected to contain a
        # dictionary mapping source names to API identifiers.
        try:
            import json
            cache_path = os.path.join(os.path.dirname(__file__), "newsapi_source_map.json")
            if os.path.exists(cache_path):
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached_map = json.load(f)
                    if isinstance(cached_map, dict):
                        self.newsapi_source_map.update({
                            k: v for k, v in cached_map.items() if k not in self.newsapi_source_map
                        })
        except Exception as e:
            logger.warning(f"Failed to load cached newsapi source map: {e}")

    async def discover_api_for_source(self, source_name: str) -> Optional[str]:
        """
        Attempt to discover the official NewsAPI identifier for a given source
        name.  This method is a placeholder for future AI-assisted search.

        In a fully featured implementation, this function would leverage
        external tools (such as the ``pomp`` or ``pompyt`` libraries, web
        search APIs, or AI agents via LangChain) to search the internet
        for a free and valid API corresponding to the news outlet.  For
        example, it could query a search engine for "<source> NewsAPI id" or
        scrape the outlet's developer documentation.  If a valid identifier
        is found, it would be returned so it can be cached and used for
        future requests.

        Because this environment does not provide network access, the
        current implementation logs the discovery attempt and returns
        ``None``.  Developers may implement this method using an AI
        assistant or web scraping tools in their own environment.

        :param source_name: Human-readable source name (e.g., "BBC News")
        :return: The corresponding NewsAPI source ID if found, otherwise None.
        """
        logger.info(f"Attempting to discover API ID for source '{source_name}' via AI agent...")
        # TODO: Implement AI-assisted discovery of NewsAPI identifiers
        return None

        # RSS feed URLs for each source.  These feeds can be used to fetch
        # headlines without requiring an API key.  Not all outlets provide
        # straightforward RSS feeds; some may require scraping or are omitted.
        self.rss_feed_map = {
            "Reuters": "http://feeds.reuters.com/reuters/topNews",
            "BBC News": "http://feeds.bbci.co.uk/news/rss.xml",
            "NPR": "https://feeds.npr.org/1001/rss.xml",
            "The Guardian": "https://www.theguardian.com/world/rss",
            # Note: Associated Press does not provide a public RSS feed; omitted.
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
    
    async def fetch_articles(self, topics: List[str], sources: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
        """
        Simulate fetching articles from various news sources.
        In production, this would make actual API calls to news services.
        """
        # Build a list of recognized NewsAPI identifiers for the requested sources.
        valid_source_ids = []
        for source in sources:
            name = source.get("name")
            source_id = self.newsapi_source_map.get(name)
            if not source_id:
                # Attempt to discover the API ID using an AI-assisted search.  If
                # successful, cache the result and use it for this request.
                discovered = await self.discover_api_for_source(name)
                if discovered:
                    self.newsapi_source_map[name] = discovered
                    source_id = discovered
            if source_id:
                valid_source_ids.append((name, source_id))

        # If a NEWS_API_KEY is provided and we have at least one recognized
        # source, attempt to fetch real articles.  Otherwise, skip the API.
        if settings.NEWS_API_KEY and valid_source_ids:
            try:
                real_articles = await self._fetch_real_articles(topics, sources, count)
                if real_articles:
                    return real_articles
                logger.warning(
                    "NewsAPI returned no articles for topics %s and sources %s; falling back to RSS.",
                    topics,
                    [s.get("name") for s in sources],
                )
            except Exception as e:
                logger.error(f"Error fetching real articles: {e}. Falling back to RSS.")
        # If the API call fails or no valid sources exist, try RSS feeds.
        try:
            rss_articles = await self._fetch_rss_articles(topics, sources, count)
            if rss_articles:
                return rss_articles
            logger.warning(
                "RSS feeds returned no articles for topics %s and sources %s.",
                topics,
                [s.get("name") for s in sources],
            )
        except Exception as e:
            logger.error(f"Error fetching RSS articles: {e}.")
        # Do not generate mock articles.  Returning an empty list signals the
        # caller that no articles could be retrieved from real sources.
        return []

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
            feed = feedparser.parse(feed_url)
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
                articles.append({
                    "title": title,
                    "content": description,
                    "url": entry.get("link", ""),
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