import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
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
        # If a NEWS_API_KEY is provided, fetch real articles from the news API.
        if settings.NEWS_API_KEY:
            try:
                return await self._fetch_real_articles(topics, sources, count)
            except Exception as e:
                logger.error(f"Error fetching real articles: {e}. Falling back to RSS or mock data.")
        # If no API key or API fetch fails, try RSS feeds.  If RSS fails,
        # generate mock articles.
        try:
            rss_articles = await self._fetch_rss_articles(topics, sources, count)
            if rss_articles:
                return rss_articles
        except Exception as e:
            logger.error(f"Error fetching RSS articles: {e}. Falling back to mock data.")
        return self._generate_mock_articles(topics, sources, count)

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
                        f"&apiKey={api_key}"
                    )
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            text = await resp.text()
                            logger.warning(f"NewsAPI responded with status {resp.status}: {text}")
                            continue
                        data = await resp.json()
                        for item in data.get("articles", []):
                            published_at = item.get("publishedAt") or datetime.utcnow().isoformat()
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
                articles.append({
                    "title": title,
                    "content": description,
                    "url": entry.get("link", ""),
                    "source": name,
                    "published_at": published,
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
        
        # Generate published time (within last 24 hours)
        published_at = datetime.now() - timedelta(hours=random.randint(1, 24))
        
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