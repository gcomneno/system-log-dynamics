from __future__ import annotations

from pathlib import Path

from digit_probe import AnalysisResult

from system_log_dynamics.analysis import (
    analyze_classified_events,
)
from system_log_dynamics.classification import (
    iter_classified_events,
)
from system_log_dynamics.encoding import (
    EVENT_ALPHABET_SIZE,
)
from system_log_dynamics.journal import (
    iter_normalized_journal_json_lines,
)

EVENTS_PATH = Path("fixtures/synthetic/classification.jsonl")

EXPECTED_COUNTS = {
    0: 2,
    1: 2,
    2: 1,
    3: 1,
    4: 1,
    5: 2,
    6: 2,
    7: 1,
    8: 2,
}


def test_complete_pipeline_returns_structured_analysis() -> None:
    with EVENTS_PATH.open(encoding="utf-8") as source:
        normalized = iter_normalized_journal_json_lines(source)
        classified = iter_classified_events(normalized)
        result = analyze_classified_events(classified)

    assert isinstance(result, AnalysisResult)
    assert result.mode == "integers"
    assert result.sample_size == 14
    assert result.alphabet == EVENT_ALPHABET_SIZE
    assert result.counts == EXPECTED_COUNTS
    assert result.max_observed == 8


def test_complete_pipeline_preserves_full_alphabet() -> None:
    with EVENTS_PATH.open(encoding="utf-8") as source:
        result = analyze_classified_events(
            iter_classified_events(iter_normalized_journal_json_lines(source))
        )

    assert set(result.counts) == set(range(EVENT_ALPHABET_SIZE))
    assert sum(result.counts.values()) == result.sample_size
