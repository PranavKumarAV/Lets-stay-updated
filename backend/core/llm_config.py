"""
LLM Configuration - Switch between Groq, OpenAI, Anthropic
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
    free_tier: bool = False
    requests_per_minute: Optional[int] = None

class LLMManager:
    PROVIDERS = {
        "groq": {
            "name": "Groq",
            "base_url": "https://api.groq.com/openai/v1",
            "models": {
                "llama-3.1-70b-versatile": {
                    "name": "Llama 3.1 70B",
                    "free_tier": True,
                    "requests_per_minute": 30,
                    "tokens_per_hour": 1000000,
                    "context_window": 131072
                },
                "llama-3.1-8b-instant": {
                    "name": "Llama 3.1 8B (Ultra Fast)",
                    "free_tier": True,
                    "requests_per_minute": 30,
                    "tokens_per_hour": 1000000,
                    "context_window": 131072
                },
                "mixtral-8x7b-32768": {
                    "name": "Mixtral 8x7B",
                    "free_tier": True,
                    "requests_per_minute": 30,
                    "tokens_per_hour": 1000000,
                    "context_window": 32768
                }
            }
        },
        "openai": {
            "name": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "models": {
                "gpt-4o-mini": {
                    "name": "GPT-4o Mini",
                    "free_tier": False,
                    "cost_per_1k_tokens": 0.00015,
                    "context_window": 128000
                },
                "gpt-4o": {
                    "name": "GPT-4o",
                    "free_tier": False,
                    "cost_per_1k_tokens": 0.005,
                    "context_window": 128000
                }
            }
        },
        "anthropic": {
            "name": "Anthropic",
            "base_url": "https://api.anthropic.com/v1",
            "models": {
                "claude-3-haiku-20240307": {
                    "name": "Claude 3 Haiku",
                    "free_tier": False,
                    "cost_per_1k_tokens": 0.00025,
                    "context_window": 200000
                }
            }
        }
    }

    @classmethod
    def get_best_free_config(cls) -> LLMConfig:
        if os.getenv("GROQ_API_KEY"):
            return LLMConfig(
                provider="groq",
                model="llama-3.1-70b-versatile",
                api_key=os.getenv("GROQ_API_KEY"),
                base_url=cls.PROVIDERS["groq"]["base_url"],
                max_tokens=2048,
                temperature=0.7,
                free_tier=True,
                requests_per_minute=30
            )
        raise ValueError("No free-tier LLM API key found. Set GROQ_API_KEY.")

    @classmethod
    def get_config_from_env(cls) -> LLMConfig:
        provider = os.getenv("LLM_PROVIDER", "groq").lower()
        model = os.getenv("LLM_MODEL", "llama-3.1-70b-versatile")

        if provider == "groq":
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
        elif provider == "openai":
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                raise ValueError("Missing OPENAI_API_KEY")
            return LLMConfig(
                provider="openai",
                model=model if model.startswith("gpt") else "gpt-4o-mini",
                api_key=key,
                base_url=cls.PROVIDERS["openai"]["base_url"],
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                free_tier=False
            )

        return cls.get_best_free_config()

    @classmethod
    def list_available_models(cls) -> Dict[str, Any]:
        available = {}
        for provider_key, provider_info in cls.PROVIDERS.items():
            env_var = f"{provider_key.upper()}_API_KEY"
            available[provider_key] = {
                "name": provider_info["name"],
                "models": provider_info["models"],
                "available": bool(os.getenv(env_var)),
                "required_key": env_var
            }
        return available
