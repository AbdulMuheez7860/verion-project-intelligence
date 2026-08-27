from dataclasses import dataclass


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMCompletion:
    content: str
    model: str


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""

    pass


class LLMNotConfiguredError(LLMProviderError):
    """Raised when the LLM provider is not configured."""

    pass


class LLMProvider:
    """Abstract interface for LLM providers."""

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
    ) -> LLMCompletion:
        raise NotImplementedError

    @property
    def model_name(self) -> str:
        raise NotImplementedError