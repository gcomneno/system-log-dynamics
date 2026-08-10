"""Deterministic streaming classification of normalized journal events."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from system_log_dynamics.models import (
    ClassifiedJournalEvent,
    EventType,
    EvidenceLevel,
    NormalizedJournalEvent,
    SourceDomain,
)

SYSTEMD_UNIT_STARTED_MESSAGE_ID = "39f53479d3a045ac8e11786248231fbf"
SYSTEMD_UNIT_STOPPED_MESSAGE_ID = "9d1aaa27d60140bd96365438aad20286"
SYSTEMD_SESSION_STARTED_MESSAGE_ID = "8d45620c1a4348dbb17410da57c60c66"
SYSTEMD_SESSION_STOPPED_MESSAGE_ID = "3354939424b4456d9802ca8333ed424a"

_SERVICE_STARTED_MESSAGE_IDS = frozenset(
    {
        SYSTEMD_UNIT_STARTED_MESSAGE_ID,
    }
)
_SERVICE_STOPPED_MESSAGE_IDS = frozenset(
    {
        SYSTEMD_UNIT_STOPPED_MESSAGE_ID,
    }
)
_SESSION_MESSAGE_IDS = frozenset(
    {
        SYSTEMD_SESSION_STARTED_MESSAGE_ID,
        SYSTEMD_SESSION_STOPPED_MESSAGE_ID,
    }
)

_AUTHENTICATION_IDENTIFIERS = frozenset(
    {
        "gdm-password",
        "login",
        "pam_unix",
        "polkitd",
        "sshd",
        "su",
        "sudo",
    }
)
_SESSION_IDENTIFIERS = frozenset(
    {
        "gdm-session-worker",
        "systemd-logind",
    }
)
_NETWORK_IDENTIFIERS = frozenset(
    {
        "dhclient",
        "networkmanager",
        "systemd-networkd",
        "wpa_supplicant",
    }
)

_AUTHENTICATION_UNITS = frozenset(
    {
        "polkit.service",
        "sshd.service",
    }
)
_SESSION_UNITS = frozenset(
    {
        "systemd-logind.service",
        "systemd-user-sessions.service",
    }
)
_NETWORK_UNITS = frozenset(
    {
        "networkmanager.service",
        "systemd-networkd.service",
        "wpa_supplicant.service",
    }
)

_SESSION_OPEN_PHRASES = (
    "new session ",
    "session opened",
)
_SESSION_CLOSE_PHRASES = (
    "removed session ",
    "session closed",
)

_AUTHENTICATION_FAILURE_PHRASES = (
    "authentication failure",
    "authentication failed",
    "failed password",
    "invalid user",
    "permission denied",
)
_AUTHENTICATION_SUCCESS_PHRASES = (
    "accepted password",
    "accepted publickey",
    "authentication success",
    "authentication succeeded",
)


@dataclass(frozen=True, slots=True)
class _RuleMatch:
    event_type: EventType
    rule_id: str
    evidence: EvidenceLevel


def _casefold(value: str | None) -> str:
    if value is None:
        return ""

    return value.casefold()


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _structured_service_unit(
    event: NormalizedJournalEvent,
) -> str | None:
    for value in (event.unit, event.user_unit):
        if _casefold(value).endswith(".service"):
            return value

    return None


def _is_service_context(
    event: NormalizedJournalEvent,
) -> bool:
    return _structured_service_unit(event) is not None or _casefold(
        event.systemd_unit
    ).endswith(".service")


def _source_domain(
    event: NormalizedJournalEvent,
) -> SourceDomain:
    message_id = _casefold(event.message_id)
    identifier = _casefold(event.syslog_identifier)
    source_unit = _casefold(event.systemd_unit)
    structured_unit = _casefold(_structured_service_unit(event))
    transport = _casefold(event.transport)

    if (
        identifier in _AUTHENTICATION_IDENTIFIERS
        or source_unit in _AUTHENTICATION_UNITS
    ):
        return SourceDomain.AUTHENTICATION

    if (
        message_id in _SESSION_MESSAGE_IDS
        or identifier in _SESSION_IDENTIFIERS
        or source_unit in _SESSION_UNITS
    ):
        return SourceDomain.SESSION

    if identifier in _NETWORK_IDENTIFIERS or source_unit in _NETWORK_UNITS:
        return SourceDomain.NETWORK

    if transport == "kernel" or identifier == "kernel":
        return SourceDomain.KERNEL

    if (
        structured_unit.endswith(".service")
        or source_unit.endswith(".service")
        or identifier == "systemd"
    ):
        return SourceDomain.SERVICE

    return SourceDomain.OTHER


def _service_rule(
    event: NormalizedJournalEvent,
) -> _RuleMatch | None:
    message_id = _casefold(event.message_id)
    structured_unit = _structured_service_unit(event)

    if structured_unit is not None:
        if message_id in _SERVICE_STOPPED_MESSAGE_IDS:
            return _RuleMatch(
                event_type=EventType.SERVICE_STOPPED,
                rule_id="service.message_id.stopped",
                evidence=EvidenceLevel.EXACT,
            )

        if message_id in _SERVICE_STARTED_MESSAGE_IDS:
            return _RuleMatch(
                event_type=EventType.SERVICE_STARTED,
                rule_id="service.message_id.started",
                evidence=EvidenceLevel.EXACT,
            )

    if not _is_service_context(event):
        return None

    message = _casefold(event.message)

    if message.startswith("stopped "):
        return _RuleMatch(
            event_type=EventType.SERVICE_STOPPED,
            rule_id="service.message.stopped",
            evidence=EvidenceLevel.HEURISTIC,
        )

    if message.startswith("started "):
        return _RuleMatch(
            event_type=EventType.SERVICE_STARTED,
            rule_id="service.message.started",
            evidence=EvidenceLevel.HEURISTIC,
        )

    return None


def _session_rule(
    event: NormalizedJournalEvent,
    source_domain: SourceDomain,
) -> _RuleMatch | None:
    message_id = _casefold(event.message_id)

    if message_id in _SESSION_MESSAGE_IDS:
        return _RuleMatch(
            event_type=EventType.SESSION_BOUNDARY,
            rule_id="session.message_id.boundary",
            evidence=EvidenceLevel.EXACT,
        )

    if source_domain not in {
        SourceDomain.SESSION,
        SourceDomain.AUTHENTICATION,
    }:
        return None

    message = _casefold(event.message)

    if _contains_any(message, _SESSION_CLOSE_PHRASES):
        return _RuleMatch(
            event_type=EventType.SESSION_BOUNDARY,
            rule_id="session.message.closed",
            evidence=EvidenceLevel.HEURISTIC,
        )

    if _contains_any(message, _SESSION_OPEN_PHRASES):
        return _RuleMatch(
            event_type=EventType.SESSION_BOUNDARY,
            rule_id="session.message.opened",
            evidence=EvidenceLevel.HEURISTIC,
        )

    return None


def _authentication_rule(
    event: NormalizedJournalEvent,
    source_domain: SourceDomain,
) -> _RuleMatch | None:
    if source_domain is not SourceDomain.AUTHENTICATION:
        return None

    message = _casefold(event.message)

    if _contains_any(
        message,
        _AUTHENTICATION_FAILURE_PHRASES,
    ):
        return _RuleMatch(
            event_type=EventType.AUTHENTICATION_FAILURE,
            rule_id="authentication.message.failure",
            evidence=EvidenceLevel.HEURISTIC,
        )

    if _contains_any(
        message,
        _AUTHENTICATION_SUCCESS_PHRASES,
    ):
        return _RuleMatch(
            event_type=EventType.AUTHENTICATION_SUCCESS,
            rule_id="authentication.message.success",
            evidence=EvidenceLevel.HEURISTIC,
        )

    return None


def _severity_rule(
    event: NormalizedJournalEvent,
) -> _RuleMatch | None:
    if event.priority is not None and event.priority <= 3:
        return _RuleMatch(
            event_type=EventType.ERROR,
            rule_id="severity.priority.error",
            evidence=EvidenceLevel.EXACT,
        )

    if event.priority == 4:
        return _RuleMatch(
            event_type=EventType.WARNING,
            rule_id="severity.priority.warning",
            evidence=EvidenceLevel.EXACT,
        )

    return None


def _fallback_rule() -> _RuleMatch:
    return _RuleMatch(
        event_type=EventType.OTHER,
        rule_id="fallback.other",
        evidence=EvidenceLevel.FALLBACK,
    )


def _classify_without_boot_boundary(
    event: NormalizedJournalEvent,
    source_domain: SourceDomain,
) -> _RuleMatch:
    for match in (
        _service_rule(event),
        _session_rule(event, source_domain),
        _authentication_rule(event, source_domain),
        _severity_rule(event),
    ):
        if match is not None:
            return match

    return _fallback_rule()


def iter_classified_events(
    events: Iterable[NormalizedJournalEvent],
) -> Iterator[ClassifiedJournalEvent]:
    """Classify normalized events in order without buffering the input."""

    most_recent_known_boot: int | None = None

    for event in events:
        source_domain = _source_domain(event)

        if event.boot_index is None:
            match = _classify_without_boot_boundary(
                event,
                source_domain,
            )
        elif most_recent_known_boot is None:
            most_recent_known_boot = event.boot_index
            match = _classify_without_boot_boundary(
                event,
                source_domain,
            )
        elif event.boot_index != most_recent_known_boot:
            match = _RuleMatch(
                event_type=EventType.BOOT_BOUNDARY,
                rule_id="boot.index.changed",
                evidence=EvidenceLevel.EXACT,
            )
            most_recent_known_boot = event.boot_index
        else:
            match = _classify_without_boot_boundary(
                event,
                source_domain,
            )

        yield ClassifiedJournalEvent(
            normalized_event=event,
            event_type=match.event_type,
            source_domain=source_domain,
            rule_id=match.rule_id,
            evidence=match.evidence,
        )
