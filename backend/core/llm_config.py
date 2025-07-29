"""
LLM Configuration - Groq with Dynamic Model Selection & Failover
"""
import os
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

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
    tokens_per_hour: Optional[int] = None
    context_window: Optional[int] = None

class LLMManager:
    _exhausted_models: Dict[str, float] = {}
    COOLDOWN_SECONDS = int(os.getenv("LLM_COOLDOWN_SECONDS", "300"))

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
                }
            }
        }
    }

    @classmethod
    def get_available_config(cls) -> LLMConfig:
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("Missing GROQ_API_KEY")

        for model_name, meta in cls.PROVIDERS["groq"]["models"].items():
            cooldown_until = cls._exhausted_models.get(model_name)

            if cooldown_until and time.time() < cooldown_until:
                logger.info(f"Skipping model {model_name}: in cooldown until {cooldown_until}")
                continue

            logger.info(f"Trying Groq model: {model_name}")
            return LLMConfig(
                provider="groq",
                model=model_name,
                api_key=key,
                base_url=cls.PROVIDERS["groq"]["base_url"],
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                free_tier=True,
                requests_per_minute=meta["requests_per_minute"],
                tokens_per_hour=meta["tokens_per_hour"],
                context_window=meta["context_window"]
            )

        raise RuntimeError("All Groq LLM models are currently exhausted or unavailable.")

    @classmethod
    def get_config_from_env(cls) -> LLMConfig:
        return cls.get_available_config()

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
