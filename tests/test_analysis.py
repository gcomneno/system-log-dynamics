from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace

import pytest
from digit_probe import (
    AnalysisConfig,
    AnalysisResult,
)
from digit_probe import (
    analyze_integer_symbols as digit_probe_analyze_integer_symbols,
)

import system_log_dynamics.analysis as analysis_module
from system_log_dynamics.analysis import (
    analyze_classified_events,
    analyze_event_symbols,
)
from system_log_dynamics.encoding import EVENT_ALPHABET_SIZE
from system_log_dynamics.models import (
    ClassifiedJournalEvent,
    EventType,
    EvidenceLevel,
    NormalizedJournalEvent,
    SourceDomain,
)


def make_digit_probe_result(
    symbols: list[int],
    *,
    config: AnalysisConfig | None = None,
) -> AnalysisResult:
    return digit_probe_analyze_integer_symbols(
        symbols,
        alphabet=EVENT_ALPHABET_SIZE,
        config=config,
    )


def make_classified_event(
    event_type: EventType,
    *,
    sequence_index: int = 0,
) -> ClassifiedJournalEvent:
    normalized = NormalizedJournalEvent(
        sequence_index=sequence_index,
        source_line=sequence_index + 1,
        boot_index=0,
        relative_realtime_us=sequence_index * 100,
        monotonic_us=sequence_index * 100,
        priority=6,
        message="Synthetic event",
        message_id=None,
        transport="journal",
        systemd_unit=None,
        syslog_identifier="synthetic",
    )

    return ClassifiedJournalEvent(
        normalized_event=normalized,
        event_type=event_type,
        source_domain=SourceDomain.OTHER,
        rule_id="synthetic.rule",
        evidence=EvidenceLevel.EXACT,
    )


def test_analyze_event_symbols_passes_validated_list_and_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = AnalysisConfig(schur_capacity=64)
    expected = make_digit_probe_result(
        [0, 8],
        config=config,
    )
    calls: list[tuple[list[int], int, AnalysisConfig | None]] = []

    def fake_analyze_integer_symbols(
        symbols: list[int],
        alphabet: int,
        config: AnalysisConfig | None = None,
    ) -> AnalysisResult:
        calls.append((symbols, alphabet, config))
        return expected

    monkeypatch.setattr(
        analysis_module.digit_probe,
        "analyze_integer_symbols",
        fake_analyze_integer_symbols,
    )

    result = analyze_event_symbols(
        (symbol for symbol in (0, 8)),
        config=config,
    )

    assert result is expected
    assert calls == [([0, 8], EVENT_ALPHABET_SIZE, config)]
    assert type(calls[0][0]) is list
    assert calls[0][2] is config


def test_analyze_event_symbols_passes_none_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = make_digit_probe_result([1, 2])
    calls: list[tuple[list[int], int, AnalysisConfig | None]] = []

    def fake_analyze_integer_symbols(
        symbols: list[int],
        alphabet: int,
        config: AnalysisConfig | None = None,
    ) -> AnalysisResult:
        calls.append((symbols, alphabet, config))
        return expected

    monkeypatch.setattr(
        analysis_module.digit_probe,
        "analyze_integer_symbols",
        fake_analyze_integer_symbols,
    )

    result = analyze_event_symbols([1, 2])

    assert result is expected
    assert calls == [([1, 2], EVENT_ALPHABET_SIZE, None)]


def test_analyze_event_symbols_materializes_input_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = make_digit_probe_result([0, 5, 8])

    class SingleUseIterable:
        def __init__(self) -> None:
            self.iterations = 0
            self.yielded: list[int] = []

        def __iter__(self) -> Iterator[int]:
            self.iterations += 1

            if self.iterations > 1:
                raise AssertionError("input iterable consumed more than once")

            for symbol in (0, 5, 8):
                self.yielded.append(symbol)
                yield symbol

    source = SingleUseIterable()
    received: list[list[int]] = []

    def fake_analyze_integer_symbols(
        symbols: list[int],
        alphabet: int,
        config: AnalysisConfig | None = None,
    ) -> AnalysisResult:
        del config
        assert alphabet == EVENT_ALPHABET_SIZE
        received.append(symbols)
        return expected

    monkeypatch.setattr(
        analysis_module.digit_probe,
        "analyze_integer_symbols",
        fake_analyze_integer_symbols,
    )

    result = analyze_event_symbols(source)

    assert result is expected
    assert source.iterations == 1
    assert source.yielded == [0, 5, 8]
    assert received == [[0, 5, 8]]


@pytest.mark.parametrize(
    "invalid",
    [
        pytest.param(True, id="true"),
        pytest.param(False, id="false"),
        pytest.param(-1, id="negative"),
        pytest.param(9, id="too-large"),
        pytest.param("1", id="string"),
        pytest.param(1.0, id="float"),
        pytest.param(None, id="none"),
        pytest.param(object(), id="object"),
    ],
)
def test_analyze_event_symbols_rejects_invalid_input_before_call(
    monkeypatch: pytest.MonkeyPatch,
    invalid: object,
) -> None:
    called = False

    def fail_if_called(
        symbols: list[int],
        alphabet: int,
        config: AnalysisConfig | None = None,
    ) -> AnalysisResult:
        del symbols, alphabet, config
        nonlocal called
        called = True
        raise AssertionError("Digit-Probe must not be invoked")

    monkeypatch.setattr(
        analysis_module.digit_probe,
        "analyze_integer_symbols",
        fail_if_called,
    )

    with pytest.raises(ValueError):
        analyze_event_symbols([invalid])

    assert called is False


def test_analyze_event_symbols_stops_at_first_invalid_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    consumed: list[object] = []
    called = False

    def symbols() -> Iterator[object]:
        for symbol in (0, 17, 8):
            consumed.append(symbol)
            yield symbol

    def fail_if_called(
        values: list[int],
        alphabet: int,
        config: AnalysisConfig | None = None,
    ) -> AnalysisResult:
        del values, alphabet, config
        nonlocal called
        called = True
        raise AssertionError("Digit-Probe must not be invoked")

    monkeypatch.setattr(
        analysis_module.digit_probe,
        "analyze_integer_symbols",
        fail_if_called,
    )

    with pytest.raises(
        ValueError,
        match=r"event symbol must be in range \[0, 9\)",
    ):
        analyze_event_symbols(symbols())

    assert consumed == [0, 17]
    assert called is False


def test_analyze_event_symbols_rejects_empty_input_before_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def fail_if_called(
        symbols: list[int],
        alphabet: int,
        config: AnalysisConfig | None = None,
    ) -> AnalysisResult:
        del symbols, alphabet, config
        nonlocal called
        called = True
        raise AssertionError("Digit-Probe must not be invoked")

    monkeypatch.setattr(
        analysis_module.digit_probe,
        "analyze_integer_symbols",
        fail_if_called,
    )

    with pytest.raises(
        ValueError,
        match="event symbol sequence must not be empty",
    ):
        analyze_event_symbols(iter(()))

    assert called is False


def test_analyze_event_symbols_returns_real_structured_result() -> None:
    result = analyze_event_symbols([0, 1, 5, 5, 4, 3, 6, 7, 8])

    assert isinstance(result, AnalysisResult)
    assert result.mode == "integers"
    assert result.sample_size == 9
    assert result.alphabet == EVENT_ALPHABET_SIZE
    assert result.max_observed == 8


def test_analyze_classified_events_is_thin_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = AnalysisConfig(schur_capacity=32)
    expected = make_digit_probe_result(
        [7, 1],
        config=config,
    )
    calls: list[tuple[list[int], int, AnalysisConfig | None]] = []

    def fake_analyze_integer_symbols(
        symbols: list[int],
        alphabet: int,
        config: AnalysisConfig | None = None,
    ) -> AnalysisResult:
        calls.append((symbols, alphabet, config))
        return expected

    monkeypatch.setattr(
        analysis_module.digit_probe,
        "analyze_integer_symbols",
        fake_analyze_integer_symbols,
    )

    events = (
        make_classified_event(
            EventType.ERROR,
            sequence_index=0,
        ),
        make_classified_event(
            EventType.SERVICE_STARTED,
            sequence_index=1,
        ),
    )

    result = analyze_classified_events(
        events,
        config=config,
    )

    assert result is expected
    assert calls == [([7, 1], EVENT_ALPHABET_SIZE, config)]
    assert calls[0][2] is config


def test_analyze_classified_events_rejects_before_digit_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    consumed: list[str] = []
    called = False

    def events() -> Iterator[object]:
        consumed.append("valid")
        yield make_classified_event(EventType.WARNING)

        consumed.append("invalid")
        yield object()

        consumed.append("later")
        yield make_classified_event(EventType.OTHER)

    def fail_if_called(
        symbols: list[int],
        alphabet: int,
        config: AnalysisConfig | None = None,
    ) -> AnalysisResult:
        del symbols, alphabet, config
        nonlocal called
        called = True
        raise AssertionError("Digit-Probe must not be invoked")

    monkeypatch.setattr(
        analysis_module.digit_probe,
        "analyze_integer_symbols",
        fail_if_called,
    )

    with pytest.raises(
        ValueError,
        match="event must be a ClassifiedJournalEvent",
    ):
        analyze_classified_events(  # type: ignore[arg-type]
            events()
        )

    assert consumed == ["valid", "invalid"]
    assert called is False


def test_analysis_rejects_non_analysis_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        analysis_module.digit_probe,
        "analyze_integer_symbols",
        lambda *args, **kwargs: object(),
    )

    with pytest.raises(
        RuntimeError,
        match="Digit-Probe must return an AnalysisResult",
    ):
        analyze_event_symbols([0])


def test_analysis_rejects_wrong_result_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid = make_digit_probe_result([0])
    invalid = replace(valid, mode="digits")

    monkeypatch.setattr(
        analysis_module.digit_probe,
        "analyze_integer_symbols",
        lambda *args, **kwargs: invalid,
    )

    with pytest.raises(
        RuntimeError,
        match="result mode must be 'integers'",
    ):
        analyze_event_symbols([0])


def test_analysis_rejects_wrong_result_alphabet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid = make_digit_probe_result([0])
    invalid = replace(valid, alphabet=8)

    monkeypatch.setattr(
        analysis_module.digit_probe,
        "analyze_integer_symbols",
        lambda *args, **kwargs: invalid,
    )

    with pytest.raises(
        RuntimeError,
        match="result alphabet must match",
    ):
        analyze_event_symbols([0])


def test_analysis_rejects_wrong_result_sample_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid = make_digit_probe_result([0])
    invalid = replace(valid, sample_size=2)

    monkeypatch.setattr(
        analysis_module.digit_probe,
        "analyze_integer_symbols",
        lambda *args, **kwargs: invalid,
    )

    with pytest.raises(
        RuntimeError,
        match="result sample size must match",
    ):
        analyze_event_symbols([0])


@pytest.mark.parametrize(
    "max_observed",
    [
        pytest.param(None, id="none"),
        pytest.param(True, id="boolean"),
        pytest.param(-1, id="negative"),
        pytest.param(9, id="too-large"),
    ],
)
def test_analysis_rejects_invalid_result_max_observed(
    monkeypatch: pytest.MonkeyPatch,
    max_observed: int | None,
) -> None:
    valid = make_digit_probe_result([0])
    invalid = replace(
        valid,
        max_observed=max_observed,
    )

    monkeypatch.setattr(
        analysis_module.digit_probe,
        "analyze_integer_symbols",
        lambda *args, **kwargs: invalid,
    )

    with pytest.raises(
        RuntimeError,
        match=r"max_observed must be in range \[0, 9\)",
    ):
        analyze_event_symbols([0])
