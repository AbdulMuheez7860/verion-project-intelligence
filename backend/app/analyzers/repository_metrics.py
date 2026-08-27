"""
Repository / LOC / language-distribution metrics.

Verion previously had NO independent computation of repository size,
file counts, lines-of-code, or language distribution. The only
"language" information available anywhere in the pipeline was GitHub's
single primary-language string for the whole repo, and the frontend
explicitly displayed "not available" for every metric in this category.

This module fills that gap with a dependency-free, purely local
computation:

    - total / source / test / config / documentation file counts
    - repository size on disk
    - per-language file count + LOC (by extension)
    - total / code / comment / blank LOC, with a documented,
      best-effort per-language comment heuristic

It deliberately does NOT attempt cyclomatic complexity, duplication,
or maintainability scoring - those require a real per-language parser
(e.g. tree-sitter grammars) that is not available in this analyzer's
dependency-free design, and Verion must not fabricate them. Those
remain explicitly reported as unavailable elsewhere in the product.

SECURITY (hostile repository model):
    - Symlinks are never followed. A cloned repository is untrusted
      input and a symlink can point outside the workspace (e.g. at
      `/etc/passwd`); following it during a "read every file" scan
      would leak host filesystem content into analysis results.
    - Individual files above MAX_FILE_SIZE_BYTES are skipped for LOC
      counting (still counted toward file totals) to avoid reading
      pathologically large files into memory.
    - The walk stops after MAX_FILES_SCANNED files as a hard resource
      ceiling so a repository with millions of tiny files cannot make
      analysis run unbounded.
    - Directories that are virtually never source (`.git`, dependency
      caches, build output) are pruned from the walk both for
      correctness (they would otherwise dominate/skew LOC numbers with
      vendored code) and for performance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ----------------------------------------------------------------------
# Resource limits (hostile-repository hardening)
# ----------------------------------------------------------------------

MAX_FILES_SCANNED = 50_000
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB - large generated/data files
MAX_TOTAL_BYTES_READ = 500 * 1024 * 1024  # 500 MB ceiling across all files

EXCLUDED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "vendor",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "dist",
    "build",
    "out",
    "target",
    ".next",
    ".nuxt",
    ".turbo",
    "coverage",
    ".idea",
    ".vscode",
    "bin",
    "obj",
}

# Extension -> (language label, category)
# category is one of: "source", "markup", "config", "docs", "data"
LANGUAGE_EXTENSIONS: dict[str, tuple[str, str]] = {
    ".py": ("Python", "source"),
    ".js": ("JavaScript", "source"),
    ".jsx": ("JavaScript", "source"),
    ".mjs": ("JavaScript", "source"),
    ".cjs": ("JavaScript", "source"),
    ".ts": ("TypeScript", "source"),
    ".tsx": ("TypeScript", "source"),
    ".java": ("Java", "source"),
    ".kt": ("Kotlin", "source"),
    ".kts": ("Kotlin", "source"),
    ".swift": ("Swift", "source"),
    ".c": ("C", "source"),
    ".h": ("C", "source"),
    ".cc": ("C++", "source"),
    ".cpp": ("C++", "source"),
    ".cxx": ("C++", "source"),
    ".hpp": ("C++", "source"),
    ".cs": ("C#", "source"),
    ".go": ("Go", "source"),
    ".rs": ("Rust", "source"),
    ".php": ("PHP", "source"),
    ".rb": ("Ruby", "source"),
    ".scala": ("Scala", "source"),
    ".m": ("Objective-C", "source"),
    ".mm": ("Objective-C++", "source"),
    ".sh": ("Shell", "source"),
    ".bash": ("Shell", "source"),
    ".sql": ("SQL", "source"),
    ".html": ("HTML", "markup"),
    ".htm": ("HTML", "markup"),
    ".css": ("CSS", "markup"),
    ".scss": ("SCSS", "markup"),
    ".less": ("Less", "markup"),
    ".vue": ("Vue", "source"),
    ".svelte": ("Svelte", "source"),
    ".json": ("JSON", "config"),
    ".yml": ("YAML", "config"),
    ".yaml": ("YAML", "config"),
    ".toml": ("TOML", "config"),
    ".ini": ("INI", "config"),
    ".cfg": ("INI", "config"),
    ".xml": ("XML", "config"),
    ".md": ("Markdown", "docs"),
    ".rst": ("reStructuredText", "docs"),
    ".txt": ("Text", "docs"),
}

# Per-language single-line comment prefixes. Best-effort only - block
# comments are not modeled, so comment_loc is a lower bound, not an
# exact count. This is documented in the returned metrics rather than
# silently presented as exact.
LINE_COMMENT_PREFIXES: dict[str, tuple[str, ...]] = {
    "Python": ("#",),
    "Shell": ("#",),
    "YAML": ("#",),
    "TOML": ("#",),
    "INI": ((";",) + ("#",)),
    "Ruby": ("#",),
    "JavaScript": ("//",),
    "TypeScript": ("//",),
    "Java": ("//",),
    "Kotlin": ("//",),
    "Swift": ("//",),
    "C": ("//",),
    "C++": ("//",),
    "C#": ("//",),
    "Go": ("//",),
    "Rust": ("//",),
    "Scala": ("//",),
    "SQL": ("--",),
}

TEST_PATH_MARKERS = ("test", "tests", "spec", "specs", "__tests__")
TEST_FILENAME_PATTERNS = ("test_", "_test.", ".test.", ".spec.", "spec_")
CONFIG_FILENAMES = {
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "makefile",
    ".env.example",
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "pom.xml",
    "build.gradle",
    "go.mod",
    "cargo.toml",
}


@dataclass
class LanguageStats:
    files: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0

    @property
    def total_lines(self) -> int:
        return self.code_lines + self.comment_lines + self.blank_lines


@dataclass
class RepositoryMetrics:
    total_files: int = 0
    source_files: int = 0
    test_files: int = 0
    config_files: int = 0
    documentation_files: int = 0
    other_files: int = 0

    repository_size_bytes: int = 0

    total_loc: int = 0
    code_loc: int = 0
    comment_loc: int = 0
    blank_loc: int = 0

    files_scanned_for_loc: int = 0
    files_skipped_too_large: int = 0
    files_skipped_binary: int = 0
    symlinks_skipped: int = 0

    truncated: bool = False
    """True when MAX_FILES_SCANNED was hit before the walk finished.
    When true, all counts are a lower bound on the true repository
    size, not the exact total."""

    language_distribution: dict[str, LanguageStats] = field(
        default_factory=dict
    )

    @property
    def comment_to_code_ratio(self) -> float | None:
        if self.code_loc <= 0:
            return None
        return round(self.comment_loc / self.code_loc, 4)

    @property
    def test_to_source_ratio(self) -> float | None:
        if self.source_files <= 0:
            return None
        return round(self.test_files / self.source_files, 4)

    def to_dict(self) -> dict:
        return {
            "total_files": self.total_files,
            "source_files": self.source_files,
            "test_files": self.test_files,
            "config_files": self.config_files,
            "documentation_files": self.documentation_files,
            "other_files": self.other_files,
            "repository_size_bytes": self.repository_size_bytes,
            "total_loc": self.total_loc,
            "code_loc": self.code_loc,
            "comment_loc": self.comment_loc,
            "blank_loc": self.blank_loc,
            "comment_to_code_ratio": self.comment_to_code_ratio,
            "test_to_source_ratio": self.test_to_source_ratio,
            "files_scanned_for_loc": self.files_scanned_for_loc,
            "files_skipped_too_large": self.files_skipped_too_large,
            "files_skipped_binary": self.files_skipped_binary,
            "symlinks_skipped": self.symlinks_skipped,
            "truncated": self.truncated,
            "language_distribution": {
                language: {
                    "files": stats.files,
                    "code_loc": stats.code_lines,
                    "comment_loc": stats.comment_lines,
                    "blank_loc": stats.blank_lines,
                    "total_loc": stats.total_lines,
                }
                for language, stats in sorted(
                    self.language_distribution.items(),
                    key=lambda item: item[1].code_lines,
                    reverse=True,
                )
            },
            "methodology": (
                "Deterministic local computation over the cloned "
                "working tree (vendored/build/dependency directories "
                "excluded). Comment-line counts are a single-line-"
                "comment heuristic per language and do not detect "
                "block comments, so comment_loc is a lower bound. "
                "Cyclomatic complexity, duplication, and maintainability "
                "are not computed by this module and are reported as "
                "unavailable elsewhere."
            ),
        }


def _is_test_path(relative_path: str, filename_lower: str) -> bool:
    parts = relative_path.replace("\\", "/").split("/")
    if any(part.lower() in TEST_PATH_MARKERS for part in parts[:-1]):
        return True
    return any(marker in filename_lower for marker in TEST_FILENAME_PATTERNS)


def _looks_binary(sample: bytes) -> bool:
    if b"\x00" in sample:
        return True
    return False


def compute_repository_metrics(workspace: Path) -> RepositoryMetrics:
    """
    Walk ``workspace`` and compute deterministic repository/LOC/language
    metrics.

    Safe against hostile repository content: never follows symlinks,
    bounds total files scanned and per-file/total bytes read, and skips
    binary files for LOC counting (still counted toward file totals).
    """

    workspace = Path(workspace)
    metrics = RepositoryMetrics()

    total_bytes_read = 0
    files_seen = 0

    stack: list[Path] = [workspace]

    while stack:
        current = stack.pop()

        try:
            entries = list(current.iterdir())
        except OSError:
            continue

        for entry in entries:
            if files_seen >= MAX_FILES_SCANNED:
                metrics.truncated = True
                break

            try:
                if entry.is_symlink():
                    metrics.symlinks_skipped += 1
                    continue

                if entry.is_dir():
                    if entry.name in EXCLUDED_DIR_NAMES:
                        continue
                    stack.append(entry)
                    continue

                if not entry.is_file():
                    continue
            except OSError:
                continue

            files_seen += 1
            metrics.total_files += 1

            try:
                relative = str(entry.relative_to(workspace))
            except ValueError:
                relative = entry.name

            filename_lower = entry.name.lower()
            suffix = entry.suffix.lower()

            try:
                size_bytes = entry.stat().st_size
            except OSError:
                size_bytes = 0

            metrics.repository_size_bytes += size_bytes

            language_info = LANGUAGE_EXTENSIONS.get(suffix)
            is_test = _is_test_path(relative, filename_lower)

            if is_test:
                metrics.test_files += 1
            elif filename_lower in CONFIG_FILENAMES:
                metrics.config_files += 1
            elif language_info and language_info[1] == "source":
                metrics.source_files += 1
            elif language_info and language_info[1] == "docs":
                metrics.documentation_files += 1
            elif language_info and language_info[1] == "config":
                metrics.config_files += 1
            elif language_info and language_info[1] == "markup":
                metrics.source_files += 1
            else:
                metrics.other_files += 1

            if language_info is None:
                continue

            language, category = language_info

            if category not in ("source", "markup"):
                continue

            if size_bytes > MAX_FILE_SIZE_BYTES:
                metrics.files_skipped_too_large += 1
                continue

            if total_bytes_read + size_bytes > MAX_TOTAL_BYTES_READ:
                metrics.truncated = True
                continue

            try:
                raw = entry.read_bytes()
            except OSError:
                continue

            total_bytes_read += len(raw)

            if _looks_binary(raw[:2048]):
                metrics.files_skipped_binary += 1
                continue

            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="replace")

            stats = metrics.language_distribution.setdefault(
                language, LanguageStats()
            )
            stats.files += 1
            metrics.files_scanned_for_loc += 1

            comment_prefixes = LINE_COMMENT_PREFIXES.get(language, ())

            for raw_line in text.splitlines():
                line = raw_line.strip()

                if not line:
                    stats.blank_lines += 1
                    metrics.blank_loc += 1
                elif comment_prefixes and line.startswith(
                    comment_prefixes
                ):
                    stats.comment_lines += 1
                    metrics.comment_loc += 1
                else:
                    stats.code_lines += 1
                    metrics.code_loc += 1

        if files_seen >= MAX_FILES_SCANNED:
            metrics.truncated = True
            break

    metrics.total_loc = (
        metrics.code_loc + metrics.comment_loc + metrics.blank_loc
    )

    return metrics
