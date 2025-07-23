"""
LLM Configuration - Easy to switch between different LLM providers
Currently supports: Groq (free), OpenAI, Anthropic, and more
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
    """Manages different LLM providers with easy switching"""
    
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
        """Get the best free LLM configuration available"""
        # Priority: Groq Llama 3.1 70B (best free model)
        if os.getenv("GROQ_API_KEY"):
            return LLMConfig(
                provider="groq",
                model="llama-3.1-70b-versatile",
                api_key=os.getenv("GROQ_API_KEY"),
                base_url="https://api.groq.com/openai/v1",
                max_tokens=2048,
                temperature=0.7,
                free_tier=True,
                requests_per_minute=30
            )
        
        # Fallback to other providers if keys are available
        if os.getenv("OPENAI_API_KEY"):
            return LLMConfig(
                provider="openai",
                model="gpt-4o-mini",
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url="https://api.openai.com/v1",
                max_tokens=2048,
                temperature=0.7,
                free_tier=False
            )
            
        raise ValueError("No LLM API keys found. Please set GROQ_API_KEY for free usage.")
    
    @classmethod
    def get_config_from_env(cls) -> LLMConfig:
        """Get LLM config from environment variables with fallbacks"""
        provider = os.getenv("LLM_PROVIDER", "groq").lower()
        model = os.getenv("LLM_MODEL", "llama-3.1-70b-versatile")
        
        if provider == "groq" and os.getenv("GROQ_API_KEY"):
            return LLMConfig(
                provider="groq",
                model=model,
                api_key=os.getenv("GROQ_API_KEY"),
                base_url="https://api.groq.com/openai/v1",
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                free_tier=True,
                requests_per_minute=30
            )
        elif provider == "openai" and os.getenv("OPENAI_API_KEY"):
            return LLMConfig(
                provider="openai",
                model=model if model.startswith("gpt") else "gpt-4o-mini",
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url="https://api.openai.com/v1",
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                free_tier=False
            )
        
        # Default to best free option
        return cls.get_best_free_config()
    
    @classmethod
    def list_available_models(cls) -> Dict[str, Any]:
        """List all available models with their capabilities"""
        available = {}
        
        for provider_key, provider_info in cls.PROVIDERS.items():
            api_key_name = f"{provider_key.upper()}_API_KEY"
            if os.getenv(api_key_name):
                available[provider_key] = {
                    "name": provider_info["name"],
                    "models": provider_info["models"],
                    "available": True
                }
            else:
                available[provider_key] = {
                    "name": provider_info["name"],
                    "models": provider_info["models"],
                    "available": False,
                    "required_key": api_key_name
                }
                
        return available