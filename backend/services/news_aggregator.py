import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class NewsAggregator:
    """
    Mock news aggregator that simulates fetching articles from various sources.
    In a real implementation, this would integrate with actual news APIs.
    """
    
    def __init__(self):
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
        
        # Sample authors for different source types - X/Twitter removed due to API restrictions
        # Pre-defined author names for different source categories.  These lists
        # are used to populate the metadata for mock articles.  A missing key
        # previously caused a KeyError when generating metadata for Twitter/X
        # sources.  To prevent that, include a `twitter` category with some
        # placeholder handles.  Note that real-time Twitter scraping is not
        # performed; these names are used purely for mock data generation.
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
            # Note: we intentionally omit Twitter/X as a source of authors to
            # avoid relying on that platform for content generation.
        }
    
    async def fetch_articles(self, topics: List[str], sources: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
        """
        Simulate fetching articles from various news sources.
        In production, this would make actual API calls to news services.
        """
        articles = []
        source_names = [source['name'] for source in sources]
        
        # Generate articles for each topic and source combination
        articles_per_combination = max(1, count // (len(topics) * len(source_names)))
        
        for topic in topics:
            for source_name in source_names:
                for _ in range(articles_per_combination + 1):  # +1 for some variety
                    article = self._generate_mock_article(topic, source_name)
                    articles.append(article)
        
        # Shuffle and return requested count
        random.shuffle(articles)
        return articles[:count * 2]  # Return extra for AI to filter
    
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