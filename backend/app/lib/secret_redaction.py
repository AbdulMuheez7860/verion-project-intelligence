import re

_SECRET_PATTERNS = [
    re.compile(r"(?i)(password|secret|token|api[_-]?key|auth)\s*[=:]\s*\S+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9\-._~+/]+=*"),
]


def redact_sensitive_text(value: str | None) -> str | None:
    if value is None:
        return None
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: match.group(0).split("=")[0] + "=***REDACTED***" if "=" in match.group(0) else "***REDACTED***", redacted)
    return redacted
