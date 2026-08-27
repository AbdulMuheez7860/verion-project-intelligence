from pathlib import Path

from app.analyzers.repository_metrics import (
    MAX_FILE_SIZE_BYTES,
    compute_repository_metrics,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_basic_language_and_loc_counts(tmp_path: Path):
    _write(
        tmp_path / "src" / "main.py",
        "# comment\nimport os\n\ndef foo():\n    return 1\n",
    )
    _write(
        tmp_path / "src" / "app.js",
        "// header\nfunction hi() {\n  return 1;\n}\n",
    )
    _write(tmp_path / "tests" / "test_main.py", "def test_foo():\n    assert True\n")
    _write(tmp_path / "requirements.txt", "flask==2.0.0\n")
    _write(tmp_path / "README.md", "# Title\n")

    metrics = compute_repository_metrics(tmp_path)

    assert metrics.total_files == 5
    assert metrics.source_files == 2
    assert metrics.test_files == 1
    assert metrics.config_files == 1
    assert metrics.documentation_files == 1
    assert "Python" in metrics.language_distribution
    assert "JavaScript" in metrics.language_distribution
    assert metrics.code_loc > 0
    assert metrics.comment_loc >= 2


def test_excluded_directories_are_never_scanned(tmp_path: Path):
    _write(tmp_path / "node_modules" / "pkg" / "index.js", "var x = 1;\n" * 100)
    _write(tmp_path / ".git" / "config", "junk")
    _write(tmp_path / "src" / "main.py", "x = 1\n")

    metrics = compute_repository_metrics(tmp_path)

    assert metrics.total_files == 1
    assert "JavaScript" not in metrics.language_distribution


def test_symlinks_are_never_followed(tmp_path: Path):
    import tempfile

    outside_dir = Path(tempfile.mkdtemp())
    target = outside_dir / "outside.txt"
    target.write_text("should never be read")

    link = tmp_path / "src" / "link.py"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target)

    metrics = compute_repository_metrics(tmp_path)

    assert metrics.symlinks_skipped == 1
    assert metrics.total_files == 0
    assert metrics.total_loc == 0


def test_oversized_files_are_skipped_for_loc_but_counted(tmp_path: Path):
    big = tmp_path / "big.py"
    big.write_text("x = 1\n" * ((MAX_FILE_SIZE_BYTES // 6) + 1000))

    metrics = compute_repository_metrics(tmp_path)

    assert metrics.total_files == 1
    assert metrics.files_skipped_too_large == 1
    assert metrics.total_loc == 0


def test_binary_files_are_not_counted_as_loc(tmp_path: Path):
    binary = tmp_path / "asset.py"
    binary.write_bytes(b"\x00\x01\x02binarydata")

    metrics = compute_repository_metrics(tmp_path)

    assert metrics.total_files == 1
    assert metrics.files_skipped_binary == 1
    assert metrics.total_loc == 0


def test_scan_is_truncated_after_max_files(tmp_path: Path, monkeypatch):
    import app.analyzers.repository_metrics as rm

    monkeypatch.setattr(rm, "MAX_FILES_SCANNED", 5)

    for i in range(20):
        _write(tmp_path / f"f{i}.py", "a = 1\n")

    metrics = rm.compute_repository_metrics(tmp_path)

    assert metrics.truncated is True
    assert metrics.total_files <= 5


def test_empty_repository_has_zeroed_ratios(tmp_path: Path):
    metrics = compute_repository_metrics(tmp_path)

    assert metrics.total_files == 0
    assert metrics.comment_to_code_ratio is None
    assert metrics.test_to_source_ratio is None


def test_to_dict_is_json_serializable(tmp_path: Path):
    import json

    _write(tmp_path / "main.py", "x = 1\n")
    metrics = compute_repository_metrics(tmp_path)

    # Must not raise - this is what gets persisted/returned via the API.
    json.dumps(metrics.to_dict())
