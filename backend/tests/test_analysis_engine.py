import json
from pathlib import Path

from app.analyzers.bandit import parse_bandit_results
from app.analyzers.dependencies import parse_pip_audit_results
from app.analyzers.ruff import parse_ruff_results
from app.analyzers.secrets import parse_detect_secrets_results
from app.analyzers.semgrep import parse_semgrep_results
from app.services.risk_engine import compute_risk_metrics


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_semgrep_results():
    payload = json.loads((FIXTURES / "semgrep.json").read_text(encoding="utf-8"))
    findings = parse_semgrep_results(payload, "/workspace")
    assert len(findings) == 1
    assert findings[0].rule_id == "python.lang.security.audit.insecure-transport"
    assert findings[0].category == "security"


def test_parse_bandit_results():
    payload = json.loads((FIXTURES / "bandit.json").read_text(encoding="utf-8"))
    findings = parse_bandit_results(payload, "/workspace")
    assert len(findings) == 1
    assert findings[0].rule_id == "B105"
    assert findings[0].category == "security"


def test_parse_ruff_results():
    payload = json.loads((FIXTURES / "ruff.json").read_text(encoding="utf-8"))
    findings = parse_ruff_results(payload, "/workspace")
    assert len(findings) == 1
    assert findings[0].rule_id == "F401"
    assert findings[0].category == "quality"


def test_parse_detect_secrets_results():
    payload = json.loads((FIXTURES / "detect-secrets.json").read_text(encoding="utf-8"))
    findings = parse_detect_secrets_results(payload, "/workspace")
    assert len(findings) == 1
    assert findings[0].category == "secret"
    assert findings[0].severity == "high"


def test_parse_pip_audit_results():
    payload = json.loads((FIXTURES / "pip-audit.json").read_text(encoding="utf-8"))
    findings = parse_pip_audit_results(payload)
    assert len(findings) == 1
    assert findings[0].category == "dependency"
    assert findings[0].rule_id == "PYSEC-2024-1"


def test_risk_engine_scores():
    findings = [
        {"severity": "critical", "category": "security"},
        {"severity": "medium", "category": "quality"},
    ]
    metrics = compute_risk_metrics(findings)
    assert metrics.security_score == 75.0
    assert metrics.code_quality_score == 92.0
    assert metrics.risk_level == "critical"
