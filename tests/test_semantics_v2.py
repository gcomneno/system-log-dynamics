from __future__ import annotations

from pathlib import Path

from system_log_dynamics.classification import iter_classified_events
from system_log_dynamics.encoding import EVENT_TAXONOMY_VERSION
from system_log_dynamics.journal import iter_normalized_journal_json_lines
from system_log_dynamics.models import EventType, EvidenceLevel
from system_log_dynamics.semantics import (
    SEMANTIC_EVIDENCE_SCHEMA_VERSION,
    SEMANTIC_FACET_VERSION,
    SemanticAction,
    SemanticFamily,
    build_semantic_evidence_envelope,
    iter_semantic_events,
    parse_semantic_evidence_json,
    render_semantic_evidence_json,
)

FIXTURE = Path("fixtures/synthetic/systemd-lifecycle-semantic-v2.jsonl")


def _classified_fixture():
    with FIXTURE.open(encoding="utf-8") as source:
        return tuple(iter_classified_events(iter_normalized_journal_json_lines(source)))


def _classify_lines(lines: list[str]):
    return tuple(iter_classified_events(iter_normalized_journal_json_lines(lines)))


def test_v2_fixture_preserves_taxonomy_and_recovers_structured_lifecycle() -> None:
    classified = _classified_fixture()
    semantic = tuple(iter_semantic_events(classified))

    assert EVENT_TAXONOMY_VERSION == "2"
    assert [event.event_type for event in classified] == [EventType.OTHER] * 4
    assert [event.facets.family for event in semantic] == [
        SemanticFamily.SERVICE_LIFECYCLE,
    ] * 4
    assert [event.facets.action for event in semantic] == [
        SemanticAction.START_JOB_BEGUN,
        SemanticAction.UNIT_SUCCEEDED,
        SemanticAction.START_JOB_BEGUN,
        SemanticAction.UNIT_SUCCEEDED,
    ]
    assert [event.facets.subject_unit for event in semantic] == [
        "alpha-worker.service",
        "alpha-worker.service",
        "beta-worker.service",
        "beta-worker.service",
    ]
    assert all(event.facets.transport is None for event in semantic)
    assert all(event.semantic_evidence is EvidenceLevel.EXACT for event in semantic)
    assert [event.semantic_rule_id for event in semantic] == [
        "semantic.systemd.start_job_begun.message_id",
        "semantic.systemd.unit_succeeded.message_id",
        "semantic.systemd.start_job_begun.message_id",
        "semantic.systemd.unit_succeeded.message_id",
    ]


def test_v2_evidence_keeps_schema_v1_and_bumps_only_facet_version() -> None:
    envelope = build_semantic_evidence_envelope(
        FIXTURE.read_bytes(),
        _classified_fixture(),
        window_id="synthetic-systemd-lifecycle-v2",
    )

    assert envelope.schema_version == SEMANTIC_EVIDENCE_SCHEMA_VERSION == 1
    assert envelope.payload["provenance"]["taxonomy_version"] == "2"
    assert (
        envelope.payload["provenance"]["semantic_facets_version"]
        == SEMANTIC_FACET_VERSION
        == "2"
    )
    assert envelope.payload["coverage"] == {
        "source_event_count": 4,
        "semantic_event_count": 4,
        "semantic_event_proportion": 1.0,
    }

    rendered = render_semantic_evidence_json(envelope)
    parsed = parse_semantic_evidence_json(rendered)

    assert render_semantic_evidence_json(parsed) == rendered
    assert "Opaque lifecycle marker" not in rendered
    assert '"contains_raw_messages":false' in rendered


def test_v2_message_ids_require_structured_subject_and_systemd_identifier() -> None:
    missing_subject = _classify_lines(
        [
            '{"__REALTIME_TIMESTAMP":"1","_BOOT_ID":"boot-a",'
            '"PRIORITY":"6","MESSAGE":"opaque",'
            '"MESSAGE_ID":"7d4958e842da4a758f6c1cdc7b36dcc5",'
            '"_TRANSPORT":"journal","_SYSTEMD_UNIT":"init.scope",'
            '"SYSLOG_IDENTIFIER":"systemd"}\n'
        ]
    )
    wrong_identifier = _classify_lines(
        [
            '{"__REALTIME_TIMESTAMP":"1","_BOOT_ID":"boot-a",'
            '"PRIORITY":"6","MESSAGE":"opaque",'
            '"MESSAGE_ID":"7ad2d189f7e94e70a38c781354912448",'
            '"_TRANSPORT":"journal","_SYSTEMD_UNIT":"init.scope",'
            '"SYSLOG_IDENTIFIER":"not-systemd","UNIT":"demo.service"}\n'
        ]
    )

    assert tuple(iter_semantic_events(missing_subject)) == ()
    assert tuple(iter_semantic_events(wrong_identifier)) == ()


def test_v2_does_not_infer_lifecycle_from_similar_free_text() -> None:
    classified = _classify_lines(
        [
            '{"__REALTIME_TIMESTAMP":"1","_BOOT_ID":"boot-a",'
            '"PRIORITY":"6","MESSAGE":"Starting Example Service",'
            '"MESSAGE_ID":"11111111111111111111111111111111",'
            '"_TRANSPORT":"journal","_SYSTEMD_UNIT":"init.scope",'
            '"SYSLOG_IDENTIFIER":"systemd","UNIT":"demo.service"}\n',
            '{"__REALTIME_TIMESTAMP":"2","_BOOT_ID":"boot-a",'
            '"PRIORITY":"6","MESSAGE":"Example Service deactivated successfully",'
            '"MESSAGE_ID":"22222222222222222222222222222222",'
            '"_TRANSPORT":"journal","_SYSTEMD_UNIT":"init.scope",'
            '"SYSLOG_IDENTIFIER":"systemd","UNIT":"demo.service"}\n',
        ]
    )

    assert tuple(iter_semantic_events(classified)) == ()


def test_v2_exact_lifecycle_match_precedes_generic_process_output() -> None:
    classified = _classify_lines(
        [
            '{"__REALTIME_TIMESTAMP":"1","_BOOT_ID":"boot-a",'
            '"PRIORITY":"6","MESSAGE":"opaque conflicting record",'
            '"MESSAGE_ID":"7d4958e842da4a758f6c1cdc7b36dcc5",'
            '"_TRANSPORT":"stdout","_SYSTEMD_UNIT":"producer.service",'
            '"SYSLOG_IDENTIFIER":"systemd","UNIT":"target.service"}\n',
            '{"__REALTIME_TIMESTAMP":"2","_BOOT_ID":"boot-a",'
            '"PRIORITY":"6","MESSAGE":"opaque conflicting record",'
            '"MESSAGE_ID":"7ad2d189f7e94e70a38c781354912448",'
            '"_TRANSPORT":"stderr","_SYSTEMD_UNIT":"producer.service",'
            '"SYSLOG_IDENTIFIER":"systemd","USER_UNIT":"target-user.service"}\n',
        ]
    )

    semantic = tuple(iter_semantic_events(classified))

    assert [event.facets.action for event in semantic] == [
        SemanticAction.START_JOB_BEGUN,
        SemanticAction.UNIT_SUCCEEDED,
    ]
    assert [event.facets.subject_unit for event in semantic] == [
        "target.service",
        "target-user.service",
    ]
    assert all(event.facets.transport is None for event in semantic)


def test_dbus_and_cron_text_only_patterns_remain_unrecognized() -> None:
    classified = _classify_lines(
        [
            '{"__REALTIME_TIMESTAMP":"1","_BOOT_ID":"boot-a",'
            '"PRIORITY":"6","MESSAGE":"Activating service name=example",'
            '"_TRANSPORT":"syslog","_SYSTEMD_UNIT":"dbus.service",'
            '"SYSLOG_IDENTIFIER":"dbus-daemon"}\n',
            '{"__REALTIME_TIMESTAMP":"2","_BOOT_ID":"boot-a",'
            '"PRIORITY":"5","MESSAGE":"Failed to activate service: timed out",'
            '"_TRANSPORT":"syslog","_SYSTEMD_UNIT":"dbus.service",'
            '"SYSLOG_IDENTIFIER":"dbus-daemon"}\n',
            '{"__REALTIME_TIMESTAMP":"3","_BOOT_ID":"boot-a",'
            '"PRIORITY":"6","MESSAGE":"session opened for user example",'
            '"_TRANSPORT":"syslog","_SYSTEMD_UNIT":"cron.service",'
            '"SYSLOG_IDENTIFIER":"CRON"}\n',
            '{"__REALTIME_TIMESTAMP":"4","_BOOT_ID":"boot-a",'
            '"PRIORITY":"6","MESSAGE":"session closed for user example",'
            '"_TRANSPORT":"syslog","_SYSTEMD_UNIT":"cron.service",'
            '"SYSLOG_IDENTIFIER":"CRON"}\n',
        ]
    )

    assert tuple(iter_semantic_events(classified)) == ()
