"""Strict decoding and normalization for journal JSON Lines."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator

from system_log_dynamics.models import (
    NormalizedJournalEvent,
    RawJournalEvent,
)


class JournalParseError(ValueError):
    """Controlled decoding error associated with one physical input line."""

    def __init__(self, source_line: int, detail: str) -> None:
        self.source_line = source_line
        self.detail = detail
        super().__init__(f"line {source_line}: {detail}")


class JournalNormalizationError(ValueError):
    """Controlled field error associated with one decoded journal event."""

    def __init__(
        self,
        source_line: int,
        field: str,
        detail: str,
    ) -> None:
        self.source_line = source_line
        self.field = field
        self.detail = detail
        super().__init__(f"line {source_line}, field {field}: {detail}")


class _DuplicateKeyError(ValueError):
    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(key)


class _InvalidConstantError(ValueError):
    def __init__(self, constant: str) -> None:
        self.constant = constant
        super().__init__(constant)


def _strict_object(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}

    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(key)
        result[key] = value

    return result


def _reject_nonstandard_constant(constant: str) -> object:
    raise _InvalidConstantError(constant)


def iter_journal_json_lines(
    lines: Iterable[str],
) -> Iterator[RawJournalEvent]:
    """Decode JSON objects while preserving physical source line numbers."""

    for source_line, line in enumerate(lines, start=1):
        if not isinstance(line, str):
            raise JournalParseError(
                source_line,
                "input line must be text",
            )

        if not line.strip():
            continue

        try:
            decoded = json.loads(
                line,
                object_pairs_hook=_strict_object,
                parse_constant=_reject_nonstandard_constant,
            )
        except json.JSONDecodeError as exc:
            raise JournalParseError(
                source_line,
                f"invalid JSON at column {exc.colno}: {exc.msg}",
            ) from exc
        except _DuplicateKeyError as exc:
            raise JournalParseError(
                source_line,
                f"duplicate JSON object key: {exc.key!r}",
            ) from exc
        except _InvalidConstantError as exc:
            raise JournalParseError(
                source_line,
                f"invalid JSON constant: {exc.constant}",
            ) from exc

        if not isinstance(decoded, dict):
            type_name = type(decoded).__name__
            raise JournalParseError(
                source_line,
                f"expected a JSON object, got {type_name}",
            )

        try:
            event = RawJournalEvent(
                source_line=source_line,
                fields=decoded,
            )
        except ValueError as exc:
            raise JournalParseError(
                source_line,
                f"invalid JSON value: {exc}",
            ) from exc

        yield event


def _optional_nonnegative_integer(
    event: RawJournalEvent,
    field: str,
) -> int | None:
    value = event.fields.get(field)

    if value is None:
        return None

    if isinstance(value, bool):
        raise JournalNormalizationError(
            event.source_line,
            field,
            "must not be a boolean",
        )

    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str) and value and value.isascii() and value.isdigit():
        parsed = int(value)
    else:
        raise JournalNormalizationError(
            event.source_line,
            field,
            "must be a non-negative integer or decimal string",
        )

    if parsed < 0:
        raise JournalNormalizationError(
            event.source_line,
            field,
            "must be non-negative",
        )

    return parsed


def _optional_priority(
    event: RawJournalEvent,
) -> int | None:
    field = "PRIORITY"
    value = event.fields.get(field)

    if value is None:
        return None

    if isinstance(value, bool):
        raise JournalNormalizationError(
            event.source_line,
            field,
            "must not be a boolean",
        )

    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str) and len(value) == 1 and value in "01234567":
        parsed = int(value)
    else:
        raise JournalNormalizationError(
            event.source_line,
            field,
            "must be an integer from 0 through 7 or its one-digit string",
        )

    if not 0 <= parsed <= 7:
        raise JournalNormalizationError(
            event.source_line,
            field,
            "must be between 0 and 7",
        )

    return parsed


def _is_byte_array(value: tuple[object, ...]) -> bool:
    return bool(value) and all(
        isinstance(item, int) and not isinstance(item, bool) and 0 <= item <= 255
        for item in value
    )


def _optional_text(
    event: RawJournalEvent,
    field: str,
) -> str | None:
    value = event.fields.get(field)

    if value is None:
        return None

    if isinstance(value, str):
        return value

    if isinstance(value, tuple):
        representation = (
            "byte-array" if _is_byte_array(value) else "repeated-value array"
        )
        raise JournalNormalizationError(
            event.source_line,
            field,
            f"{representation} representation is unsupported",
        )

    raise JournalNormalizationError(
        event.source_line,
        field,
        "must be a string or null",
    )


def _optional_boot_identifier(
    event: RawJournalEvent,
) -> str | None:
    field = "_BOOT_ID"
    value = _optional_text(event, field)

    if value == "":
        raise JournalNormalizationError(
            event.source_line,
            field,
            "must not be empty",
        )

    return value


def iter_normalized_events(
    events: Iterable[RawJournalEvent],
) -> Iterator[NormalizedJournalEvent]:
    """Normalize selected fields without retaining absolute identifiers."""

    boot_indexes: dict[str, int] = {}
    first_realtime_us: int | None = None
    previous_realtime_us: int | None = None
    previous_monotonic_by_boot: dict[int, int] = {}

    for sequence_index, event in enumerate(events):
        if not isinstance(event, RawJournalEvent):
            raise TypeError("events must contain RawJournalEvent instances")

        boot_identifier = _optional_boot_identifier(event)
        boot_index: int | None = None

        if boot_identifier is not None:
            if boot_identifier not in boot_indexes:
                boot_indexes[boot_identifier] = len(boot_indexes)
            boot_index = boot_indexes[boot_identifier]

        realtime_us = _optional_nonnegative_integer(
            event,
            "__REALTIME_TIMESTAMP",
        )

        if realtime_us is None:
            relative_realtime_us = None
        else:
            if previous_realtime_us is not None and realtime_us < previous_realtime_us:
                raise JournalNormalizationError(
                    event.source_line,
                    "__REALTIME_TIMESTAMP",
                    "must not decrease across accepted events",
                )

            if first_realtime_us is None:
                first_realtime_us = realtime_us

            relative_realtime_us = realtime_us - first_realtime_us
            previous_realtime_us = realtime_us

        monotonic_us = _optional_nonnegative_integer(
            event,
            "__MONOTONIC_TIMESTAMP",
        )

        if monotonic_us is not None and boot_index is not None:
            previous_monotonic = previous_monotonic_by_boot.get(boot_index)

            if previous_monotonic is not None and monotonic_us < previous_monotonic:
                raise JournalNormalizationError(
                    event.source_line,
                    "__MONOTONIC_TIMESTAMP",
                    "must not decrease within the same boot",
                )

            previous_monotonic_by_boot[boot_index] = monotonic_us

        yield NormalizedJournalEvent(
            sequence_index=sequence_index,
            source_line=event.source_line,
            boot_index=boot_index,
            relative_realtime_us=relative_realtime_us,
            monotonic_us=monotonic_us,
            priority=_optional_priority(event),
            message=_optional_text(event, "MESSAGE"),
            message_id=_optional_text(event, "MESSAGE_ID"),
            transport=_optional_text(event, "_TRANSPORT"),
            systemd_unit=_optional_text(event, "_SYSTEMD_UNIT"),
            syslog_identifier=_optional_text(
                event,
                "SYSLOG_IDENTIFIER",
            ),
        )


def iter_normalized_journal_json_lines(
    lines: Iterable[str],
) -> Iterator[NormalizedJournalEvent]:
    """Decode and normalize journal JSON Lines in one streaming pipeline."""

    return iter_normalized_events(iter_journal_json_lines(lines))
