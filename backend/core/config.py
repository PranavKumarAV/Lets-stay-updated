"""
Application configuration management.

This module defines a ``Settings`` dataclass that reads its values from
environment variables at instantiation time.  It replaces the
``pydantic.BaseSettings`` implementation that is incompatible with
Pydantic v2 and avoids a dependency on the uninstalled
``pydantic_settings`` package.  Each configuration option has a
reasonable default which can be overridden by setting the corresponding
environment variable.
"""

from dataclasses import dataclass, field
import os
from typing import List, Optional


@dataclass
class Settings:
    """Configuration values loaded from environment variables with defaults."""

    # Application settings
    ENVIRONMENT: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    PORT: int = field(default_factory=lambda: int(os.getenv("PORT", "5000")))
    DEBUG: bool = field(init=False)
    LOG_LEVEL: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # LLM configuration
    LLM_PROVIDER: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "groq").lower())
    LLM_MODEL: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "llama3-70b-8192"))
    LLM_MAX_TOKENS: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "2048")))
    LLM_TEMPERATURE: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.7")))

    # API keys for providers
    GROQ_API_KEY: Optional[str] = field(default_factory=lambda: os.getenv("GROQ_API_KEY"))

    # External news API key.  When provided, the news aggregator will fetch
    # real articles from the configured news service (e.g. NewsAPI.org).  If
    # absent, the aggregator falls back to generating mock articles.  Set
    # ``NEWS_API_KEY`` as an environment variable in your deployment to
    # enable real news fetching.
    NEWS_API_KEY: Optional[str] = field(default_factory=lambda: os.getenv("NEWS_API_KEY"))

    # Support multiple NewsAPI keys for quota rotation.  You can provide
    # additional keys as environment variables ``NEWS_API_KEY_1``,
    # and ``NEWS_API_KEY_2``.  These will be used in
    # sequence when the primary key is exhausted.
    NEWS_API_KEY_1: Optional[str] = field(default_factory=lambda: os.getenv("NEWS_API_KEY_1"))
    NEWS_API_KEY_2: Optional[str] = field(default_factory=lambda: os.getenv("NEWS_API_KEY_2"))

    # Compatibility with legacy usage
    MAX_TOKENS: int = field(init=False)
    TEMPERATURE: float = field(init=False)
    DEFAULT_MODEL: str = field(init=False)

    # Database
    DATABASE_URL: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./news_app.db"))

    # News API settings
    MAX_ARTICLES_PER_REQUEST: int = field(default_factory=lambda: int(os.getenv("MAX_ARTICLES_PER_REQUEST", "25")))
    DEFAULT_ARTICLE_COUNT: int = field(default_factory=lambda: int(os.getenv("DEFAULT_ARTICLE_COUNT", "5")))
    ARTICLE_CACHE_HOURS: int = field(default_factory=lambda: int(os.getenv("ARTICLE_CACHE_HOURS", "24")))

    # CORS
    CORS_ORIGINS: List[str] = field(default_factory=lambda: [
        "http://localhost:3000",
        "http://localhost:5000",
        "http://localhost:8000",
    ])

    def __post_init__(self) -> None:
        """Derive additional configuration settings after initialization."""
        # Derive debug flag from environment
        self.DEBUG = self.ENVIRONMENT.lower() == "development"
        # Mirror legacy names used elsewhere in the codebase
        self.MAX_TOKENS = self.LLM_MAX_TOKENS
        self.TEMPERATURE = self.LLM_TEMPERATURE
        self.DEFAULT_MODEL = self.LLM_MODEL

    @property
    def is_development(self) -> bool:
        """Return True if the environment is set to development."""
        return self.ENVIRONMENT.lower() == "development"

    @property
    def has_any_llm_key(self) -> bool:
        """
        Return True if any LLM API key is configured.

        Checks the presence of the ``GROQ_API_KEY`` environment variable.
        Additional providers could be checked here in the future.
        """
        return bool(self.GROQ_API_KEY)


# Instantiate a single settings object that can be imported across the
# application.  This mirrors the behaviour of Pydantic's settings
# management while avoiding its heavy dependencies.
settings = Settings()