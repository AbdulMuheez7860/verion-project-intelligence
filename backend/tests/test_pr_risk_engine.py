from app.services.pr_risk_engine import (
    PRRiskSignals,
    compute_pr_risk_score,
    file_matches_changed_paths,
    filter_findings_for_changed_files,
)


def test_pr_risk_score_matches_portfolio_example():
    signals = PRRiskSignals(
        security_findings=[
            {"severity": "high"},
            {"severity": "high"},
            {"severity": "medium"},
        ],
        files_changed=18,
        additions=900,
        deletions=300,
        changed_files=["src/payment/service.ts", "requirements.txt"],
        coverage_percent=58,
        dependency_vulnerabilities=1,
        repository_risk_level="high",
        prior_pr_risk_average=48,
    )
    score = compute_pr_risk_score(signals)
    assert score.value >= 50
    assert score.level in {"high", "critical"}
    labels = [factor.label for factor in score.factors]
    assert "Security findings" in labels
    assert "Change size" in labels
    assert "Change complexity" in labels
    assert "Test coverage" in labels
    assert "Dependency changes" in labels
    assert "Historical risk" in labels
    assert score.engine == "Verion Risk Engine v1"
    assert sum(factor.contribution for factor in score.factors) >= score.value


def test_filter_findings_for_changed_files():
    findings = [
        {"file": "app/main.py", "severity": "high"},
        {"file": "docs/readme.md", "severity": "low"},
    ]
    matched = filter_findings_for_changed_files(findings, ["src/app/main.py"])
    assert len(matched) == 1
    assert file_matches_changed_paths("app/main.py", ["src/app/main.py"])


def test_pr_risk_without_coverage_omits_factor():
    signals = PRRiskSignals(
        security_findings=[],
        files_changed=2,
        additions=20,
        deletions=10,
        changed_files=["README.md"],
        coverage_percent=None,
        repository_risk_level="low",
    )
    score = compute_pr_risk_score(signals)
    labels = [factor.label for factor in score.factors]
    assert "Coverage" not in labels
