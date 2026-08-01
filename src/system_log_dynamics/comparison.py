"""Typed, deterministic comparisons of completed analysis windows."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from math import isfinite, isnan
from types import MappingProxyType
from typing import Final

from digit_probe import AnalysisResult

from system_log_dynamics.encoding import (
    EVENT_ALPHABET_SIZE,
    EVENT_TAXONOMY_VERSION,
)
from system_log_dynamics.manifests import (
    ANALYSIS_MANIFEST_SCHEMA_VERSION,
    INPUT_DIGEST_ALGORITHM,
    AnalysisConfigurationSnapshot,
    AnalysisManifest,
)
from system_log_dynamics.temporal import TemporalBurstSummary

__all__ = [
    "AnalysisWindow",
    "GapDifference",
    "IncompatibleAnalysisWindowsError",
    "ManifestCompatibility",
    "NumericDifference",
    "NumericState",
    "NumericValue",
    "RunsDifference",
    "SymbolDifference",
    "TemporalDifference",
    "WindowComparison",
    "compare_analysis_windows",
]

_SYMBOLS: Final = tuple(range(EVENT_ALPHABET_SIZE))
_BLOCKING_FIELDS: Final = (
    "schema_version",
    "taxonomy_version",
    "alphabet_size",
    "digit_probe_commit",
    "analysis_config",
    "input_digest_algorithm",
    "burst_threshold_us",
)
_SHA1_PATTERN: Final = re.compile(r"[0-9a-f]{40}")


class NumericState(StrEnum):
    """The deterministic representation of a source or derived numeric value."""

    FINITE = "finite"
    MISSING = "missing"
    NAN = "nan"
    POSITIVE_INFINITY = "positive_infinity"
    NEGATIVE_INFINITY = "negative_infinity"
    NOT_COMPUTABLE = "not_computable"


def _require_finite_number(name: str, value: object) -> int | float:
    if type(value) not in (int, float):
        raise ValueError(f"{name} must be a concrete non-boolean integer or float")
    if type(value) is float and not isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _require_non_negative_integer(name: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative concrete integer")
    return value


def _require_positive_integer(name: str, value: object) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive concrete integer")
    return value


def _require_float(name: str, value: object) -> float:
    if type(value) is not float:
        raise ValueError(f"{name} must be a float")
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


def _validated_window_id(
    name: str,
    value: object,
) -> str | None:
    if value is None:
        return None

    return _require_non_empty_text(name, value)


def _immutable_mapping(
    name: str,
    value: object,
    *,
    keys: tuple[int, ...] | None,
    item_type: type[object],
) -> Mapping[int, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    copied: dict[int, object] = {}
    for key, item in value.items():
        if type(key) is not int:
            raise ValueError(f"{name} keys must be concrete integers")
        if not isinstance(item, item_type):
            raise ValueError(f"{name} values have an invalid type")
        copied[key] = item
    if keys is not None and set(copied) != set(keys):
        raise ValueError(f"{name} keys are invalid")
    return MappingProxyType({key: copied[key] for key in sorted(copied)})


@dataclass(frozen=True, slots=True)
class NumericValue:
    state: NumericState
    value: int | float | None

    def __post_init__(self) -> None:
        if not isinstance(self.state, NumericState):
            raise ValueError("state must be a NumericState")
        if self.state is NumericState.FINITE:
            _require_finite_number("value", self.value)
        elif self.value is not None:
            raise ValueError("non-finite numeric values must not retain a value")


def _numeric_value(value: object) -> NumericValue:
    if value is None:
        return NumericValue(NumericState.MISSING, None)
    if type(value) is int:
        return NumericValue(NumericState.FINITE, value)
    if type(value) is not float:
        raise ValueError(
            "numeric values must be concrete non-boolean integers or floats"
        )
    if isnan(value):
        return NumericValue(NumericState.NAN, None)
    if value == float("inf"):
        return NumericValue(NumericState.POSITIVE_INFINITY, None)
    if value == float("-inf"):
        return NumericValue(NumericState.NEGATIVE_INFINITY, None)
    return NumericValue(NumericState.FINITE, value)


def _float_delta(right: int | float, left: int | float) -> float:
    """Subtract mixed finite values while representing conversion overflow."""

    try:
        return float(right) - float(left)
    except OverflowError:
        # An integer too large for float necessarily dominates the finite float.
        if type(right) is int and abs(right) > 1.7976931348623157e308:
            return float("inf") if right > 0 else float("-inf")
        return float("-inf") if left > 0 else float("inf")


def _delta(left: NumericValue, right: NumericValue) -> NumericValue:
    if left.state is not NumericState.FINITE or right.state is not NumericState.FINITE:
        return NumericValue(NumericState.NOT_COMPUTABLE, None)
    assert left.value is not None
    assert right.value is not None
    if type(left.value) is int and type(right.value) is int:
        return NumericValue(NumericState.FINITE, right.value - left.value)
    return _numeric_value(_float_delta(right.value, left.value))


@dataclass(frozen=True, slots=True)
class NumericDifference:
    left: NumericValue
    right: NumericValue
    delta: NumericValue

    def __post_init__(self) -> None:
        if not all(
            isinstance(value, NumericValue)
            for value in (self.left, self.right, self.delta)
        ):
            raise ValueError("numeric differences require NumericValue fields")
        if (
            self.left.state is NumericState.NOT_COMPUTABLE
            or self.right.state is NumericState.NOT_COMPUTABLE
        ):
            raise ValueError("source numeric values cannot be not computable")
        if self.delta != _delta(self.left, self.right):
            raise ValueError("delta must equal right minus left")


def _difference(left: object, right: object) -> NumericDifference:
    left_value = _numeric_value(left)
    right_value = _numeric_value(right)
    return NumericDifference(left_value, right_value, _delta(left_value, right_value))


def _require_non_negative_integer_difference(
    name: str,
    difference: object,
) -> NumericDifference:
    if not isinstance(difference, NumericDifference):
        raise ValueError(f"{name} must be a NumericDifference")

    for side in ("left", "right"):
        value = getattr(difference, side)

        if (
            value.state is not NumericState.FINITE
            or type(value.value) is not int
            or value.value < 0
        ):
            raise ValueError(f"{name} sources must be non-negative concrete integers")

    return difference


def _require_proportion_difference(
    name: str,
    difference: object,
) -> NumericDifference:
    if not isinstance(difference, NumericDifference):
        raise ValueError(f"{name} must be a NumericDifference")

    for side in ("left", "right"):
        value = getattr(difference, side)

        if (
            value.state is not NumericState.FINITE
            or type(value.value) is not float
            or not 0.0 <= value.value <= 1.0
        ):
            raise ValueError(f"{name} sources must be finite float proportions")

    return difference


def _require_float_metric_difference(
    name: str,
    difference: object,
) -> NumericDifference:
    if not isinstance(difference, NumericDifference):
        raise ValueError(f"{name} must be a NumericDifference")

    for side in ("left", "right"):
        value = getattr(difference, side)

        if value.state in {
            NumericState.MISSING,
            NumericState.NOT_COMPUTABLE,
        }:
            raise ValueError(f"{name} sources must not be missing")

        if value.state is NumericState.FINITE and type(value.value) is not float:
            raise ValueError(f"{name} finite sources must be floats")

    return difference


def _require_union_float_difference(
    name: str,
    difference: object,
) -> NumericDifference:
    if not isinstance(difference, NumericDifference):
        raise ValueError(f"{name} must be a NumericDifference")

    states = []

    for side in ("left", "right"):
        value = getattr(difference, side)
        states.append(value.state)

        if value.state is NumericState.NOT_COMPUTABLE:
            raise ValueError(f"{name} sources cannot be not computable")

        if value.state is NumericState.FINITE and type(value.value) is not float:
            raise ValueError(f"{name} finite sources must be floats")

    if states == [
        NumericState.MISSING,
        NumericState.MISSING,
    ]:
        raise ValueError(f"{name} cannot be missing on both sides")

    return difference


def _optional_non_negative_integer_source(
    name: str,
    difference: NumericDifference,
    side: str,
) -> int | None:
    value = getattr(difference, side)

    if value.state is NumericState.MISSING:
        return None

    if (
        value.state is not NumericState.FINITE
        or type(value.value) is not int
        or value.value < 0
    ):
        raise ValueError(f"{name} must be a missing or non-negative integer source")

    return value.value


def _optional_non_negative_float_source(
    name: str,
    difference: NumericDifference,
    side: str,
) -> float | None:
    value = getattr(difference, side)

    if value.state is NumericState.MISSING:
        return None

    if (
        value.state is not NumericState.FINITE
        or type(value.value) is not float
        or value.value < 0.0
    ):
        raise ValueError(f"{name} must be a missing or non-negative float source")

    return value.value


def _required_non_negative_integer_source(
    name: str,
    difference: NumericDifference,
    side: str,
) -> int:
    value = _optional_non_negative_integer_source(
        name,
        difference,
        side,
    )

    if value is None:
        raise ValueError(f"{name} must be present on both sides")

    return value


def _validate_temporal_side(
    value: TemporalDifference,
    side: str,
) -> None:
    event_count = _required_non_negative_integer_source(
        "event_count",
        value.event_count,
        side,
    )
    timed_event_count = _required_non_negative_integer_source(
        "timed_event_count",
        value.timed_event_count,
        side,
    )
    untimed_event_count = _required_non_negative_integer_source(
        "untimed_event_count",
        value.untimed_event_count,
        side,
    )

    if timed_event_count + untimed_event_count != event_count:
        raise ValueError("temporal timed and untimed totals must equal event_count")

    duration_us = _optional_non_negative_integer_source(
        "duration_us",
        value.duration_us,
        side,
    )

    if timed_event_count == 0 and duration_us is not None:
        raise ValueError("zero timed events require missing duration")

    if timed_event_count == 1 and duration_us != 0:
        raise ValueError("one timed event requires zero duration")

    gap_count = _required_non_negative_integer_source(
        "inter_event_gap_count",
        value.inter_event_gap_count,
        side,
    )

    if gap_count > max(event_count - 1, 0):
        raise ValueError("temporal gap count exceeds adjacent pairs")

    minimum_gap = _optional_non_negative_integer_source(
        "minimum_gap_us",
        value.minimum_gap_us,
        side,
    )
    maximum_gap = _optional_non_negative_integer_source(
        "maximum_gap_us",
        value.maximum_gap_us,
        side,
    )
    mean_gap = _optional_non_negative_float_source(
        "mean_gap_us",
        value.mean_gap_us,
        side,
    )
    median_gap = _optional_non_negative_float_source(
        "median_gap_us",
        value.median_gap_us,
        side,
    )

    statistics = (
        minimum_gap,
        maximum_gap,
        mean_gap,
        median_gap,
    )

    if gap_count == 0:
        if any(item is not None for item in statistics):
            raise ValueError("zero temporal gaps require missing gap statistics")
    else:
        if any(item is None for item in statistics):
            raise ValueError("positive temporal gaps require all gap statistics")

        assert minimum_gap is not None
        assert maximum_gap is not None
        assert mean_gap is not None
        assert median_gap is not None

        if not (minimum_gap <= median_gap <= maximum_gap):
            raise ValueError("temporal median gap lies outside gap bounds")

        if not (minimum_gap <= mean_gap <= maximum_gap):
            raise ValueError("temporal mean gap lies outside gap bounds")

    burst_count = _required_non_negative_integer_source(
        "burst_count",
        value.burst_count,
        side,
    )
    burst_event_count = _required_non_negative_integer_source(
        "burst_event_count",
        value.burst_event_count,
        side,
    )
    largest_burst_size = _required_non_negative_integer_source(
        "largest_burst_size",
        value.largest_burst_size,
        side,
    )
    longest_burst_duration = _required_non_negative_integer_source(
        "longest_burst_duration_us",
        value.longest_burst_duration_us,
        side,
    )

    if burst_event_count > timed_event_count:
        raise ValueError("burst event total exceeds timed events")

    if burst_count == 0:
        if (
            burst_event_count != 0
            or largest_burst_size != 0
            or longest_burst_duration != 0
        ):
            raise ValueError("zero bursts require zero aggregates")
        return

    if burst_event_count < 2 * burst_count:
        raise ValueError("each burst requires at least two events")

    if largest_burst_size < 2 or largest_burst_size > burst_event_count:
        raise ValueError("largest burst size is inconsistent")

    if largest_burst_size > burst_event_count - 2 * (burst_count - 1):
        raise ValueError("largest burst size conflicts with burst count")

    if largest_burst_size * burst_count < burst_event_count:
        raise ValueError("largest burst size cannot cover all burst events")

    if burst_event_count - burst_count > gap_count:
        raise ValueError("bursts require enough connecting gaps")


@dataclass(frozen=True, slots=True)
class SymbolDifference:
    count: NumericDifference
    proportion: NumericDifference

    def __post_init__(self) -> None:
        _require_non_negative_integer_difference(
            "symbol count",
            self.count,
        )
        _require_proportion_difference(
            "symbol proportion",
            self.proportion,
        )


@dataclass(frozen=True, slots=True)
class RunsDifference:
    z_score: NumericDifference
    p_two_tailed: NumericDifference

    def __post_init__(self) -> None:
        _require_float_metric_difference(
            "runs z_score",
            self.z_score,
        )
        _require_float_metric_difference(
            "runs p_two_tailed",
            self.p_two_tailed,
        )


@dataclass(frozen=True, slots=True)
class GapDifference:
    count: NumericDifference
    mean: NumericDifference

    def __post_init__(self) -> None:
        _require_non_negative_integer_difference(
            "gap count",
            self.count,
        )
        _require_float_metric_difference(
            "gap mean",
            self.mean,
        )


@dataclass(frozen=True, slots=True)
class TemporalDifference:
    event_count: NumericDifference
    timed_event_count: NumericDifference
    untimed_event_count: NumericDifference
    duration_us: NumericDifference
    inter_event_gap_count: NumericDifference
    minimum_gap_us: NumericDifference
    maximum_gap_us: NumericDifference
    mean_gap_us: NumericDifference
    median_gap_us: NumericDifference
    burst_count: NumericDifference
    burst_event_count: NumericDifference
    largest_burst_size: NumericDifference
    longest_burst_duration_us: NumericDifference

    def __post_init__(self) -> None:
        values = (
            self.event_count,
            self.timed_event_count,
            self.untimed_event_count,
            self.duration_us,
            self.inter_event_gap_count,
            self.minimum_gap_us,
            self.maximum_gap_us,
            self.mean_gap_us,
            self.median_gap_us,
            self.burst_count,
            self.burst_event_count,
            self.largest_burst_size,
            self.longest_burst_duration_us,
        )

        if not all(isinstance(value, NumericDifference) for value in values):
            raise ValueError("temporal differences require NumericDifference fields")

        _validate_temporal_side(self, "left")
        _validate_temporal_side(self, "right")


@dataclass(frozen=True, slots=True)
class ManifestCompatibility:
    schema_version: int
    taxonomy_version: str
    alphabet_size: int
    digit_probe_commit: str
    analysis_config: AnalysisConfigurationSnapshot
    input_digest_algorithm: str
    burst_threshold_us: int
    left_project_version: str
    right_project_version: str
    project_version_matches: bool
    window_id_matches: bool
    input_digest_matches: bool
    input_size_matches: bool
    sample_size_matches: bool

    def __post_init__(self) -> None:
        if (
            type(self.schema_version) is not int
            or self.schema_version != ANALYSIS_MANIFEST_SCHEMA_VERSION
        ):
            raise ValueError(
                "schema_version must match ANALYSIS_MANIFEST_SCHEMA_VERSION"
            )

        if self.taxonomy_version != EVENT_TAXONOMY_VERSION:
            raise ValueError("taxonomy_version must match EVENT_TAXONOMY_VERSION")

        if (
            type(self.alphabet_size) is not int
            or self.alphabet_size != EVENT_ALPHABET_SIZE
        ):
            raise ValueError("alphabet_size must match EVENT_ALPHABET_SIZE")

        if (
            not isinstance(self.digit_probe_commit, str)
            or _SHA1_PATTERN.fullmatch(self.digit_probe_commit) is None
        ):
            raise ValueError("digit_probe_commit must be a lowercase full commit")

        if not isinstance(
            self.analysis_config,
            AnalysisConfigurationSnapshot,
        ):
            raise ValueError("analysis_config must be an AnalysisConfigurationSnapshot")

        try:
            analysis_config = replace(self.analysis_config)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "analysis_config must satisfy AnalysisConfigurationSnapshot invariants"
            ) from error

        object.__setattr__(
            self,
            "analysis_config",
            analysis_config,
        )

        if self.input_digest_algorithm != INPUT_DIGEST_ALGORITHM:
            raise ValueError("input_digest_algorithm must match INPUT_DIGEST_ALGORITHM")

        _require_positive_integer(
            "burst_threshold_us",
            self.burst_threshold_us,
        )
        _require_non_empty_text(
            "left_project_version",
            self.left_project_version,
        )
        _require_non_empty_text(
            "right_project_version",
            self.right_project_version,
        )

        match_values = (
            self.project_version_matches,
            self.window_id_matches,
            self.input_digest_matches,
            self.input_size_matches,
            self.sample_size_matches,
        )

        if not all(type(value) is bool for value in match_values):
            raise ValueError("manifest compatibility match fields must be booleans")

        expected_project_match = self.left_project_version == self.right_project_version

        if self.project_version_matches is not expected_project_match:
            raise ValueError(
                "project_version_matches is inconsistent with project versions"
            )


def _validate_analysis_result(
    result: AnalysisResult,
    manifest: AnalysisManifest,
    temporal: TemporalBurstSummary,
) -> None:
    if result.mode != "integers":
        raise ValueError("result mode must be 'integers'")
    if type(result.alphabet) is not int or result.alphabet != EVENT_ALPHABET_SIZE:
        raise ValueError("result alphabet must match EVENT_ALPHABET_SIZE")
    if result.alphabet != manifest.alphabet_size:
        raise ValueError("result alphabet must match manifest alphabet")
    sample_size = _require_positive_integer("result sample size", result.sample_size)
    if sample_size != manifest.sample_size:
        raise ValueError("result sample size must match manifest sample size")
    if sample_size != temporal.event_count:
        raise ValueError("result sample size must match temporal event count")
    if (
        type(result.max_observed) is not int
        or not 0 <= result.max_observed < EVENT_ALPHABET_SIZE
    ):
        raise ValueError("result max_observed must be a symbol in the event alphabet")
    if not isinstance(result.counts, Mapping) or set(result.counts) != set(_SYMBOLS):
        raise ValueError("result counts must be a complete symbol dictionary")
    for symbol, count in result.counts.items():
        if type(symbol) is not int or type(count) is not int or count < 0:
            raise ValueError("result counts must be non-negative concrete integers")
    if sum(result.counts.values()) != sample_size:
        raise ValueError("result counts must sum to the sample size")

    if not isinstance(result.zscores, Mapping) or set(result.zscores) != set(_SYMBOLS):
        raise ValueError("result zscores must be a complete symbol mapping")

    for symbol, value in result.zscores.items():
        if type(symbol) is not int:
            raise ValueError("result zscore keys must be concrete integers")
        _require_float("zscore value", value)

    if not isinstance(result.gaps, Mapping) or set(result.gaps) != set(_SYMBOLS):
        raise ValueError("result gaps must be a complete symbol dictionary")
    for symbol, gap in result.gaps.items():
        if type(symbol) is not int:
            raise ValueError("result gap keys must be concrete integers")
        try:
            _require_non_negative_integer("gap count", gap.count)
            _require_float("gap mean", gap.mean)
        except AttributeError as error:
            raise ValueError("result gaps must expose count and mean") from error
    try:
        _require_float("runs z_score", result.runs.z_score)
        _require_float("runs p_two_tailed", result.runs.p_two_tailed)
    except AttributeError as error:
        raise ValueError("result runs must expose z_score and p_two_tailed") from error
    for name, mapping in (
        ("autocorr", result.autocorr),
        ("ngram_accuracy", result.ngram_accuracy),
    ):
        if not isinstance(mapping, Mapping):
            raise ValueError(f"result {name} must be a dictionary")
        for key, value in mapping.items():
            _require_positive_integer(f"{name} key", key)
            _require_float(f"{name} value", value)
    _require_float(
        "compress ratio",
        result.compress_ratio,
    )


def _snapshot_result_mapping(
    value: Mapping[int, object],
) -> Mapping[int, object]:
    return MappingProxyType({key: value[key] for key in sorted(value)})


def _snapshot_analysis_result(
    result: AnalysisResult,
) -> AnalysisResult:
    try:
        return replace(
            result,
            counts=_snapshot_result_mapping(result.counts),
            zscores=_snapshot_result_mapping(result.zscores),
            runs=replace(result.runs),
            gaps=MappingProxyType(
                {key: replace(result.gaps[key]) for key in sorted(result.gaps)}
            ),
            autocorr=_snapshot_result_mapping(result.autocorr),
            ngram_accuracy=_snapshot_result_mapping(result.ngram_accuracy),
            schur=replace(result.schur),
        )
    except (
        AttributeError,
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            "result nested values must satisfy Digit-Probe dataclass invariants"
        ) from error


def _validated_manifest_snapshot(
    manifest: AnalysisManifest,
) -> AnalysisManifest:
    try:
        configuration = replace(manifest.analysis_config)

        return replace(
            manifest,
            analysis_config=configuration,
        )
    except (TypeError, ValueError) as error:
        raise ValueError("manifest must satisfy AnalysisManifest invariants") from error


def _validated_temporal_snapshot(
    temporal: TemporalBurstSummary,
) -> TemporalBurstSummary:
    try:
        return replace(temporal)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "temporal must satisfy TemporalBurstSummary invariants"
        ) from error


@dataclass(frozen=True, slots=True)
class AnalysisWindow:
    manifest: AnalysisManifest
    result: AnalysisResult
    temporal: TemporalBurstSummary

    def __post_init__(self) -> None:
        if not isinstance(
            self.manifest,
            AnalysisManifest,
        ):
            raise ValueError("manifest must be an AnalysisManifest")

        if not isinstance(
            self.result,
            AnalysisResult,
        ):
            raise ValueError("result must be an AnalysisResult")

        if not isinstance(
            self.temporal,
            TemporalBurstSummary,
        ):
            raise ValueError("temporal must be a TemporalBurstSummary")

        manifest = _validated_manifest_snapshot(self.manifest)
        temporal = _validated_temporal_snapshot(self.temporal)

        _validate_analysis_result(
            self.result,
            manifest,
            temporal,
        )

        object.__setattr__(
            self,
            "manifest",
            manifest,
        )
        object.__setattr__(
            self,
            "result",
            _snapshot_analysis_result(self.result),
        )
        object.__setattr__(
            self,
            "temporal",
            temporal,
        )


@dataclass(frozen=True, slots=True)
class WindowComparison:
    left_window_id: str | None
    right_window_id: str | None
    compatibility: ManifestCompatibility
    counts: Mapping[int, SymbolDifference]
    runs: RunsDifference
    gaps: Mapping[int, GapDifference]
    autocorrelation: Mapping[int, NumericDifference]
    ngram_accuracy: Mapping[int, NumericDifference]
    compression_ratio: NumericDifference
    temporal: TemporalDifference

    def __post_init__(self) -> None:
        _validated_window_id(
            "left_window_id",
            self.left_window_id,
        )
        _validated_window_id(
            "right_window_id",
            self.right_window_id,
        )
        if not isinstance(self.compatibility, ManifestCompatibility):
            raise ValueError("compatibility must be a ManifestCompatibility")
        object.__setattr__(
            self,
            "counts",
            _immutable_mapping(
                "counts", self.counts, keys=_SYMBOLS, item_type=SymbolDifference
            ),
        )
        if not isinstance(self.runs, RunsDifference):
            raise ValueError("runs must be a RunsDifference")
        object.__setattr__(
            self,
            "gaps",
            _immutable_mapping(
                "gaps", self.gaps, keys=_SYMBOLS, item_type=GapDifference
            ),
        )
        autocorrelation = _immutable_mapping(
            "autocorrelation",
            self.autocorrelation,
            keys=None,
            item_type=NumericDifference,
        )
        ngram_accuracy = _immutable_mapping(
            "ngram_accuracy",
            self.ngram_accuracy,
            keys=None,
            item_type=NumericDifference,
        )
        if any(key <= 0 for key in autocorrelation) or any(
            key <= 0 for key in ngram_accuracy
        ):
            raise ValueError("autocorrelation and ngram_accuracy keys must be positive")

        for key, difference in autocorrelation.items():
            _require_union_float_difference(
                f"autocorrelation[{key}]",
                difference,
            )

        for key, difference in ngram_accuracy.items():
            _require_union_float_difference(
                f"ngram_accuracy[{key}]",
                difference,
            )

        object.__setattr__(
            self,
            "autocorrelation",
            autocorrelation,
        )
        object.__setattr__(
            self,
            "ngram_accuracy",
            ngram_accuracy,
        )

        _require_float_metric_difference(
            "compression_ratio",
            self.compression_ratio,
        )

        if not isinstance(
            self.temporal,
            TemporalDifference,
        ):
            raise ValueError("temporal must be a TemporalDifference")


class IncompatibleAnalysisWindowsError(ValueError):
    """Raised when required analysis-window contracts differ."""

    def __init__(self, fields: tuple[str, ...]) -> None:
        if (
            not isinstance(fields, tuple)
            or not fields
            or any(type(field) is not str for field in fields)
        ):
            raise ValueError(
                "fields must be a non-empty tuple of canonical blocking fields"
            )

        canonical = tuple(field for field in _BLOCKING_FIELDS if field in fields)

        if fields != canonical:
            raise ValueError(
                "fields must be unique and follow canonical blocking-field order"
            )

        self.fields = fields

        super().__init__("incompatible analysis windows: " + ", ".join(fields))


def _compatibility(
    left: AnalysisWindow,
    right: AnalysisWindow,
) -> ManifestCompatibility:
    left_manifest = left.manifest
    right_manifest = right.manifest
    mismatches = tuple(
        field
        for field in _BLOCKING_FIELDS
        if (
            getattr(left.temporal, field)
            if field == "burst_threshold_us"
            else getattr(left_manifest, field)
        )
        != (
            getattr(right.temporal, field)
            if field == "burst_threshold_us"
            else getattr(right_manifest, field)
        )
    )
    if mismatches:
        raise IncompatibleAnalysisWindowsError(mismatches)
    return ManifestCompatibility(
        schema_version=left_manifest.schema_version,
        taxonomy_version=left_manifest.taxonomy_version,
        alphabet_size=left_manifest.alphabet_size,
        digit_probe_commit=left_manifest.digit_probe_commit,
        analysis_config=left_manifest.analysis_config,
        input_digest_algorithm=left_manifest.input_digest_algorithm,
        burst_threshold_us=left.temporal.burst_threshold_us,
        left_project_version=left_manifest.project_version,
        right_project_version=right_manifest.project_version,
        project_version_matches=(
            left_manifest.project_version == right_manifest.project_version
        ),
        window_id_matches=(left_manifest.window_id == right_manifest.window_id),
        input_digest_matches=(
            left_manifest.input_sha256 == right_manifest.input_sha256
        ),
        input_size_matches=(
            left_manifest.input_size_bytes == right_manifest.input_size_bytes
        ),
        sample_size_matches=(left_manifest.sample_size == right_manifest.sample_size),
    )


def _temporal_difference(
    left: TemporalBurstSummary,
    right: TemporalBurstSummary,
) -> TemporalDifference:
    return TemporalDifference(
        event_count=_difference(left.event_count, right.event_count),
        timed_event_count=_difference(left.timed_event_count, right.timed_event_count),
        untimed_event_count=_difference(
            left.untimed_event_count, right.untimed_event_count
        ),
        duration_us=_difference(left.duration_us, right.duration_us),
        inter_event_gap_count=_difference(
            left.inter_event_gap_count, right.inter_event_gap_count
        ),
        minimum_gap_us=_difference(left.minimum_gap_us, right.minimum_gap_us),
        maximum_gap_us=_difference(left.maximum_gap_us, right.maximum_gap_us),
        mean_gap_us=_difference(left.mean_gap_us, right.mean_gap_us),
        median_gap_us=_difference(left.median_gap_us, right.median_gap_us),
        burst_count=_difference(left.burst_count, right.burst_count),
        burst_event_count=_difference(left.burst_event_count, right.burst_event_count),
        largest_burst_size=_difference(
            left.largest_burst_size, right.largest_burst_size
        ),
        longest_burst_duration_us=_difference(
            left.longest_burst_duration_us, right.longest_burst_duration_us
        ),
    )


def compare_analysis_windows(
    left: AnalysisWindow,
    right: AnalysisWindow,
) -> WindowComparison:
    """Compare two validated, completed windows using ``right - left`` deltas."""

    if not isinstance(left, AnalysisWindow) or not isinstance(right, AnalysisWindow):
        raise ValueError("left and right must be AnalysisWindow instances")

    for name, window in (
        ("left", left),
        ("right", right),
    ):
        if not isinstance(
            window.manifest,
            AnalysisManifest,
        ):
            raise ValueError(f"{name} manifest must be an AnalysisManifest")

        if not isinstance(
            window.result,
            AnalysisResult,
        ):
            raise ValueError(f"{name} result must be an AnalysisResult")

        if not isinstance(
            window.temporal,
            TemporalBurstSummary,
        ):
            raise ValueError(f"{name} temporal must be a TemporalBurstSummary")

    compatibility = _compatibility(left, right)

    left = AnalysisWindow(
        left.manifest,
        left.result,
        left.temporal,
    )
    right = AnalysisWindow(
        right.manifest,
        right.result,
        right.temporal,
    )
    left_result = left.result
    right_result = right.result
    counts = {
        symbol: SymbolDifference(
            count=_difference(left_result.counts[symbol], right_result.counts[symbol]),
            proportion=_difference(
                left_result.counts[symbol] / left_result.sample_size,
                right_result.counts[symbol] / right_result.sample_size,
            ),
        )
        for symbol in _SYMBOLS
    }
    gaps = {
        symbol: GapDifference(
            count=_difference(
                left_result.gaps[symbol].count,
                right_result.gaps[symbol].count,
            ),
            mean=_difference(
                left_result.gaps[symbol].mean,
                right_result.gaps[symbol].mean,
            ),
        )
        for symbol in _SYMBOLS
    }
    autocorrelation = {
        key: _difference(left_result.autocorr.get(key), right_result.autocorr.get(key))
        for key in sorted(set(left_result.autocorr) | set(right_result.autocorr))
    }
    ngram_accuracy = {
        key: _difference(
            left_result.ngram_accuracy.get(key), right_result.ngram_accuracy.get(key)
        )
        for key in sorted(
            set(left_result.ngram_accuracy) | set(right_result.ngram_accuracy)
        )
    }
    return WindowComparison(
        left_window_id=left.manifest.window_id,
        right_window_id=right.manifest.window_id,
        compatibility=compatibility,
        counts=counts,
        runs=RunsDifference(
            z_score=_difference(left_result.runs.z_score, right_result.runs.z_score),
            p_two_tailed=_difference(
                left_result.runs.p_two_tailed, right_result.runs.p_two_tailed
            ),
        ),
        gaps=gaps,
        autocorrelation=autocorrelation,
        ngram_accuracy=ngram_accuracy,
        compression_ratio=_difference(
            left_result.compress_ratio, right_result.compress_ratio
        ),
        temporal=_temporal_difference(left.temporal, right.temporal),
    )
