"""Stable immutable models for raw and normalized journal events."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType


def _require_integer(
    name: str,
    value: object,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")

    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")

    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be at most {maximum}")

    return value


def _require_optional_integer(
    name: str,
    value: object,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int | None:
    if value is None:
        return None

    return _require_integer(
        name,
        value,
        minimum=minimum,
        maximum=maximum,
    )


def _require_optional_string(name: str, value: object) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string or None")

    return value


def _freeze_json_value(value: object) -> object:
    if isinstance(value, Mapping):
        copied: dict[str, object] = {}

        for key, nested_value in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON object values must contain only string keys")
            copied[key] = _freeze_json_value(nested_value)

        return MappingProxyType(copied)

    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_value(item) for item in value)

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("JSON number values must be finite")
        return value

    if value is None or isinstance(value, (str, int, bool)):
        return value

    raise ValueError("fields must contain only JSON-compatible values")


@dataclass(frozen=True, slots=True)
class RawJournalEvent:
    """One untrusted JSON object together with its source line number."""

    source_line: int
    fields: Mapping[str, object]

    def __post_init__(self) -> None:
        _require_integer("source_line", self.source_line, minimum=1)

        if not isinstance(self.fields, Mapping):
            raise ValueError("fields must be a mapping")

        frozen_fields = _freeze_json_value(self.fields)

        if not isinstance(frozen_fields, Mapping):
            raise RuntimeError("frozen fields must remain a mapping")

        object.__setattr__(self, "fields", frozen_fields)


@dataclass(frozen=True, slots=True)
class NormalizedJournalEvent:
    """Validated journal data with privacy-safe temporal coordinates."""

    sequence_index: int
    source_line: int
    boot_index: int | None
    relative_realtime_us: int | None
    monotonic_us: int | None
    priority: int | None
    message: str | None
    message_id: str | None
    transport: str | None
    systemd_unit: str | None
    syslog_identifier: str | None
    unit: str | None = None
    user_unit: str | None = None

    def __post_init__(self) -> None:
        _require_integer(
            "sequence_index",
            self.sequence_index,
            minimum=0,
        )
        _require_integer(
            "source_line",
            self.source_line,
            minimum=1,
        )
        _require_optional_integer(
            "boot_index",
            self.boot_index,
            minimum=0,
        )
        _require_optional_integer(
            "relative_realtime_us",
            self.relative_realtime_us,
            minimum=0,
        )
        _require_optional_integer(
            "monotonic_us",
            self.monotonic_us,
            minimum=0,
        )
        _require_optional_integer(
            "priority",
            self.priority,
            minimum=0,
            maximum=7,
        )

        for name in (
            "message",
            "message_id",
            "transport",
            "systemd_unit",
            "syslog_identifier",
            "unit",
            "user_unit",
        ):
            _require_optional_string(name, getattr(self, name))


class EventType(StrEnum):
    """Stable semantic classification assigned to one normalized event."""

    BOOT_BOUNDARY = "boot_boundary"
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"
    AUTHENTICATION_SUCCESS = "authentication_success"
    AUTHENTICATION_FAILURE = "authentication_failure"
    SESSION_BOUNDARY = "session_boundary"
    WARNING = "warning"
    ERROR = "error"
    OTHER = "other"


class SourceDomain(StrEnum):
    """Stable source-domain metadata independent from event type."""

    SERVICE = "service"
    AUTHENTICATION = "authentication"
    SESSION = "session"
    KERNEL = "kernel"
    NETWORK = "network"
    OTHER = "other"


class EvidenceLevel(StrEnum):
    """Strength and origin of the classification evidence."""

    EXACT = "exact"
    HEURISTIC = "heuristic"
    FALLBACK = "fallback"


@dataclass(frozen=True, slots=True)
class ClassifiedJournalEvent:
    """One normalized event together with reproducible classifier metadata."""

    normalized_event: NormalizedJournalEvent
    event_type: EventType
    source_domain: SourceDomain
    rule_id: str
    evidence: EvidenceLevel

    def __post_init__(self) -> None:
        if not isinstance(
            self.normalized_event,
            NormalizedJournalEvent,
        ):
            raise ValueError("normalized_event must be a NormalizedJournalEvent")

        if not isinstance(self.event_type, EventType):
            raise ValueError("event_type must be an EventType")

        if not isinstance(self.source_domain, SourceDomain):
            raise ValueError("source_domain must be a SourceDomain")

        if not isinstance(self.evidence, EvidenceLevel):
            raise ValueError("evidence must be an EvidenceLevel")

        if (
            not isinstance(self.rule_id, str)
            or not self.rule_id
            or self.rule_id != self.rule_id.strip()
        ):
            raise ValueError(
                "rule_id must be a non-empty string without surrounding whitespace"
            )
