from functools import lru_cache

from app.core.config import get_settings
from app.integrations.llm.base import LLMNotConfiguredError, LLMProvider
from app.integrations.llm.openai_compatible import OpenAICompatibleProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if not settings.llm_configured:
        raise LLMNotConfiguredError("LLM is not configured.")
    return OpenAICompatibleProvider(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )


def is_llm_configured() -> bool:
    return get_settings().llm_configured
