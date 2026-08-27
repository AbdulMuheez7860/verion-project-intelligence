import json
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.analyzers.base import AnalyzerFinding
from app.analyzers.normalize import normalize_severity, truncate


# ----------------------------------------------------------------------
# Hostile-input hardening for requirements.txt
#
# requirements.txt is analyzed content from an UNTRUSTED repository, but
# it is also a pip *configuration* format: a line in the file can tell
# pip (and therefore pip-audit, which resolves versions via pip) to
# install from an attacker-controlled index, to follow a VCS URL, or to
# build a local/editable path. Any of those can result in Verion's
# analysis worker fetching from an attacker-controlled host or executing
# an attacker-supplied `setup.py`/build backend during resolution.
#
# Verion must never let an analyzed repository redirect its own
# dependency scanner. Before pip-audit ever sees a requirements file,
# strip anything that changes *where* pip resolves packages from or
# that would build local/VCS code, keeping only plain
# `package==version` style specifiers.
# ----------------------------------------------------------------------

_UNSAFE_REQUIREMENT_LINE_PREFIXES = (
    "-i",
    "--index-url",
    "--extra-index-url",
    "-f",
    "--find-links",
    "--trusted-host",
    "-e",
    "--editable",
    "-r",
    "--requirement",
    "-c",
    "--constraint",
    "--pre",
)

_UNSAFE_REQUIREMENT_LINE_PATTERN = re.compile(
    r"^\s*([\w.\-]+\s*(@|git\+|hg\+|svn\+|bzr\+)|https?://|file://)",
    re.IGNORECASE,
)

# Applied to manifests parsed without a subprocess (pom.xml,
# build.gradle) as a resource-limit guard against a hostile,
# pathologically large manifest - matches the per-file ceiling already
# used for source files in repository_metrics.py.
MAX_MANIFEST_SIZE_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class DependencyRecord:
    package_name: str
    current_version: str
    latest_version: str
    status: str
    vulnerability: str | None
    license: str


def sanitize_requirements_content(raw_text: str) -> tuple[str, list[str]]:
    """
    Strip pip options/VCS/URL/local-path directives from an untrusted
    requirements.txt before it is handed to pip-audit.

    Returns the sanitized text plus the list of raw lines that were
    removed, so callers can surface what was excluded from the scan
    instead of silently dropping dependency coverage.
    """

    safe_lines: list[str] = []
    removed_lines: list[str] = []

    for raw_line in raw_text.splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            safe_lines.append(raw_line)
            continue

        lowered = line.lower()

        is_unsafe_option = any(
            lowered == prefix or lowered.startswith(prefix + " ") or lowered.startswith(prefix + "=")
            for prefix in _UNSAFE_REQUIREMENT_LINE_PREFIXES
        )

        is_unsafe_target = bool(_UNSAFE_REQUIREMENT_LINE_PATTERN.match(line))

        if is_unsafe_option or is_unsafe_target:
            removed_lines.append(line)
            continue

        safe_lines.append(raw_line)

    return "\n".join(safe_lines) + "\n", removed_lines


class DependencyAnalyzer:
    """
    Dependency vulnerability analyzer.

    Supported manifests:
        - requirements.txt / pyproject.toml (Python)   -> pip-audit
        - package.json + package-lock.json (JS/TS/Node) -> npm audit

    Important:
        A scanner failure is never treated as a clean scan. A valid
        scan with zero vulnerabilities is considered healthy. This
        matters especially for `npm audit`, which reports both
        "vulnerabilities found" and genuine failures (network error,
        registry auth failure, malformed lockfile) as a non-zero exit
        code and JSON on stdout - the two are only distinguishable by
        inspecting the JSON payload shape, not the exit code alone.
    """

    name = "pip-audit"

    SUPPORTED_MANIFESTS = (
        "requirements.txt",
        "pyproject.toml",
        "package.json",
        "go.mod",
        "Cargo.toml",
        "composer.json",
        "Gemfile",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
    )

    # Manifests where Verion only performs a text-parsed dependency
    # INVENTORY (name + declared version constraint), not vulnerability
    # scanning - no offline advisory database and no network access is
    # available for these ecosystems in this environment, and Verion
    # does not fabricate vulnerability data it cannot actually check.
    # This is surfaced to the user explicitly rather than silently
    # presented as equivalent to the pip-audit/npm-audit ecosystems.
    INVENTORY_ONLY_MANIFESTS = (
        "go.mod",
        "Cargo.toml",
        "composer.json",
        "Gemfile",
    )

    TIMEOUT_SECONDS = 180

    def supports(self, workspace: Path) -> bool:
        """Return True when a supported dependency manifest exists."""

        if not workspace.exists() or not workspace.is_dir():
            return False

        return any(
            (workspace / manifest).is_file()
            for manifest in self.SUPPORTED_MANIFESTS
        )

    def run(self, workspace: Path) -> list[AnalyzerFinding]:
        findings, _records = self.scan(workspace)
        return findings

    def scan(
        self,
        workspace: Path,
    ) -> tuple[list[AnalyzerFinding], list[DependencyRecord]]:
        """
        Run dependency analysis.

        requirements.txt / pyproject.toml (Python):
            pip-audit - full vulnerability scanning.

        package.json + package-lock.json (JS/TS/Node):
            npm audit - full vulnerability scanning.

        go.mod (Go) / Cargo.toml (Rust) / composer.json (PHP) /
        Gemfile (Ruby):
            Text-parsed dependency INVENTORY only (declared package
            name + version constraint). No vulnerability scanning: no
            toolchain (go/cargo/composer/bundler) is installed in the
            analysis environment for these ecosystems, and there is no
            offline advisory database to check against without a live
            network call to each ecosystem's registry. Reported
            explicitly as partial support - never presented as
            equivalent to the pip-audit/npm-audit result.

        The analyzer never reports a clean vulnerability result when
        the scanner failed or was never run.
        """

        requirements = workspace / "requirements.txt"
        pyproject = workspace / "pyproject.toml"
        package_json = workspace / "package.json"
        go_mod = workspace / "go.mod"
        cargo_toml = workspace / "Cargo.toml"
        composer_json = workspace / "composer.json"
        gemfile = workspace / "Gemfile"
        pom_xml = workspace / "pom.xml"
        build_gradle = workspace / "build.gradle"
        build_gradle_kts = workspace / "build.gradle.kts"

        if requirements.is_file():
            return self._scan_requirements(requirements)

        if pyproject.is_file():
            return self._scan_pyproject(pyproject)

        if package_json.is_file():
            return self._scan_npm(workspace, package_json)

        if go_mod.is_file():
            return self._inventory_go_mod(go_mod)

        if cargo_toml.is_file():
            return self._inventory_cargo_toml(cargo_toml)

        if composer_json.is_file():
            return self._inventory_composer_json(composer_json)

        if gemfile.is_file():
            return self._inventory_gemfile(gemfile)

        if pom_xml.is_file():
            return self._inventory_pom_xml(pom_xml)

        if build_gradle.is_file():
            return self._inventory_gradle(build_gradle)

        if build_gradle_kts.is_file():
            return self._inventory_gradle(build_gradle_kts)

        return [], []

    # ------------------------------------------------------------------
    # requirements.txt
    # ------------------------------------------------------------------

    def _scan_requirements(
        self,
        requirements: Path,
    ) -> tuple[list[AnalyzerFinding], list[DependencyRecord]]:
        """Run pip-audit against requirements.txt.

        SECURITY: `requirements.txt` comes from an untrusted repository.
        It is sanitized into a temp file before pip-audit ever sees it,
        removing any directive (custom index, VCS URL, editable/local
        install, etc.) that could make dependency scanning fetch from or
        build attacker-controlled code. See
        ``sanitize_requirements_content``.
        """

        executable = shutil.which("pip-audit")

        if executable is None:
            raise RuntimeError(
                "pip-audit executable was not found in PATH. "
                "Install pip-audit in the Verion analysis environment."
            )

        raw_text = requirements.read_text(
            encoding="utf-8",
            errors="replace",
        )

        sanitized_text, removed_lines = sanitize_requirements_content(
            raw_text
        )

        tmp_fd, tmp_path_str = tempfile.mkstemp(
            prefix="verion-req-",
            suffix=".txt",
        )
        tmp_path = Path(tmp_path_str)

        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmp_file:
                tmp_file.write(sanitized_text)

            try:
                result = subprocess.run(
                    [
                        executable,
                        "-r",
                        str(tmp_path),
                        "--format",
                        "json",
                        "--progress-spinner",
                        "off",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=self.TIMEOUT_SECONDS,
                    # The sanitized file no longer contains index/VCS
                    # directives, but as defense in depth also deny pip
                    # any implicit network config from the environment.
                    env={
                        **os.environ,
                        "PIP_NO_INPUT": "1",
                        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                    },
                )
            except subprocess.TimeoutExpired as exc:
                raise TimeoutError(
                    "Dependency analysis exceeded the "
                    f"{self.TIMEOUT_SECONDS} second timeout."
                ) from exc

            except OSError as exc:
                raise RuntimeError(
                    f"Failed to start pip-audit: {exc}"
                ) from exc
        finally:
            tmp_path.unlink(missing_ok=True)

        findings, records = self._process_audit_result(
            result=result,
            manifest=requirements,
        )

        if removed_lines:
            findings.append(
                AnalyzerFinding(
                    severity="info",
                    category="dependencies",
                    rule_id="verion.requirements-sanitized",
                    title="Unsafe requirements.txt directives were excluded from scanning",
                    description=(
                        "requirements.txt contained "
                        f"{len(removed_lines)} directive(s) "
                        "(custom index/VCS/editable/local install) that "
                        "were removed before dependency scanning to "
                        "prevent the analyzed repository from "
                        "redirecting Verion's scanner to an untrusted "
                        "source. Packages installed via those "
                        "directives were not audited."
                    ),
                    file="requirements.txt",
                    line=1,
                    confidence=1.0,
                    metadata={
                        "engine": "verion",
                        "removed_count": str(len(removed_lines)),
                    },
                )
            )

        return findings, records

    # ------------------------------------------------------------------
    # pyproject.toml
    # ------------------------------------------------------------------

    def _scan_pyproject(
        self,
        pyproject: Path,
    ) -> tuple[list[AnalyzerFinding], list[DependencyRecord]]:
        """
        Run pip-audit against pyproject.toml.

        pip-audit supports project dependency scanning through --project.

        SECURITY / KNOWN LIMITATION: unlike the requirements.txt path,
        `pip-audit --project` resolves dependencies by invoking the
        project's own PEP 517 build backend (setuptools, hatchling,
        etc.), which can execute code declared by the analyzed
        repository itself (e.g. a malicious `setup.py` or
        build-backend hook). This is a materially higher-risk operation
        against untrusted input than static scanning, and cannot be
        fully neutralized by text sanitization the way requirements.txt
        can. Verion restricts pip's environment as defense in depth and
        keeps the existing timeout, but genuinely isolating this
        (container-per-analysis, no network egress, non-root/ephemeral
        filesystem) is an infrastructure-level control that belongs in
        the analyzer execution environment/Docker setup, not in this
        function. This is documented as a remaining limitation.
        """

        executable = shutil.which("pip-audit")

        if executable is None:
            raise RuntimeError(
                "pip-audit executable was not found in PATH. "
                "Install pip-audit in the Verion analysis environment."
            )

        try:
            result = subprocess.run(
                [
                    executable,
                    "--project",
                    str(pyproject),
                    "--format",
                    "json",
                    "--progress-spinner",
                    "off",
                ],
                cwd=pyproject.parent,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.TIMEOUT_SECONDS,
                env={
                    **os.environ,
                    "PIP_NO_INPUT": "1",
                    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                },
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                "Dependency analysis exceeded the "
                f"{self.TIMEOUT_SECONDS} second timeout."
            ) from exc

        except OSError as exc:
            raise RuntimeError(
                f"Failed to start pip-audit: {exc}"
            ) from exc

        return self._process_audit_result(
            result=result,
            manifest=pyproject,
        )

    # ------------------------------------------------------------------
    # npm audit (JS/TS/Node)
    # ------------------------------------------------------------------

    def _scan_npm(
        self,
        workspace: Path,
        package_json: Path,
    ) -> tuple[list[AnalyzerFinding], list[DependencyRecord]]:
        """
        Run `npm audit` against a JS/TS/Node project's locked
        dependency tree.

        REQUIRES A LOCKFILE. `npm audit` needs `package-lock.json`
        (or `npm-shrinkwrap.json`) to resolve exact versions; Verion
        does not run `npm install` against untrusted repository
        content to generate one (that would execute the repo's own
        install scripts/postinstall hooks - arbitrary code execution
        from a hostile repo). A `package.json` with no lockfile is
        therefore reported as unsupported for vulnerability scanning,
        not silently treated as "no dependencies".

        SECURITY: a repository's own `.npmrc` can set `registry=` to
        an attacker-controlled host, redirecting where audit data (and
        Verion's outbound requests) is sent. Verion ignores any
        repository-supplied `.npmrc` by pointing npm at an isolated,
        empty user config and explicitly pinning the real npm
        registry, the same "don't let the analyzed repo redirect the
        scanner" principle already applied to pip-audit above.
        """

        lockfile = None
        for candidate_name in ("package-lock.json", "npm-shrinkwrap.json"):
            candidate = workspace / candidate_name
            if candidate.is_file():
                lockfile = candidate
                break

        if lockfile is None:
            raise RuntimeError(
                "package.json was found but no package-lock.json / "
                "npm-shrinkwrap.json is present. npm audit requires a "
                "lockfile; Verion does not run `npm install` against "
                "untrusted repository content to generate one, so "
                "dependency vulnerability scanning is unsupported for "
                "this repository."
            )

        executable = shutil.which("npm")

        if executable is None:
            raise RuntimeError(
                "npm executable was not found in PATH. "
                "Install Node.js/npm in the Verion analysis environment."
            )

        empty_userconfig_fd, empty_userconfig_path = tempfile.mkstemp(
            prefix="verion-npmrc-",
            suffix=".ini",
        )
        os.close(empty_userconfig_fd)

        try:
            result = subprocess.run(
                [
                    executable,
                    "audit",
                    "--json",
                    "--registry",
                    "https://registry.npmjs.org",
                    "--userconfig",
                    empty_userconfig_path,
                ],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.TIMEOUT_SECONDS,
                env={
                    **os.environ,
                    "NPM_CONFIG_UPDATE_NOTIFIER": "false",
                    "NO_UPDATE_NOTIFIER": "1",
                },
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                "Dependency analysis exceeded the "
                f"{self.TIMEOUT_SECONDS} second timeout."
            ) from exc
        except OSError as exc:
            raise RuntimeError(f"Failed to start npm audit: {exc}") from exc
        finally:
            Path(empty_userconfig_path).unlink(missing_ok=True)

        return self._process_npm_audit_result(
            result=result,
            manifest=package_json,
        )

    def _process_npm_audit_result(
        self,
        *,
        result: subprocess.CompletedProcess[str],
        manifest: Path,
    ) -> tuple[list[AnalyzerFinding], list[DependencyRecord]]:
        """
        Validate and normalize npm audit output.

        CRITICAL: npm audit's exit code cannot distinguish "found
        vulnerabilities" from "the scan itself failed" (network error,
        registry auth failure, malformed request all also exit
        non-zero). The only reliable signal is the JSON payload shape:
        a real scan result contains a `vulnerabilities` object; a
        failed scan instead contains a top-level `error`/`message`/
        `statusCode`. This distinction was verified against a real
        `npm audit --json` invocation, not assumed.
        """

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if not stdout:
            error_details = stderr or "Unknown npm audit error."
            raise RuntimeError(
                "npm audit produced no JSON output "
                f"(exit code {result.returncode}): "
                f"{truncate(error_details, 500)}"
            )

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            error_details = stderr or "Invalid JSON returned by npm audit."
            raise RuntimeError(
                "npm audit returned invalid JSON output. "
                f"{truncate(error_details, 500)}"
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(
                "npm audit returned an unexpected JSON structure."
            )

        if "vulnerabilities" not in payload:
            # A genuine failure (network/registry/auth error), not a
            # clean scan. Surface whatever detail npm gave us.
            error_message = (
                payload.get("message")
                or payload.get("error", {}).get("summary")
                if isinstance(payload.get("error"), dict)
                else None
            ) or "npm audit did not return vulnerability data."

            status_code = payload.get("statusCode")
            suffix = f" (HTTP {status_code})" if status_code else ""

            raise RuntimeError(
                f"npm audit failed{suffix}: {truncate(str(error_message), 400)}"
            )

        findings = parse_npm_audit_results(payload, package_json=manifest)
        records = self._records_from_npm_audit(payload, manifest)

        return findings, records

    def _records_from_npm_audit(
        self,
        payload: dict[str, Any],
        manifest: Path,
    ) -> list[DependencyRecord]:
        records: list[DependencyRecord] = []
        vulnerabilities = payload.get("vulnerabilities")

        if not isinstance(vulnerabilities, dict):
            return records

        for package_name, info in vulnerabilities.items():
            if not isinstance(info, dict):
                continue

            severity = str(info.get("severity") or "").lower()
            status = "healthy"
            if severity in ("critical",):
                status = "critical"
            elif severity in ("high", "moderate", "low"):
                status = "vulnerable"

            range_value = info.get("range")
            version = (
                str(range_value)
                if isinstance(range_value, str)
                else "unknown"
            )

            records.append(
                DependencyRecord(
                    package_name=str(package_name),
                    current_version=version,
                    latest_version="unknown",
                    status=status,
                    vulnerability=(
                        severity.capitalize() if severity else None
                    ),
                    license="unknown",
                )
            )

        return records

    # ------------------------------------------------------------------
    # Text-parsed dependency inventory (Go / Rust / PHP / Ruby)
    #
    # These ecosystems get real, accurate dependency INVENTORY (name +
    # declared version constraint) from pure text parsing of the
    # manifest - no subprocess execution, so no hostile-input risk from
    # running a toolchain. They deliberately do NOT get vulnerability
    # findings, and each returns one explicit "inventory only" info
    # finding so the limitation is visible in the UI rather than silent.
    # ------------------------------------------------------------------

    @staticmethod
    def _inventory_only_notice(
        ecosystem: str,
        manifest_name: str,
        dependency_count: int,
    ) -> AnalyzerFinding:
        return AnalyzerFinding(
            severity="info",
            category="dependencies",
            rule_id=f"verion.inventory-only.{ecosystem}",
            title=f"{ecosystem} dependency vulnerability scanning is unavailable",
            description=(
                f"Detected {dependency_count} {ecosystem} "
                f"dependenc{'y' if dependency_count == 1 else 'ies'} in "
                f"{manifest_name}. Verion lists these as an inventory, "
                "but does not check them against a vulnerability "
                f"database for this ecosystem - no {ecosystem} "
                "toolchain or offline advisory database is configured "
                "in the analysis environment. This is different from "
                "Python and JS/TS dependencies, which get full "
                "vulnerability scanning (pip-audit / npm audit)."
            ),
            file=manifest_name,
            line=1,
            confidence=1.0,
            metadata={"engine": "verion-inventory", "ecosystem": ecosystem},
        )

    def _inventory_go_mod(
        self,
        go_mod: Path,
    ) -> tuple[list[AnalyzerFinding], list[DependencyRecord]]:
        """
        Parse `go.mod` `require` blocks for a dependency inventory.

        Handles both single-line (`require example.com/x v1.2.3`) and
        block (`require (\\n\\texample.com/x v1.2.3\\n)`) forms. Does
        not run `go` - go.mod is plain text, no toolchain needed.
        """

        text = go_mod.read_text(encoding="utf-8", errors="replace")
        records: list[DependencyRecord] = []

        in_block = False
        for raw_line in text.splitlines():
            line = raw_line.strip()

            if not line or line.startswith("//"):
                continue

            if line.startswith("require (") or line == "require (":
                in_block = True
                continue

            if in_block and line == ")":
                in_block = False
                continue

            if in_block:
                entry = line
            elif line.startswith("require "):
                entry = line[len("require "):].strip()
            else:
                continue

            entry = entry.split("//", 1)[0].strip()
            parts = entry.split()
            if len(parts) < 2:
                continue

            module_path, version = parts[0], parts[1]
            records.append(
                DependencyRecord(
                    package_name=module_path,
                    current_version=version,
                    latest_version="unknown",
                    status="unknown",
                    vulnerability=None,
                    license="unknown",
                )
            )

        findings = (
            [self._inventory_only_notice("Go", go_mod.name, len(records))]
            if records
            else []
        )
        return findings, records

    def _inventory_cargo_toml(
        self,
        cargo_toml: Path,
    ) -> tuple[list[AnalyzerFinding], list[DependencyRecord]]:
        """
        Parse `[dependencies]` (and dev/build variants) from Cargo.toml.

        Handles `name = "1.2.3"` and `name = { version = "1.2.3" }`.
        Does not run `cargo` - avoids hostile build-script execution.
        """

        text = cargo_toml.read_text(encoding="utf-8", errors="replace")
        records: list[DependencyRecord] = []

        section_re = re.compile(
            r"^\[(dependencies|dev-dependencies|build-dependencies)"
            r"(\.[\w.\-]+)?\]\s*$"
        )
        simple_re = re.compile(r'^([\w.\-]+)\s*=\s*"([^"]+)"')
        inline_table_re = re.compile(
            r'^([\w.\-]+)\s*=\s*\{[^}]*version\s*=\s*"([^"]+)"'
        )

        in_dependency_section = False
        for raw_line in text.splitlines():
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            if line.startswith("["):
                in_dependency_section = bool(section_re.match(line))
                continue

            if not in_dependency_section:
                continue

            match = simple_re.match(line) or inline_table_re.match(line)
            if not match:
                continue

            name, version = match.group(1), match.group(2)
            records.append(
                DependencyRecord(
                    package_name=name,
                    current_version=version,
                    latest_version="unknown",
                    status="unknown",
                    vulnerability=None,
                    license="unknown",
                )
            )

        findings = (
            [
                self._inventory_only_notice(
                    "Rust", cargo_toml.name, len(records)
                )
            ]
            if records
            else []
        )
        return findings, records

    def _inventory_composer_json(
        self,
        composer_json: Path,
    ) -> tuple[list[AnalyzerFinding], list[DependencyRecord]]:
        """
        Parse the `require`/`require-dev` objects of composer.json.

        Pure JSON parsing - no `composer` invocation, so no
        arbitrary-code risk from composer plugins/scripts.
        """

        try:
            payload = json.loads(
                composer_json.read_text(encoding="utf-8", errors="replace")
            )
        except json.JSONDecodeError:
            return [], []

        if not isinstance(payload, dict):
            return [], []

        records: list[DependencyRecord] = []
        for section in ("require", "require-dev"):
            deps = payload.get(section)
            if not isinstance(deps, dict):
                continue
            for name, version in deps.items():
                if not isinstance(name, str) or name.lower() == "php":
                    continue  # the PHP runtime constraint, not a package
                if name.startswith("ext-"):
                    continue  # a PHP extension requirement, not a package
                records.append(
                    DependencyRecord(
                        package_name=name,
                        current_version=str(version),
                        latest_version="unknown",
                        status="unknown",
                        vulnerability=None,
                        license="unknown",
                    )
                )

        findings = (
            [
                self._inventory_only_notice(
                    "PHP", composer_json.name, len(records)
                )
            ]
            if records
            else []
        )
        return findings, records

    def _inventory_gemfile(
        self,
        gemfile: Path,
    ) -> tuple[list[AnalyzerFinding], list[DependencyRecord]]:
        """
        Parse `gem "name", "version"` declarations from a Gemfile.

        Pure text/regex parsing - does not invoke `bundle`/`ruby`.
        """

        text = gemfile.read_text(encoding="utf-8", errors="replace")
        records: list[DependencyRecord] = []

        gem_re = re.compile(
            r'^\s*gem\s+["\']([\w.\-]+)["\']'
            r'(?:\s*,\s*["\']([^"\']+)["\'])?'
        )

        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0]
            match = gem_re.match(line)
            if not match:
                continue

            name = match.group(1)
            version = match.group(2) or "unspecified"

            records.append(
                DependencyRecord(
                    package_name=name,
                    current_version=version,
                    latest_version="unknown",
                    status="unknown",
                    vulnerability=None,
                    license="unknown",
                )
            )

        findings = (
            [
                self._inventory_only_notice(
                    "Ruby", gemfile.name, len(records)
                )
            ]
            if records
            else []
        )
        return findings, records

    def _inventory_pom_xml(
        self,
        pom_xml: Path,
    ) -> tuple[list[AnalyzerFinding], list[DependencyRecord]]:
        """
        Parse Maven `<dependencies>` from pom.xml using the stdlib XML
        parser (no `mvn` invocation, so no plugin/build-script
        execution risk).

        SECURITY CAVEAT (documented rather than assumed away): XML
        parsers are a known vector for entity-expansion ("billion
        laughs") denial-of-service and, on some stacks, external
        entity resolution. This method does not independently verify
        which protections the installed `xml.etree.ElementTree`
        provides on every Python build it might run on, so as cheap,
        verifiable defense in depth it refuses to parse a pom.xml
        above MAX_FILE_SIZE_BYTES (matching the same ceiling used for
        source files in `repository_metrics.py`) rather than relying
        solely on stdlib defaults against a hostile file.

        Only literal version strings are resolved; a version expressed
        as a Maven property (e.g. `${jackson.version}`) is reported as
        "managed by pom.xml properties" rather than guessed.
        """

        try:
            file_size = pom_xml.stat().st_size
        except OSError:
            return [], []

        if file_size > MAX_MANIFEST_SIZE_BYTES:
            raise RuntimeError(
                "pom.xml exceeds the "
                f"{MAX_MANIFEST_SIZE_BYTES} byte limit for "
                "dependency inventory parsing."
            )

        try:
            tree = ET.parse(str(pom_xml))
        except ET.ParseError:
            return [], []

        root = tree.getroot()

        # Maven's default namespace varies by pom.xml but is almost
        # always the standard POM 4.0.0 namespace when present.
        namespace_match = re.match(r"\{(.*)\}", root.tag)
        ns = {"m": namespace_match.group(1)} if namespace_match else {}
        prefix = "m:" if ns else ""

        records: list[DependencyRecord] = []

        dependencies_path = (
            f"{prefix}dependencies/{prefix}dependency"
        )

        for dependency in root.findall(dependencies_path, ns):
            group_id_el = dependency.find(f"{prefix}groupId", ns)
            artifact_id_el = dependency.find(f"{prefix}artifactId", ns)
            version_el = dependency.find(f"{prefix}version", ns)

            if group_id_el is None or artifact_id_el is None:
                continue

            group_id = (group_id_el.text or "").strip()
            artifact_id = (artifact_id_el.text or "").strip()

            if not group_id or not artifact_id:
                continue

            raw_version = (version_el.text or "").strip() if version_el is not None else ""

            if raw_version.startswith("${"):
                version = "managed by pom.xml properties"
            elif raw_version:
                version = raw_version
            else:
                version = "managed by parent/BOM"

            records.append(
                DependencyRecord(
                    package_name=f"{group_id}:{artifact_id}",
                    current_version=version,
                    latest_version="unknown",
                    status="unknown",
                    vulnerability=None,
                    license="unknown",
                )
            )

        findings = (
            [self._inventory_only_notice("Java (Maven)", pom_xml.name, len(records))]
            if records
            else []
        )
        return findings, records

    def _inventory_gradle(
        self,
        build_file: Path,
    ) -> tuple[list[AnalyzerFinding], list[DependencyRecord]]:
        """
        Parse Gradle dependency declarations from build.gradle /
        build.gradle.kts using regex over the common declaration
        forms. Does not invoke `gradle` (which can execute arbitrary
        build-script code, including from `plugins {}` blocks and init
        scripts) - text parsing only.

        Handles the two dominant forms:
            implementation 'group:artifact:version'
            implementation("group:artifact:version")
        across the common configurations (implementation, api,
        compileOnly, runtimeOnly, testImplementation, etc.). Does not
        resolve version catalogs (`libs.someLib`) or variables - those
        are reported as "unresolved" rather than guessed.
        """

        text = build_file.read_text(encoding="utf-8", errors="replace")

        if len(text.encode("utf-8", errors="ignore")) > MAX_MANIFEST_SIZE_BYTES:
            raise RuntimeError(
                f"{build_file.name} exceeds the "
                f"{MAX_MANIFEST_SIZE_BYTES} byte limit for "
                "dependency inventory parsing."
            )

        records: list[DependencyRecord] = []
        seen: set[str] = set()

        configurations = (
            "implementation",
            "api",
            "compileOnly",
            "runtimeOnly",
            "testImplementation",
            "testRuntimeOnly",
            "annotationProcessor",
        )
        config_pattern = "|".join(configurations)

        coordinate_re = re.compile(
            rf'^\s*(?:{config_pattern})\s*[\(\s]\s*'
            r'''["']([^:'"]+):([^:'"]+):([^:'")\s]+)["']'''
        )

        for raw_line in text.splitlines():
            line = raw_line.split("//", 1)[0]
            match = coordinate_re.match(line)
            if not match:
                continue

            group_id, artifact_id, version = match.groups()
            package_name = f"{group_id}:{artifact_id}"

            if package_name in seen:
                continue
            seen.add(package_name)

            records.append(
                DependencyRecord(
                    package_name=package_name,
                    current_version=version,
                    latest_version="unknown",
                    status="unknown",
                    vulnerability=None,
                    license="unknown",
                )
            )

        findings = (
            [self._inventory_only_notice("Java (Gradle)", build_file.name, len(records))]
            if records
            else []
        )
        return findings, records

    # ------------------------------------------------------------------
    # Common pip-audit processing
    # ------------------------------------------------------------------

    def _process_audit_result(
        self,
        *,
        result: subprocess.CompletedProcess[str],
        manifest: Path,
    ) -> tuple[list[AnalyzerFinding], list[DependencyRecord]]:
        """
        Validate and normalize pip-audit output.

        pip-audit may return non-zero when vulnerabilities are found.
        Therefore the exit code alone must NOT determine whether the
        analysis failed.
        """

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if not stdout:
            error_details = stderr or "Unknown pip-audit error."

            raise RuntimeError(
                "pip-audit produced no JSON output "
                f"(exit code {result.returncode}): "
                f"{truncate(error_details, 500)}"
            )

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            error_details = stderr or "Invalid JSON returned by pip-audit."

            raise RuntimeError(
                "pip-audit returned invalid JSON output. "
                f"{truncate(error_details, 500)}"
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(
                "pip-audit returned an unexpected JSON structure. "
                "Expected an object containing 'dependencies'."
            )

        dependencies = payload.get("dependencies")

        if dependencies is None:
            raise RuntimeError(
                "pip-audit JSON response does not contain "
                "the expected 'dependencies' field."
            )

        if not isinstance(dependencies, list):
            raise RuntimeError(
                "pip-audit 'dependencies' field must be a list."
            )

        findings = parse_pip_audit_results(
            payload,
            requirements_file=manifest,
        )

        records = self._records_from_audit(
            payload,
            manifest,
        )

        return findings, records

    # ------------------------------------------------------------------
    # Dependency inventory
    # ------------------------------------------------------------------

    def _parse_requirements(
        self,
        requirements: Path,
    ) -> list[DependencyRecord]:
        """
        Parse common requirements.txt entries.

        This is an inventory parser, not a complete implementation of
        Python packaging syntax.
        """

        records: list[DependencyRecord] = []

        try:
            content = requirements.read_text(
                encoding="utf-8"
            )
        except OSError as exc:
            raise RuntimeError(
                f"Unable to read {requirements}: {exc}"
            ) from exc

        for raw_line in content.splitlines():
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            # Ignore pip options and include directives.
            if line.startswith("-"):
                continue

            package_name, version = self._parse_requirement_line(line)

            if not package_name:
                continue

            records.append(
                DependencyRecord(
                    package_name=package_name,
                    current_version=version,
                    latest_version="unknown",
                    status="unknown",
                    vulnerability=None,
                    license="unknown",
                )
            )

        return records

    # ------------------------------------------------------------------
    # pyproject inventory
    # ------------------------------------------------------------------

    def _parse_pyproject_dependencies(
        self,
        pyproject: Path,
    ) -> list[DependencyRecord]:
        """Parse PEP 621 project dependencies for inventory purposes."""

        try:
            import tomllib
        except ImportError as exc:
            raise RuntimeError(
                "Python 3.11+ is required for pyproject.toml parsing."
            ) from exc

        try:
            with pyproject.open("rb") as file:
                payload = tomllib.load(file)
        except (OSError, ValueError) as exc:
            raise RuntimeError(
                f"Unable to parse {pyproject}: {exc}"
            ) from exc

        records: list[DependencyRecord] = []

        project = payload.get("project", {})

        if not isinstance(project, dict):
            return records

        dependencies = project.get("dependencies", [])

        if not isinstance(dependencies, list):
            return records

        for dependency in dependencies:
            if not isinstance(dependency, str):
                continue

            package_name, version = self._parse_requirement_line(
                dependency
            )

            if not package_name:
                continue

            records.append(
                DependencyRecord(
                    package_name=package_name,
                    current_version=version,
                    latest_version="unknown",
                    status="unknown",
                    vulnerability=None,
                    license="unknown",
                )
            )

        return records

    # ------------------------------------------------------------------
    # Convert pip-audit output into DependencyRecord
    # ------------------------------------------------------------------

    def _records_from_audit(
        self,
        payload: dict[str, Any],
        manifest: Path,
    ) -> list[DependencyRecord]:
        """
        Build dependency records from the actual pip-audit results.

        Vulnerability severity is propagated into status so the pipeline
        can distinguish:
            healthy
            vulnerable
            critical
        """

        if manifest.name == "requirements.txt":
            base_records = self._parse_requirements(manifest)
        else:
            base_records = self._parse_pyproject_dependencies(manifest)

        base = {
            record.package_name.lower(): record
            for record in base_records
        }

        dependencies = payload.get("dependencies", [])

        if not isinstance(dependencies, list):
            return list(base.values())

        for dep in dependencies:
            if not isinstance(dep, dict):
                continue

            name = str(
                dep.get("name") or ""
            ).strip()

            if not name:
                continue

            current_version = str(
                dep.get("version") or "unknown"
            ).strip()

            vulnerabilities = dep.get("vulns", [])

            if not isinstance(vulnerabilities, list):
                vulnerabilities = []

            vulnerability_ids: list[str] = []
            highest_severity = "low"

            for vulnerability in vulnerabilities:
                if not isinstance(vulnerability, dict):
                    continue

                vuln_id = str(
                    vulnerability.get("id") or ""
                ).strip()

                if vuln_id:
                    vulnerability_ids.append(vuln_id)

                severity = determine_vulnerability_severity(
                    vulnerability
                )

                highest_severity = _highest_severity(
                    highest_severity,
                    severity,
                )

            if not vulnerability_ids:
                status = "healthy"
                vulnerability = None
            elif highest_severity == "critical":
                status = "critical"
                vulnerability = ", ".join(vulnerability_ids)
            else:
                status = "vulnerable"
                vulnerability = ", ".join(vulnerability_ids)

            base[name.lower()] = DependencyRecord(
                package_name=name,
                current_version=current_version,
                latest_version="unknown",
                status=status,
                vulnerability=vulnerability,
                license="unknown",
            )

        return list(base.values())

    # ------------------------------------------------------------------
    # Requirement parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_requirement_line(
        line: str,
    ) -> tuple[str, str]:
        """
        Extract package name and version.

        Examples:

            requests==2.31.0
            requests>=2.31.0
            requests~=2.31
            requests
            requests[security]==2.31.0
        """

        requirement = line.split(";", 1)[0].strip()

        if requirement.startswith("git+"):
            return "", "unknown"

        package_part = requirement

        for separator in (
            "==",
            ">=",
            "<=",
            "~=",
            "!=",
            ">",
            "<",
        ):
            if separator in package_part:
                package_part = package_part.split(
                    separator,
                    1,
                )[0]

        package_part = package_part.strip()

        # Remove extras.
        if "[" in package_part:
            package_part = package_part.split(
                "[",
                1,
            )[0]

        package_name = package_part.strip()

        if not package_name:
            return "", "unknown"

        version = "unknown"

        if "==" in requirement:
            version = requirement.split(
                "==",
                1,
            )[1].strip()

        elif ">=" in requirement:
            version = requirement.split(
                ">=",
                1,
            )[1].strip()

        elif "~=" in requirement:
            version = requirement.split(
                "~=",
                1,
            )[1].strip()

        elif ">" in requirement:
            version = requirement.split(
                ">",
                1,
            )[1].strip()

        elif "<" in requirement:
            version = requirement.split(
                "<",
                1,
            )[1].strip()

        return package_name, version


# ======================================================================
# pip-audit result normalization
# ======================================================================


def parse_pip_audit_results(
    payload: dict[str, Any],
    requirements_file: Path | None = None,
) -> list[AnalyzerFinding]:
    """
    Convert pip-audit results into Verion findings.

    One vulnerability = one Verion finding.
    """

    findings: list[AnalyzerFinding] = []

    dependencies = payload.get(
        "dependencies",
        [],
    )

    if not isinstance(dependencies, list):
        raise ValueError(
            "pip-audit dependencies must be a list."
        )

    finding_file = (
        requirements_file.name
        if requirements_file is not None
        else "requirements.txt"
    )

    for dep in dependencies:
        if not isinstance(dep, dict):
            continue

        package = str(
            dep.get("name") or "unknown"
        ).strip()

        current_version = str(
            dep.get("version") or "unknown"
        ).strip()

        vulnerabilities = dep.get(
            "vulns",
            [],
        )

        if not isinstance(vulnerabilities, list):
            continue

        for vulnerability in vulnerabilities:
            if not isinstance(vulnerability, dict):
                continue

            vuln_id = str(
                vulnerability.get("id")
                or "PYSEC-UNKNOWN"
            ).strip()

            description = truncate(
                str(
                    vulnerability.get("description")
                    or f"Vulnerability in {package}"
                ).strip()
            )

            severity = determine_vulnerability_severity(
                vulnerability
            )

            aliases = extract_aliases(
                vulnerability
            )

            fix_versions = extract_fix_versions(
                vulnerability
            )

            remediation = build_remediation(
                package=package,
                fix_versions=fix_versions,
            )

            metadata: dict[str, str] = {
                "engine": "pip-audit",
                "package": package,
                "current_version": current_version,
                "vulnerability": vuln_id,
            }

            if aliases:
                metadata["aliases"] = ", ".join(
                    aliases
                )

            if fix_versions:
                metadata["fix_versions"] = ", ".join(
                    fix_versions
                )

            findings.append(
                AnalyzerFinding(
                    severity=severity,
                    category="dependency",
                    rule_id=vuln_id,
                    title=f"{package}: {vuln_id}",
                    description=description,
                    file=finding_file,
                    line=1,
                    confidence=1.0,
                    remediation=remediation,
                    metadata=metadata,
                )
            )

    return findings


def parse_npm_audit_results(
    payload: dict[str, Any],
    package_json: Path | None = None,
) -> list[AnalyzerFinding]:
    """
    Convert `npm audit --json` results into Verion findings.

    One vulnerable package = one Verion finding (matching npm's own
    per-package grouping, rather than npm's "via" advisory chain,
    which can reference either an advisory ID or a nested package
    name and is not a stable, always-numeric identifier to key on).

    Caller must have already verified `payload` contains a
    `vulnerabilities` object (i.e. this is a real scan result, not a
    failure) - see `_process_npm_audit_result`.
    """

    findings: list[AnalyzerFinding] = []

    vulnerabilities = payload.get("vulnerabilities", {})

    if not isinstance(vulnerabilities, dict):
        raise ValueError("npm audit 'vulnerabilities' must be an object.")

    finding_file = (
        package_json.name if package_json is not None else "package.json"
    )

    for package_name, info in vulnerabilities.items():
        if not isinstance(info, dict):
            continue

        package = str(package_name).strip()

        severity = normalize_severity(str(info.get("severity") or "high"))

        range_value = info.get("range")
        affected_range = (
            str(range_value) if isinstance(range_value, str) else "unknown"
        )

        via = info.get("via", [])
        advisory_titles: list[str] = []
        if isinstance(via, list):
            for entry in via:
                if isinstance(entry, dict) and entry.get("title"):
                    advisory_titles.append(str(entry["title"]))
                elif isinstance(entry, str):
                    # npm sometimes lists a nested package name here
                    # instead of an advisory object - not itself a
                    # human-readable title, so it's excluded rather
                    # than surfaced as if it were one.
                    continue

        description = truncate(
            "; ".join(advisory_titles)
            or f"{package} has a known {severity}-severity vulnerability "
            f"in range {affected_range}."
        )

        fix_available = info.get("fixAvailable")
        remediation = None
        if fix_available is True:
            remediation = f"Run `npm audit fix` or upgrade {package}."
        elif isinstance(fix_available, dict) and fix_available.get("name"):
            remediation = (
                f"Upgrade {package} to {fix_available.get('name')}"
                f"@{fix_available.get('version', 'latest')}."
            )

        metadata: dict[str, str] = {
            "engine": "npm-audit",
            "package": package,
            "affected_range": affected_range,
        }

        if info.get("isDirect") is not None:
            metadata["direct_dependency"] = str(bool(info.get("isDirect")))

        findings.append(
            AnalyzerFinding(
                severity=severity,
                category="dependency",
                rule_id=f"npm-audit:{package}",
                title=f"{package}: {severity}-severity vulnerability",
                description=description,
                file=finding_file,
                line=1,
                confidence=1.0,
                remediation=remediation,
                metadata=metadata,
            )
        )

    return findings


def determine_vulnerability_severity(
    vulnerability: dict[str, Any],
) -> str:
    """
    Normalize advisory severity.

    If the advisory does not provide severity, HIGH is used because
    the vulnerability itself is confirmed even though its severity
    metadata is unavailable.
    """

    raw_severity = vulnerability.get("severity")

    if raw_severity:
        return normalize_severity(
            str(raw_severity)
        )

    return normalize_severity("high")


def extract_aliases(
    vulnerability: dict[str, Any],
) -> list[str]:
    """Extract CVE/GHSA/PYSEC aliases."""

    aliases = vulnerability.get(
        "aliases",
        [],
    )

    if not isinstance(aliases, list):
        return []

    return [
        str(alias).strip()
        for alias in aliases
        if str(alias).strip()
    ][:20]


def extract_fix_versions(
    vulnerability: dict[str, Any],
) -> list[str]:
    """Extract patched versions."""

    fix_versions = vulnerability.get(
        "fix_versions",
        [],
    )

    if not isinstance(fix_versions, list):
        return []

    return [
        str(version).strip()
        for version in fix_versions
        if str(version).strip()
    ][:20]


def build_remediation(
    *,
    package: str,
    fix_versions: list[str],
) -> str:
    """Generate actionable remediation."""

    if fix_versions:
        versions = ", ".join(fix_versions)

        return (
            f"Upgrade {package} to a patched version "
            f"({versions}) or later, then regenerate and verify "
            "the dependency lock/requirements data."
        )

    return (
        f"Upgrade {package} to a vendor-supported patched version "
        "that resolves this vulnerability. If no patched version "
        "exists, replace or remove the affected dependency."
    )


def _highest_severity(
    current: str,
    candidate: str,
) -> str:
    """Return the higher of two normalized severities."""

    order = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }

    if order.get(candidate, 1) > order.get(current, 1):
        return candidate

    return current