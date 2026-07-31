"""Controlled integration boundary with the public Digit-Probe API."""

from __future__ import annotations

from collections.abc import Iterable

import digit_probe
from digit_probe import AnalysisConfig, AnalysisResult

from system_log_dynamics.encoding import (
    EVENT_ALPHABET_SIZE,
    iter_event_symbols,
    iter_validated_event_symbols,
)
from system_log_dynamics.models import ClassifiedJournalEvent


def _validated_analysis_result(
    result: object,
    *,
    sample_size: int,
) -> AnalysisResult:
    """Verify the dependency result without transforming it."""

    if not isinstance(result, AnalysisResult):
        raise RuntimeError("Digit-Probe must return an AnalysisResult")

    if result.mode != "integers":
        raise RuntimeError("Digit-Probe result mode must be 'integers'")

    if result.alphabet != EVENT_ALPHABET_SIZE:
        raise RuntimeError("Digit-Probe result alphabet must match EVENT_ALPHABET_SIZE")

    if result.sample_size != sample_size:
        raise RuntimeError(
            "Digit-Probe result sample size must match the validated sequence"
        )

    max_observed = result.max_observed

    if (
        not isinstance(max_observed, int)
        or isinstance(max_observed, bool)
        or max_observed < 0
        or max_observed >= EVENT_ALPHABET_SIZE
    ):
        raise RuntimeError(
            "Digit-Probe result max_observed must be "
            f"in range [0, {EVENT_ALPHABET_SIZE})"
        )

    return result


def analyze_event_symbols(
    symbols: Iterable[object],
    config: AnalysisConfig | None = None,
) -> AnalysisResult:
    """Validate and analyze one non-empty event-symbol sequence."""

    validated_symbols = list(iter_validated_event_symbols(symbols))

    if not validated_symbols:
        raise ValueError("event symbol sequence must not be empty")

    result = digit_probe.analyze_integer_symbols(
        validated_symbols,
        alphabet=EVENT_ALPHABET_SIZE,
        config=config,
    )

    return _validated_analysis_result(
        result,
        sample_size=len(validated_symbols),
    )


def analyze_classified_events(
    events: Iterable[ClassifiedJournalEvent],
    config: AnalysisConfig | None = None,
) -> AnalysisResult:
    """Encode, validate, and analyze classified events."""

    return analyze_event_symbols(
        iter_event_symbols(events),
        config=config,
    )
