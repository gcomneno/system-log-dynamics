"""Release-facing contracts for the first public milestone."""

from __future__ import annotations

import tomllib
from importlib import metadata
from pathlib import Path

import system_log_dynamics

RELEASE_VERSION = "0.1.0"
RELEASE_DATE = "2026-08-06"
DIGIT_PROBE_COMMIT = "55e3eae4c55017703e023c1aaac0838b873482db"
DIGIT_PROBE_RELEASE_COMMIT = "86867d600fb8c8836bed43b7543270d6ffd93aa8"
ROOT = Path(__file__).resolve().parents[1]


def project_configuration() -> dict[str, object]:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_authoritative_version_surfaces_match_first_public_release() -> None:
    configuration = project_configuration()
    project = configuration["project"]
    distribution = metadata.distribution("system-log-dynamics")

    assert project["version"] == RELEASE_VERSION
    assert system_log_dynamics.__version__ == RELEASE_VERSION
    assert distribution.version == RELEASE_VERSION


def test_manifest_version_contract_is_the_release_version() -> None:
    source = (ROOT / "src/system_log_dynamics/manifests.py").read_text(encoding="utf-8")

    assert "from system_log_dynamics import __version__" in source
    assert "project_version != __version__" in source
    assert "return project_version, commit" in source


def test_release_notes_and_changelog_record_the_version_decision() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    release_notes = (ROOT / "docs/releases/0.1.0.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    changelog_header = (
        "# Changelog\n\n"
        "All notable changes to this project will be documented "
        "in this file.\n\n"
        "## Unreleased\n"
    )
    release_heading = f"\n## [{RELEASE_VERSION}] - {RELEASE_DATE}\n"

    assert changelog.startswith(changelog_header)
    assert changelog.count(release_heading) == 1

    unreleased_section, released_section = changelog.split(
        release_heading,
        maxsplit=1,
    )

    assert unreleased_section.startswith(changelog_header)
    assert released_section.startswith("\n### Added\n")
    assert RELEASE_VERSION in release_notes
    assert RELEASE_DATE in release_notes
    assert "no existing Git\ntag" in release_notes
    assert "not 1.0.0" in release_notes
    assert "Version 0.1.0 is the first public milestone." in readme


def test_digit_probe_is_an_immutable_full_commit_pin() -> None:
    configuration = project_configuration()
    dependencies = configuration["project"]["dependencies"]
    expected_requirement = (
        "digit-probe @ git+https://github.com/gcomneno/"
        f"digit-probe.git@{DIGIT_PROBE_COMMIT}"
    )
    release_notes = (ROOT / "docs/releases/0.1.0.md").read_text(encoding="utf-8")

    assert expected_requirement in dependencies
    assert DIGIT_PROBE_COMMIT in release_notes
    assert DIGIT_PROBE_RELEASE_COMMIT in release_notes
    assert "`v0.1.0` release" in release_notes
    assert "no `[project]` package metadata" in release_notes
    assert "fourteen commits ahead" in release_notes
    assert "floating version range" in release_notes
    assert "installed dependency metadata" in release_notes


def test_release_material_is_configured_for_source_and_wheel_artifacts() -> None:
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    data_files = project_configuration()["tool"]["setuptools"]["data-files"]

    assert "include CHANGELOG.md" in manifest
    assert "recursive-include docs *.md" in manifest
    assert "recursive-include fixtures/synthetic *.jsonl" in manifest
    assert "recursive-include fixtures/reports *.md" in manifest
    assert data_files["share/system-log-dynamics"] == ["CHANGELOG.md"]
    assert data_files["share/system-log-dynamics/docs"] == ["docs/release-process.md"]
    assert data_files["share/system-log-dynamics/docs/decisions"] == [
        "docs/decisions/*.md"
    ]
    assert data_files["share/system-log-dynamics/docs/experiments"] == [
        "docs/experiments/*.md"
    ]
    assert data_files["share/system-log-dynamics/docs/releases"] == [
        "docs/releases/*.md"
    ]
    assert data_files["share/system-log-dynamics/fixtures/synthetic"] == [
        "fixtures/synthetic/*.jsonl"
    ]
    assert data_files["share/system-log-dynamics/fixtures/reports"] == [
        "fixtures/reports/*.md"
    ]


def test_release_process_covers_approval_and_corrective_release_policy() -> None:
    process = (ROOT / "docs/release-process.md").read_text(encoding="utf-8")

    for required_phrase in (
        "final release commit or pull request",
        "complete validation",
        "squash-merge",
        "annotated tag",
        "GitHub Release notes",
        "Artifact publication",
        "After publication",
        "corrective release",
    ):
        assert required_phrase in process
