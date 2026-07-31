import pytest

from system_log_dynamics.classification import (
    SYSTEMD_UNIT_STARTED_MESSAGE_ID,
    SYSTEMD_UNIT_STOPPED_MESSAGE_ID,
    iter_classified_events,
)
from system_log_dynamics.journal import (
    JournalNormalizationError,
    iter_normalized_journal_json_lines,
)
from system_log_dynamics.models import (
    EventType,
    EvidenceLevel,
    NormalizedJournalEvent,
    SourceDomain,
)


def normalize_one(payload: str) -> NormalizedJournalEvent:
    events = list(iter_normalized_journal_json_lines([payload + "\n"]))

    assert len(events) == 1
    return events[0]


def test_unit_is_retained_as_service_subject() -> None:
    event = normalize_one(
        "{"
        '"PRIORITY":"6",'
        '"MESSAGE":"Started Synthetic Service.",'
        f'"MESSAGE_ID":"{SYSTEMD_UNIT_STARTED_MESSAGE_ID}",'
        '"_TRANSPORT":"journal",'
        '"_SYSTEMD_UNIT":"init.scope",'
        '"UNIT":"synthetic.service",'
        '"SYSLOG_IDENTIFIER":"systemd"'
        "}"
    )

    assert event.systemd_unit == "init.scope"
    assert event.unit == "synthetic.service"
    assert event.user_unit is None

    classified = next(iter_classified_events([event]))

    assert classified.event_type is EventType.SERVICE_STARTED
    assert classified.source_domain is SourceDomain.SERVICE
    assert classified.rule_id == "service.message_id.started"
    assert classified.evidence is EvidenceLevel.EXACT


def test_user_unit_is_retained_as_service_subject() -> None:
    event = normalize_one(
        "{"
        '"PRIORITY":"6",'
        '"MESSAGE":"Stopped Synthetic User Service.",'
        f'"MESSAGE_ID":"{SYSTEMD_UNIT_STOPPED_MESSAGE_ID}",'
        '"_TRANSPORT":"journal",'
        '"_SYSTEMD_UNIT":"user@1000.service",'
        '"USER_UNIT":"synthetic-user.service",'
        '"SYSLOG_IDENTIFIER":"systemd"'
        "}"
    )

    assert event.systemd_unit == "user@1000.service"
    assert event.unit is None
    assert event.user_unit == "synthetic-user.service"

    classified = next(iter_classified_events([event]))

    assert classified.event_type is EventType.SERVICE_STOPPED
    assert classified.source_domain is SourceDomain.SERVICE
    assert classified.rule_id == "service.message_id.stopped"
    assert classified.evidence is EvidenceLevel.EXACT


def test_exact_service_message_id_requires_subject_unit() -> None:
    event = NormalizedJournalEvent(
        sequence_index=0,
        source_line=1,
        boot_index=None,
        relative_realtime_us=None,
        monotonic_us=None,
        priority=6,
        message=None,
        message_id=SYSTEMD_UNIT_STARTED_MESSAGE_ID,
        transport="journal",
        systemd_unit="synthetic.service",
        syslog_identifier="systemd",
    )

    classified = next(iter_classified_events([event]))

    assert classified.event_type is EventType.OTHER
    assert classified.source_domain is SourceDomain.SERVICE
    assert classified.rule_id == "fallback.other"
    assert classified.evidence is EvidenceLevel.FALLBACK


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("UNIT", '["a.service","b.service"]'),
        ("USER_UNIT", "[65,66]"),
        ("UNIT", '{"name":"a.service"}'),
    ],
)
def test_structured_unit_fields_reject_non_text_values(
    field: str,
    value: str,
) -> None:
    payload = f'{{"{field}":{value}}}'

    with pytest.raises(
        JournalNormalizationError,
        match=field,
    ):
        list(iter_normalized_journal_json_lines([payload + "\n"]))
