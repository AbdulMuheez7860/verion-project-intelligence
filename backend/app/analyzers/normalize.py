import json
import re
from pathlib import Path
from typing import Any


SEVERITY_ORDER = ("critical", "high", "medium", "low")

SEVERITY_WEIGHTS = {
    "critical": 25,
    "high": 15,
    "medium": 8,
    "low": 3,
}


_SEVERITY_ALIASES: dict[str, str] = {
    "critical": "critical",
    "crit": "critical",
    "fatal": "critical",

    "high": "high",
    "error": "high",
    "err": "high",

    "medium": "medium",
    "moderate": "medium",
    "warning": "medium",
    "warn": "medium",

    "low": "low",
    "info": "low",
    "informational": "low",
    "note": "low",
}


def normalize_severity(value: str | None) -> str:
    """
    Normalize severity values produced by different analysis engines.

    Supported examples:
        critical, high, medium, low
        error, warning, info
        fatal, moderate, note

    Unknown or missing values default to low rather than inventing
    a higher severity.
    """
    if value is None:
        return "low"

    normalized = str(value).strip().lower()

    if not normalized:
        return "low"

    return _SEVERITY_ALIASES.get(normalized, "low")


def severity_weight(value: str | None) -> int:
    """
    Return the normalized severity weight used by the risk engine.
    """
    return SEVERITY_WEIGHTS[normalize_severity(value)]


def relative_path(
    path: str,
    workspace_root: str | None = None,
) -> str:
    """
    Convert an analyzer file path into a stable repository-relative path.

    Handles:
    - Windows paths
    - Linux/macOS paths
    - absolute paths
    - ./ prefixes
    - ../ prefixes where possible
    - mixed path separators
    - workspace-root prefixes
    """
    if not path:
        return ""

    raw_path = str(path).strip()

    if not raw_path:
        return ""

    # Normalize Windows separators.
    normalized_path = raw_path.replace("\\", "/")

    # Normalize workspace root.
    if workspace_root:
        root = str(workspace_root).strip().replace("\\", "/").rstrip("/")

        if root:
            # Exact workspace path.
            if normalized_path == root:
                normalized_path = ""

            # Workspace prefix.
            elif normalized_path.startswith(f"{root}/"):
                normalized_path = normalized_path[len(root) + 1 :]

            # Case-insensitive comparison is useful for Windows paths.
            elif normalized_path.lower().startswith(f"{root.lower()}/"):
                normalized_path = normalized_path[len(root) + 1 :]

    # Remove leading "./".
    while normalized_path.startswith("./"):
        normalized_path = normalized_path[2:]

    # Avoid returning an absolute Unix path.
    normalized_path = normalized_path.lstrip("/")

    # Handle Windows drive paths such as:
    # C:/repo/file.py
    if re.match(r"^[A-Za-z]:/", normalized_path):
        drive, remainder = normalized_path.split(":", 1)
        normalized_path = f"{drive}{remainder}"

    # Collapse duplicate separators.
    normalized_path = re.sub(r"/+", "/", normalized_path)

    # Normalize "." and ".." segments without allowing filesystem access.
    parts: list[str] = []

    for part in normalized_path.split("/"):
        if not part or part == ".":
            continue

        if part == "..":
            if parts:
                parts.pop()
            continue

        parts.append(part)

    return "/".join(parts)


def parse_json_lines(stdout: str) -> list[dict[str, Any]]:
    """
    Parse newline-delimited JSON safely.

    Some analysis tools can emit:
        {"result": ...}
        {"result": ...}

    while also emitting non-JSON diagnostic output. Invalid lines
    are ignored rather than causing the entire analyzer to fail.
    """
    items: list[dict[str, Any]] = []

    if not stdout:
        return items

    for line in stdout.splitlines():
        line = line.strip()

        if not line:
            continue

        try:
            payload = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue

        if isinstance(payload, dict):
            items.append(payload)

    return items


def parse_json_document(stdout: str) -> dict[str, Any] | list[Any] | None:
    """
    Parse a complete JSON document.

    Useful when analyzers return one JSON object/list instead of
    newline-delimited JSON.
    """
    if not stdout or not stdout.strip():
        return None

    try:
        payload = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        return None

    if isinstance(payload, (dict, list)):
        return payload

    return None


def first_int(*values: Any, default: int = 1) -> int:
    """
    Return the first valid positive integer.

    Handles:
        10
        "10"
        "10.0"
        None
        invalid strings

    Analyzer line numbers should always be at least 1.
    """
    for value in values:
        if isinstance(value, bool):
            continue

        if isinstance(value, int) and value > 0:
            return value

        if isinstance(value, float) and value.is_integer() and value > 0:
            return int(value)

        if isinstance(value, str):
            candidate = value.strip()

            if not candidate:
                continue

            if candidate.isdigit():
                parsed = int(candidate)

                if parsed > 0:
                    return parsed

            # Some tools may return "12.0".
            try:
                parsed_float = float(candidate)

                if parsed_float.is_integer() and parsed_float > 0:
                    return int(parsed_float)
            except ValueError:
                continue

    return default


def truncate(text: str, limit: int = 500) -> str:
    """
    Normalize whitespace and limit description size.

    Prevents extremely large analyzer messages from being stored
    in MongoDB/API responses.
    """
    if limit < 4:
        raise ValueError("truncate limit must be at least 4")

    cleaned = re.sub(r"\s+", " ", str(text)).strip()

    if len(cleaned) <= limit:
        return cleaned

    return cleaned[: limit - 3].rstrip() + "..."


def normalize_rule_id(value: Any, default: str = "unknown") -> str:
    """
    Normalize analyzer rule identifiers.
    """
    if value is None:
        return default

    normalized = str(value).strip()

    if not normalized:
        return default

    return normalized


def normalize_confidence(
    value: Any,
    default: float | None = None,
) -> float | None:
    """
    Normalize confidence values to the range 0.0-1.0.

    Supports:
        0.95
        "0.95"
        95
        "95%"
    """
    if value is None:
        return default

    try:
        if isinstance(value, str):
            raw = value.strip()

            if not raw:
                return default

            if raw.endswith("%"):
                number = float(raw[:-1]) / 100.0
            else:
                number = float(raw)
        else:
            number = float(value)
    except (TypeError, ValueError):
        return default

    # Treat values such as 95 as 95%.
    if number > 1.0 and number <= 100.0:
        number /= 100.0

    if not 0.0 <= number <= 1.0:
        return default

    return round(number, 4)


def is_safe_repository_path(path: str) -> bool:
    """
    Check whether a normalized repository path is suitable for
    displaying/storing as a finding path.

    This does not access the filesystem.
    """
    normalized = relative_path(path)

    if not normalized:
        return False

    if normalized.startswith("/"):
        return False

    if re.match(r"^[A-Za-z]:/", normalized):
        return False

    parts = normalized.split("/")

    return ".." not in parts


__all__ = [
    "SEVERITY_ORDER",
    "SEVERITY_WEIGHTS",
    "normalize_severity",
    "severity_weight",
    "relative_path",
    "parse_json_lines",
    "parse_json_document",
    "first_int",
    "truncate",
    "normalize_rule_id",
    "normalize_confidence",
    "is_safe_repository_path",
]