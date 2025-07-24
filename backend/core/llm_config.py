"""
LLM Configuration - Groq only
"""
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class LLMConfig:
    provider: str
    model: str
    api_key: str
    base_url: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.7
    free_tier: bool = True
    requests_per_minute: Optional[int] = None

class LLMManager:
    PROVIDERS = {
        "groq": {
            "name": "Groq",
            "base_url": "https://api.groq.com/openai/v1",
            "models": {
                "llama3-70b-8192": {
                    "name": "Llama 3.1 70B",
                    "free_tier": True,
                    "requests_per_minute": 30,
                    "tokens_per_hour": 1_000_000,
                    "context_window": 131072
                },
                "llama-3.1-8b-instant": {
                    "name": "Llama 3.1 8B (Ultra Fast)",
                    "free_tier": True,
                    "requests_per_minute": 30,
                    "tokens_per_hour": 1_000_000,
                    "context_window": 131072
                },
                "mixtral-8x7b-32768": {
                    "name": "Mixtral 8x7B",
                    "free_tier": True,
                    "requests_per_minute": 30,
                    "tokens_per_hour": 1_000_000,
                    "context_window": 32768
                }
            }
        }
    }

    @classmethod
    def get_best_free_config(cls) -> LLMConfig:
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("No free-tier LLM API key found. Set GROQ_API_KEY.")
        
        return LLMConfig(
            provider="groq",
            model="llama3-70b-8192",
            api_key=key,
            base_url=cls.PROVIDERS["groq"]["base_url"],
            max_tokens=2048,
            temperature=0.7,
            free_tier=True,
            requests_per_minute=30
        )

    @classmethod
    def get_config_from_env(cls) -> LLMConfig:
        model = os.getenv("LLM_MODEL", "llama3-70b-8192")
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("Missing GROQ_API_KEY")
        
        return LLMConfig(
            provider="groq",
            model=model,
            api_key=key,
            base_url=cls.PROVIDERS["groq"]["base_url"],
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            free_tier=True,
            requests_per_minute=30
        )

    @classmethod
    def list_available_models(cls) -> Dict[str, Any]:
        key_present = bool(os.getenv("GROQ_API_KEY"))
        return {
            "groq": {
                "name": cls.PROVIDERS["groq"]["name"],
                "models": cls.PROVIDERS["groq"]["models"],
                "available": key_present,
                "required_key": "GROQ_API_KEY"
            }
        }
