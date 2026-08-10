"""Validated conversion from classified events to integer symbols."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from types import MappingProxyType

from system_log_dynamics.models import (
    ClassifiedJournalEvent,
    EventType,
)

EVENT_ALPHABET_SIZE = 9
EVENT_TAXONOMY_VERSION = "2"

EVENT_TYPE_TO_SYMBOL: Mapping[EventType, int] = MappingProxyType(
    {
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
)

SYMBOL_TO_EVENT_TYPE: Mapping[int, EventType] = MappingProxyType(
    {symbol: event_type for event_type, symbol in EVENT_TYPE_TO_SYMBOL.items()}
)


def validate_event_symbol(symbol: object) -> int:
    """Return one valid event symbol without coercing the input."""

    if not isinstance(symbol, int) or isinstance(symbol, bool):
        raise ValueError("event symbol must be an integer")

    if symbol < 0 or symbol >= EVENT_ALPHABET_SIZE:
        raise ValueError(f"event symbol must be in range [0, {EVENT_ALPHABET_SIZE})")

    return symbol


def encode_event_type(event_type: EventType) -> int:
    """Encode one validated semantic event type."""

    if not isinstance(event_type, EventType):
        raise ValueError("event_type must be an EventType")

    return validate_event_symbol(EVENT_TYPE_TO_SYMBOL[event_type])


def decode_event_symbol(symbol: object) -> EventType:
    """Decode one validated integer symbol to its semantic event type."""

    return SYMBOL_TO_EVENT_TYPE[validate_event_symbol(symbol)]


def encode_classified_event(
    event: ClassifiedJournalEvent,
) -> int:
    """Encode one classified event using only its semantic event type."""

    if not isinstance(event, ClassifiedJournalEvent):
        raise ValueError("event must be a ClassifiedJournalEvent")

    return encode_event_type(event.event_type)


def iter_event_symbols(
    events: Iterable[ClassifiedJournalEvent],
) -> Iterator[int]:
    """Lazily encode classified events while preserving input order."""

    for event in events:
        yield encode_classified_event(event)


def iter_validated_event_symbols(
    symbols: Iterable[object],
) -> Iterator[int]:
    """Lazily validate symbols without modulo normalization or coercion."""

    for symbol in symbols:
        yield validate_event_symbol(symbol)
