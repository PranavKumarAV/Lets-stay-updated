import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class NewsDatabase:
    def __init__(self, db_path: str = "news_app.db"):
        self.db_path = db_path

    async def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                region TEXT NOT NULL,
                country TEXT,
                topics TEXT NOT NULL,
                article_count INTEGER DEFAULT 10,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                url TEXT NOT NULL,
                source TEXT NOT NULL,
                topic TEXT NOT NULL,
                ai_score INTEGER NOT NULL,
                published_at TIMESTAMP NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_topic ON news_articles(topic)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_score ON news_articles(ai_score)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_fetched ON news_articles(fetched_at)')

        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")

    async def create_news_preferences(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO news_preferences (region, country, topics, article_count)
            VALUES (?, ?, ?, ?)
        ''', (
            preferences['region'],
            preferences.get('country'),
            json.dumps(preferences['topics']),
            preferences.get('article_count', 10)
        ))

        pref_id = cursor.lastrowid
        conn.commit()
        conn.close()

        preferences['id'] = pref_id
        preferences['created_at'] = datetime.now().isoformat()
        return preferences

    async def create_news_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO news_articles (title, content, url, source, topic, ai_score, published_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            article['title'],
            article['content'],
            article['url'],
            article['source'],
            article['topic'],
            article['ai_score'],
            article['published_at'],
            json.dumps(article.get('metadata', {}))
        ))

        article_id = cursor.lastrowid
        conn.commit()
        conn.close()

        article['id'] = article_id
        article['fetched_at'] = datetime.now().isoformat()
        # If the metadata includes a summary, surface it at the top level
        metadata = article.get('metadata') or {}
        if isinstance(metadata, dict) and 'summary' in metadata:
            article['summary'] = metadata.get('summary')
        return article

    async def get_news_articles(self, topics: Optional[List[str]] = None,
                                source: Optional[str] = None,
                                min_ai_score: Optional[int] = None,
                                limit: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = '''
            SELECT id, title, content, url, source, topic, ai_score, published_at, fetched_at, metadata
            FROM news_articles WHERE 1=1
        '''
        params = []

        if topics:
            query += f" AND topic IN ({','.join(['?' for _ in topics])})"
            params.extend(topics)

        if source:
            query += " AND source = ?"
            params.append(source)

        if min_ai_score:
            query += " AND ai_score >= ?"
            params.append(min_ai_score)

        query += " ORDER BY ai_score DESC, published_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        articles = []
        for row in rows:
            metadata = json.loads(row[9]) if row[9] else {}
            article_obj = {
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'url': row[3],
                'source': row[4],
                'topic': row[5],
                'ai_score': row[6],
                'published_at': row[7],
                'fetched_at': row[8],
                'metadata': metadata
            }
            # If a summary exists in metadata, expose it at the top level
            if isinstance(metadata, dict) and 'summary' in metadata:
                article_obj['summary'] = metadata.get('summary')
            articles.append(article_obj)

        return articles

    async def clear_old_articles(self) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = datetime.now() - timedelta(hours=24)
        cursor.execute("DELETE FROM news_articles WHERE fetched_at < ?", (cutoff.isoformat(),))

        count = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Cleared {count} old articles")
        return count

# Global DB instance
db = NewsDatabase()

async def init_db():
    await db.init_db()
