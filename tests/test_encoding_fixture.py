from __future__ import annotations

import json
from pathlib import Path

from system_log_dynamics.classification import (
    iter_classified_events,
)
from system_log_dynamics.encoding import (
    EVENT_ALPHABET_SIZE,
    EVENT_TYPE_TO_SYMBOL,
    iter_event_symbols,
    iter_validated_event_symbols,
)
from system_log_dynamics.journal import (
    iter_normalized_journal_json_lines,
)

EVENTS_PATH = Path("fixtures/synthetic/classification.jsonl")
EXPECTED_PATH = Path("fixtures/synthetic/encoding-expected.jsonl")

EXPECTED_MAPPING = {
    "boot_boundary": 0,
    "service_started": 1,
    "service_stopped": 2,
    "authentication_success": 3,
    "authentication_failure": 4,
    "session_boundary": 5,
    "warning": 6,
    "error": 7,
    "other": 8,
}

EXPECTED_SYMBOLS = [
    0,
    1,
    5,
    5,
    4,
    3,
    6,
    7,
    8,
    8,
    1,
    2,
    0,
    6,
]


def read_expected() -> dict[str, object]:
    lines = EXPECTED_PATH.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 1

    value = json.loads(lines[0])

    assert isinstance(value, dict)

    return value


def test_encoding_fixture_records_exact_contract() -> None:
    expected = read_expected()

    assert expected == {
        "alphabet_size": 9,
        "event_type_to_symbol": EXPECTED_MAPPING,
        "symbols": EXPECTED_SYMBOLS,
    }


def test_encoding_fixture_matches_public_mapping() -> None:
    expected = read_expected()

    actual_mapping = {
        event_type.value: symbol for event_type, symbol in EVENT_TYPE_TO_SYMBOL.items()
    }

    assert expected["alphabet_size"] == EVENT_ALPHABET_SIZE
    assert actual_mapping == EXPECTED_MAPPING
    assert set(actual_mapping.values()) == set(range(EVENT_ALPHABET_SIZE))


def test_complete_pipeline_matches_exact_symbol_sequence() -> None:
    with EVENTS_PATH.open(encoding="utf-8") as source:
        normalized = iter_normalized_journal_json_lines(source)
        classified = iter_classified_events(normalized)
        symbols = list(iter_event_symbols(classified))

    assert symbols == EXPECTED_SYMBOLS
    assert len(symbols) == 14
    assert all(type(symbol) is int for symbol in symbols)
    assert all(0 <= symbol < EVENT_ALPHABET_SIZE for symbol in symbols)


def test_fixture_symbols_pass_shared_validation_boundary() -> None:
    expected = read_expected()
    symbols = expected["symbols"]

    assert isinstance(symbols, list)
    assert list(iter_validated_event_symbols(symbols)) == EXPECTED_SYMBOLS
