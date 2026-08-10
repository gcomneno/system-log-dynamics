"""Synthetic evidence for the issue #26 Linux vocabulary review."""

from __future__ import annotations

import json
from pathlib import Path

from system_log_dynamics.analysis import analyze_classified_events
from system_log_dynamics.classification import iter_classified_events
from system_log_dynamics.coverage import (
    CoverageStatus,
    build_taxonomy_coverage,
)
from system_log_dynamics.journal import (
    iter_normalized_journal_json_lines,
)

FIXTURE_DIRECTORY = Path("fixtures/synthetic")
INPUT_PATH = FIXTURE_DIRECTORY / "taxonomy-coverage-review.jsonl"
EXPECTED_PATH = FIXTURE_DIRECTORY / "taxonomy-coverage-review-expected.jsonl"


def _expected() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in EXPECTED_PATH.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _classified():
    with INPUT_PATH.open(encoding="utf-8") as source:
        normalized = iter_normalized_journal_json_lines(source)
        return list(iter_classified_events(normalized))


def test_review_fixture_matches_exact_classification_contract() -> None:
    classified = _classified()

    actual = [
        {
            "sequence_index": (item.normalized_event.sequence_index),
            "event_type": item.event_type.value,
            "source_domain": item.source_domain.value,
            "rule_id": item.rule_id,
            "evidence": item.evidence.value,
        }
        for item in classified
    ]

    assert actual == _expected()


def test_review_fixture_exercises_previously_missing_rules() -> None:
    expected = _expected()
    rules = {item["rule_id"] for item in expected}

    assert "service.message_id.stopped" in rules
    assert "session.message.opened" in rules
    assert "session.message.closed" in rules


def test_restart_is_preserved_as_stop_then_start() -> None:
    expected = _expected()

    assert expected[7]["event_type"] == "service_stopped"
    assert expected[8]["event_type"] == "service_started"
    assert expected[7]["rule_id"] == ("service.message_id.stopped")
    assert expected[8]["rule_id"] == ("service.message_id.started")


def test_service_failure_uses_existing_severity_semantics() -> None:
    expected = _expected()

    assert expected[9] == {
        "sequence_index": 9,
        "event_type": "error",
        "source_domain": "service",
        "rule_id": "severity.priority.error",
        "evidence": "exact",
    }


def test_access_denials_require_authentication_context() -> None:
    expected = _expected()

    assert [item["event_type"] for item in expected[10:13]] == [
        "authentication_failure",
        "authentication_failure",
        "authentication_failure",
    ]

    assert expected[13]["event_type"] == "other"
    assert expected[13]["source_domain"] == "other"
    assert expected[13]["rule_id"] == "fallback.other"


def test_session_wording_requires_supported_context() -> None:
    expected = _expected()

    assert expected[5]["event_type"] == "session_boundary"
    assert expected[6]["event_type"] == "session_boundary"
    assert expected[14]["event_type"] == "other"
    assert expected[14]["rule_id"] == "fallback.other"


def test_review_fixture_has_explicit_taxonomy_coverage() -> None:
    result = analyze_classified_events(_classified())
    coverage = build_taxonomy_coverage(result)

    assert coverage.sample_size == 15
    assert coverage.named_event_count == 12
    assert coverage.other_event_count == 3
    assert coverage.represented_named_symbols == (
        1,
        2,
        3,
        4,
        5,
        7,
    )
    assert coverage.absent_named_symbols == (0, 6)
    assert coverage.status is CoverageStatus.MIXED
