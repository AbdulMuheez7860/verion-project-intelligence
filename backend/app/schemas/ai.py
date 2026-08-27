from app.schemas.common import APIModel


class FindingAIExplanation(APIModel):
    explanation: str
    remediation_suggestion: str
    generated_at: str
    model: str
    source: str = "ai"
    disclaimer: str = (
        "AI-generated explanation based on scanner output. "
        "Does not replace static analysis or change finding severity."
    )