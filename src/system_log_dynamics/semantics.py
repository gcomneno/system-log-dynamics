"""Versioned descriptive semantic facets for downstream consumers."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from system_log_dynamics import __version__
from system_log_dynamics.encoding import (
    EVENT_TAXONOMY_VERSION,
    EVENT_TYPE_TO_SYMBOL,
    SYMBOL_TO_EVENT_TYPE,
)
from system_log_dynamics.models import (
    ClassifiedJournalEvent,
    EventType,
    EvidenceLevel,
    SourceDomain,
)

__all__ = [
    "SEMANTIC_EVIDENCE_SCHEMA_NAME",
    "SEMANTIC_EVIDENCE_SCHEMA_VERSION",
    "SEMANTIC_FACET_VERSION",
    "SemanticAction",
    "SemanticEvidenceEnvelope",
    "SemanticFacets",
    "SemanticFamily",
    "SemanticJournalEvent",
    "build_semantic_evidence_envelope",
    "iter_semantic_events",
    "parse_semantic_evidence_json",
    "render_semantic_evidence_json",
]

SEMANTIC_EVIDENCE_SCHEMA_NAME: Final = "system-log-dynamics.semantic-evidence"
SEMANTIC_EVIDENCE_SCHEMA_VERSION: Final = 1
SEMANTIC_FACET_VERSION: Final = "2"
SEMANTIC_BUNDLE_TYPE: Final = "semantic_events"

SYSTEMD_RESTART_SCHEDULED_MESSAGE_ID: Final = "5eb03494b6584870a536b337290809b3"
SYSTEMD_UNIT_PROCESS_EXITED_MESSAGE_ID: Final = "98e322203f7a4ed290d09fe03c09fe15"
SYSTEMD_START_JOB_BEGUN_MESSAGE_ID: Final = "7d4958e842da4a758f6c1cdc7b36dcc5"
SYSTEMD_UNIT_SUCCEEDED_MESSAGE_ID: Final = "7ad2d189f7e94e70a38c781354912448"


class SemanticFamily(StrEnum):
    """Small descriptive families independent from the primary symbol alphabet."""

    SERVICE_LIFECYCLE = "service_lifecycle"
    PROCESS_RUNTIME = "process_runtime"


class SemanticAction(StrEnum):
    """Stable descriptive actions carried as semantic facets."""

    RESTART_SCHEDULED = "restart_scheduled"
    PROCESS_EXITED = "process_exited"
    START_JOB_BEGUN = "start_job_begun"
    UNIT_SUCCEEDED = "unit_succeeded"
    PROCESS_OUTPUT = "process_output"


@dataclass(frozen=True, slots=True)
class SemanticFacets:
    family: SemanticFamily
    action: SemanticAction
    subject_unit: str
    transport: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.family, SemanticFamily):
            raise ValueError("family must be a SemanticFamily")
        if not isinstance(self.action, SemanticAction):
            raise ValueError("action must be a SemanticAction")
        if (
            not isinstance(self.subject_unit, str)
            or not self.subject_unit
            or self.subject_unit != self.subject_unit.strip()
            or not self.subject_unit.casefold().endswith(".service")
        ):
            raise ValueError("subject_unit must be a non-empty systemd service unit")

        if self.action in {
            SemanticAction.RESTART_SCHEDULED,
            SemanticAction.PROCESS_EXITED,
            SemanticAction.START_JOB_BEGUN,
            SemanticAction.UNIT_SUCCEEDED,
        }:
            if self.family is not SemanticFamily.SERVICE_LIFECYCLE:
                raise ValueError("service lifecycle actions require service_lifecycle")
            if self.transport is not None:
                raise ValueError("service lifecycle facets must not carry transport")
        elif self.action is SemanticAction.PROCESS_OUTPUT:
            if self.family is not SemanticFamily.PROCESS_RUNTIME:
                raise ValueError("process output requires process_runtime")
            if self.transport not in {"stdout", "stderr"}:
                raise ValueError("process output transport must be stdout or stderr")


@dataclass(frozen=True, slots=True)
class SemanticJournalEvent:
    sequence_index: int
    relative_realtime_us: int | None
    primary_event_type: EventType
    primary_symbol: int
    source_domain: SourceDomain
    primary_rule_id: str
    primary_evidence: EvidenceLevel
    facets: SemanticFacets
    semantic_rule_id: str
    semantic_evidence: EvidenceLevel

    def __post_init__(self) -> None:
        if type(self.sequence_index) is not int or self.sequence_index < 0:
            raise ValueError("sequence_index must be a non-negative integer")
        if self.relative_realtime_us is not None and (
            type(self.relative_realtime_us) is not int or self.relative_realtime_us < 0
        ):
            raise ValueError("relative_realtime_us must be non-negative or None")
        if not isinstance(self.primary_event_type, EventType):
            raise ValueError("primary_event_type must be an EventType")
        if self.primary_symbol != EVENT_TYPE_TO_SYMBOL[self.primary_event_type]:
            raise ValueError("primary_symbol must match primary_event_type")
        if not isinstance(self.source_domain, SourceDomain):
            raise ValueError("source_domain must be a SourceDomain")
        if not isinstance(self.primary_evidence, EvidenceLevel):
            raise ValueError("primary_evidence must be an EvidenceLevel")
        if not isinstance(self.semantic_evidence, EvidenceLevel):
            raise ValueError("semantic_evidence must be an EvidenceLevel")
        if not isinstance(self.facets, SemanticFacets):
            raise ValueError("facets must be SemanticFacets")
        for name in ("primary_rule_id", "semantic_rule_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value or value != value.strip():
                raise ValueError(f"{name} must be non-empty canonical text")


@dataclass(frozen=True, slots=True)
class SemanticEvidenceEnvelope:
    schema_name: str
    schema_version: int
    bundle_type: str
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.schema_name != SEMANTIC_EVIDENCE_SCHEMA_NAME:
            raise ValueError("unsupported semantic evidence schema name")
        if self.schema_version != SEMANTIC_EVIDENCE_SCHEMA_VERSION:
            raise ValueError("unsupported semantic evidence schema version")
        if self.bundle_type != SEMANTIC_BUNDLE_TYPE:
            raise ValueError("unsupported semantic evidence bundle type")
        if not isinstance(self.payload, Mapping):
            raise ValueError("payload must be a mapping")
        object.__setattr__(self, "payload", _freeze_json(self.payload))


def _freeze_json(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or type(value) in {bool, int, float, str}:
        if type(value) is float and not math.isfinite(value):
            raise ValueError("semantic evidence cannot contain non-finite numbers")
        return value
    raise ValueError("semantic evidence contains a non-JSON value")


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _structured_service_subject(event: ClassifiedJournalEvent) -> str | None:
    normalized = event.normalized_event
    for value in (normalized.unit, normalized.user_unit):
        if value is not None and value.casefold().endswith(".service"):
            return value
    return None


def _semantic_match(
    event: ClassifiedJournalEvent,
) -> tuple[SemanticFacets, str, EvidenceLevel] | None:
    normalized = event.normalized_event
    message_id = (normalized.message_id or "").casefold()
    structured_subject = _structured_service_subject(event)

    if (
        message_id == SYSTEMD_RESTART_SCHEDULED_MESSAGE_ID
        and structured_subject is not None
    ):
        return (
            SemanticFacets(
                family=SemanticFamily.SERVICE_LIFECYCLE,
                action=SemanticAction.RESTART_SCHEDULED,
                subject_unit=structured_subject,
            ),
            "semantic.systemd.restart_scheduled.message_id",
            EvidenceLevel.EXACT,
        )

    if (
        message_id == SYSTEMD_UNIT_PROCESS_EXITED_MESSAGE_ID
        and structured_subject is not None
    ):
        return (
            SemanticFacets(
                family=SemanticFamily.SERVICE_LIFECYCLE,
                action=SemanticAction.PROCESS_EXITED,
                subject_unit=structured_subject,
            ),
            "semantic.systemd.process_exited.message_id",
            EvidenceLevel.EXACT,
        )

    systemd_identifier = (normalized.syslog_identifier or "").casefold()

    if (
        message_id == SYSTEMD_START_JOB_BEGUN_MESSAGE_ID
        and systemd_identifier == "systemd"
        and structured_subject is not None
    ):
        return (
            SemanticFacets(
                family=SemanticFamily.SERVICE_LIFECYCLE,
                action=SemanticAction.START_JOB_BEGUN,
                subject_unit=structured_subject,
            ),
            "semantic.systemd.start_job_begun.message_id",
            EvidenceLevel.EXACT,
        )

    if (
        message_id == SYSTEMD_UNIT_SUCCEEDED_MESSAGE_ID
        and systemd_identifier == "systemd"
        and structured_subject is not None
    ):
        return (
            SemanticFacets(
                family=SemanticFamily.SERVICE_LIFECYCLE,
                action=SemanticAction.UNIT_SUCCEEDED,
                subject_unit=structured_subject,
            ),
            "semantic.systemd.unit_succeeded.message_id",
            EvidenceLevel.EXACT,
        )

    source_unit = normalized.systemd_unit
    transport = (normalized.transport or "").casefold()
    if (
        source_unit is not None
        and source_unit.casefold().endswith(".service")
        and transport in {"stdout", "stderr"}
    ):
        return (
            SemanticFacets(
                family=SemanticFamily.PROCESS_RUNTIME,
                action=SemanticAction.PROCESS_OUTPUT,
                subject_unit=source_unit,
                transport=transport,
            ),
            "semantic.service.process_output.transport",
            EvidenceLevel.EXACT,
        )

    return None


def iter_semantic_events(
    events: Iterable[ClassifiedJournalEvent],
) -> Iterable[SemanticJournalEvent]:
    """Yield only events carrying semantic facets, preserving source order."""

    for event in events:
        if not isinstance(event, ClassifiedJournalEvent):
            raise ValueError("events must contain ClassifiedJournalEvent instances")

        match = _semantic_match(event)
        if match is None:
            continue

        facets, rule_id, evidence = match
        normalized = event.normalized_event
        yield SemanticJournalEvent(
            sequence_index=normalized.sequence_index,
            relative_realtime_us=normalized.relative_realtime_us,
            primary_event_type=event.event_type,
            primary_symbol=EVENT_TYPE_TO_SYMBOL[event.event_type],
            source_domain=event.source_domain,
            primary_rule_id=event.rule_id,
            primary_evidence=event.evidence,
            facets=facets,
            semantic_rule_id=rule_id,
            semantic_evidence=evidence,
        )


def _event_payload(event: SemanticJournalEvent) -> dict[str, object]:
    return {
        "sequence_index": event.sequence_index,
        "relative_realtime_us": event.relative_realtime_us,
        "primary": {
            "symbol": event.primary_symbol,
            "event_type": event.primary_event_type.value,
            "source_domain": event.source_domain.value,
            "rule_id": event.primary_rule_id,
            "evidence": event.primary_evidence.value,
        },
        "semantic": {
            "family": event.facets.family.value,
            "action": event.facets.action.value,
            "subject": {
                "kind": "systemd_unit",
                "value": event.facets.subject_unit,
            },
            "transport": event.facets.transport,
            "rule_id": event.semantic_rule_id,
            "evidence": event.semantic_evidence.value,
        },
    }


def build_semantic_evidence_envelope(
    input_bytes: bytes,
    classified_events: Iterable[ClassifiedJournalEvent],
    *,
    window_id: str | None = None,
) -> SemanticEvidenceEnvelope:
    """Build semantic-evidence schema v1 without changing primary taxonomy output."""

    if not isinstance(input_bytes, bytes) or not input_bytes:
        raise ValueError("input_bytes must be non-empty bytes")
    if window_id is not None and (
        not isinstance(window_id, str)
        or not window_id
        or window_id != window_id.strip()
    ):
        raise ValueError("window_id must be non-empty canonical text or None")

    classified = tuple(classified_events)
    if not classified:
        raise ValueError("classified_events must be non-empty")

    semantic = tuple(iter_semantic_events(classified))
    semantic_count = len(semantic)
    source_count = len(classified)

    payload = {
        "provenance": {
            "project_version": __version__,
            "taxonomy_version": EVENT_TAXONOMY_VERSION,
            "semantic_facets_version": SEMANTIC_FACET_VERSION,
            "window_id": window_id,
            "input": {
                "digest_algorithm": "sha256",
                "sha256": hashlib.sha256(input_bytes).hexdigest(),
                "size_bytes": len(input_bytes),
            },
        },
        "coverage": {
            "source_event_count": source_count,
            "semantic_event_count": semantic_count,
            "semantic_event_proportion": semantic_count / source_count,
        },
        "events": [_event_payload(event) for event in semantic],
        "semantics": {
            "scope": "descriptive_semantic_evidence",
            "limitations": [
                "not_anomaly_score",
                "not_threat_score",
                "not_intrusion_verdict",
                "not_causality_claim",
                "no_automatic_action",
                "no_raw_message_export",
            ],
            "flags": {
                "contains_raw_messages": False,
                "contains_absolute_timestamps": False,
                "contains_normalized_subject_identifiers": True,
                "anomaly_score": False,
                "threat_score": False,
                "intrusion_verdict": False,
                "causality_claim": False,
                "automatic_action": False,
            },
        },
    }

    return SemanticEvidenceEnvelope(
        schema_name=SEMANTIC_EVIDENCE_SCHEMA_NAME,
        schema_version=SEMANTIC_EVIDENCE_SCHEMA_VERSION,
        bundle_type=SEMANTIC_BUNDLE_TYPE,
        payload=payload,
    )


def render_semantic_evidence_json(envelope: SemanticEvidenceEnvelope) -> str:
    """Render canonical semantic evidence JSON plus one newline."""

    if not isinstance(envelope, SemanticEvidenceEnvelope):
        raise ValueError("envelope must be a SemanticEvidenceEnvelope")

    value = {
        "schema_name": envelope.schema_name,
        "schema_version": envelope.schema_version,
        "bundle_type": envelope.bundle_type,
        "payload": _thaw_json(envelope.payload),
    }
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=False,
        )
        + "\n"
    )


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key rejected: {key}")
        result[key] = value
    return result


def _strict_object(
    name: str,
    value: object,
    keys: tuple[str, ...],
) -> dict[str, object]:
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(f"{name} must contain exactly: " + ", ".join(keys))
    return value


def _strict_text(name: str, value: object) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{name} must be non-empty canonical text")
    return value


def parse_semantic_evidence_json(data: str) -> SemanticEvidenceEnvelope:
    """Strictly parse and validate one semantic-evidence schema-v1 document."""

    if not isinstance(data, str):
        raise ValueError("semantic evidence must be text")
    try:
        root = json.loads(
            data,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"invalid JSON constant: {value}")
            ),
        )
    except json.JSONDecodeError as error:
        raise ValueError("semantic evidence is not valid JSON") from error

    root = _strict_object(
        "root",
        root,
        ("schema_name", "schema_version", "bundle_type", "payload"),
    )
    if root["schema_name"] != SEMANTIC_EVIDENCE_SCHEMA_NAME:
        raise ValueError("unsupported semantic evidence schema name")
    if root["schema_version"] != SEMANTIC_EVIDENCE_SCHEMA_VERSION:
        raise ValueError("unsupported semantic evidence schema version")
    if root["bundle_type"] != SEMANTIC_BUNDLE_TYPE:
        raise ValueError("unsupported semantic evidence bundle type")

    payload = _strict_object(
        "payload",
        root["payload"],
        ("provenance", "coverage", "events", "semantics"),
    )
    provenance = _strict_object(
        "provenance",
        payload["provenance"],
        (
            "project_version",
            "taxonomy_version",
            "semantic_facets_version",
            "window_id",
            "input",
        ),
    )
    _strict_text("provenance.project_version", provenance["project_version"])
    if provenance["taxonomy_version"] != EVENT_TAXONOMY_VERSION:
        raise ValueError("unsupported taxonomy version")
    if provenance["semantic_facets_version"] != SEMANTIC_FACET_VERSION:
        raise ValueError("unsupported semantic facets version")
    if provenance["window_id"] is not None:
        _strict_text("provenance.window_id", provenance["window_id"])

    input_info = _strict_object(
        "provenance.input",
        provenance["input"],
        ("digest_algorithm", "sha256", "size_bytes"),
    )
    if input_info["digest_algorithm"] != "sha256":
        raise ValueError("semantic input digest algorithm must be sha256")
    digest = _strict_text("provenance.input.sha256", input_info["sha256"])
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("semantic input sha256 must be lowercase hexadecimal")
    if type(input_info["size_bytes"]) is not int or input_info["size_bytes"] <= 0:
        raise ValueError("semantic input size must be positive")

    coverage = _strict_object(
        "coverage",
        payload["coverage"],
        ("source_event_count", "semantic_event_count", "semantic_event_proportion"),
    )
    source_count = coverage["source_event_count"]
    semantic_count = coverage["semantic_event_count"]
    proportion = coverage["semantic_event_proportion"]
    if type(source_count) is not int or source_count <= 0:
        raise ValueError("source_event_count must be positive")
    if type(semantic_count) is not int or not 0 <= semantic_count <= source_count:
        raise ValueError("semantic_event_count is invalid")
    if type(proportion) is not float or not math.isclose(
        proportion,
        semantic_count / source_count,
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise ValueError("semantic_event_proportion does not match counts")

    events = payload["events"]
    if type(events) is not list or len(events) != semantic_count:
        raise ValueError("events must match semantic_event_count")

    previous_index = -1
    for index, raw_event in enumerate(events):
        item = _strict_object(
            f"events[{index}]",
            raw_event,
            ("sequence_index", "relative_realtime_us", "primary", "semantic"),
        )
        sequence_index = item["sequence_index"]
        if type(sequence_index) is not int or sequence_index <= previous_index:
            raise ValueError("semantic event sequence indexes must increase")
        if sequence_index >= source_count:
            raise ValueError("semantic event sequence index exceeds source window")
        previous_index = sequence_index
        offset = item["relative_realtime_us"]
        if offset is not None and (type(offset) is not int or offset < 0):
            raise ValueError("relative_realtime_us must be non-negative or null")

        primary = _strict_object(
            f"events[{index}].primary",
            item["primary"],
            ("symbol", "event_type", "source_domain", "rule_id", "evidence"),
        )
        symbol = primary["symbol"]
        if type(symbol) is not int or symbol not in SYMBOL_TO_EVENT_TYPE:
            raise ValueError("primary symbol is unsupported")
        if primary["event_type"] != SYMBOL_TO_EVENT_TYPE[symbol].value:
            raise ValueError("primary event type does not match symbol")
        SourceDomain(_strict_text("primary.source_domain", primary["source_domain"]))
        _strict_text("primary.rule_id", primary["rule_id"])
        EvidenceLevel(_strict_text("primary.evidence", primary["evidence"]))

        semantic_item = _strict_object(
            f"events[{index}].semantic",
            item["semantic"],
            ("family", "action", "subject", "transport", "rule_id", "evidence"),
        )
        family = SemanticFamily(
            _strict_text("semantic.family", semantic_item["family"])
        )
        action = SemanticAction(
            _strict_text("semantic.action", semantic_item["action"])
        )
        subject = _strict_object(
            "semantic.subject",
            semantic_item["subject"],
            ("kind", "value"),
        )
        if subject["kind"] != "systemd_unit":
            raise ValueError("semantic subject kind must be systemd_unit")
        subject_value = _strict_text("semantic.subject.value", subject["value"])
        transport = semantic_item["transport"]
        if transport is not None:
            transport = _strict_text("semantic.transport", transport)
        SemanticFacets(
            family=family,
            action=action,
            subject_unit=subject_value,
            transport=transport,
        )
        _strict_text("semantic.rule_id", semantic_item["rule_id"])
        EvidenceLevel(_strict_text("semantic.evidence", semantic_item["evidence"]))

    semantics = _strict_object(
        "semantics",
        payload["semantics"],
        ("scope", "limitations", "flags"),
    )
    if semantics["scope"] != "descriptive_semantic_evidence":
        raise ValueError("semantic evidence scope mismatch")
    if semantics["limitations"] != [
        "not_anomaly_score",
        "not_threat_score",
        "not_intrusion_verdict",
        "not_causality_claim",
        "no_automatic_action",
        "no_raw_message_export",
    ]:
        raise ValueError("semantic evidence limitations mismatch")
    flags = _strict_object(
        "semantics.flags",
        semantics["flags"],
        (
            "contains_raw_messages",
            "contains_absolute_timestamps",
            "contains_normalized_subject_identifiers",
            "anomaly_score",
            "threat_score",
            "intrusion_verdict",
            "causality_claim",
            "automatic_action",
        ),
    )
    expected_flags = {
        "contains_raw_messages": False,
        "contains_absolute_timestamps": False,
        "contains_normalized_subject_identifiers": True,
        "anomaly_score": False,
        "threat_score": False,
        "intrusion_verdict": False,
        "causality_claim": False,
        "automatic_action": False,
    }
    if flags != expected_flags:
        raise ValueError("semantic evidence flags mismatch")

    return SemanticEvidenceEnvelope(
        schema_name=root["schema_name"],
        schema_version=root["schema_version"],
        bundle_type=root["bundle_type"],
        payload=payload,
    )
