import json
import subprocess
from pathlib import Path

import pytest

from app.analyzers.dependencies import DependencyAnalyzer, parse_npm_audit_results


def _completed(stdout: str, returncode: int = 1, stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["npm", "audit"], returncode=returncode, stdout=stdout, stderr=stderr
    )


SYNTHETIC_VULNERABLE_PAYLOAD = {
    "vulnerabilities": {
        "lodash": {
            "name": "lodash",
            "severity": "high",
            "isDirect": True,
            "via": [{"title": "Prototype Pollution in lodash", "severity": "high"}],
            "range": "<4.17.21",
            "fixAvailable": {"name": "lodash", "version": "4.17.21"},
        }
    },
    "metadata": {"vulnerabilities": {"total": 1}},
}

# Captured verbatim from a real `npm audit --json` invocation against a
# network-blocked environment (see engineering notes) - a genuine
# failure payload, not a synthetic guess.
REAL_CAPTURED_FAILURE_PAYLOAD = json.dumps(
    {
        "message": "403 Forbidden - POST https://registry.npmjs.org/-/npm/v1/security/audits/quick",
        "method": "POST",
        "uri": "https://registry.npmjs.org/-/npm/v1/security/audits/quick",
        "statusCode": 403,
        "body": "Host not in allowlist: registry.npmjs.org.",
        "error": {"summary": "", "detail": ""},
    }
)


def test_npm_audit_failure_is_never_treated_as_clean():
    analyzer = DependencyAnalyzer()
    result = _completed(REAL_CAPTURED_FAILURE_PAYLOAD)

    with pytest.raises(RuntimeError, match="npm audit failed"):
        analyzer._process_npm_audit_result(result=result, manifest=Path("package.json"))


def test_npm_audit_vulnerable_package_produces_finding():
    analyzer = DependencyAnalyzer()
    result = _completed(json.dumps(SYNTHETIC_VULNERABLE_PAYLOAD))

    findings, records = analyzer._process_npm_audit_result(
        result=result, manifest=Path("package.json")
    )

    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert "Prototype Pollution" in findings[0].description
    assert findings[0].remediation == "Upgrade lodash to lodash@4.17.21."

    assert len(records) == 1
    assert records[0].status == "vulnerable"


def test_npm_audit_clean_scan_produces_no_findings():
    analyzer = DependencyAnalyzer()
    result = _completed(json.dumps({"vulnerabilities": {}, "metadata": {}}), returncode=0)

    findings, records = analyzer._process_npm_audit_result(
        result=result, manifest=Path("package.json")
    )

    assert findings == []
    assert records == []


def test_npm_audit_malformed_json_raises():
    analyzer = DependencyAnalyzer()
    result = _completed("not json at all")

    with pytest.raises(RuntimeError, match="invalid JSON"):
        analyzer._process_npm_audit_result(result=result, manifest=Path("package.json"))


def test_npm_audit_empty_stdout_raises():
    analyzer = DependencyAnalyzer()
    result = _completed("", returncode=1, stderr="some npm error")

    with pytest.raises(RuntimeError, match="no JSON output"):
        analyzer._process_npm_audit_result(result=result, manifest=Path("package.json"))


def test_package_json_without_lockfile_is_unsupported(tmp_path: Path):
    analyzer = DependencyAnalyzer()
    (tmp_path / "package.json").write_text(json.dumps({"name": "x"}))

    # supports() is True (a manifest exists)...
    assert analyzer.supports(tmp_path) is True

    # ...but scanning must fail explicitly rather than report "no deps".
    with pytest.raises(RuntimeError, match="no package-lock.json"):
        analyzer.scan(tmp_path)


def test_supports_detects_package_json(tmp_path: Path):
    analyzer = DependencyAnalyzer()
    assert analyzer.supports(tmp_path) is False

    (tmp_path / "package.json").write_text("{}")
    assert analyzer.supports(tmp_path) is True


def test_parse_npm_audit_results_direct():
    findings = parse_npm_audit_results(SYNTHETIC_VULNERABLE_PAYLOAD, Path("package.json"))
    assert len(findings) == 1
    assert findings[0].category == "dependency"
    assert findings[0].metadata["engine"] == "npm-audit"
