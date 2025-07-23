from pydantic import BaseSettings
import os
from typing import Optional, List

class Settings(BaseSettings):
    # Application settings
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    PORT: int = int(os.getenv("PORT", "5000"))
    DEBUG: bool = ENVIRONMENT == "development"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # LLM Configuration - Easy to change providers
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq").lower()
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.1-70b-versatile")
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    
    # API Keys for different providers
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")  
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    
    # Legacy support for existing code
    MAX_TOKENS: int = LLM_MAX_TOKENS
    TEMPERATURE: float = LLM_TEMPERATURE
    DEFAULT_MODEL: str = LLM_MODEL
    
    # Database (SQLite for simplicity and free deployment)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./news_app.db")
    
    # News API settings
    MAX_ARTICLES_PER_REQUEST: int = 50
    DEFAULT_ARTICLE_COUNT: int = 10
    ARTICLE_CACHE_HOURS: int = 24
    
    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000", 
        "http://localhost:5000", 
        "http://localhost:8000"
    ]
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"
    
    @property
    def has_any_llm_key(self) -> bool:
        return bool(self.GROQ_API_KEY or self.OPENAI_API_KEY or self.ANTHROPIC_API_KEY)
    
    class Config:
        env_file = ".env"

settings = Settings()