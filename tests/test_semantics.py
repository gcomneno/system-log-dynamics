from __future__ import annotations

import json
from pathlib import Path

import pytest

from system_log_dynamics.classification import iter_classified_events
from system_log_dynamics.encoding import EVENT_TAXONOMY_VERSION
from system_log_dynamics.journal import iter_normalized_journal_json_lines
from system_log_dynamics.models import EventType, EvidenceLevel
from system_log_dynamics.semantics import (
    SEMANTIC_EVIDENCE_SCHEMA_NAME,
    SEMANTIC_EVIDENCE_SCHEMA_VERSION,
    SEMANTIC_FACET_VERSION,
    SemanticAction,
    SemanticFamily,
    build_semantic_evidence_envelope,
    iter_semantic_events,
    parse_semantic_evidence_json,
    render_semantic_evidence_json,
)

FIXTURE = Path("fixtures/synthetic/restart-loop-semantic.jsonl")


def _classified_fixture():
    with FIXTURE.open(encoding="utf-8") as source:
        return tuple(iter_classified_events(iter_normalized_journal_json_lines(source)))


def _classify_lines(lines: list[str]):
    return tuple(iter_classified_events(iter_normalized_journal_json_lines(lines)))


def test_restart_loop_fixture_preserves_small_primary_taxonomy() -> None:
    classified = _classified_fixture()

    assert len(classified) == 6
    assert EVENT_TAXONOMY_VERSION == "2"
    assert [event.event_type for event in classified] == [EventType.OTHER] * 6


def test_restart_loop_fixture_recovers_descriptive_semantics() -> None:
    semantic = tuple(iter_semantic_events(_classified_fixture()))

    assert [event.facets.family for event in semantic] == [
        SemanticFamily.SERVICE_LIFECYCLE,
        SemanticFamily.PROCESS_RUNTIME,
        SemanticFamily.SERVICE_LIFECYCLE,
        SemanticFamily.SERVICE_LIFECYCLE,
        SemanticFamily.PROCESS_RUNTIME,
        SemanticFamily.SERVICE_LIFECYCLE,
    ]
    assert [event.facets.action for event in semantic] == [
        SemanticAction.RESTART_SCHEDULED,
        SemanticAction.PROCESS_OUTPUT,
        SemanticAction.PROCESS_EXITED,
        SemanticAction.RESTART_SCHEDULED,
        SemanticAction.PROCESS_OUTPUT,
        SemanticAction.PROCESS_EXITED,
    ]
    assert {event.facets.subject_unit for event in semantic} == {"demo-restart.service"}
    assert [event.facets.transport for event in semantic] == [
        None,
        "stdout",
        None,
        None,
        "stdout",
        None,
    ]
    assert all(event.semantic_evidence is EvidenceLevel.EXACT for event in semantic)
    assert [event.sequence_index for event in semantic] == list(range(6))
    assert [event.relative_realtime_us for event in semantic] == [
        0,
        37_000,
        42_000,
        5_250_000,
        5_288_000,
        5_294_000,
    ]


def test_semantic_evidence_is_versioned_strict_and_deterministic() -> None:
    input_bytes = FIXTURE.read_bytes()
    envelope = build_semantic_evidence_envelope(
        input_bytes,
        _classified_fixture(),
        window_id="synthetic-restart-loop",
    )

    assert envelope.schema_name == SEMANTIC_EVIDENCE_SCHEMA_NAME
    assert envelope.schema_version == SEMANTIC_EVIDENCE_SCHEMA_VERSION == 1
    assert envelope.bundle_type == "semantic_events"
    assert envelope.payload["provenance"]["taxonomy_version"] == "2"
    assert (
        envelope.payload["provenance"]["semantic_facets_version"]
        == SEMANTIC_FACET_VERSION
        == "1"
    )
    assert envelope.payload["coverage"] == {
        "source_event_count": 6,
        "semantic_event_count": 6,
        "semantic_event_proportion": 1.0,
    }

    rendered = render_semantic_evidence_json(envelope)
    parsed = parse_semantic_evidence_json(rendered)

    assert render_semantic_evidence_json(parsed) == rendered
    assert "Synthetic manager" not in rendered
    assert "Synthetic child output" not in rendered
    assert '"contains_raw_messages":false' in rendered
    assert '"contains_normalized_subject_identifiers":true' in rendered


def test_semantic_evidence_keeps_primary_and_semantic_rules_distinct() -> None:
    envelope = build_semantic_evidence_envelope(
        FIXTURE.read_bytes(),
        _classified_fixture(),
    )
    events = envelope.payload["events"]

    first = events[0]
    assert first["primary"] == {
        "symbol": 8,
        "event_type": "other",
        "source_domain": "service",
        "rule_id": "fallback.other",
        "evidence": "fallback",
    }
    assert first["semantic"] == {
        "family": "service_lifecycle",
        "action": "restart_scheduled",
        "subject": {
            "kind": "systemd_unit",
            "value": "demo-restart.service",
        },
        "transport": None,
        "rule_id": "semantic.systemd.restart_scheduled.message_id",
        "evidence": "exact",
    }


def test_semantic_parser_rejects_unknown_fields_and_versions() -> None:
    rendered = render_semantic_evidence_json(
        build_semantic_evidence_envelope(
            FIXTURE.read_bytes(),
            _classified_fixture(),
        )
    )
    document = json.loads(rendered)

    document["payload"]["unknown"] = True
    with pytest.raises(ValueError, match="payload must contain exactly"):
        parse_semantic_evidence_json(json.dumps(document))

    document = json.loads(rendered)
    document["schema_version"] = 2
    with pytest.raises(
        ValueError,
        match="unsupported semantic evidence schema version",
    ):
        parse_semantic_evidence_json(json.dumps(document))

    document = json.loads(rendered)
    document["payload"]["provenance"]["semantic_facets_version"] = "2"
    with pytest.raises(ValueError, match="unsupported semantic facets version"):
        parse_semantic_evidence_json(json.dumps(document))


def test_semantic_parser_rejects_duplicate_keys() -> None:
    with pytest.raises(ValueError, match="duplicate JSON object key rejected"):
        parse_semantic_evidence_json(
            '{"schema_name":"system-log-dynamics.semantic-evidence",'
            '"schema_name":"duplicate","schema_version":1,'
            '"bundle_type":"semantic_events","payload":{}}'
        )


def test_unrecognized_other_remains_without_semantic_facet() -> None:
    classified = _classify_lines(
        [
            '{"__REALTIME_TIMESTAMP":"1","_BOOT_ID":"boot-a",'
            '"PRIORITY":"6","MESSAGE":"opaque synthetic event",'
            '"_TRANSPORT":"journal","SYSLOG_IDENTIFIER":"example"}\n'
        ]
    )

    assert classified[0].event_type is EventType.OTHER
    assert tuple(iter_semantic_events(classified)) == ()


def test_lifecycle_message_id_without_structured_subject_is_not_invented() -> None:
    classified = _classify_lines(
        [
            '{"__REALTIME_TIMESTAMP":"1","_BOOT_ID":"boot-a",'
            '"PRIORITY":"6","MESSAGE":"synthetic restart notice",'
            '"MESSAGE_ID":"5eb03494b6584870a536b337290809b3",'
            '"_TRANSPORT":"journal","_SYSTEMD_UNIT":"init.scope",'
            '"SYSLOG_IDENTIFIER":"systemd"}\n'
        ]
    )

    assert tuple(iter_semantic_events(classified)) == ()


def test_exact_lifecycle_match_precedes_generic_process_output_match() -> None:
    classified = _classify_lines(
        [
            '{"__REALTIME_TIMESTAMP":"1","_BOOT_ID":"boot-a",'
            '"PRIORITY":"6","MESSAGE":"synthetic conflicting record",'
            '"MESSAGE_ID":"5eb03494b6584870a536b337290809b3",'
            '"_TRANSPORT":"stdout","_SYSTEMD_UNIT":"producer.service",'
            '"SYSLOG_IDENTIFIER":"systemd","UNIT":"target.service"}\n'
        ]
    )

    semantic = tuple(iter_semantic_events(classified))

    assert len(semantic) == 1
    assert semantic[0].facets.family is SemanticFamily.SERVICE_LIFECYCLE
    assert semantic[0].facets.action is SemanticAction.RESTART_SCHEDULED
    assert semantic[0].facets.subject_unit == "target.service"
    assert semantic[0].facets.transport is None
    assert (
        semantic[0].semantic_rule_id == "semantic.systemd.restart_scheduled.message_id"
    )
