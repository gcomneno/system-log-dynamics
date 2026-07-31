from collections.abc import Iterator

import pytest

from system_log_dynamics.classification import (
    SYSTEMD_SESSION_STARTED_MESSAGE_ID,
    SYSTEMD_SESSION_STOPPED_MESSAGE_ID,
    SYSTEMD_UNIT_STARTED_MESSAGE_ID,
    SYSTEMD_UNIT_STOPPED_MESSAGE_ID,
    iter_classified_events,
)
from system_log_dynamics.models import (
    EventType,
    EvidenceLevel,
    NormalizedJournalEvent,
    SourceDomain,
)


def make_event(
    *,
    sequence_index: int = 0,
    source_line: int = 1,
    boot_index: int | None = None,
    priority: int | None = 6,
    message: str | None = None,
    message_id: str | None = None,
    transport: str | None = "journal",
    systemd_unit: str | None = None,
    syslog_identifier: str | None = None,
    unit: str | None = None,
    user_unit: str | None = None,
) -> NormalizedJournalEvent:
    return NormalizedJournalEvent(
        sequence_index=sequence_index,
        source_line=source_line,
        boot_index=boot_index,
        relative_realtime_us=sequence_index * 100,
        monotonic_us=sequence_index * 10,
        priority=priority,
        message=message,
        message_id=message_id,
        transport=transport,
        systemd_unit=systemd_unit,
        syslog_identifier=syslog_identifier,
        unit=unit,
        user_unit=user_unit,
    )


def classify_one(
    event: NormalizedJournalEvent,
):
    return next(iter_classified_events([event]))


def test_empty_input_produces_empty_output() -> None:
    assert list(iter_classified_events([])) == []


def test_classification_preserves_order_and_event_identity() -> None:
    events = [
        make_event(sequence_index=0, source_line=2),
        make_event(sequence_index=1, source_line=4),
        make_event(sequence_index=2, source_line=7),
    ]

    classified = list(iter_classified_events(events))

    assert [item.normalized_event.sequence_index for item in classified] == [0, 1, 2]

    assert [item.normalized_event for item in classified] == events

    assert all(
        item.normalized_event is event
        for item, event in zip(classified, events, strict=True)
    )


def test_classifier_is_lazy() -> None:
    consumed: list[int] = []

    def source() -> Iterator[NormalizedJournalEvent]:
        for index in range(3):
            consumed.append(index)
            yield make_event(sequence_index=index)

    classified = iter_classified_events(source())

    assert consumed == []

    first = next(classified)

    assert first.normalized_event.sequence_index == 0
    assert consumed == [0]


def test_first_known_boot_is_boundary() -> None:
    classified = classify_one(
        make_event(
            boot_index=0,
            message="Started Synthetic Service.",
            systemd_unit="synthetic.service",
        )
    )

    assert classified.event_type is EventType.BOOT_BOUNDARY
    assert classified.rule_id == "boot.index.changed"
    assert classified.evidence is EvidenceLevel.EXACT
    assert classified.source_domain is SourceDomain.SERVICE


def test_boot_context_survives_missing_boot_identifier() -> None:
    events = [
        make_event(sequence_index=0, boot_index=0),
        make_event(sequence_index=1, boot_index=None),
        make_event(sequence_index=2, boot_index=0),
        make_event(sequence_index=3, boot_index=1),
    ]

    classified = list(iter_classified_events(events))

    assert [item.event_type for item in classified] == [
        EventType.BOOT_BOUNDARY,
        EventType.OTHER,
        EventType.OTHER,
        EventType.BOOT_BOUNDARY,
    ]


@pytest.mark.parametrize(
    ("message_id", "event_type", "rule_id"),
    [
        (
            SYSTEMD_UNIT_STARTED_MESSAGE_ID,
            EventType.SERVICE_STARTED,
            "service.message_id.started",
        ),
        (
            SYSTEMD_UNIT_STOPPED_MESSAGE_ID,
            EventType.SERVICE_STOPPED,
            "service.message_id.stopped",
        ),
    ],
)
def test_structured_service_rules_are_exact(
    message_id: str,
    event_type: EventType,
    rule_id: str,
) -> None:
    classified = classify_one(
        make_event(
            message_id=message_id,
            unit="synthetic.service",
            systemd_unit="init.scope",
            syslog_identifier="systemd",
        )
    )

    assert classified.event_type is event_type
    assert classified.rule_id == rule_id
    assert classified.evidence is EvidenceLevel.EXACT
    assert classified.source_domain is SourceDomain.SERVICE


@pytest.mark.parametrize(
    ("message", "event_type", "rule_id"),
    [
        (
            "Started Synthetic Service.",
            EventType.SERVICE_STARTED,
            "service.message.started",
        ),
        (
            "Stopped Synthetic Service.",
            EventType.SERVICE_STOPPED,
            "service.message.stopped",
        ),
    ],
)
def test_bounded_service_text_rules_are_heuristic(
    message: str,
    event_type: EventType,
    rule_id: str,
) -> None:
    classified = classify_one(
        make_event(
            message=message,
            systemd_unit="synthetic.service",
        )
    )

    assert classified.event_type is event_type
    assert classified.rule_id == rule_id
    assert classified.evidence is EvidenceLevel.HEURISTIC


@pytest.mark.parametrize(
    "message",
    [
        "Started processing request.",
        "Stopped reading input.",
        "Worker failed after startup.",
    ],
)
def test_generic_service_keywords_without_context_fall_back(
    message: str,
) -> None:
    classified = classify_one(make_event(message=message))

    assert classified.event_type is EventType.OTHER
    assert classified.rule_id == "fallback.other"
    assert classified.evidence is EvidenceLevel.FALLBACK


@pytest.mark.parametrize(
    "message_id",
    [
        SYSTEMD_SESSION_STARTED_MESSAGE_ID,
        SYSTEMD_SESSION_STOPPED_MESSAGE_ID,
    ],
)
def test_structured_session_boundaries_are_exact(
    message_id: str,
) -> None:
    classified = classify_one(make_event(message_id=message_id))

    assert classified.event_type is EventType.SESSION_BOUNDARY
    assert classified.rule_id == "session.message_id.boundary"
    assert classified.evidence is EvidenceLevel.EXACT
    assert classified.source_domain is SourceDomain.SESSION


@pytest.mark.parametrize(
    ("message", "rule_id"),
    [
        (
            "Session opened for user synthetic.",
            "session.message.opened",
        ),
        (
            "Session closed for user synthetic.",
            "session.message.closed",
        ),
    ],
)
def test_session_text_rules_precede_authentication(
    message: str,
    rule_id: str,
) -> None:
    classified = classify_one(
        make_event(
            message=message,
            syslog_identifier="sudo",
        )
    )

    assert classified.event_type is EventType.SESSION_BOUNDARY
    assert classified.rule_id == rule_id
    assert classified.evidence is EvidenceLevel.HEURISTIC
    assert classified.source_domain is SourceDomain.AUTHENTICATION


def test_authentication_failure_precedes_success() -> None:
    classified = classify_one(
        make_event(
            message=("Accepted password followed by authentication failure."),
            syslog_identifier="sshd",
        )
    )

    assert classified.event_type is EventType.AUTHENTICATION_FAILURE
    assert classified.rule_id == "authentication.message.failure"
    assert classified.evidence is EvidenceLevel.HEURISTIC


@pytest.mark.parametrize(
    ("message", "event_type", "rule_id"),
    [
        (
            "Failed password for synthetic user.",
            EventType.AUTHENTICATION_FAILURE,
            "authentication.message.failure",
        ),
        (
            "Accepted publickey for synthetic user.",
            EventType.AUTHENTICATION_SUCCESS,
            "authentication.message.success",
        ),
    ],
)
def test_authentication_rules_require_authentication_context(
    message: str,
    event_type: EventType,
    rule_id: str,
) -> None:
    classified = classify_one(
        make_event(
            message=message,
            syslog_identifier="sshd",
        )
    )

    assert classified.event_type is event_type
    assert classified.rule_id == rule_id
    assert classified.source_domain is SourceDomain.AUTHENTICATION

    without_context = classify_one(make_event(message=message))

    assert without_context.event_type is EventType.OTHER


@pytest.mark.parametrize(
    ("priority", "event_type", "rule_id"),
    [
        (
            0,
            EventType.ERROR,
            "severity.priority.error",
        ),
        (
            3,
            EventType.ERROR,
            "severity.priority.error",
        ),
        (
            4,
            EventType.WARNING,
            "severity.priority.warning",
        ),
    ],
)
def test_priority_severity_rules(
    priority: int,
    event_type: EventType,
    rule_id: str,
) -> None:
    classified = classify_one(make_event(priority=priority))

    assert classified.event_type is event_type
    assert classified.rule_id == rule_id
    assert classified.evidence is EvidenceLevel.EXACT


def test_semantic_rule_precedes_priority_severity() -> None:
    classified = classify_one(
        make_event(
            priority=3,
            message="Accepted password for synthetic user.",
            syslog_identifier="sshd",
        )
    )

    assert classified.event_type is EventType.AUTHENTICATION_SUCCESS
    assert classified.rule_id == "authentication.message.success"


@pytest.mark.parametrize(
    ("event", "source_domain"),
    [
        (
            make_event(systemd_unit="synthetic.service"),
            SourceDomain.SERVICE,
        ),
        (
            make_event(syslog_identifier="sshd"),
            SourceDomain.AUTHENTICATION,
        ),
        (
            make_event(syslog_identifier="systemd-logind"),
            SourceDomain.SESSION,
        ),
        (
            make_event(transport="kernel"),
            SourceDomain.KERNEL,
        ),
        (
            make_event(syslog_identifier="NetworkManager"),
            SourceDomain.NETWORK,
        ),
        (
            make_event(),
            SourceDomain.OTHER,
        ),
    ],
)
def test_every_source_domain_is_deterministic(
    event: NormalizedJournalEvent,
    source_domain: SourceDomain,
) -> None:
    assert classify_one(event).source_domain is source_domain


def test_source_domain_is_independent_from_event_type() -> None:
    classified = classify_one(
        make_event(
            priority=3,
            transport="kernel",
        )
    )

    assert classified.event_type is EventType.ERROR
    assert classified.source_domain is SourceDomain.KERNEL


@pytest.mark.parametrize(
    "priority",
    [
        None,
        5,
        6,
        7,
    ],
)
def test_non_severe_unmatched_events_use_fallback(
    priority: int | None,
) -> None:
    classified = classify_one(make_event(priority=priority))

    assert classified.event_type is EventType.OTHER
    assert classified.rule_id == "fallback.other"
    assert classified.evidence is EvidenceLevel.FALLBACK
