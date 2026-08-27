import json
from pathlib import Path

from app.analyzers.dependencies import DependencyAnalyzer


def test_go_mod_inventory(tmp_path: Path):
    (tmp_path / "go.mod").write_text(
        "module example.com/app\n\n"
        "go 1.21\n\n"
        "require (\n"
        "\tgithub.com/gin-gonic/gin v1.9.1\n"
        "\tgithub.com/stretchr/testify v1.8.4 // indirect\n"
        ")\n\n"
        "require golang.org/x/text v0.14.0\n"
    )

    analyzer = DependencyAnalyzer()
    findings, records = analyzer.scan(tmp_path)

    names = sorted(r.package_name for r in records)
    assert names == [
        "github.com/gin-gonic/gin",
        "github.com/stretchr/testify",
        "golang.org/x/text",
    ]
    assert all(r.status == "unknown" for r in records)
    # Exactly one "vulnerability scanning unavailable" notice, not one per dep.
    assert len(findings) == 1
    assert "unavailable" in findings[0].title.lower()


def test_cargo_toml_inventory(tmp_path: Path):
    (tmp_path / "Cargo.toml").write_text(
        '[package]\nname = "app"\nversion = "0.1.0"\n\n'
        '[dependencies]\nserde = "1.0.195"\n'
        'tokio = { version = "1.35.1", features = ["full"] }\n\n'
        '[dev-dependencies]\nproptest = "1.4.0"\n'
    )

    analyzer = DependencyAnalyzer()
    findings, records = analyzer.scan(tmp_path)

    names = sorted(r.package_name for r in records)
    assert names == ["proptest", "serde", "tokio"]
    assert len(findings) == 1


def test_composer_json_inventory_excludes_platform_requirements(tmp_path: Path):
    (tmp_path / "composer.json").write_text(
        json.dumps(
            {
                "require": {
                    "php": ">=8.1",
                    "ext-json": "*",
                    "guzzlehttp/guzzle": "^7.8",
                },
                "require-dev": {"phpunit/phpunit": "^10.0"},
            }
        )
    )

    analyzer = DependencyAnalyzer()
    findings, records = analyzer.scan(tmp_path)

    names = sorted(r.package_name for r in records)
    # "php" (runtime constraint) and "ext-json" (extension) are not
    # real installable packages and must be excluded.
    assert names == ["guzzlehttp/guzzle", "phpunit/phpunit"]
    assert len(findings) == 1


def test_composer_json_malformed_does_not_crash(tmp_path: Path):
    (tmp_path / "composer.json").write_text("not valid json{{{")

    analyzer = DependencyAnalyzer()
    findings, records = analyzer.scan(tmp_path)

    assert findings == []
    assert records == []


def test_gemfile_inventory(tmp_path: Path):
    (tmp_path / "Gemfile").write_text(
        'source "https://rubygems.org"\n\n'
        'gem "rails", "7.1.2"\n'
        'gem "pg"\n'
        'gem "puma", "~> 6.4" # web server\n'
    )

    analyzer = DependencyAnalyzer()
    findings, records = analyzer.scan(tmp_path)

    names = sorted(r.package_name for r in records)
    assert names == ["pg", "puma", "rails"]

    pg_record = next(r for r in records if r.package_name == "pg")
    assert pg_record.current_version == "unspecified"

    assert len(findings) == 1


def test_empty_manifest_produces_no_notice_finding(tmp_path: Path):
    """A manifest with zero declared dependencies should not emit a
    spurious 'vulnerability scanning unavailable' notice - there's
    nothing to caveat."""
    (tmp_path / "go.mod").write_text("module example.com/empty\n\ngo 1.21\n")

    analyzer = DependencyAnalyzer()
    findings, records = analyzer.scan(tmp_path)

    assert findings == []
    assert records == []


def test_supports_detects_each_new_manifest(tmp_path: Path):
    analyzer = DependencyAnalyzer()
    assert analyzer.supports(tmp_path) is False

    for manifest_name, content in [
        ("go.mod", "module x\n"),
        ("Cargo.toml", "[package]\n"),
        ("composer.json", "{}"),
        ("Gemfile", 'gem "x"\n'),
        ("pom.xml", "<project/>"),
        ("build.gradle", ""),
        ("build.gradle.kts", ""),
    ]:
        d = tmp_path / manifest_name
        d.write_text(content)
        assert analyzer.supports(tmp_path) is True
        d.unlink()


def test_pom_xml_inventory(tmp_path: Path):
    (tmp_path / "pom.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<project xmlns="http://maven.apache.org/POM/4.0.0">\n'
        "  <modelVersion>4.0.0</modelVersion>\n"
        "  <groupId>com.example</groupId>\n"
        "  <artifactId>app</artifactId>\n"
        "  <version>1.0.0</version>\n"
        "  <properties><jackson.version>2.15.2</jackson.version></properties>\n"
        "  <dependencies>\n"
        "    <dependency>\n"
        "      <groupId>org.springframework.boot</groupId>\n"
        "      <artifactId>spring-boot-starter-web</artifactId>\n"
        "      <version>3.1.4</version>\n"
        "    </dependency>\n"
        "    <dependency>\n"
        "      <groupId>com.fasterxml.jackson.core</groupId>\n"
        "      <artifactId>jackson-databind</artifactId>\n"
        "      <version>${jackson.version}</version>\n"
        "    </dependency>\n"
        "    <dependency>\n"
        "      <groupId>org.junit.jupiter</groupId>\n"
        "      <artifactId>junit-jupiter</artifactId>\n"
        "      <scope>test</scope>\n"
        "    </dependency>\n"
        "  </dependencies>\n"
        "</project>\n"
    )

    analyzer = DependencyAnalyzer()
    findings, records = analyzer.scan(tmp_path)

    names = sorted(r.package_name for r in records)
    assert names == [
        "com.fasterxml.jackson.core:jackson-databind",
        "org.junit.jupiter:junit-jupiter",
        "org.springframework.boot:spring-boot-starter-web",
    ]

    versions = {r.package_name: r.current_version for r in records}
    assert versions["org.springframework.boot:spring-boot-starter-web"] == "3.1.4"
    assert versions["com.fasterxml.jackson.core:jackson-databind"] == "managed by pom.xml properties"
    assert versions["org.junit.jupiter:junit-jupiter"] == "managed by parent/BOM"
    assert len(findings) == 1


def test_pom_xml_malformed_does_not_crash(tmp_path: Path):
    (tmp_path / "pom.xml").write_text("<project><unclosed>")

    analyzer = DependencyAnalyzer()
    findings, records = analyzer.scan(tmp_path)

    assert findings == []
    assert records == []


def test_pom_xml_oversized_raises(tmp_path: Path):
    from app.analyzers.dependencies import MAX_MANIFEST_SIZE_BYTES

    (tmp_path / "pom.xml").write_text("<!-- padding -->" * (MAX_MANIFEST_SIZE_BYTES // 16 + 1000))

    analyzer = DependencyAnalyzer()
    try:
        analyzer.scan(tmp_path)
        raise AssertionError("expected RuntimeError for an oversized pom.xml")
    except RuntimeError as exc:
        assert "byte limit" in str(exc)


def test_build_gradle_inventory(tmp_path: Path):
    (tmp_path / "build.gradle").write_text(
        "plugins {\n    id 'java'\n}\n\n"
        "dependencies {\n"
        "    implementation 'org.springframework.boot:spring-boot-starter-web:3.1.4'\n"
        '    api("com.google.guava:guava:32.1.3-jre")\n'
        "    testImplementation 'org.junit.jupiter:junit-jupiter:5.10.0'\n"
        "    implementation libs.someLib // unresolved version catalog ref\n"
        "}\n"
    )

    analyzer = DependencyAnalyzer()
    findings, records = analyzer.scan(tmp_path)

    names = sorted(r.package_name for r in records)
    assert names == [
        "com.google.guava:guava",
        "org.junit.jupiter:junit-jupiter",
        "org.springframework.boot:spring-boot-starter-web",
    ]
    assert len(findings) == 1


def test_build_gradle_kts_detected(tmp_path: Path):
    (tmp_path / "build.gradle.kts").write_text(
        'dependencies {\n    implementation("org.jetbrains.kotlin:kotlin-stdlib:1.9.20")\n}\n'
    )

    analyzer = DependencyAnalyzer()
    findings, records = analyzer.scan(tmp_path)

    assert len(records) == 1
    assert records[0].package_name == "org.jetbrains.kotlin:kotlin-stdlib"


def test_empty_gradle_deps_produces_no_notice(tmp_path: Path):
    (tmp_path / "build.gradle").write_text('plugins { id "java" }')

    analyzer = DependencyAnalyzer()
    findings, records = analyzer.scan(tmp_path)

    assert findings == []
    assert records == []
