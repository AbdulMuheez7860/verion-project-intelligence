import json
from typing import Any

import httpx

from app.integrations.llm.base import LLMCompletion, LLMMessage, LLMProvider, LLMProviderError


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, *, api_key: str, base_url: str, model: str, timeout_seconds: float = 60.0) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(self, messages: list[LLMMessage], *, temperature: float = 0.2) -> LLMCompletion:
        payload = {
            "model": self._model,
            "messages": [{"role": message.role, "content": message.content} for message in messages],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"LLM request failed: {exc}") from exc

        content = _extract_content(data)
        if not content:
            raise LLMProviderError("LLM returned an empty response.")
        return LLMCompletion(content=content, model=self._model)


def _extract_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices", [])
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message", {})
    if not isinstance(message, dict):
        return ""
    content = message.get("content", "")
    return content if isinstance(content, str) else ""


def parse_json_object(content: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMProviderError("LLM response was not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise LLMProviderError("LLM response must be a JSON object.")
    return payload