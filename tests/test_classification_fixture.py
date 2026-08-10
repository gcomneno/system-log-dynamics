import json
from pathlib import Path

from system_log_dynamics.classification import (
    iter_classified_events,
)
from system_log_dynamics.journal import (
    iter_normalized_journal_json_lines,
)

FIXTURE_DIRECTORY = Path("fixtures/synthetic")
INPUT_PATH = FIXTURE_DIRECTORY / "classification.jsonl"
EXPECTED_PATH = FIXTURE_DIRECTORY / "classification-expected.jsonl"


def read_expected() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in EXPECTED_PATH.read_text(encoding="utf-8").splitlines()
        if line
    ]


def test_classification_fixture_matches_exact_contract() -> None:
    with INPUT_PATH.open(encoding="utf-8") as source:
        normalized = iter_normalized_journal_json_lines(source)
        classified = list(iter_classified_events(normalized))

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

    assert actual == read_expected()


def test_classification_fixture_covers_complete_taxonomy() -> None:
    expected = read_expected()

    assert {item["event_type"] for item in expected} == {
        "boot_boundary",
        "service_started",
        "service_stopped",
        "authentication_success",
        "authentication_failure",
        "session_boundary",
        "warning",
        "error",
        "other",
    }

    assert {item["source_domain"] for item in expected} == {
        "service",
        "authentication",
        "session",
        "kernel",
        "network",
        "other",
    }

    assert {item["evidence"] for item in expected} == {
        "exact",
        "heuristic",
        "fallback",
    }


def test_missing_boot_identifier_preserves_boot_context() -> None:
    expected = read_expected()

    assert expected[0]["event_type"] == "other"
    assert expected[9]["event_type"] == "other"
    assert expected[10]["event_type"] == "service_started"
    assert expected[12]["event_type"] == "boot_boundary"


def test_fixture_covers_session_open_and_close() -> None:
    expected = read_expected()

    assert expected[2] == {
        "sequence_index": 2,
        "event_type": "session_boundary",
        "source_domain": "session",
        "rule_id": "session.message_id.boundary",
        "evidence": "exact",
    }

    assert expected[3] == {
        "sequence_index": 3,
        "event_type": "session_boundary",
        "source_domain": "session",
        "rule_id": "session.message_id.boundary",
        "evidence": "exact",
    }
