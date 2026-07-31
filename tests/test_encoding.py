from __future__ import annotations

from collections.abc import Iterator

import pytest

import system_log_dynamics.encoding as encoding_module
from system_log_dynamics.encoding import (
    EVENT_ALPHABET_SIZE,
    EVENT_TYPE_TO_SYMBOL,
    SYMBOL_TO_EVENT_TYPE,
    decode_event_symbol,
    encode_classified_event,
    encode_event_type,
    iter_event_symbols,
    iter_validated_event_symbols,
    validate_event_symbol,
)
from system_log_dynamics.models import (
    ClassifiedJournalEvent,
    EventType,
    EvidenceLevel,
    NormalizedJournalEvent,
    SourceDomain,
)

EXPECTED_EVENT_TYPE_TO_SYMBOL = {
    EventType.BOOT_BOUNDARY: 0,
    EventType.SERVICE_STARTED: 1,
    EventType.SERVICE_STOPPED: 2,
    EventType.AUTHENTICATION_SUCCESS: 3,
    EventType.AUTHENTICATION_FAILURE: 4,
    EventType.SESSION_BOUNDARY: 5,
    EventType.WARNING: 6,
    EventType.ERROR: 7,
    EventType.OTHER: 8,
}


def make_normalized_event(
    *,
    sequence_index: int = 0,
    priority: int | None = 6,
    message: str | None = "Synthetic event",
) -> NormalizedJournalEvent:
    return NormalizedJournalEvent(
        sequence_index=sequence_index,
        source_line=sequence_index + 1,
        boot_index=0,
        relative_realtime_us=sequence_index * 100,
        monotonic_us=sequence_index * 100,
        priority=priority,
        message=message,
        message_id=None,
        transport="journal",
        systemd_unit=None,
        syslog_identifier="synthetic",
    )


def make_classified_event(
    event_type: EventType,
    *,
    sequence_index: int = 0,
    source_domain: SourceDomain = SourceDomain.OTHER,
    rule_id: str = "synthetic.rule",
    evidence: EvidenceLevel = EvidenceLevel.EXACT,
) -> ClassifiedJournalEvent:
    return ClassifiedJournalEvent(
        normalized_event=make_normalized_event(sequence_index=sequence_index),
        event_type=event_type,
        source_domain=source_domain,
        rule_id=rule_id,
        evidence=evidence,
    )


def test_alphabet_size_is_exactly_nine() -> None:
    assert EVENT_ALPHABET_SIZE == 9


def test_forward_mapping_is_exact_and_complete() -> None:
    assert EVENT_TYPE_TO_SYMBOL == EXPECTED_EVENT_TYPE_TO_SYMBOL
    assert set(EVENT_TYPE_TO_SYMBOL) == set(EventType)


def test_mapping_does_not_depend_on_enum_iteration_order() -> None:
    event_types = tuple(reversed(tuple(EventType)))

    assert [EVENT_TYPE_TO_SYMBOL[item] for item in event_types] == [
        EXPECTED_EVENT_TYPE_TO_SYMBOL[item] for item in event_types
    ]


def test_symbol_set_is_exactly_zero_through_eight() -> None:
    symbols = tuple(EVENT_TYPE_TO_SYMBOL.values())

    assert len(symbols) == EVENT_ALPHABET_SIZE
    assert len(set(symbols)) == EVENT_ALPHABET_SIZE
    assert set(symbols) == set(range(EVENT_ALPHABET_SIZE))


def test_forward_and_reverse_mappings_are_exact_inverses() -> None:
    assert {
        symbol: event_type
        for event_type, symbol in EXPECTED_EVENT_TYPE_TO_SYMBOL.items()
    } == SYMBOL_TO_EVENT_TYPE

    for event_type, symbol in EVENT_TYPE_TO_SYMBOL.items():
        assert SYMBOL_TO_EVENT_TYPE[symbol] is event_type


def test_public_mappings_are_immutable() -> None:
    with pytest.raises(TypeError):
        EVENT_TYPE_TO_SYMBOL[EventType.OTHER] = 0  # type: ignore[index]

    with pytest.raises(TypeError):
        SYMBOL_TO_EVENT_TYPE[8] = EventType.ERROR  # type: ignore[index]


def test_module_does_not_expose_mutable_mapping_backing() -> None:
    assert not hasattr(
        encoding_module,
        "_EVENT_TYPE_TO_SYMBOL",
    )


@pytest.mark.parametrize("symbol", range(EVENT_ALPHABET_SIZE))
def test_validate_event_symbol_accepts_exact_range(
    symbol: int,
) -> None:
    validated = validate_event_symbol(symbol)

    assert validated == symbol
    assert type(validated) is int


@pytest.mark.parametrize("symbol", [True, False])
def test_validate_event_symbol_rejects_booleans(
    symbol: bool,
) -> None:
    with pytest.raises(
        ValueError,
        match="event symbol must be an integer",
    ):
        validate_event_symbol(symbol)


@pytest.mark.parametrize(
    "symbol",
    [
        pytest.param("1", id="string"),
        pytest.param(1.0, id="float"),
        pytest.param(None, id="none"),
        pytest.param(object(), id="object"),
    ],
)
def test_validate_event_symbol_rejects_non_integers(
    symbol: object,
) -> None:
    with pytest.raises(
        ValueError,
        match="event symbol must be an integer",
    ):
        validate_event_symbol(symbol)


@pytest.mark.parametrize("symbol", [-10, -1, 9, 10, 100])
def test_validate_event_symbol_rejects_out_of_range_integers(
    symbol: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=r"event symbol must be in range \[0, 9\)",
    ):
        validate_event_symbol(symbol)


@pytest.mark.parametrize(
    ("event_type", "expected_symbol"),
    tuple(EXPECTED_EVENT_TYPE_TO_SYMBOL.items()),
)
def test_encode_event_type_uses_stable_mapping(
    event_type: EventType,
    expected_symbol: int,
) -> None:
    assert encode_event_type(event_type) == expected_symbol


@pytest.mark.parametrize(
    "event_type",
    [
        pytest.param("error", id="string"),
        pytest.param(7, id="integer"),
        pytest.param(None, id="none"),
        pytest.param(object(), id="object"),
    ],
)
def test_encode_event_type_rejects_invalid_types(
    event_type: object,
) -> None:
    with pytest.raises(
        ValueError,
        match="event_type must be an EventType",
    ):
        encode_event_type(event_type)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("symbol", "expected_event_type"),
    tuple(
        (symbol, event_type)
        for event_type, symbol in EXPECTED_EVENT_TYPE_TO_SYMBOL.items()
    ),
)
def test_decode_event_symbol_uses_reverse_mapping(
    symbol: int,
    expected_event_type: EventType,
) -> None:
    assert decode_event_symbol(symbol) is expected_event_type


@pytest.mark.parametrize(
    "symbol",
    [
        pytest.param(True, id="boolean"),
        pytest.param(-1, id="negative"),
        pytest.param(9, id="too-large"),
        pytest.param("0", id="string"),
    ],
)
def test_decode_event_symbol_uses_shared_validation(
    symbol: object,
) -> None:
    with pytest.raises(ValueError):
        decode_event_symbol(symbol)


def test_encode_classified_event_uses_only_event_type() -> None:
    first = make_classified_event(
        EventType.ERROR,
        source_domain=SourceDomain.KERNEL,
        rule_id="severity.priority.error",
        evidence=EvidenceLevel.EXACT,
    )
    second = make_classified_event(
        EventType.ERROR,
        sequence_index=1,
        source_domain=SourceDomain.AUTHENTICATION,
        rule_id="synthetic.different.rule",
        evidence=EvidenceLevel.HEURISTIC,
    )

    assert encode_classified_event(first) == 7
    assert encode_classified_event(second) == 7


def test_encode_classified_event_does_not_mutate_input() -> None:
    event = make_classified_event(EventType.SERVICE_STARTED)
    before = event

    assert encode_classified_event(event) == 1
    assert event is before
    assert event == before


@pytest.mark.parametrize(
    "event",
    [
        pytest.param(None, id="none"),
        pytest.param(EventType.ERROR, id="event-type"),
        pytest.param(object(), id="object"),
    ],
)
def test_encode_classified_event_rejects_invalid_types(
    event: object,
) -> None:
    with pytest.raises(
        ValueError,
        match="event must be a ClassifiedJournalEvent",
    ):
        encode_classified_event(event)  # type: ignore[arg-type]


def test_iter_event_symbols_is_lazy_and_preserves_order() -> None:
    consumed: list[EventType] = []

    def events() -> Iterator[ClassifiedJournalEvent]:
        for index, event_type in enumerate(
            (
                EventType.BOOT_BOUNDARY,
                EventType.WARNING,
                EventType.OTHER,
            )
        ):
            consumed.append(event_type)
            yield make_classified_event(
                event_type,
                sequence_index=index,
            )

    symbols = iter_event_symbols(events())

    assert consumed == []
    assert next(symbols) == 0
    assert consumed == [EventType.BOOT_BOUNDARY]
    assert list(symbols) == [6, 8]
    assert consumed == [
        EventType.BOOT_BOUNDARY,
        EventType.WARNING,
        EventType.OTHER,
    ]


def test_iter_event_symbols_stops_before_later_invalid_items() -> None:
    consumed: list[str] = []

    def events() -> Iterator[object]:
        consumed.append("valid")
        yield make_classified_event(EventType.SERVICE_STOPPED)

        consumed.append("invalid")
        yield object()

        consumed.append("later")
        yield make_classified_event(EventType.OTHER)

    symbols = iter_event_symbols(events())  # type: ignore[arg-type]

    assert next(symbols) == 2

    with pytest.raises(
        ValueError,
        match="event must be a ClassifiedJournalEvent",
    ):
        next(symbols)

    assert consumed == ["valid", "invalid"]


def test_iter_validated_event_symbols_is_lazy_and_preserves_order() -> None:
    consumed: list[int] = []

    def symbols() -> Iterator[int]:
        for symbol in (0, 5, 8):
            consumed.append(symbol)
            yield symbol

    validated = iter_validated_event_symbols(symbols())

    assert consumed == []
    assert next(validated) == 0
    assert consumed == [0]
    assert list(validated) == [5, 8]
    assert consumed == [0, 5, 8]


def test_iter_validated_event_symbols_stops_at_first_error() -> None:
    consumed: list[object] = []

    def symbols() -> Iterator[object]:
        for symbol in (0, True, 8):
            consumed.append(symbol)
            yield symbol

    validated = iter_validated_event_symbols(symbols())

    assert next(validated) == 0

    with pytest.raises(
        ValueError,
        match="event symbol must be an integer",
    ):
        next(validated)

    assert consumed == [0, True]


def test_streaming_apis_accept_empty_iterables() -> None:
    assert list(iter_event_symbols(())) == []
    assert list(iter_validated_event_symbols(())) == []
