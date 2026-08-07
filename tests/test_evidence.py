"""Contracts for versioned machine-readable evidence."""

from __future__ import annotations

import io
import json
from dataclasses import (
    FrozenInstanceError,
    fields,
    replace,
)
from math import inf, nan
from pathlib import Path

import pytest
from digit_probe import AnalysisConfig

import system_log_dynamics.evidence as evidence
from system_log_dynamics.analysis import (
    analyze_classified_events,
)
from system_log_dynamics.classification import (
    iter_classified_events,
)
from system_log_dynamics.comparison import (
    AnalysisWindow,
    NumericState,
    NumericValue,
)
from system_log_dynamics.evidence import (
    ANALYSIS_EVIDENCE_SCHEMA_NAME,
    COMPARISON_EVIDENCE_SCHEMA_NAME,
    EVIDENCE_SCHEMA_VERSION,
    EvidenceBundleType,
    EvidenceEnvelope,
    EvidenceNumber,
    build_analysis_evidence_envelope,
    build_comparison_evidence_envelope,
    build_evidence_number,
    evidence_number_from_json_object,
    evidence_number_to_json_object,
    parse_evidence_bundle_json,
    parse_evidence_envelope_json,
    render_evidence_json,
)
from system_log_dynamics.journal import (
    iter_normalized_journal_json_lines,
)
from system_log_dynamics.manifests import (
    build_analysis_manifest,
)
from system_log_dynamics.temporal import (
    summarize_temporal_bursts,
)


def _analysis_envelope() -> EvidenceEnvelope:
    return EvidenceEnvelope(
        schema_name=ANALYSIS_EVIDENCE_SCHEMA_NAME,
        schema_version=EVIDENCE_SCHEMA_VERSION,
        bundle_type=EvidenceBundleType.ANALYSIS_WINDOW,
        payload={
            "sample_size": 3,
            "available": True,
            "labels": ["one", "two"],
            "optional": None,
            "nested": {"value": 1.5},
        },
    )


FIXTURE_DIRECTORY = Path("fixtures/synthetic")
ROUTINE_PATH = FIXTURE_DIRECTORY / "experiment-001-routine.jsonl"
BURST_PATH = FIXTURE_DIRECTORY / "experiment-001-boot-error-burst.jsonl"


def _routine_window() -> AnalysisWindow:
    input_bytes = ROUTINE_PATH.read_bytes()
    config = AnalysisConfig(schur_capacity=5000)

    with io.StringIO(input_bytes.decode("utf-8")) as source:
        normalized = tuple(iter_normalized_journal_json_lines(source))

    classified = tuple(iter_classified_events(normalized))
    result = analyze_classified_events(
        classified,
        config=config,
    )

    return AnalysisWindow(
        manifest=build_analysis_manifest(
            input_bytes,
            result,
            config=config,
            window_id=("experiment-001-routine"),
        ),
        result=result,
        temporal=summarize_temporal_bursts(
            normalized,
            burst_threshold_us=100_000,
        ),
    )


def _burst_window() -> AnalysisWindow:
    input_bytes = BURST_PATH.read_bytes()
    config = AnalysisConfig(schur_capacity=5000)

    with io.StringIO(input_bytes.decode("utf-8")) as source:
        normalized = tuple(iter_normalized_journal_json_lines(source))

    classified = tuple(iter_classified_events(normalized))
    result = analyze_classified_events(
        classified,
        config=config,
    )

    return AnalysisWindow(
        manifest=build_analysis_manifest(
            input_bytes,
            result,
            config=config,
            window_id=("experiment-001-boot-error-burst"),
        ),
        result=result,
        temporal=summarize_temporal_bursts(
            normalized,
            burst_threshold_us=100_000,
        ),
    )


def test_public_contract_is_explicit() -> None:
    assert evidence.__all__ == [
        "ANALYSIS_EVIDENCE_SCHEMA_NAME",
        "COMPARISON_EVIDENCE_SCHEMA_NAME",
        "EVIDENCE_SCHEMA_VERSION",
        "EvidenceBundleType",
        "EvidenceEnvelope",
        "EvidenceNumber",
        "build_analysis_evidence_envelope",
        "build_comparison_evidence_envelope",
        "build_evidence_number",
        "evidence_number_from_json_object",
        "evidence_number_to_json_object",
        "parse_evidence_bundle_json",
        "parse_evidence_envelope_json",
        "render_evidence_json",
    ]

    assert EVIDENCE_SCHEMA_VERSION == 1
    assert ANALYSIS_EVIDENCE_SCHEMA_NAME == ("system-log-dynamics.analysis-evidence")
    assert COMPARISON_EVIDENCE_SCHEMA_NAME == (
        "system-log-dynamics.comparison-evidence"
    )

    assert list(EvidenceBundleType) == [
        EvidenceBundleType.ANALYSIS_WINDOW,
        EvidenceBundleType.WINDOW_COMPARISON,
    ]

    assert [field.name for field in fields(EvidenceNumber)] == [
        "state",
        "value",
    ]

    assert [field.name for field in fields(EvidenceEnvelope)] == [
        "schema_name",
        "schema_version",
        "bundle_type",
        "payload",
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            4,
            EvidenceNumber(NumericState.FINITE, 4),
        ),
        (
            1.25,
            EvidenceNumber(NumericState.FINITE, 1.25),
        ),
        (
            None,
            EvidenceNumber(NumericState.MISSING, None),
        ),
        (
            nan,
            EvidenceNumber(NumericState.NAN, None),
        ),
        (
            inf,
            EvidenceNumber(
                NumericState.POSITIVE_INFINITY,
                None,
            ),
        ),
        (
            -inf,
            EvidenceNumber(
                NumericState.NEGATIVE_INFINITY,
                None,
            ),
        ),
        (
            NumericValue(
                NumericState.NOT_COMPUTABLE,
                None,
            ),
            EvidenceNumber(
                NumericState.NOT_COMPUTABLE,
                None,
            ),
        ),
    ],
)
def test_evidence_numbers_cover_all_numeric_states(
    source: object,
    expected: EvidenceNumber,
) -> None:
    assert build_evidence_number(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        True,
        False,
        "1",
        object(),
        [],
        {},
    ],
)
def test_evidence_number_builder_rejects_non_numbers(
    source: object,
) -> None:
    with pytest.raises(ValueError):
        build_evidence_number(source)


@pytest.mark.parametrize(
    "state",
    [
        NumericState.MISSING,
        NumericState.NAN,
        NumericState.POSITIVE_INFINITY,
        NumericState.NEGATIVE_INFINITY,
        NumericState.NOT_COMPUTABLE,
    ],
)
def test_non_finite_states_require_null_values(
    state: NumericState,
) -> None:
    with pytest.raises(ValueError):
        EvidenceNumber(state, 1)


@pytest.mark.parametrize(
    "value",
    [
        True,
        nan,
        inf,
        -inf,
        "1",
    ],
)
def test_finite_state_requires_concrete_finite_number(
    value: object,
) -> None:
    with pytest.raises(ValueError):
        EvidenceNumber(
            NumericState.FINITE,
            value,  # type: ignore[arg-type]
        )


def test_evidence_number_json_round_trip() -> None:
    original = EvidenceNumber(
        NumericState.POSITIVE_INFINITY,
        None,
    )

    encoded = evidence_number_to_json_object(original)

    assert encoded == {
        "state": "positive_infinity",
        "value": None,
    }
    assert evidence_number_from_json_object(encoded) == original


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {"state": "finite"},
        {
            "state": "finite",
            "value": 1,
            "extra": False,
        },
        {
            "state": "unsupported",
            "value": None,
        },
        {
            "state": "finite",
            "value": True,
        },
    ],
)
def test_evidence_number_decoder_is_strict(
    value: object,
) -> None:
    with pytest.raises(ValueError):
        evidence_number_from_json_object(value)


def test_envelope_is_frozen_and_snapshots_payload() -> None:
    source = {
        "items": [1, {"nested": True}],
    }

    envelope = EvidenceEnvelope(
        schema_name=ANALYSIS_EVIDENCE_SCHEMA_NAME,
        schema_version=1,
        bundle_type=(EvidenceBundleType.ANALYSIS_WINDOW),
        payload=source,
    )

    source["items"].append(2)

    assert envelope.payload == {
        "items": (
            1,
            {"nested": True},
        )
    }

    with pytest.raises(FrozenInstanceError):
        envelope.schema_version = 2  # type: ignore[misc]

    with pytest.raises(TypeError):
        envelope.payload["new"] = 1  # type: ignore[index]


@pytest.mark.parametrize(
    ("schema_name", "schema_version", "bundle_type"),
    [
        (
            COMPARISON_EVIDENCE_SCHEMA_NAME,
            1,
            EvidenceBundleType.ANALYSIS_WINDOW,
        ),
        (
            ANALYSIS_EVIDENCE_SCHEMA_NAME,
            1,
            EvidenceBundleType.WINDOW_COMPARISON,
        ),
        (
            ANALYSIS_EVIDENCE_SCHEMA_NAME,
            2,
            EvidenceBundleType.ANALYSIS_WINDOW,
        ),
        (
            "",
            1,
            EvidenceBundleType.ANALYSIS_WINDOW,
        ),
    ],
)
def test_envelope_rejects_incompatible_identity(
    schema_name: str,
    schema_version: int,
    bundle_type: EvidenceBundleType,
) -> None:
    with pytest.raises(ValueError):
        EvidenceEnvelope(
            schema_name=schema_name,
            schema_version=schema_version,
            bundle_type=bundle_type,
            payload={},
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"value": nan},
        {"value": inf},
        {"value": -inf},
        {1: "invalid key"},
        {"value": object()},
        {"value": {1, 2}},
    ],
)
def test_envelope_rejects_non_json_payloads(
    payload: object,
) -> None:
    with pytest.raises(ValueError):
        EvidenceEnvelope(
            schema_name=ANALYSIS_EVIDENCE_SCHEMA_NAME,
            schema_version=1,
            bundle_type=(EvidenceBundleType.ANALYSIS_WINDOW),
            payload=payload,  # type: ignore[arg-type]
        )


def test_canonical_json_is_byte_stable() -> None:
    envelope = _analysis_envelope()

    expected = (
        '{"schema_name":'
        '"system-log-dynamics.analysis-evidence",'
        '"schema_version":1,'
        '"bundle_type":"analysis_window",'
        '"payload":{"sample_size":3,'
        '"available":true,'
        '"labels":["one","two"],'
        '"optional":null,'
        '"nested":{"value":1.5}}}\n'
    )

    assert render_evidence_json(envelope) == expected
    assert render_evidence_json(envelope) == (render_evidence_json(envelope))
    assert render_evidence_json(envelope).encode("utf-8") == expected.encode("utf-8")


def test_envelope_json_round_trip() -> None:
    original = _analysis_envelope()
    rendered = render_evidence_json(original)

    assert parse_evidence_envelope_json(rendered) == original

    assert parse_evidence_envelope_json(rendered.encode("utf-8")) == original


@pytest.mark.parametrize(
    "source",
    [
        "[]",
        "null",
        '{"schema_name":"x"}',
        (
            '{"schema_name":'
            '"system-log-dynamics.analysis-evidence",'
            '"schema_version":2,'
            '"bundle_type":"analysis_window",'
            '"payload":{}}'
        ),
        (
            '{"schema_name":'
            '"system-log-dynamics.analysis-evidence",'
            '"schema_version":1,'
            '"bundle_type":"unsupported",'
            '"payload":{}}'
        ),
        (
            '{"schema_name":'
            '"system-log-dynamics.analysis-evidence",'
            '"schema_version":1,'
            '"bundle_type":"analysis_window",'
            '"payload":{},'
            '"extra":true}'
        ),
        (
            '{"schema_name":'
            '"system-log-dynamics.analysis-evidence",'
            '"schema_version":1,'
            '"bundle_type":"analysis_window",'
            '"payload":{"value":NaN}}'
        ),
        (
            '{"schema_name":'
            '"system-log-dynamics.analysis-evidence",'
            '"schema_version":1,'
            '"bundle_type":"analysis_window",'
            '"payload":{},'
            '"payload":{}}'
        ),
    ],
)
def test_envelope_parser_rejects_incompatible_json(
    source: str,
) -> None:
    with pytest.raises(ValueError):
        parse_evidence_envelope_json(source)


def test_envelope_parser_rejects_invalid_utf8() -> None:
    with pytest.raises(ValueError):
        parse_evidence_envelope_json(b"\xff")


def test_envelope_parser_rejects_non_text_sources() -> None:
    with pytest.raises(ValueError):
        parse_evidence_envelope_json(
            object(),  # type: ignore[arg-type]
        )


def test_analysis_bundle_has_canonical_top_level_shape() -> None:
    envelope = build_analysis_evidence_envelope(_routine_window())

    assert envelope.schema_name == (ANALYSIS_EVIDENCE_SCHEMA_NAME)
    assert envelope.schema_version == 1
    assert envelope.bundle_type is (EvidenceBundleType.ANALYSIS_WINDOW)

    assert tuple(envelope.payload) == (
        "provenance",
        "analysis",
        "semantics",
    )

    assert tuple(envelope.payload["provenance"]) == (
        "project_version",
        "digit_probe_commit",
        "manifest_schema_version",
        "taxonomy_version",
        "window_id",
        "input",
        "analysis_configuration",
    )

    assert tuple(envelope.payload["analysis"]) == (
        "mode",
        "sample_size",
        "alphabet_size",
        "max_observed_symbol",
        "category_distribution",
        "taxonomy_coverage",
        "statistics",
        "temporal",
    )


def test_analysis_bundle_carries_exact_provenance() -> None:
    envelope = build_analysis_evidence_envelope(_routine_window())
    provenance = envelope.payload["provenance"]

    assert provenance["project_version"] == ("0.1.0")
    assert provenance["digit_probe_commit"] == (
        "55e3eae4c55017703e023c1aaac0838b873482db"
    )
    assert provenance["manifest_schema_version"] == 1
    assert provenance["taxonomy_version"] == "1"
    assert provenance["window_id"] == ("experiment-001-routine")

    assert provenance["input"] == {
        "digest_algorithm": "sha256",
        "sha256": ("ee096cc33749b9d7d9dfd9ba69aa5c6fd582f433ec9cbaf5857a5335c7a5a3ee"),
        "size_bytes": 4969,
    }

    assert provenance["analysis_configuration"] == {
        "schur_capacity": 5000,
        "burst_threshold_us": 100000,
    }


def test_analysis_bundle_has_complete_distribution() -> None:
    envelope = build_analysis_evidence_envelope(_routine_window())
    analysis = envelope.payload["analysis"]
    distribution = analysis["category_distribution"]

    assert analysis["sample_size"] == 24
    assert analysis["alphabet_size"] == 9
    assert analysis["max_observed_symbol"] == 8

    assert [item["symbol"] for item in distribution] == list(range(9))

    assert [item["event_type"] for item in distribution] == [
        "boot_boundary",
        "service_started",
        "service_stopped",
        "authentication_success",
        "authentication_failure",
        "session_boundary",
        "warning",
        "error",
        "other",
    ]

    assert [item["count"] for item in distribution] == [
        0,
        5,
        4,
        2,
        0,
        2,
        2,
        0,
        9,
    ]

    assert sum(item["proportion"] for item in distribution) == pytest.approx(1.0)


def test_analysis_bundle_carries_taxonomy_coverage() -> None:
    envelope = build_analysis_evidence_envelope(_routine_window())
    coverage = envelope.payload["analysis"]["taxonomy_coverage"]

    assert coverage == {
        "status": "mixed",
        "sample_size": 24,
        "named_event_count": 15,
        "named_event_proportion": 0.625,
        "other_event_count": 9,
        "other_event_proportion": 0.375,
        "represented_named_symbols": (
            1,
            2,
            3,
            5,
            6,
        ),
        "absent_named_symbols": (
            0,
            4,
            7,
        ),
        "represented_named_event_types": (
            "service_started",
            "service_stopped",
            "authentication_success",
            "session_boundary",
            "warning",
        ),
        "absent_named_event_types": (
            "boot_boundary",
            "authentication_failure",
            "error",
        ),
    }


def test_analysis_bundle_represents_infinite_gaps_explicitly() -> None:
    envelope = build_analysis_evidence_envelope(_routine_window())
    gaps = envelope.payload["analysis"]["statistics"]["gaps"]

    assert gaps[0] == {
        "symbol": 0,
        "event_type": "boot_boundary",
        "count": 0,
        "mean": {
            "state": "positive_infinity",
            "value": None,
        },
    }

    assert gaps[4]["mean"] == {
        "state": "positive_infinity",
        "value": None,
    }
    assert gaps[7]["mean"] == {
        "state": "positive_infinity",
        "value": None,
    }

    assert gaps[1]["mean"] == {
        "state": "finite",
        "value": 5.25,
    }


def test_analysis_bundle_serializes_complete_schur_result() -> None:
    envelope = build_analysis_evidence_envelope(_routine_window())
    schur = envelope.payload["analysis"]["statistics"]["schur"]

    assert schur == {
        "triples": 276,
        "count": 22,
        "expected": {
            "state": "finite",
            "value": 30.666666666666664,
        },
        "fraction": {
            "state": "finite",
            "value": 0.07971014492753623,
        },
        "z_score": {
            "state": "finite",
            "value": -1.6599502349795594,
        },
        "first_matching_relation_index": {
            "state": "finite",
            "value": 12,
        },
    }


def test_analysis_bundle_carries_temporal_summary() -> None:
    envelope = build_analysis_evidence_envelope(_routine_window())
    temporal = envelope.payload["analysis"]["temporal"]

    assert temporal == {
        "event_count": 24,
        "timed_event_count": 24,
        "untimed_event_count": 0,
        "duration_us": {
            "state": "finite",
            "value": 299000000,
        },
        "inter_event_gap_count": 23,
        "minimum_gap_us": {
            "state": "finite",
            "value": 2000000,
        },
        "maximum_gap_us": {
            "state": "finite",
            "value": 24000000,
        },
        "mean_gap_us": {
            "state": "finite",
            "value": 13000000.0,
        },
        "median_gap_us": {
            "state": "finite",
            "value": 13000000.0,
        },
        "burst_threshold_us": 100000,
        "burst_count": 0,
        "burst_event_count": 0,
        "largest_burst_size": 0,
        "longest_burst_duration_us": 0,
    }


def test_analysis_bundle_has_machine_readable_limitations() -> None:
    envelope = build_analysis_evidence_envelope(_routine_window())
    semantics = envelope.payload["semantics"]

    assert semantics["scope"] == ("descriptive_evidence")
    assert semantics["limitations"] == (
        "descriptive_evidence_only",
        "representation_dependent",
        "not_anomaly_score",
        "not_threat_score",
        "not_intrusion_verdict",
        "not_confidence_estimate",
        "no_automatic_action",
        "no_raw_event_export",
    )

    assert semantics["flags"] == {
        "contains_raw_events": False,
        "contains_raw_messages": False,
        "contains_input_path": False,
        "anomaly_score": False,
        "threat_score": False,
        "intrusion_verdict": False,
        "confidence_estimate": False,
        "automatic_action": False,
    }


def test_analysis_json_is_deterministic_and_standard() -> None:
    window = _routine_window()

    first = render_evidence_json(build_analysis_evidence_envelope(window))
    second = render_evidence_json(build_analysis_evidence_envelope(window))

    assert first == second
    assert first.endswith("\n")
    assert not first.endswith("\n\n")

    assert "NaN" not in first
    assert "Infinity" not in first

    parsed = parse_evidence_envelope_json(first)

    assert parsed == (build_analysis_evidence_envelope(window))


def test_analysis_bundle_excludes_private_source_material() -> None:
    rendered = render_evidence_json(build_analysis_evidence_envelope(_routine_window()))

    forbidden = (
        str(ROUTINE_PATH),
        "/home/",
        "MESSAGE",
        "__REALTIME_TIMESTAMP",
        "_BOOT_ID",
        "Synthetic",
        "password",
        "publickey",
    )

    for fragment in forbidden:
        assert fragment not in rendered


def test_analysis_builder_revalidates_window() -> None:
    window = _routine_window()

    object.__setattr__(
        window.manifest,
        "sample_size",
        999,
    )

    with pytest.raises(ValueError):
        build_analysis_evidence_envelope(window)


def test_comparison_bundle_has_canonical_shape() -> None:
    envelope = build_comparison_evidence_envelope(
        _routine_window(),
        _burst_window(),
    )

    assert envelope.schema_name == (COMPARISON_EVIDENCE_SCHEMA_NAME)
    assert envelope.schema_version == 1
    assert envelope.bundle_type is (EvidenceBundleType.WINDOW_COMPARISON)

    assert tuple(envelope.payload) == (
        "left",
        "right",
        "comparison",
        "semantics",
    )

    comparison = envelope.payload["comparison"]

    assert comparison["direction"] == ("right_minus_left")
    assert comparison["left_window_id"] == ("experiment-001-routine")
    assert comparison["right_window_id"] == ("experiment-001-boot-error-burst")


def test_comparison_bundle_embeds_both_windows() -> None:
    left = _routine_window()
    right = _burst_window()

    envelope = build_comparison_evidence_envelope(
        left,
        right,
    )

    left_analysis = build_analysis_evidence_envelope(left)
    right_analysis = build_analysis_evidence_envelope(right)

    assert envelope.payload["left"] == {
        "provenance": (left_analysis.payload["provenance"]),
        "analysis": left_analysis.payload["analysis"],
    }

    assert envelope.payload["right"] == {
        "provenance": (right_analysis.payload["provenance"]),
        "analysis": right_analysis.payload["analysis"],
    }


def test_comparison_bundle_carries_coverage_delta() -> None:
    envelope = build_comparison_evidence_envelope(
        _routine_window(),
        _burst_window(),
    )

    coverage = envelope.payload["comparison"]["taxonomy_coverage"]

    assert coverage["named_event_count_delta"] == 5
    assert coverage["other_event_count_delta"] == -5
    assert coverage["represented_named_category_count_delta"] == 2

    assert coverage["newly_represented_named_symbols"] == (0, 4, 7)

    assert coverage["newly_absent_named_symbols"] == (3,)

    assert coverage["newly_represented_named_event_types"] == (
        "boot_boundary",
        "authentication_failure",
        "error",
    )

    assert coverage["newly_absent_named_event_types"] == ("authentication_success",)


def test_comparison_distribution_is_complete() -> None:
    envelope = build_comparison_evidence_envelope(
        _routine_window(),
        _burst_window(),
    )

    distribution = envelope.payload["comparison"]["category_distribution"]

    assert [item["symbol"] for item in distribution] == list(range(9))

    for item in distribution:
        assert tuple(item) == (
            "symbol",
            "event_type",
            "count",
            "proportion",
        )

        assert tuple(item["count"]) == (
            "left",
            "right",
            "delta",
        )
        assert tuple(item["proportion"]) == (
            "left",
            "right",
            "delta",
        )


def test_comparison_bundle_carries_compatibility() -> None:
    envelope = build_comparison_evidence_envelope(
        _routine_window(),
        _burst_window(),
    )

    compatibility = envelope.payload["comparison"]["compatibility"]

    assert compatibility["manifest_schema_version"] == 1
    assert compatibility["taxonomy_version"] == "1"
    assert compatibility["alphabet_size"] == 9
    assert compatibility["input_digest_algorithm"] == "sha256"

    assert compatibility["analysis_configuration"] == {
        "schur_capacity": 5000,
        "burst_threshold_us": 100000,
    }

    assert compatibility["matches"]["project_version"] is True

    assert compatibility["matches"]["window_id"] is False

    assert compatibility["matches"]["input_digest"] is False


def test_comparison_represents_not_computable_explicitly() -> None:
    envelope = build_comparison_evidence_envelope(
        _routine_window(),
        _burst_window(),
    )

    rendered = render_evidence_json(envelope)

    assert '"state":"not_computable","value":null' in rendered

    gaps = envelope.payload["comparison"]["statistics"]["gaps"]

    assert any(item["mean"]["delta"]["state"] == "not_computable" for item in gaps)


def test_comparison_temporal_has_all_differences() -> None:
    envelope = build_comparison_evidence_envelope(
        _routine_window(),
        _burst_window(),
    )

    temporal = envelope.payload["comparison"]["temporal"]

    assert tuple(temporal) == (
        "event_count",
        "timed_event_count",
        "untimed_event_count",
        "duration_us",
        "inter_event_gap_count",
        "minimum_gap_us",
        "maximum_gap_us",
        "mean_gap_us",
        "median_gap_us",
        "burst_count",
        "burst_event_count",
        "largest_burst_size",
        "longest_burst_duration_us",
    )

    for difference in temporal.values():
        assert tuple(difference) == (
            "left",
            "right",
            "delta",
        )


def test_comparison_json_is_deterministic_and_round_trips() -> None:
    left = _routine_window()
    right = _burst_window()

    first = render_evidence_json(
        build_comparison_evidence_envelope(
            left,
            right,
        )
    )
    second = render_evidence_json(
        build_comparison_evidence_envelope(
            left,
            right,
        )
    )

    assert first == second
    assert first.endswith("\n")
    assert not first.endswith("\n\n")

    assert ":NaN" not in first
    assert ":Infinity" not in first
    assert ":-Infinity" not in first

    parsed = parse_evidence_envelope_json(first)

    assert parsed == (
        build_comparison_evidence_envelope(
            left,
            right,
        )
    )


def test_comparison_bundle_excludes_private_material() -> None:
    rendered = render_evidence_json(
        build_comparison_evidence_envelope(
            _routine_window(),
            _burst_window(),
        )
    )

    for forbidden in (
        str(ROUTINE_PATH),
        str(BURST_PATH),
        "/home/",
        '"MESSAGE"',
        "__REALTIME_TIMESTAMP",
        "_BOOT_ID",
        "password",
        "publickey",
    ):
        assert forbidden not in rendered


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (object(), None),
        (None, object()),
    ],
)
def test_comparison_builder_rejects_invalid_windows(
    left: object,
    right: object,
) -> None:
    valid_left = _routine_window()
    valid_right = _burst_window()

    candidate_left = valid_left if left is None else left
    candidate_right = valid_right if right is None else right

    with pytest.raises(ValueError):
        build_comparison_evidence_envelope(
            candidate_left,  # type: ignore[arg-type]
            candidate_right,  # type: ignore[arg-type]
        )


def test_envelope_revalidates_after_replace() -> None:
    envelope = _analysis_envelope()

    with pytest.raises(ValueError):
        replace(
            envelope,
            schema_version=2,
        )


def _golden_document(
    name: str,
) -> dict[str, object]:
    path = Path("fixtures/reports") / name

    return json.loads(path.read_text(encoding="utf-8"))


def _strict_json(
    document: dict[str, object],
) -> str:
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        + "\n"
    )


@pytest.mark.parametrize(
    "name",
    [
        "experiment-001-routine.evidence.json",
        "experiment-001-comparison.evidence.json",
    ],
)
def test_strict_bundle_parser_accepts_golden_v1(
    name: str,
) -> None:
    path = Path("fixtures/reports") / name

    envelope = parse_evidence_bundle_json(path.read_bytes())

    assert envelope.schema_version == 1


def test_strict_analysis_rejects_unknown_payload_field() -> None:
    document = _golden_document("experiment-001-routine.evidence.json")

    payload = document["payload"]
    assert type(payload) is dict

    payload["unexpected"] = True

    with pytest.raises(
        ValueError,
        match="must contain exactly",
    ):
        parse_evidence_bundle_json(_strict_json(document))


def test_strict_analysis_rejects_unknown_nested_field() -> None:
    document = _golden_document("experiment-001-routine.evidence.json")

    analysis = document["payload"]["analysis"]
    assert type(analysis) is dict

    temporal = analysis["temporal"]
    assert type(temporal) is dict

    temporal["interpretation"] = "anomaly"

    with pytest.raises(
        ValueError,
        match="must contain exactly",
    ):
        parse_evidence_bundle_json(_strict_json(document))


def test_strict_analysis_rejects_taxonomy_symbol_mismatch() -> None:
    document = _golden_document("experiment-001-routine.evidence.json")

    distribution = document["payload"]["analysis"]["category_distribution"]

    assert type(distribution) is list
    assert type(distribution[0]) is dict

    distribution[0]["event_type"] = "other"

    with pytest.raises(
        ValueError,
        match="does not match symbol",
    ):
        parse_evidence_bundle_json(_strict_json(document))


def test_strict_analysis_rejects_count_proportion_mismatch() -> None:
    document = _golden_document("experiment-001-routine.evidence.json")

    distribution = document["payload"]["analysis"]["category_distribution"]

    assert type(distribution) is list
    assert type(distribution[1]) is dict

    distribution[1]["proportion"] = 0.5

    with pytest.raises(
        ValueError,
        match="does not match count",
    ):
        parse_evidence_bundle_json(_strict_json(document))


def test_strict_analysis_rejects_invalid_numeric_state() -> None:
    document = _golden_document("experiment-001-routine.evidence.json")

    statistics = document["payload"]["analysis"]["statistics"]

    assert type(statistics) is dict

    statistics["chi_square"] = {
        "state": "unknown",
        "value": None,
    }

    with pytest.raises(
        ValueError,
        match="valid evidence number",
    ):
        parse_evidence_bundle_json(_strict_json(document))


def test_strict_analysis_rejects_security_semantic_flip() -> None:
    document = _golden_document("experiment-001-routine.evidence.json")

    flags = document["payload"]["semantics"]["flags"]

    assert type(flags) is dict
    flags["intrusion_verdict"] = True

    with pytest.raises(
        ValueError,
        match="must all be false",
    ):
        parse_evidence_bundle_json(_strict_json(document))


def test_strict_comparison_rejects_wrong_direction() -> None:
    document = _golden_document("experiment-001-comparison.evidence.json")

    comparison = document["payload"]["comparison"]

    assert type(comparison) is dict
    comparison["direction"] = "left_minus_right"

    with pytest.raises(
        ValueError,
        match="right_minus_left",
    ):
        parse_evidence_bundle_json(_strict_json(document))


def test_strict_comparison_rejects_unknown_difference_field() -> None:
    document = _golden_document("experiment-001-comparison.evidence.json")

    distribution = document["payload"]["comparison"]["category_distribution"]

    assert type(distribution) is list
    assert type(distribution[0]) is dict

    count = distribution[0]["count"]
    assert type(count) is dict

    count["interpretation"] = "increase"

    with pytest.raises(
        ValueError,
        match="must contain exactly",
    ):
        parse_evidence_bundle_json(_strict_json(document))


def test_strict_comparison_rejects_snapshot_window_mismatch() -> None:
    document = _golden_document("experiment-001-comparison.evidence.json")

    comparison = document["payload"]["comparison"]

    assert type(comparison) is dict
    comparison["left_window_id"] = "wrong-window"

    with pytest.raises(
        ValueError,
        match="window id mismatch",
    ):
        parse_evidence_bundle_json(_strict_json(document))


def test_envelope_parser_remains_envelope_only() -> None:
    document = _golden_document("experiment-001-routine.evidence.json")

    payload = document["payload"]
    assert type(payload) is dict

    payload["future_payload_field"] = True

    envelope = parse_evidence_envelope_json(_strict_json(document))

    assert envelope.payload["future_payload_field"] is True

    with pytest.raises(ValueError):
        parse_evidence_bundle_json(_strict_json(document))
