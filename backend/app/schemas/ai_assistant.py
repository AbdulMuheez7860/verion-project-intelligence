from typing import Literal

from pydantic import Field

from app.schemas.common import APIModel

AssistantRole = Literal["user", "assistant"]


class AssistantChatMessage(APIModel):
    role: AssistantRole
    content: str = Field(min_length=1, max_length=4000)


class AssistantChatRequest(APIModel):
    message: str = Field(min_length=1, max_length=4000)
    # Prior turns of this conversation, supplied by the client (the backend is
    # stateless per-request). Capped to keep prompt size and cost bounded.
    history: list[AssistantChatMessage] = Field(default_factory=list, max_length=20)


class AssistantEvidenceRef(APIModel):
    """A pointer to a specific piece of evidence the assistant's answer relied on,
    so the frontend can render "grounded in: finding #123" style citations and the
    user can verify the claim against the real finding rather than trusting prose."""

    finding_id: str | None = None
    kind: Literal["finding", "score", "dependency", "analyzer_status", "repository"]
    label: str


class AssistantChatResponse(APIModel):
    reply: str
    evidence: list[AssistantEvidenceRef] = Field(default_factory=list)
    has_sufficient_evidence: bool
    model: str
    generated_at: str
    disclaimer: str = (
        "AI-generated response based on Verion's stored analysis evidence for this "
        "repository. It can be wrong or incomplete — verify against the underlying "
        "findings before acting, especially for security-critical decisions."
    )


class AssistantStatusResponse(APIModel):
    available: bool
    reason: str | None = None
    has_analysis_data: bool
