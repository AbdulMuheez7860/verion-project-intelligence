import json
from datetime import UTC, datetime

import pytest

from app.integrations.llm.base import LLMCompletion, LLMMessage, LLMProvider
from app.repositories.findings import FindingRepository
from app.services.finding_ai import FindingAIService, _build_user_prompt


class FakeLLMProvider(LLMProvider):
    def __init__(self) -> None:
        self.last_messages: list[LLMMessage] = []

    @property
    def model_name(self) -> str:
        return "fake-model"

    async def complete(self, messages: list[LLMMessage], *, temperature: float = 0.2) -> LLMCompletion:
        self.last_messages = messages
        return LLMCompletion(
            content=json.dumps(
                {
                    "explanation": "This rule flags insecure transport because HTTP is used instead of HTTPS.",
                    "remediation_suggestion": "Switch the endpoint to HTTPS and enforce TLS.",
                },
            ),
            model=self.model_name,
        )


@pytest.mark.asyncio
async def test_explain_finding_persists_ai_explanation(client):
    from bson import ObjectId

    from app.core.database import get_database

    db = get_database()
    finding_id = str(ObjectId())
    organization_id = "org-test"

    await db["findings"].insert_one(
        {
            "_id": ObjectId(finding_id),
            "organization_id": organization_id,
            "repository_id": "repo-1",
            "analysis_id": "analysis-1",
            "severity": "high",
            "category": "security",
            "rule_id": "python.lang.security.audit.insecure-transport",
            "title": "Insecure transport",
            "description": "Detected HTTP usage",
            "file": "app/main.py",
            "line": 12,
            "status": "open",
            "metadata": {"engine": "semgrep"},
            "created_at": datetime.now(UTC),
        },
    )

    service = FindingAIService(FindingRepository(db), provider=FakeLLMProvider())
    explanation = await service.explain_finding(finding_id, organization_id)

    assert explanation.source == "ai"
    assert "insecure transport" in explanation.explanation.lower()
    assert explanation.remediation_suggestion

    stored = await db["findings"].find_one({"_id": ObjectId(finding_id)})
    assert stored is not None
    assert stored["ai_explanation"]["model"] == "fake-model"


def test_build_user_prompt_includes_scanner_context():
    prompt = _build_user_prompt(
        {
            "rule_id": "B105",
            "title": "Hardcoded password",
            "description": "Possible hardcoded password",
            "severity": "high",
            "category": "security",
            "file": "app/config.py",
            "line": 8,
            "remediation": None,
            "metadata": {"engine": "bandit"},
        },
    )
    assert "bandit" in prompt
    assert "B105" in prompt
    assert "risk score" not in prompt.lower()


@pytest.mark.asyncio
async def test_explain_finding_returns_cached_explanation(client):
    from bson import ObjectId

    from app.core.database import get_database

    db = get_database()
    finding_id = str(ObjectId())
    organization_id = "org-cache"
    cached = {
        "explanation": "Cached explanation",
        "remediation_suggestion": "Cached remediation",
        "generated_at": datetime.now(UTC).isoformat(),
        "model": "cached-model",
        "source": "ai",
    }
    await db["findings"].insert_one(
        {
            "_id": ObjectId(finding_id),
            "organization_id": organization_id,
            "repository_id": "repo-1",
            "analysis_id": "analysis-1",
            "severity": "low",
            "category": "quality",
            "rule_id": "F401",
            "title": "Unused import",
            "description": "Import unused",
            "file": "app/main.py",
            "line": 1,
            "status": "open",
            "metadata": {"engine": "ruff"},
            "ai_explanation": cached,
            "created_at": datetime.now(UTC),
        },
    )

    provider = FakeLLMProvider()
    service = FindingAIService(FindingRepository(db), provider=provider)
    explanation = await service.explain_finding(finding_id, organization_id)

    assert explanation.explanation == "Cached explanation"
    assert provider.last_messages == []
