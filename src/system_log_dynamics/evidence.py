"""Versioned deterministic machine-readable evidence foundations."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from math import isfinite, isnan
from types import MappingProxyType
from typing import Final

from system_log_dynamics.comparison import (
    AnalysisWindow,
    NumericDifference,
    NumericState,
    NumericValue,
    WindowComparison,
    compare_analysis_windows,
)
from system_log_dynamics.coverage import (
    build_taxonomy_coverage,
    compare_taxonomy_coverage,
)
from system_log_dynamics.encoding import (
    EVENT_ALPHABET_SIZE,
    EVENT_TAXONOMY_VERSION,
    SYMBOL_TO_EVENT_TYPE,
)

__all__ = [
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

ANALYSIS_EVIDENCE_SCHEMA_NAME: Final = "system-log-dynamics.analysis-evidence"
COMPARISON_EVIDENCE_SCHEMA_NAME: Final = "system-log-dynamics.comparison-evidence"
EVIDENCE_SCHEMA_VERSION: Final = 1
_EVIDENCE_FLOAT_SIGNIFICANT_DIGITS: Final = 14
_EVIDENCE_FLOAT_COMPARISON_ABS_TOLERANCE: Final = 5e-14


class EvidenceBundleType(StrEnum):
    """The two explicitly versioned evidence document kinds."""

    ANALYSIS_WINDOW = "analysis_window"
    WINDOW_COMPARISON = "window_comparison"


_SCHEMA_NAMES: Final = MappingProxyType(
    {
        EvidenceBundleType.ANALYSIS_WINDOW: (ANALYSIS_EVIDENCE_SCHEMA_NAME),
        EvidenceBundleType.WINDOW_COMPARISON: (COMPARISON_EVIDENCE_SCHEMA_NAME),
    }
)


def _require_concrete_integer(
    name: str,
    value: object,
) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be a concrete non-boolean integer")

    return value


def _require_finite_number(
    name: str,
    value: object,
) -> int | float:
    if type(value) not in (int, float):
        raise ValueError(f"{name} must be a concrete non-boolean number")

    if type(value) is float and not isfinite(value):
        raise ValueError(f"{name} must be finite")

    return value


def _require_non_empty_text(
    name: str,
    value: object,
) -> str:
    if (
        not isinstance(value, str)
        or not value
        or not value.strip()
        or value != value.strip()
    ):
        raise ValueError(
            f"{name} must be non-empty text without surrounding whitespace"
        )

    return value


def _freeze_json_value(
    value: object,
    *,
    location: str,
) -> object:
    if value is None or type(value) is bool:
        return value

    if type(value) is int:
        return value

    if type(value) is float:
        if not isfinite(value):
            raise ValueError(f"{location} must not contain non-finite JSON numbers")

        return value

    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        copied: dict[str, object] = {}

        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{location} object keys must be strings")

            copied[key] = _freeze_json_value(
                item,
                location=f"{location}.{key}",
            )

        return MappingProxyType(copied)

    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_json_value(
                item,
                location=f"{location}[{index}]",
            )
            for index, item in enumerate(value)
        )

    raise ValueError(f"{location} contains a value that is not JSON-compatible")


def _thaw_json_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw_json_value(item) for key, item in value.items()}

    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]

    return value


def _canonicalize_serialized_floats(
    value: object,
) -> object:
    if isinstance(value, Mapping):
        return {
            key: _canonicalize_serialized_floats(item) for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_canonicalize_serialized_floats(item) for item in value]

    if type(value) is float:
        if not isfinite(value):
            raise ValueError("serialized evidence floats must be finite")

        canonical = float(
            format(
                value,
                (f".{_EVIDENCE_FLOAT_SIGNIFICANT_DIGITS}g"),
            )
        )

        if canonical == 0.0:
            return 0.0

        return canonical

    return value


@dataclass(frozen=True, slots=True)
class EvidenceNumber:
    """A JSON-safe explicit representation of one numeric value."""

    state: NumericState
    value: int | float | None

    def __post_init__(self) -> None:
        if not isinstance(self.state, NumericState):
            raise ValueError("state must be a NumericState")

        if self.state is NumericState.FINITE:
            _require_finite_number("value", self.value)
        elif self.value is not None:
            raise ValueError("non-finite evidence numbers must have a null value")


def build_evidence_number(
    value: object,
) -> EvidenceNumber:
    """Convert one domain numeric value to its evidence form."""

    if isinstance(value, EvidenceNumber):
        return value

    if isinstance(value, NumericValue):
        return EvidenceNumber(
            state=value.state,
            value=value.value,
        )

    if value is None:
        return EvidenceNumber(
            state=NumericState.MISSING,
            value=None,
        )

    if type(value) is int:
        return EvidenceNumber(
            state=NumericState.FINITE,
            value=value,
        )

    if type(value) is not float:
        raise ValueError(
            "evidence numbers require a concrete "
            "non-boolean integer, float, null, NumericValue, "
            "or EvidenceNumber"
        )

    if isnan(value):
        state = NumericState.NAN
        numeric_value = None
    elif value == float("inf"):
        state = NumericState.POSITIVE_INFINITY
        numeric_value = None
    elif value == float("-inf"):
        state = NumericState.NEGATIVE_INFINITY
        numeric_value = None
    else:
        state = NumericState.FINITE
        numeric_value = value

    return EvidenceNumber(
        state=state,
        value=numeric_value,
    )


def evidence_number_to_json_object(
    number: EvidenceNumber,
) -> dict[str, object]:
    """Return the stable two-field JSON representation."""

    if not isinstance(number, EvidenceNumber):
        raise ValueError("number must be an EvidenceNumber")

    return {
        "state": number.state.value,
        "value": number.value,
    }


def evidence_number_from_json_object(
    value: object,
) -> EvidenceNumber:
    """Validate and decode one evidence-number JSON object."""

    if not isinstance(value, Mapping):
        raise ValueError("evidence number must be a JSON object")

    if set(value) != {"state", "value"}:
        raise ValueError("evidence number fields must be exactly 'state' and 'value'")

    state_value = value["state"]

    if not isinstance(state_value, str):
        raise ValueError("evidence number state must be text")

    try:
        state = NumericState(state_value)
    except ValueError as error:
        raise ValueError("evidence number state is unsupported") from error

    return EvidenceNumber(
        state=state,
        value=value["value"],
    )


@dataclass(frozen=True, slots=True)
class EvidenceEnvelope:
    """Immutable versioned envelope around one evidence payload."""

    schema_name: str
    schema_version: int
    bundle_type: EvidenceBundleType
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        schema_name = _require_non_empty_text(
            "schema_name",
            self.schema_name,
        )
        schema_version = _require_concrete_integer(
            "schema_version",
            self.schema_version,
        )

        if not isinstance(
            self.bundle_type,
            EvidenceBundleType,
        ):
            raise ValueError("bundle_type must be an EvidenceBundleType")

        if schema_version != EVIDENCE_SCHEMA_VERSION:
            raise ValueError("schema_version is unsupported")

        expected_schema_name = _SCHEMA_NAMES[self.bundle_type]

        if schema_name != expected_schema_name:
            raise ValueError("schema_name does not match bundle_type")

        if not isinstance(self.payload, Mapping):
            raise ValueError("payload must be a mapping")

        frozen_payload = _freeze_json_value(
            self.payload,
            location="payload",
        )

        assert isinstance(frozen_payload, Mapping)

        object.__setattr__(
            self,
            "payload",
            frozen_payload,
        )


_SEMANTIC_LIMITATIONS: Final = (
    "descriptive_evidence_only",
    "representation_dependent",
    "not_anomaly_score",
    "not_threat_score",
    "not_intrusion_verdict",
    "not_confidence_estimate",
    "no_automatic_action",
    "no_raw_event_export",
)


def _number_json(
    value: object,
) -> dict[str, object]:
    return evidence_number_to_json_object(build_evidence_number(value))


def _analysis_manifest_payload(
    window: AnalysisWindow,
) -> dict[str, object]:
    manifest = window.manifest

    return {
        "project_version": manifest.project_version,
        "digit_probe_commit": manifest.digit_probe_commit,
        "manifest_schema_version": manifest.schema_version,
        "taxonomy_version": manifest.taxonomy_version,
        "window_id": manifest.window_id,
        "input": {
            "digest_algorithm": (manifest.input_digest_algorithm),
            "sha256": manifest.input_sha256,
            "size_bytes": manifest.input_size_bytes,
        },
        "analysis_configuration": {
            "schur_capacity": (manifest.analysis_config.schur_capacity),
            "burst_threshold_us": (window.temporal.burst_threshold_us),
        },
    }


def _category_distribution_payload(
    window: AnalysisWindow,
) -> list[dict[str, object]]:
    result = window.result

    return [
        {
            "symbol": symbol,
            "event_type": (SYMBOL_TO_EVENT_TYPE[symbol].value),
            "count": result.counts[symbol],
            "proportion": (result.counts[symbol] / result.sample_size),
            "z_score": _number_json(result.zscores[symbol]),
        }
        for symbol in sorted(result.counts)
    ]


def _coverage_payload(
    window: AnalysisWindow,
) -> dict[str, object]:
    coverage = build_taxonomy_coverage(window.result)

    return {
        "status": coverage.status.value,
        "sample_size": coverage.sample_size,
        "named_event_count": (coverage.named_event_count),
        "named_event_proportion": (coverage.named_event_proportion),
        "other_event_count": (coverage.other_event_count),
        "other_event_proportion": (coverage.other_event_proportion),
        "represented_named_symbols": list(coverage.represented_named_symbols),
        "absent_named_symbols": list(coverage.absent_named_symbols),
        "represented_named_event_types": [
            SYMBOL_TO_EVENT_TYPE[symbol].value
            for symbol in coverage.represented_named_symbols
        ],
        "absent_named_event_types": [
            SYMBOL_TO_EVENT_TYPE[symbol].value
            for symbol in coverage.absent_named_symbols
        ],
    }


def _statistics_payload(
    window: AnalysisWindow,
) -> dict[str, object]:
    result = window.result

    return {
        "chi_square": _number_json(result.chi_square),
        "expected_per_bin": _number_json(result.expected_per_bin),
        "runs": {
            "z_score": _number_json(result.runs.z_score),
            "p_two_tailed": _number_json(result.runs.p_two_tailed),
        },
        "gaps": [
            {
                "symbol": symbol,
                "event_type": (SYMBOL_TO_EVENT_TYPE[symbol].value),
                "count": result.gaps[symbol].count,
                "mean": _number_json(result.gaps[symbol].mean),
            }
            for symbol in sorted(result.gaps)
        ],
        "autocorrelation": [
            {
                "lag": lag,
                "value": _number_json(result.autocorr[lag]),
            }
            for lag in sorted(result.autocorr)
        ],
        "compression_ratio": _number_json(result.compress_ratio),
        "ngram_accuracy": [
            {
                "order": order,
                "value": _number_json(result.ngram_accuracy[order]),
            }
            for order in sorted(result.ngram_accuracy)
        ],
        "schur": {
            "triples": result.schur.triples,
            "count": result.schur.count,
            "expected": _number_json(result.schur.expected),
            "fraction": _number_json(result.schur.fraction),
            "z_score": _number_json(result.schur.z_score),
            "first_matching_relation_index": (
                _number_json(result.schur.first_matching_relation_index)
            ),
        },
    }


def _temporal_payload(
    window: AnalysisWindow,
) -> dict[str, object]:
    temporal = window.temporal

    return {
        "event_count": temporal.event_count,
        "timed_event_count": (temporal.timed_event_count),
        "untimed_event_count": (temporal.untimed_event_count),
        "duration_us": _number_json(temporal.duration_us),
        "inter_event_gap_count": (temporal.inter_event_gap_count),
        "minimum_gap_us": _number_json(temporal.minimum_gap_us),
        "maximum_gap_us": _number_json(temporal.maximum_gap_us),
        "mean_gap_us": _number_json(temporal.mean_gap_us),
        "median_gap_us": _number_json(temporal.median_gap_us),
        "burst_threshold_us": (temporal.burst_threshold_us),
        "burst_count": temporal.burst_count,
        "burst_event_count": (temporal.burst_event_count),
        "largest_burst_size": (temporal.largest_burst_size),
        "longest_burst_duration_us": (temporal.longest_burst_duration_us),
    }


def _semantic_payload() -> dict[str, object]:
    return {
        "scope": "descriptive_evidence",
        "limitations": list(_SEMANTIC_LIMITATIONS),
        "flags": {
            "contains_raw_events": False,
            "contains_raw_messages": False,
            "contains_input_path": False,
            "anomaly_score": False,
            "threat_score": False,
            "intrusion_verdict": False,
            "confidence_estimate": False,
            "automatic_action": False,
        },
    }


def build_analysis_evidence_envelope(
    window: AnalysisWindow,
) -> EvidenceEnvelope:
    """Build version-1 evidence for one validated window."""

    if not isinstance(window, AnalysisWindow):
        raise ValueError("window must be an AnalysisWindow")

    try:
        validated = replace(window)
    except (TypeError, ValueError) as error:
        raise ValueError("window must satisfy AnalysisWindow invariants") from error

    result = validated.result

    payload = {
        "provenance": _analysis_manifest_payload(validated),
        "analysis": {
            "mode": result.mode,
            "sample_size": result.sample_size,
            "alphabet_size": result.alphabet,
            "max_observed_symbol": (result.max_observed),
            "category_distribution": (_category_distribution_payload(validated)),
            "taxonomy_coverage": (_coverage_payload(validated)),
            "statistics": (_statistics_payload(validated)),
            "temporal": (_temporal_payload(validated)),
        },
        "semantics": _semantic_payload(),
    }

    return EvidenceEnvelope(
        schema_name=(ANALYSIS_EVIDENCE_SCHEMA_NAME),
        schema_version=(EVIDENCE_SCHEMA_VERSION),
        bundle_type=(EvidenceBundleType.ANALYSIS_WINDOW),
        payload=payload,
    )


def _analysis_snapshot_payload(
    window: AnalysisWindow,
) -> dict[str, object]:
    envelope = build_analysis_evidence_envelope(window)

    return {
        "provenance": envelope.payload["provenance"],
        "analysis": envelope.payload["analysis"],
    }


def _difference_payload(
    difference: NumericDifference,
) -> dict[str, object]:
    if not isinstance(
        difference,
        NumericDifference,
    ):
        raise ValueError("difference must be a NumericDifference")

    return {
        "left": _number_json(difference.left),
        "right": _number_json(difference.right),
        "delta": _number_json(difference.delta),
    }


def _comparison_compatibility_payload(
    comparison: WindowComparison,
) -> dict[str, object]:
    compatibility = comparison.compatibility

    return {
        "manifest_schema_version": (compatibility.schema_version),
        "taxonomy_version": (compatibility.taxonomy_version),
        "alphabet_size": (compatibility.alphabet_size),
        "digit_probe_commit": (compatibility.digit_probe_commit),
        "analysis_configuration": {
            "schur_capacity": (compatibility.analysis_config.schur_capacity),
            "burst_threshold_us": (compatibility.burst_threshold_us),
        },
        "input_digest_algorithm": (compatibility.input_digest_algorithm),
        "left_project_version": (compatibility.left_project_version),
        "right_project_version": (compatibility.right_project_version),
        "matches": {
            "project_version": (compatibility.project_version_matches),
            "window_id": (compatibility.window_id_matches),
            "input_digest": (compatibility.input_digest_matches),
            "input_size": (compatibility.input_size_matches),
            "sample_size": (compatibility.sample_size_matches),
        },
    }


def _comparison_distribution_payload(
    comparison: WindowComparison,
) -> list[dict[str, object]]:
    return [
        {
            "symbol": symbol,
            "event_type": (SYMBOL_TO_EVENT_TYPE[symbol].value),
            "count": _difference_payload(comparison.counts[symbol].count),
            "proportion": _difference_payload(comparison.counts[symbol].proportion),
        }
        for symbol in sorted(comparison.counts)
    ]


def _comparison_coverage_payload(
    left: AnalysisWindow,
    right: AnalysisWindow,
) -> dict[str, object]:
    coverage = compare_taxonomy_coverage(
        left.result,
        right.result,
    )

    return {
        "named_event_count_delta": (coverage.named_event_count_delta),
        "other_event_count_delta": (coverage.other_event_count_delta),
        "named_event_proportion_delta": (coverage.named_event_proportion_delta),
        "other_event_proportion_delta": (coverage.other_event_proportion_delta),
        "represented_named_category_count_delta": (
            coverage.represented_named_category_count_delta
        ),
        "newly_represented_named_symbols": list(
            coverage.newly_represented_named_symbols
        ),
        "newly_absent_named_symbols": list(coverage.newly_absent_named_symbols),
        "newly_represented_named_event_types": [
            SYMBOL_TO_EVENT_TYPE[symbol].value
            for symbol in coverage.newly_represented_named_symbols
        ],
        "newly_absent_named_event_types": [
            SYMBOL_TO_EVENT_TYPE[symbol].value
            for symbol in coverage.newly_absent_named_symbols
        ],
    }


def _comparison_statistics_payload(
    comparison: WindowComparison,
) -> dict[str, object]:
    return {
        "runs": {
            "z_score": _difference_payload(comparison.runs.z_score),
            "p_two_tailed": _difference_payload(comparison.runs.p_two_tailed),
        },
        "gaps": [
            {
                "symbol": symbol,
                "event_type": (SYMBOL_TO_EVENT_TYPE[symbol].value),
                "count": _difference_payload(comparison.gaps[symbol].count),
                "mean": _difference_payload(comparison.gaps[symbol].mean),
            }
            for symbol in sorted(comparison.gaps)
        ],
        "autocorrelation": [
            {
                "lag": lag,
                "difference": (_difference_payload(comparison.autocorrelation[lag])),
            }
            for lag in sorted(comparison.autocorrelation)
        ],
        "compression_ratio": (_difference_payload(comparison.compression_ratio)),
        "ngram_accuracy": [
            {
                "order": order,
                "difference": (_difference_payload(comparison.ngram_accuracy[order])),
            }
            for order in sorted(comparison.ngram_accuracy)
        ],
    }


def _comparison_temporal_payload(
    comparison: WindowComparison,
) -> dict[str, object]:
    temporal = comparison.temporal

    return {
        "event_count": _difference_payload(temporal.event_count),
        "timed_event_count": _difference_payload(temporal.timed_event_count),
        "untimed_event_count": (_difference_payload(temporal.untimed_event_count)),
        "duration_us": _difference_payload(temporal.duration_us),
        "inter_event_gap_count": (_difference_payload(temporal.inter_event_gap_count)),
        "minimum_gap_us": _difference_payload(temporal.minimum_gap_us),
        "maximum_gap_us": _difference_payload(temporal.maximum_gap_us),
        "mean_gap_us": _difference_payload(temporal.mean_gap_us),
        "median_gap_us": _difference_payload(temporal.median_gap_us),
        "burst_count": _difference_payload(temporal.burst_count),
        "burst_event_count": (_difference_payload(temporal.burst_event_count)),
        "largest_burst_size": (_difference_payload(temporal.largest_burst_size)),
        "longest_burst_duration_us": (
            _difference_payload(temporal.longest_burst_duration_us)
        ),
    }


def build_comparison_evidence_envelope(
    left: AnalysisWindow,
    right: AnalysisWindow,
) -> EvidenceEnvelope:
    """Build version-1 evidence for one validated comparison."""

    if not isinstance(left, AnalysisWindow):
        raise ValueError("left must be an AnalysisWindow")

    if not isinstance(right, AnalysisWindow):
        raise ValueError("right must be an AnalysisWindow")

    try:
        validated_left = replace(left)
        validated_right = replace(right)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "comparison windows must satisfy AnalysisWindow invariants"
        ) from error

    comparison = compare_analysis_windows(
        validated_left,
        validated_right,
    )

    payload = {
        "left": _analysis_snapshot_payload(validated_left),
        "right": _analysis_snapshot_payload(validated_right),
        "comparison": {
            "direction": "right_minus_left",
            "left_window_id": (comparison.left_window_id),
            "right_window_id": (comparison.right_window_id),
            "compatibility": (_comparison_compatibility_payload(comparison)),
            "category_distribution": (_comparison_distribution_payload(comparison)),
            "taxonomy_coverage": (
                _comparison_coverage_payload(
                    validated_left,
                    validated_right,
                )
            ),
            "statistics": (_comparison_statistics_payload(comparison)),
            "temporal": (_comparison_temporal_payload(comparison)),
        },
        "semantics": _semantic_payload(),
    }

    return EvidenceEnvelope(
        schema_name=(COMPARISON_EVIDENCE_SCHEMA_NAME),
        schema_version=(EVIDENCE_SCHEMA_VERSION),
        bundle_type=(EvidenceBundleType.WINDOW_COMPARISON),
        payload=payload,
    )


def _envelope_to_json_object(
    envelope: EvidenceEnvelope,
) -> dict[str, object]:
    if not isinstance(envelope, EvidenceEnvelope):
        raise ValueError("envelope must be an EvidenceEnvelope")

    return {
        "schema_name": envelope.schema_name,
        "schema_version": envelope.schema_version,
        "bundle_type": envelope.bundle_type.value,
        "payload": _thaw_json_value(envelope.payload),
    }


def render_evidence_json(
    envelope: EvidenceEnvelope,
) -> str:
    """Render canonical UTF-8-compatible JSON plus one newline."""

    return (
        json.dumps(
            _canonicalize_serialized_floats(_envelope_to_json_object(envelope)),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=False,
        )
        + "\n"
    )


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"non-standard JSON numeric constant rejected: {value}")


def _reject_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
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
    if type(value) is not dict:
        raise ValueError(f"{name} must be a JSON object")

    if set(value) != set(keys):
        raise ValueError(f"{name} must contain exactly: " + ", ".join(keys))

    return value


def _strict_list(
    name: str,
    value: object,
) -> list[object]:
    if type(value) is not list:
        raise ValueError(f"{name} must be a JSON array")

    return value


def _strict_integer(
    name: str,
    value: object,
    *,
    minimum: int | None = None,
) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be a concrete integer")

    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")

    return value


def _strict_float(
    name: str,
    value: object,
) -> float:
    if type(value) is not float:
        raise ValueError(f"{name} must be a concrete float")

    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")

    return value


def _strict_text(
    name: str,
    value: object,
) -> str:
    if (
        type(value) is not str
        or not value
        or not value.strip()
        or value != value.strip()
    ):
        raise ValueError(
            f"{name} must be non-empty text without surrounding whitespace"
        )

    return value


def _strict_optional_window_id(
    name: str,
    value: object,
) -> str | None:
    if value is None:
        return None

    return _strict_text(name, value)


def _strict_boolean(
    name: str,
    value: object,
) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a boolean")

    return value


def _strict_number(
    name: str,
    value: object,
) -> EvidenceNumber:
    try:
        return evidence_number_from_json_object(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} is not a valid evidence number") from error


def _strict_optional_non_negative_number(
    name: str,
    value: object,
    *,
    integer: bool,
) -> EvidenceNumber:
    number = _strict_number(name, value)

    if number.state is NumericState.MISSING:
        return number

    if number.state is not NumericState.FINITE:
        raise ValueError(f"{name} must be finite or missing")

    if integer:
        if type(number.value) is not int or number.value < 0:
            raise ValueError(f"{name} finite value must be a non-negative integer")
    elif type(number.value) is not float or number.value < 0.0:
        raise ValueError(f"{name} finite value must be a non-negative float")

    return number


def _strict_difference(
    name: str,
    value: object,
) -> dict[str, object]:
    difference = _strict_object(
        name,
        value,
        (
            "left",
            "right",
            "delta",
        ),
    )

    for field in (
        "left",
        "right",
        "delta",
    ):
        _strict_number(
            f"{name}.{field}",
            difference[field],
        )

    return difference


def _strict_symbol_list(
    name: str,
    value: object,
    *,
    named_only: bool,
) -> tuple[int, ...]:
    items = _strict_list(name, value)

    symbols = tuple(
        _strict_integer(
            f"{name}[{index}]",
            item,
            minimum=0,
        )
        for index, item in enumerate(items)
    )

    if symbols != tuple(sorted(set(symbols))):
        raise ValueError(f"{name} must contain unique symbols in canonical order")

    allowed = set(range(EVENT_ALPHABET_SIZE))

    if named_only:
        allowed.remove(
            next(
                symbol
                for symbol, event_type in SYMBOL_TO_EVENT_TYPE.items()
                if event_type.value == "other"
            )
        )

    if not set(symbols) <= allowed:
        raise ValueError(f"{name} contains an unsupported symbol")

    return symbols


def _strict_event_type_list(
    name: str,
    value: object,
    symbols: tuple[int, ...],
) -> None:
    items = _strict_list(name, value)

    expected = [SYMBOL_TO_EVENT_TYPE[symbol].value for symbol in symbols]

    if items != expected:
        raise ValueError(f"{name} must match its symbol list")


def _strict_provenance(
    value: object,
) -> dict[str, object]:
    provenance = _strict_object(
        "provenance",
        value,
        (
            "project_version",
            "digit_probe_commit",
            "manifest_schema_version",
            "taxonomy_version",
            "window_id",
            "input",
            "analysis_configuration",
        ),
    )

    _strict_text(
        "provenance.project_version",
        provenance["project_version"],
    )

    commit = _strict_text(
        "provenance.digit_probe_commit",
        provenance["digit_probe_commit"],
    )

    if len(commit) != 40 or any(
        character not in "0123456789abcdef" for character in commit
    ):
        raise ValueError(
            "provenance.digit_probe_commit must be a lowercase full commit"
        )

    if provenance["manifest_schema_version"] != 1:
        raise ValueError("unsupported manifest schema version")

    if provenance["taxonomy_version"] != EVENT_TAXONOMY_VERSION:
        raise ValueError("unsupported taxonomy version")

    _strict_optional_window_id(
        "provenance.window_id",
        provenance["window_id"],
    )

    input_info = _strict_object(
        "provenance.input",
        provenance["input"],
        (
            "digest_algorithm",
            "sha256",
            "size_bytes",
        ),
    )

    if input_info["digest_algorithm"] != "sha256":
        raise ValueError("provenance input digest algorithm must be sha256")

    digest = _strict_text(
        "provenance.input.sha256",
        input_info["sha256"],
    )

    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError("provenance.input.sha256 must be a lowercase SHA-256 digest")

    _strict_integer(
        "provenance.input.size_bytes",
        input_info["size_bytes"],
        minimum=1,
    )

    configuration = _strict_object(
        "provenance.analysis_configuration",
        provenance["analysis_configuration"],
        (
            "schur_capacity",
            "burst_threshold_us",
        ),
    )

    _strict_integer(
        "provenance.analysis_configuration.schur_capacity",
        configuration["schur_capacity"],
        minimum=1,
    )

    _strict_integer(
        "provenance.analysis_configuration.burst_threshold_us",
        configuration["burst_threshold_us"],
        minimum=1,
    )

    return provenance


def _strict_category_distribution(
    value: object,
    *,
    sample_size: int,
) -> None:
    distribution = _strict_list(
        "analysis.category_distribution",
        value,
    )

    if len(distribution) != EVENT_ALPHABET_SIZE:
        raise ValueError(
            "category distribution must contain the complete event alphabet"
        )

    count_total = 0
    proportion_total = 0.0

    for symbol, raw_item in enumerate(distribution):
        item = _strict_object(
            (f"analysis.category_distribution[{symbol}]"),
            raw_item,
            (
                "symbol",
                "event_type",
                "count",
                "proportion",
                "z_score",
            ),
        )

        if item["symbol"] != symbol:
            raise ValueError(
                "category distribution symbols must be complete and canonical"
            )

        if item["event_type"] != (SYMBOL_TO_EVENT_TYPE[symbol].value):
            raise ValueError("category distribution event type does not match symbol")

        count = _strict_integer(
            (f"analysis.category_distribution[{symbol}].count"),
            item["count"],
            minimum=0,
        )

        proportion = _strict_float(
            (f"analysis.category_distribution[{symbol}].proportion"),
            item["proportion"],
        )

        if not 0.0 <= proportion <= 1.0:
            raise ValueError("category distribution proportion must be in [0, 1]")

        expected = count / sample_size

        if not math.isclose(
            proportion,
            expected,
            rel_tol=0.0,
            abs_tol=_EVIDENCE_FLOAT_COMPARISON_ABS_TOLERANCE,
        ):
            raise ValueError("category distribution proportion does not match count")

        _strict_number(
            (f"analysis.category_distribution[{symbol}].z_score"),
            item["z_score"],
        )

        count_total += count
        proportion_total += proportion

    if count_total != sample_size:
        raise ValueError("category counts must sum to sample_size")

    if not math.isclose(
        proportion_total,
        1.0,
        rel_tol=0.0,
        abs_tol=_EVIDENCE_FLOAT_COMPARISON_ABS_TOLERANCE,
    ):
        raise ValueError("category proportions must sum to one")


def _strict_coverage(
    value: object,
    *,
    sample_size: int,
    distribution: list[object],
) -> None:
    coverage = _strict_object(
        "analysis.taxonomy_coverage",
        value,
        (
            "status",
            "sample_size",
            "named_event_count",
            "named_event_proportion",
            "other_event_count",
            "other_event_proportion",
            "represented_named_symbols",
            "absent_named_symbols",
            "represented_named_event_types",
            "absent_named_event_types",
        ),
    )

    if coverage["sample_size"] != sample_size:
        raise ValueError("taxonomy coverage sample size mismatch")

    other_symbol = next(
        symbol
        for symbol, event_type in SYMBOL_TO_EVENT_TYPE.items()
        if event_type.value == "other"
    )

    counts = {
        item["symbol"]: item["count"] for item in distribution if type(item) is dict
    }

    other_count = counts[other_symbol]
    named_count = sample_size - other_count

    if coverage["named_event_count"] != named_count:
        raise ValueError("taxonomy named count mismatch")

    if coverage["other_event_count"] != other_count:
        raise ValueError("taxonomy other count mismatch")

    named_proportion = _strict_float(
        "analysis.taxonomy_coverage.named_event_proportion",
        coverage["named_event_proportion"],
    )

    other_proportion = _strict_float(
        "analysis.taxonomy_coverage.other_event_proportion",
        coverage["other_event_proportion"],
    )

    if not math.isclose(
        named_proportion,
        named_count / sample_size,
        rel_tol=0.0,
        abs_tol=_EVIDENCE_FLOAT_COMPARISON_ABS_TOLERANCE,
    ):
        raise ValueError("taxonomy named proportion mismatch")

    if not math.isclose(
        other_proportion,
        other_count / sample_size,
        rel_tol=0.0,
        abs_tol=_EVIDENCE_FLOAT_COMPARISON_ABS_TOLERANCE,
    ):
        raise ValueError("taxonomy other proportion mismatch")

    named_symbols = tuple(
        symbol for symbol in range(EVENT_ALPHABET_SIZE) if symbol != other_symbol
    )

    expected_represented = tuple(
        symbol for symbol in named_symbols if counts[symbol] > 0
    )

    expected_absent = tuple(symbol for symbol in named_symbols if counts[symbol] == 0)

    represented = _strict_symbol_list(
        "analysis.taxonomy_coverage.represented_named_symbols",
        coverage["represented_named_symbols"],
        named_only=True,
    )

    absent = _strict_symbol_list(
        "analysis.taxonomy_coverage.absent_named_symbols",
        coverage["absent_named_symbols"],
        named_only=True,
    )

    if represented != expected_represented:
        raise ValueError("represented taxonomy symbols mismatch")

    if absent != expected_absent:
        raise ValueError("absent taxonomy symbols mismatch")

    _strict_event_type_list(
        "analysis.taxonomy_coverage.represented_named_event_types",
        coverage["represented_named_event_types"],
        represented,
    )

    _strict_event_type_list(
        "analysis.taxonomy_coverage.absent_named_event_types",
        coverage["absent_named_event_types"],
        absent,
    )

    expected_status = (
        "all_named"
        if other_count == 0
        else "all_other"
        if named_count == 0
        else "mixed"
    )

    if coverage["status"] != expected_status:
        raise ValueError("taxonomy coverage status mismatch")


def _strict_indexed_metric_list(
    name: str,
    value: object,
    *,
    key_name: str,
    metric_name: str,
) -> None:
    items = _strict_list(name, value)

    previous_key = 0

    for index, raw_item in enumerate(items):
        item = _strict_object(
            f"{name}[{index}]",
            raw_item,
            (
                key_name,
                metric_name,
            ),
        )

        key = _strict_integer(
            f"{name}[{index}].{key_name}",
            item[key_name],
            minimum=1,
        )

        if key <= previous_key:
            raise ValueError(f"{name} keys must be unique and canonical")

        previous_key = key

        _strict_number(
            f"{name}[{index}].{metric_name}",
            item[metric_name],
        )


def _strict_statistics(
    value: object,
) -> None:
    statistics = _strict_object(
        "analysis.statistics",
        value,
        (
            "chi_square",
            "expected_per_bin",
            "runs",
            "gaps",
            "autocorrelation",
            "compression_ratio",
            "ngram_accuracy",
            "schur",
        ),
    )

    _strict_number(
        "analysis.statistics.chi_square",
        statistics["chi_square"],
    )

    _strict_number(
        "analysis.statistics.expected_per_bin",
        statistics["expected_per_bin"],
    )

    runs = _strict_object(
        "analysis.statistics.runs",
        statistics["runs"],
        (
            "z_score",
            "p_two_tailed",
        ),
    )

    _strict_number(
        "analysis.statistics.runs.z_score",
        runs["z_score"],
    )

    _strict_number(
        "analysis.statistics.runs.p_two_tailed",
        runs["p_two_tailed"],
    )

    gaps = _strict_list(
        "analysis.statistics.gaps",
        statistics["gaps"],
    )

    if len(gaps) != EVENT_ALPHABET_SIZE:
        raise ValueError("gap statistics must cover the complete alphabet")

    for symbol, raw_gap in enumerate(gaps):
        gap = _strict_object(
            f"analysis.statistics.gaps[{symbol}]",
            raw_gap,
            (
                "symbol",
                "event_type",
                "count",
                "mean",
            ),
        )

        if gap["symbol"] != symbol:
            raise ValueError("gap symbols must be canonical")

        if gap["event_type"] != (SYMBOL_TO_EVENT_TYPE[symbol].value):
            raise ValueError("gap event type does not match symbol")

        _strict_integer(
            (f"analysis.statistics.gaps[{symbol}].count"),
            gap["count"],
            minimum=0,
        )

        _strict_number(
            (f"analysis.statistics.gaps[{symbol}].mean"),
            gap["mean"],
        )

    _strict_indexed_metric_list(
        "analysis.statistics.autocorrelation",
        statistics["autocorrelation"],
        key_name="lag",
        metric_name="value",
    )

    _strict_number(
        "analysis.statistics.compression_ratio",
        statistics["compression_ratio"],
    )

    _strict_indexed_metric_list(
        "analysis.statistics.ngram_accuracy",
        statistics["ngram_accuracy"],
        key_name="order",
        metric_name="value",
    )

    schur = _strict_object(
        "analysis.statistics.schur",
        statistics["schur"],
        (
            "triples",
            "count",
            "expected",
            "fraction",
            "z_score",
            "first_matching_relation_index",
        ),
    )

    triples = _strict_integer(
        "analysis.statistics.schur.triples",
        schur["triples"],
        minimum=0,
    )

    count = _strict_integer(
        "analysis.statistics.schur.count",
        schur["count"],
        minimum=0,
    )

    if count > triples:
        raise ValueError("Schur count cannot exceed triples")

    _strict_number(
        "analysis.statistics.schur.expected",
        schur["expected"],
    )

    _strict_number(
        "analysis.statistics.schur.fraction",
        schur["fraction"],
    )

    _strict_number(
        "analysis.statistics.schur.z_score",
        schur["z_score"],
    )

    relation = _strict_number(
        ("analysis.statistics.schur.first_matching_relation_index"),
        schur["first_matching_relation_index"],
    )

    if relation.state is NumericState.FINITE:
        if type(relation.value) is not int or relation.value < 0:
            raise ValueError(
                "first matching relation index must be a non-negative integer"
            )
    elif relation.state is not NumericState.MISSING:
        raise ValueError("first matching relation index must be finite or missing")


def _strict_temporal(
    value: object,
    *,
    sample_size: int,
) -> None:
    temporal = _strict_object(
        "analysis.temporal",
        value,
        (
            "event_count",
            "timed_event_count",
            "untimed_event_count",
            "duration_us",
            "inter_event_gap_count",
            "minimum_gap_us",
            "maximum_gap_us",
            "mean_gap_us",
            "median_gap_us",
            "burst_threshold_us",
            "burst_count",
            "burst_event_count",
            "largest_burst_size",
            "longest_burst_duration_us",
        ),
    )

    event_count = _strict_integer(
        "analysis.temporal.event_count",
        temporal["event_count"],
        minimum=0,
    )

    if event_count != sample_size:
        raise ValueError("temporal event count must match analysis sample size")

    timed = _strict_integer(
        "analysis.temporal.timed_event_count",
        temporal["timed_event_count"],
        minimum=0,
    )

    untimed = _strict_integer(
        "analysis.temporal.untimed_event_count",
        temporal["untimed_event_count"],
        minimum=0,
    )

    if timed + untimed != event_count:
        raise ValueError("temporal timed and untimed counts must sum to event count")

    _strict_optional_non_negative_number(
        "analysis.temporal.duration_us",
        temporal["duration_us"],
        integer=True,
    )

    gap_count = _strict_integer(
        "analysis.temporal.inter_event_gap_count",
        temporal["inter_event_gap_count"],
        minimum=0,
    )

    if gap_count > max(event_count - 1, 0):
        raise ValueError("temporal gap count exceeds adjacent event pairs")

    for field in (
        "minimum_gap_us",
        "maximum_gap_us",
    ):
        _strict_optional_non_negative_number(
            f"analysis.temporal.{field}",
            temporal[field],
            integer=True,
        )

    for field in (
        "mean_gap_us",
        "median_gap_us",
    ):
        _strict_optional_non_negative_number(
            f"analysis.temporal.{field}",
            temporal[field],
            integer=False,
        )

    _strict_integer(
        "analysis.temporal.burst_threshold_us",
        temporal["burst_threshold_us"],
        minimum=1,
    )

    for field in (
        "burst_count",
        "burst_event_count",
        "largest_burst_size",
        "longest_burst_duration_us",
    ):
        _strict_integer(
            f"analysis.temporal.{field}",
            temporal[field],
            minimum=0,
        )


def _strict_analysis(
    value: object,
) -> dict[str, object]:
    analysis = _strict_object(
        "analysis",
        value,
        (
            "mode",
            "sample_size",
            "alphabet_size",
            "max_observed_symbol",
            "category_distribution",
            "taxonomy_coverage",
            "statistics",
            "temporal",
        ),
    )

    if analysis["mode"] != "integers":
        raise ValueError("analysis mode must be integers")

    sample_size = _strict_integer(
        "analysis.sample_size",
        analysis["sample_size"],
        minimum=1,
    )

    if analysis["alphabet_size"] != EVENT_ALPHABET_SIZE:
        raise ValueError("analysis alphabet size mismatch")

    max_observed = _strict_integer(
        "analysis.max_observed_symbol",
        analysis["max_observed_symbol"],
        minimum=0,
    )

    if max_observed >= EVENT_ALPHABET_SIZE:
        raise ValueError("maximum observed symbol is outside the alphabet")

    _strict_category_distribution(
        analysis["category_distribution"],
        sample_size=sample_size,
    )

    distribution = _strict_list(
        "analysis.category_distribution",
        analysis["category_distribution"],
    )

    _strict_coverage(
        analysis["taxonomy_coverage"],
        sample_size=sample_size,
        distribution=distribution,
    )

    _strict_statistics(analysis["statistics"])

    _strict_temporal(
        analysis["temporal"],
        sample_size=sample_size,
    )

    return analysis


def _strict_semantics(
    value: object,
) -> None:
    semantics = _strict_object(
        "semantics",
        value,
        (
            "scope",
            "limitations",
            "flags",
        ),
    )

    if semantics["scope"] != "descriptive_evidence":
        raise ValueError("evidence scope must be descriptive_evidence")

    limitations = _strict_list(
        "semantics.limitations",
        semantics["limitations"],
    )

    if limitations != list(_SEMANTIC_LIMITATIONS):
        raise ValueError("semantic limitations do not match the version-1 contract")

    flags = _strict_object(
        "semantics.flags",
        semantics["flags"],
        (
            "contains_raw_events",
            "contains_raw_messages",
            "contains_input_path",
            "anomaly_score",
            "threat_score",
            "intrusion_verdict",
            "confidence_estimate",
            "automatic_action",
        ),
    )

    for name, raw_value in flags.items():
        value = _strict_boolean(
            f"semantics.flags.{name}",
            raw_value,
        )

        if value:
            raise ValueError("version-1 semantic flags must all be false")


def _strict_analysis_snapshot(
    name: str,
    value: object,
) -> tuple[
    dict[str, object],
    dict[str, object],
]:
    snapshot = _strict_object(
        name,
        value,
        (
            "provenance",
            "analysis",
        ),
    )

    return (
        _strict_provenance(snapshot["provenance"]),
        _strict_analysis(snapshot["analysis"]),
    )


def _strict_compatibility(
    value: object,
    *,
    left_provenance: dict[str, object],
    right_provenance: dict[str, object],
) -> None:
    compatibility = _strict_object(
        "comparison.compatibility",
        value,
        (
            "manifest_schema_version",
            "taxonomy_version",
            "alphabet_size",
            "digit_probe_commit",
            "analysis_configuration",
            "input_digest_algorithm",
            "left_project_version",
            "right_project_version",
            "matches",
        ),
    )

    if compatibility["manifest_schema_version"] != 1:
        raise ValueError("comparison manifest schema mismatch")

    if compatibility["taxonomy_version"] != EVENT_TAXONOMY_VERSION:
        raise ValueError("comparison taxonomy version mismatch")

    if compatibility["alphabet_size"] != EVENT_ALPHABET_SIZE:
        raise ValueError("comparison alphabet size mismatch")

    if compatibility["digit_probe_commit"] != left_provenance["digit_probe_commit"]:
        raise ValueError("comparison Digit-Probe provenance mismatch")

    if compatibility["digit_probe_commit"] != right_provenance["digit_probe_commit"]:
        raise ValueError("comparison Digit-Probe provenance mismatch")

    configuration = _strict_object(
        "comparison.compatibility.analysis_configuration",
        compatibility["analysis_configuration"],
        (
            "schur_capacity",
            "burst_threshold_us",
        ),
    )

    for field in (
        "schur_capacity",
        "burst_threshold_us",
    ):
        _strict_integer(
            (f"comparison.compatibility.analysis_configuration.{field}"),
            configuration[field],
            minimum=1,
        )

    if compatibility["input_digest_algorithm"] != "sha256":
        raise ValueError("comparison digest algorithm mismatch")

    if compatibility["left_project_version"] != left_provenance["project_version"]:
        raise ValueError("left project version mismatch")

    if compatibility["right_project_version"] != right_provenance["project_version"]:
        raise ValueError("right project version mismatch")

    matches = _strict_object(
        "comparison.compatibility.matches",
        compatibility["matches"],
        (
            "project_version",
            "window_id",
            "input_digest",
            "input_size",
            "sample_size",
        ),
    )

    for field, raw_value in matches.items():
        _strict_boolean(
            (f"comparison.compatibility.matches.{field}"),
            raw_value,
        )


def _strict_comparison_distribution(
    value: object,
) -> None:
    distribution = _strict_list(
        "comparison.category_distribution",
        value,
    )

    if len(distribution) != EVENT_ALPHABET_SIZE:
        raise ValueError(
            "comparison category distribution must cover the complete alphabet"
        )

    for symbol, raw_item in enumerate(distribution):
        item = _strict_object(
            (f"comparison.category_distribution[{symbol}]"),
            raw_item,
            (
                "symbol",
                "event_type",
                "count",
                "proportion",
            ),
        )

        if item["symbol"] != symbol:
            raise ValueError("comparison category symbols must be canonical")

        if item["event_type"] != (SYMBOL_TO_EVENT_TYPE[symbol].value):
            raise ValueError("comparison category event type does not match symbol")

        _strict_difference(
            (f"comparison.category_distribution[{symbol}].count"),
            item["count"],
        )

        _strict_difference(
            (f"comparison.category_distribution[{symbol}].proportion"),
            item["proportion"],
        )


def _strict_comparison_coverage(
    value: object,
) -> None:
    coverage = _strict_object(
        "comparison.taxonomy_coverage",
        value,
        (
            "named_event_count_delta",
            "other_event_count_delta",
            "named_event_proportion_delta",
            "other_event_proportion_delta",
            "represented_named_category_count_delta",
            "newly_represented_named_symbols",
            "newly_absent_named_symbols",
            "newly_represented_named_event_types",
            "newly_absent_named_event_types",
        ),
    )

    for field in (
        "named_event_count_delta",
        "other_event_count_delta",
        "represented_named_category_count_delta",
    ):
        _strict_integer(
            (f"comparison.taxonomy_coverage.{field}"),
            coverage[field],
        )

    for field in (
        "named_event_proportion_delta",
        "other_event_proportion_delta",
    ):
        _strict_float(
            (f"comparison.taxonomy_coverage.{field}"),
            coverage[field],
        )

    newly_represented = _strict_symbol_list(
        "comparison.taxonomy_coverage.newly_represented_named_symbols",
        coverage["newly_represented_named_symbols"],
        named_only=True,
    )

    newly_absent = _strict_symbol_list(
        "comparison.taxonomy_coverage.newly_absent_named_symbols",
        coverage["newly_absent_named_symbols"],
        named_only=True,
    )

    _strict_event_type_list(
        "comparison.taxonomy_coverage.newly_represented_named_event_types",
        coverage["newly_represented_named_event_types"],
        newly_represented,
    )

    _strict_event_type_list(
        "comparison.taxonomy_coverage.newly_absent_named_event_types",
        coverage["newly_absent_named_event_types"],
        newly_absent,
    )


def _strict_comparison_statistics(
    value: object,
) -> None:
    statistics = _strict_object(
        "comparison.statistics",
        value,
        (
            "runs",
            "gaps",
            "autocorrelation",
            "compression_ratio",
            "ngram_accuracy",
        ),
    )

    runs = _strict_object(
        "comparison.statistics.runs",
        statistics["runs"],
        (
            "z_score",
            "p_two_tailed",
        ),
    )

    for field in (
        "z_score",
        "p_two_tailed",
    ):
        _strict_difference(
            f"comparison.statistics.runs.{field}",
            runs[field],
        )

    gaps = _strict_list(
        "comparison.statistics.gaps",
        statistics["gaps"],
    )

    if len(gaps) != EVENT_ALPHABET_SIZE:
        raise ValueError("comparison gaps must cover the complete alphabet")

    for symbol, raw_gap in enumerate(gaps):
        gap = _strict_object(
            (f"comparison.statistics.gaps[{symbol}]"),
            raw_gap,
            (
                "symbol",
                "event_type",
                "count",
                "mean",
            ),
        )

        if gap["symbol"] != symbol:
            raise ValueError("comparison gap symbols must be canonical")

        if gap["event_type"] != (SYMBOL_TO_EVENT_TYPE[symbol].value):
            raise ValueError("comparison gap event type mismatch")

        _strict_difference(
            (f"comparison.statistics.gaps[{symbol}].count"),
            gap["count"],
        )

        _strict_difference(
            (f"comparison.statistics.gaps[{symbol}].mean"),
            gap["mean"],
        )

    for name, key_name in (
        ("autocorrelation", "lag"),
        ("ngram_accuracy", "order"),
    ):
        items = _strict_list(
            f"comparison.statistics.{name}",
            statistics[name],
        )

        previous_key = 0

        for index, raw_item in enumerate(items):
            item = _strict_object(
                (f"comparison.statistics.{name}[{index}]"),
                raw_item,
                (
                    key_name,
                    "difference",
                ),
            )

            key = _strict_integer(
                (f"comparison.statistics.{name}[{index}].{key_name}"),
                item[key_name],
                minimum=1,
            )

            if key <= previous_key:
                raise ValueError("comparison metric keys must be unique and canonical")

            previous_key = key

            _strict_difference(
                (f"comparison.statistics.{name}[{index}].difference"),
                item["difference"],
            )

    _strict_difference(
        "comparison.statistics.compression_ratio",
        statistics["compression_ratio"],
    )


def _strict_comparison_temporal(
    value: object,
) -> None:
    temporal = _strict_object(
        "comparison.temporal",
        value,
        (
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
        ),
    )

    for field in temporal:
        _strict_difference(
            f"comparison.temporal.{field}",
            temporal[field],
        )


def _strict_analysis_payload_v1(
    payload: object,
) -> None:
    document = _strict_object(
        "analysis evidence payload",
        payload,
        (
            "provenance",
            "analysis",
            "semantics",
        ),
    )

    _strict_provenance(document["provenance"])

    _strict_analysis(document["analysis"])

    _strict_semantics(document["semantics"])


def _strict_comparison_payload_v1(
    payload: object,
) -> None:
    document = _strict_object(
        "comparison evidence payload",
        payload,
        (
            "left",
            "right",
            "comparison",
            "semantics",
        ),
    )

    (
        left_provenance,
        left_analysis,
    ) = _strict_analysis_snapshot(
        "comparison left snapshot",
        document["left"],
    )

    (
        right_provenance,
        right_analysis,
    ) = _strict_analysis_snapshot(
        "comparison right snapshot",
        document["right"],
    )

    comparison = _strict_object(
        "comparison",
        document["comparison"],
        (
            "direction",
            "left_window_id",
            "right_window_id",
            "compatibility",
            "category_distribution",
            "taxonomy_coverage",
            "statistics",
            "temporal",
        ),
    )

    if comparison["direction"] != "right_minus_left":
        raise ValueError("comparison direction must be right_minus_left")

    left_window_id = _strict_optional_window_id(
        "comparison.left_window_id",
        comparison["left_window_id"],
    )

    right_window_id = _strict_optional_window_id(
        "comparison.right_window_id",
        comparison["right_window_id"],
    )

    if left_window_id != left_provenance["window_id"]:
        raise ValueError("left comparison window id mismatch")

    if right_window_id != right_provenance["window_id"]:
        raise ValueError("right comparison window id mismatch")

    _strict_compatibility(
        comparison["compatibility"],
        left_provenance=left_provenance,
        right_provenance=right_provenance,
    )

    _strict_comparison_distribution(comparison["category_distribution"])

    _strict_comparison_coverage(comparison["taxonomy_coverage"])

    _strict_comparison_statistics(comparison["statistics"])

    _strict_comparison_temporal(comparison["temporal"])

    if left_analysis["alphabet_size"] != right_analysis["alphabet_size"]:
        raise ValueError("comparison snapshot alphabets mismatch")

    _strict_semantics(document["semantics"])


def parse_evidence_bundle_json(
    data: str | bytes,
) -> EvidenceEnvelope:
    """Parse and strictly validate one complete version-1 bundle."""

    envelope = parse_evidence_envelope_json(data)

    payload = _thaw_json_value(envelope.payload)

    if envelope.bundle_type is (EvidenceBundleType.ANALYSIS_WINDOW):
        _strict_analysis_payload_v1(payload)
    elif envelope.bundle_type is (EvidenceBundleType.WINDOW_COMPARISON):
        _strict_comparison_payload_v1(payload)
    else:
        raise ValueError("unsupported evidence bundle type")

    return envelope


def parse_evidence_envelope_json(
    source: str | bytes,
) -> EvidenceEnvelope:
    """Strictly decode and validate one evidence envelope."""

    if isinstance(source, bytes):
        try:
            text = source.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("evidence JSON must be valid UTF-8") from error
    elif isinstance(source, str):
        text = source
    else:
        raise ValueError("evidence JSON source must be text or bytes")

    try:
        decoded = json.loads(
            text,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except json.JSONDecodeError as error:
        raise ValueError("evidence JSON is malformed") from error

    if not isinstance(decoded, Mapping):
        raise ValueError("evidence JSON root must be an object")

    expected_fields = {
        "schema_name",
        "schema_version",
        "bundle_type",
        "payload",
    }

    if set(decoded) != expected_fields:
        raise ValueError("evidence envelope fields are incompatible")

    bundle_type_value = decoded["bundle_type"]

    if not isinstance(bundle_type_value, str):
        raise ValueError("bundle_type must be text")

    try:
        bundle_type = EvidenceBundleType(bundle_type_value)
    except ValueError as error:
        raise ValueError("bundle_type is unsupported") from error

    return EvidenceEnvelope(
        schema_name=decoded["schema_name"],
        schema_version=decoded["schema_version"],
        bundle_type=bundle_type,
        payload=decoded["payload"],
    )
