from dataclasses import FrozenInstanceError

import pytest

from system_log_dynamics.models import (
    ClassifiedJournalEvent,
    EventType,
    EvidenceLevel,
    NormalizedJournalEvent,
    SourceDomain,
)


def make_normalized_event() -> NormalizedJournalEvent:
    return NormalizedJournalEvent(
        sequence_index=0,
        source_line=1,
        boot_index=0,
        relative_realtime_us=0,
        monotonic_us=10,
        priority=6,
        message="Synthetic event.",
        message_id=None,
        transport="journal",
        systemd_unit="synthetic.service",
        syslog_identifier="synthetic-worker",
    )


def test_event_type_values_are_stable() -> None:
    assert tuple(EventType) == (
        EventType.BOOT_BOUNDARY,
        EventType.SERVICE_STARTED,
        EventType.SERVICE_STOPPED,
        EventType.AUTHENTICATION_SUCCESS,
        EventType.AUTHENTICATION_FAILURE,
        EventType.SESSION_BOUNDARY,
        EventType.WARNING,
        EventType.ERROR,
        EventType.OTHER,
    )

    assert {member.value for member in EventType} == {
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


def test_source_domain_values_are_stable() -> None:
    assert {member.value for member in SourceDomain} == {
        "service",
        "authentication",
        "session",
        "kernel",
        "network",
        "other",
    }


def test_evidence_level_values_are_stable() -> None:
    assert {member.value for member in EvidenceLevel} == {
        "exact",
        "heuristic",
        "fallback",
    }


def test_classified_event_preserves_normalized_event_identity() -> None:
    normalized = make_normalized_event()

    classified = ClassifiedJournalEvent(
        normalized_event=normalized,
        event_type=EventType.SERVICE_STARTED,
        source_domain=SourceDomain.SERVICE,
        rule_id="service.lifecycle.started",
        evidence=EvidenceLevel.HEURISTIC,
    )

    assert classified.normalized_event is normalized
    assert classified.event_type == "service_started"
    assert classified.source_domain == "service"
    assert classified.rule_id == "service.lifecycle.started"
    assert classified.evidence == "heuristic"
    assert isinstance(hash(classified), int)


def test_classified_event_is_immutable() -> None:
    classified = ClassifiedJournalEvent(
        normalized_event=make_normalized_event(),
        event_type=EventType.OTHER,
        source_domain=SourceDomain.OTHER,
        rule_id="fallback.other",
        evidence=EvidenceLevel.FALLBACK,
    )

    with pytest.raises(FrozenInstanceError):
        classified.rule_id = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "normalized_event",
            object(),
            "normalized_event must be a NormalizedJournalEvent",
        ),
        (
            "event_type",
            "other",
            "event_type must be an EventType",
        ),
        (
            "source_domain",
            "other",
            "source_domain must be a SourceDomain",
        ),
        (
            "evidence",
            "fallback",
            "evidence must be an EvidenceLevel",
        ),
    ],
)
def test_classified_event_rejects_untyped_contract_values(
    field: str,
    value: object,
    message: str,
) -> None:
    arguments: dict[str, object] = {
        "normalized_event": make_normalized_event(),
        "event_type": EventType.OTHER,
        "source_domain": SourceDomain.OTHER,
        "rule_id": "fallback.other",
        "evidence": EvidenceLevel.FALLBACK,
    }
    arguments[field] = value

    with pytest.raises(ValueError, match=message):
        ClassifiedJournalEvent(**arguments)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "rule_id",
    [
        "",
        " ",
        " fallback.other",
        "fallback.other ",
        None,
        3,
    ],
)
def test_classified_event_rejects_invalid_rule_identifier(
    rule_id: object,
) -> None:
    with pytest.raises(
        ValueError,
        match="rule_id must be a non-empty string",
    ):
        ClassifiedJournalEvent(
            normalized_event=make_normalized_event(),
            event_type=EventType.OTHER,
            source_domain=SourceDomain.OTHER,
            rule_id=rule_id,  # type: ignore[arg-type]
            evidence=EvidenceLevel.FALLBACK,
        )
