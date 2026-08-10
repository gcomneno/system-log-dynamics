"""Contracts for the downstream IDS trust boundary."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DECISION = (
    ROOT
    / "docs"
    / "decisions"
    / "0019-downstream-ids-integration-and-trust-boundary.md"
)
SEMANTIC_DECISION = ROOT / "docs" / "decisions" / "0021-versioned-semantic-facets.md"
SEMANTIC_V2_DECISION = (
    ROOT
    / "docs"
    / "decisions"
    / "0022-structured-systemd-lifecycle-semantic-facets-v2.md"
)

CONTRACT = ROOT / "docs" / "downstream-ids-integration-contract.md"
SEMANTIC_REFERENCE = ROOT / "docs" / "semantic-evidence-v1.md"

README = ROOT / "README.md"
DECISION_INDEX = ROOT / "docs" / "decisions" / "README.md"
PYPROJECT = ROOT / "pyproject.toml"

DIGIT_PROBE_REQUIREMENT = (
    "digit-probe @ "
    "git+https://github.com/gcomneno/"
    "digit-probe.git@"
    "55e3eae4c55017703e023c1aaac0838b873482db"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_public_boundary_documents_exist_and_are_indexed() -> None:
    assert DECISION.is_file()
    assert SEMANTIC_DECISION.is_file()
    assert SEMANTIC_V2_DECISION.is_file()
    assert CONTRACT.is_file()
    assert SEMANTIC_REFERENCE.is_file()

    index = _read(DECISION_INDEX)

    assert "0019-downstream-ids-integration-and-trust-boundary.md" in index
    assert "Downstream IDS integration and trust boundary" in index
    assert "0021-versioned-semantic-facets.md" in index
    assert "Versioned semantic facets for downstream explanation" in index
    assert "0022-structured-systemd-lifecycle-semantic-facets-v2.md" in index
    assert "Structured systemd lifecycle semantic facets v2" in index


def test_readme_declares_evidence_engine_not_ids_boundary() -> None:
    readme = _read(README)

    assert "## Downstream IDS integration boundary" in readme
    assert "System Log Dynamics is an evidence engine, not an IDS." in readme
    assert "private journal bytes" in readme
    assert "System Log Dynamics evidence" in readme
    assert "downstream consumer" in readme
    assert "STOP at the System Log Dynamics boundary" in readme


def test_contract_accepts_only_explicit_versioned_evidence() -> None:
    contract = _read(CONTRACT)

    for required in (
        "system-log-dynamics.analysis-evidence",
        "system-log-dynamics.comparison-evidence",
        "system-log-dynamics.semantic-evidence",
        "`analysis_window`",
        "`window_comparison`",
        "`semantic_events`",
        "Version `1` is the only currently accepted schema version",
        "semantic-facet version `2`",
        "parse_evidence_bundle_json()",
        "parse_semantic_evidence_json()",
        "Consumers must reject:",
        "Silent fallback to a previous version is prohibited.",
    ):
        assert required in contract


def test_contract_requires_reproducibility_provenance() -> None:
    contract = _read(CONTRACT)

    for field in (
        "schema_name",
        "schema_version",
        "bundle_type",
        "project_version",
        "digit_probe_commit",
        "manifest_schema_version",
        "taxonomy_version",
        "semantic_facets_version",
        "window_id",
        "digest_algorithm",
        "sha256",
        "size_bytes",
        "analysis_configuration",
        "right_minus_left",
    ):
        assert field in contract


def test_semantic_v2_contract_is_structured_only() -> None:
    contract = _read(CONTRACT)
    decision = _read(SEMANTIC_V2_DECISION)

    for phrase in (
        "start_job_begun",
        "unit_succeeded",
        "SYSLOG_IDENTIFIER=systemd",
        "UNIT` or `USER_UNIT",
        "DBus activation/timeout",
        "CRON session open/close",
    ):
        assert phrase in contract

    for phrase in (
        "7d4958e842da4a758f6c1cdc7b36dcc5",
        "7ad2d189f7e94e70a38c781354912448",
        "does not use broad free-text message parsing",
    ):
        assert phrase in decision


def test_observation_to_incident_vocabulary_has_explicit_ownership() -> None:
    contract = _read(CONTRACT)

    for term in (
        "Observation",
        "Signal",
        "Alert",
        "Incident hypothesis",
        "Confirmed incident",
    ):
        assert term in contract

    assert "System Log Dynamics emits observations and evidence only." in contract
    assert (
        "It never emits signals, alerts, incident hypotheses, "
        "or confirmed incidents." in contract
    )


def test_trust_model_covers_privacy_hash_ai_trigger_and_response() -> None:
    contract = _read(CONTRACT)
    decision = _read(DECISION)

    required_contract_phrases = (
        "The default integration does not require or transfer raw journal messages.",
        "Derived evidence still requires privacy review before publication.",
        "An input hash establishes byte identity for the analyzed input.",
        "AI output is untrusted advisory material.",
        "The evidence bundle itself never authorizes the trigger.",
        "A downstream response requires an explicit authorization path",
    )

    for phrase in required_contract_phrases:
        assert phrase in contract

    for phrase in (
        "Determinism establishes reproducibility",
        "AI output is untrusted advisory material.",
        "An evidence bundle alone never defines, approves, or authorizes a trigger.",
        "Response authorization must be explicit and separate",
    ):
        assert phrase in decision


def test_runtime_dependencies_remain_outside_ids_ai_boundary() -> None:
    configuration = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    dependencies = configuration["project"]["dependencies"]

    assert dependencies == [
        DIGIT_PROBE_REQUIREMENT,
        "packaging>=24",
    ]

    metadata = configuration["project"]["description"].lower()

    assert "intrusion detection" not in metadata
    assert "threat detection" not in metadata
    assert "security response" not in metadata


def test_synthetic_examples_stop_before_security_interpretation() -> None:
    contract = _read(CONTRACT)

    assert "fixtures/synthetic/experiment-001-routine.jsonl" in contract
    assert "fixtures/synthetic/restart-loop-semantic.jsonl" in contract
    assert "fixtures/synthetic/systemd-lifecycle-semantic-v2.jsonl" in contract
    assert "boundary stops here" in contract
    assert "security interpretation begins only downstream" in contract
    assert (
        "No signal, alert, incident hypothesis, confirmed incident, trigger, AI"
        in contract
    )
    assert (
        "interpretation, notification, or response action is produced "
        "by System Log" in contract
    )
