import json
from datetime import UTC, datetime
from typing import Any

from app.integrations.llm.base import LLMMessage, LLMNotConfiguredError, LLMProvider, LLMProviderError
from app.integrations.llm.factory import get_llm_provider, is_llm_configured
from app.integrations.llm.openai_compatible import parse_json_object
from app.repositories.findings import FindingRepository
from app.schemas.ai import FindingAIExplanation

SYSTEM_PROMPT = """You are Verion's finding assistant.

Your job is to explain static analysis findings produced by deterministic scanners
(Semgrep, Bandit, Ruff, ESLint, pip-audit, detect-secrets).

Rules:
- Explain ONLY the provided finding. Do not invent new vulnerabilities.
- Do NOT assign risk scores, severity changes, or new findings.
- Do NOT claim compliance, certification, or guarantees.
- Base your explanation on the scanner rule, description, file, and line provided.
- Provide a practical remediation suggestion a developer can act on.

Respond with valid JSON only:
{
  "explanation": "plain-language explanation of why this finding matters",
  "remediation_suggestion": "concrete steps to fix or mitigate the issue"
}"""


class FindingAIService:
    def __init__(self, findings: FindingRepository, provider: LLMProvider | None = None) -> None:
        self._findings = findings
        self._provider = provider

    def llm_available(self) -> bool:
        return self._provider is not None or is_llm_configured()

    async def explain_finding(
        self,
        finding_id: str,
        organization_id: str,
        *,
        regenerate: bool = False,
    ) -> FindingAIExplanation:
        doc = await self._findings.get_by_id(finding_id, organization_id)
        if not doc:
            raise ValueError("Finding not found.")

        existing = doc.get("ai_explanation")
        if not regenerate and isinstance(existing, dict) and existing.get("explanation"):
            return self._to_explanation(existing)

        provider = self._resolve_provider()
        completion = await provider.complete(
            [
                LLMMessage(role="system", content=SYSTEM_PROMPT),
                LLMMessage(role="user", content=_build_user_prompt(doc)),
            ],
        )
        payload = parse_json_object(completion.content)
        explanation_text = str(payload.get("explanation", "")).strip()
        remediation_text = str(payload.get("remediation_suggestion", "")).strip()
        if not explanation_text or not remediation_text:
            raise LLMProviderError("LLM response missing explanation or remediation.")

        stored = {
            "explanation": explanation_text,
            "remediation_suggestion": remediation_text,
            "generated_at": datetime.now(UTC).isoformat(),
            "model": completion.model,
            "source": "ai",
            "disclaimer": (
                "AI-generated explanation based on scanner output. "
                "Does not replace static analysis or change finding severity."
            ),
        }
        await self._findings.update_ai_explanation(finding_id, organization_id, stored)
        return self._to_explanation(stored)

    def _resolve_provider(self) -> LLMProvider:
        if self._provider is not None:
            return self._provider
        try:
            return get_llm_provider()
        except LLMNotConfiguredError as exc:
            raise LLMNotConfiguredError(
                "LLM is not configured. Set LLM_API_KEY to enable AI explanations.",
            ) from exc

    def _to_explanation(self, payload: dict[str, Any]) -> FindingAIExplanation:
        return FindingAIExplanation(
            explanation=str(payload.get("explanation", "")),
            remediation_suggestion=str(payload.get("remediation_suggestion", "")),
            generated_at=str(payload.get("generated_at", "")),
            model=str(payload.get("model", "unknown")),
            source=str(payload.get("source", "ai")),
            disclaimer=str(
                payload.get(
                    "disclaimer",
                    "AI-generated explanation based on scanner output. "
                    "Does not replace static analysis or change finding severity.",
                ),
            ),
        )


def _build_user_prompt(finding: dict[str, Any]) -> str:
    metadata = finding.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    scanner_engine = metadata.get("engine", "static-analyzer")
    context = {
        "scanner": scanner_engine,
        "rule_id": finding.get("rule_id"),
        "title": finding.get("title"),
        "description": finding.get("description"),
        "severity": finding.get("severity"),
        "category": finding.get("category"),
        "file": finding.get("file"),
        "line": finding.get("line"),
        "scanner_remediation": finding.get("remediation"),
        "metadata": metadata,
    }
    return (
        "Explain this scanner finding and suggest remediation.\n\n"
        f"{json.dumps(context, indent=2)}"
    )