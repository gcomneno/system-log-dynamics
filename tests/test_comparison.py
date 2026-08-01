"""Focused contracts for structured analysis-window comparison."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
from math import inf, nan

import pytest
from digit_probe import analyze_integer_symbols

from system_log_dynamics.comparison import (
    AnalysisWindow,
    GapDifference,
    IncompatibleAnalysisWindowsError,
    NumericDifference,
    NumericState,
    NumericValue,
    RunsDifference,
    SymbolDifference,
    TemporalDifference,
    WindowComparison,
    compare_analysis_windows,
)
from system_log_dynamics.encoding import EVENT_ALPHABET_SIZE, EVENT_TAXONOMY_VERSION
from system_log_dynamics.manifests import (
    ANALYSIS_MANIFEST_SCHEMA_VERSION,
    INPUT_DIGEST_ALGORITHM,
    AnalysisConfigurationSnapshot,
    AnalysisManifest,
)
from system_log_dynamics.temporal import TemporalBurstSummary


def _result(symbols: list[int] | None = None):
    return analyze_integer_symbols(
        symbols or list(range(EVENT_ALPHABET_SIZE)),
        alphabet=EVENT_ALPHABET_SIZE,
    )


def _manifest(
    sample_size: int,
    *,
    window_id: str | None = "left",
    input_sha256: str = "a" * 64,
    input_size_bytes: int = 100,
    project_version: str = "0.1.0",
) -> AnalysisManifest:
    return AnalysisManifest(
        schema_version=ANALYSIS_MANIFEST_SCHEMA_VERSION,
        window_id=window_id,
        taxonomy_version=EVENT_TAXONOMY_VERSION,
        input_digest_algorithm=INPUT_DIGEST_ALGORITHM,
        input_sha256=input_sha256,
        input_size_bytes=input_size_bytes,
        project_version=project_version,
        digit_probe_commit="b" * 40,
        alphabet_size=EVENT_ALPHABET_SIZE,
        analysis_config=AnalysisConfigurationSnapshot(schur_capacity=64),
        sample_size=sample_size,
    )


def _temporal(
    event_count: int,
    *,
    threshold: int = 10,
    timed: bool = False,
) -> TemporalBurstSummary:
    if not timed:
        return TemporalBurstSummary(
            event_count=event_count,
            timed_event_count=0,
            untimed_event_count=event_count,
            duration_us=None,
            inter_event_gap_count=0,
            minimum_gap_us=None,
            maximum_gap_us=None,
            mean_gap_us=None,
            median_gap_us=None,
            burst_threshold_us=threshold,
            burst_count=0,
            burst_event_count=0,
            largest_burst_size=0,
            longest_burst_duration_us=0,
        )
    return TemporalBurstSummary(
        event_count=event_count,
        timed_event_count=event_count,
        untimed_event_count=0,
        duration_us=event_count - 1,
        inter_event_gap_count=event_count - 1,
        minimum_gap_us=1,
        maximum_gap_us=1,
        mean_gap_us=1.0,
        median_gap_us=1.0,
        burst_threshold_us=threshold,
        burst_count=0,
        burst_event_count=0,
        largest_burst_size=0,
        longest_burst_duration_us=0,
    )


def _window(
    symbols: list[int] | None = None,
    **manifest_values: object,
) -> AnalysisWindow:
    result = _result(symbols)
    return AnalysisWindow(
        manifest=_manifest(result.sample_size, **manifest_values),
        result=result,
        temporal=_temporal(result.sample_size),
    )


def _finite_difference(
    left: int | float = 1, right: int | float = 2
) -> NumericDifference:
    return NumericDifference(
        NumericValue(NumericState.FINITE, left),
        NumericValue(NumericState.FINITE, right),
        NumericValue(NumericState.FINITE, right - left),
    )


def test_public_exports_and_dataclass_field_order() -> None:
    import system_log_dynamics.comparison as comparison

    assert comparison.__all__ == [
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
    assert [field.name for field in fields(NumericDifference)] == [
        "left",
        "right",
        "delta",
    ]
    assert [field.name for field in fields(TemporalDifference)] == [
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
    ]
    assert [field.name for field in fields(WindowComparison)] == [
        "left_window_id",
        "right_window_id",
        "compatibility",
        "counts",
        "runs",
        "gaps",
        "autocorrelation",
        "ngram_accuracy",
        "compression_ratio",
        "temporal",
    ]


def test_public_models_are_frozen_slotted_and_revalidate_on_replace() -> None:
    comparison = compare_analysis_windows(_window(), _window())
    instances = [
        NumericValue(NumericState.FINITE, 1),
        _finite_difference(),
        SymbolDifference(
            _finite_difference(),
            _finite_difference(0.1, 0.2),
        ),
        RunsDifference(
            _finite_difference(0.1, 0.2),
            _finite_difference(0.3, 0.4),
        ),
        GapDifference(
            _finite_difference(),
            _finite_difference(1.0, 2.0),
        ),
        comparison.temporal,
        comparison.compatibility,
        _window(),
        comparison,
    ]
    for instance in instances:
        assert type(instance).__slots__
        assert type(instance).__dataclass_params__.frozen
    with pytest.raises(FrozenInstanceError):
        instances[0].state = NumericState.MISSING  # type: ignore[misc]
    with pytest.raises(ValueError):
        replace(instances[0], value=nan)
    with pytest.raises(ValueError):
        replace(comparison, counts={})


@pytest.mark.parametrize(
    ("state", "value"),
    [
        (NumericState.FINITE, None),
        (NumericState.FINITE, True),
        (NumericState.FINITE, inf),
        (NumericState.MISSING, 0),
        (NumericState.NAN, nan),
        (NumericState.NOT_COMPUTABLE, 1.0),
    ],
)
def test_numeric_value_constructor_invariants(
    state: NumericState,
    value: int | float | None,
) -> None:
    with pytest.raises(ValueError):
        NumericValue(state, value)


def test_numeric_values_are_canonical_and_deltas_are_right_minus_left() -> None:
    comparison = compare_analysis_windows(_window(), _window())
    assert NumericValue(NumericState.FINITE, 3).value == 3
    assert NumericValue(NumericState.FINITE, 1.25).value == 1.25
    nan_value = comparison.ngram_accuracy[2].left
    assert nan_value == NumericValue(NumericState.NAN, None)
    assert nan_value.value is None
    assert comparison.gaps[0].mean.left == NumericValue(
        NumericState.POSITIVE_INFINITY, None
    )
    assert comparison.gaps[0].mean.delta == NumericValue(
        NumericState.NOT_COMPUTABLE, None
    )
    assert _finite_difference(5, 2).delta == NumericValue(NumericState.FINITE, -3)
    overflow = NumericDifference(
        NumericValue(NumericState.FINITE, -1.7e308),
        NumericValue(NumericState.FINITE, 1.7e308),
        NumericValue(NumericState.POSITIVE_INFINITY, None),
    )
    assert overflow.delta.state is NumericState.POSITIVE_INFINITY
    with pytest.raises(ValueError):
        NumericDifference(
            NumericValue(NumericState.NAN, None),
            NumericValue(NumericState.FINITE, 1.0),
            NumericValue(NumericState.FINITE, 0.0),
        )


def test_identical_windows_and_differing_counts_proportions_and_runs() -> None:
    left = _window()
    right_result = _result()
    counts = dict(right_result.counts)
    counts[0] += 1
    counts[1] -= 1
    right_result = replace(
        right_result,
        counts=counts,
        runs=replace(right_result.runs, z_score=nan, p_two_tailed=0.5),
    )
    right = AnalysisWindow(left.manifest, right_result, left.temporal)
    comparison = compare_analysis_windows(left, right)
    assert comparison.counts[0].count.delta.value == 1
    assert comparison.counts[1].count.delta.value == -1
    assert comparison.counts[0].proportion.delta.value == pytest.approx(1 / 9)
    assert comparison.runs.z_score.left.state is NumericState.FINITE
    assert comparison.runs.z_score.right.state is NumericState.NAN
    assert comparison.runs.z_score.delta.state is NumericState.NOT_COMPUTABLE
    assert comparison.runs.p_two_tailed.delta.value == pytest.approx(
        0.5 - left.result.runs.p_two_tailed
    )


def test_gap_autocorrelation_ngram_and_compression_comparisons() -> None:
    left = _window()
    left_gaps = dict(left.result.gaps)
    left_gaps[0] = replace(left_gaps[0], count=1, mean=1.0)
    right_result = _result()
    right_gaps = dict(right_result.gaps)
    right_gaps[0] = replace(right_gaps[0], count=2, mean=3.5)
    right_result = replace(
        right_result,
        gaps=right_gaps,
        autocorr={3: 0.3, 1: 0.1, 7: nan},
        ngram_accuracy={4: 0.4, 1: 0.1},
        compress_ratio=2.5,
    )
    left_result = replace(
        left.result,
        gaps=left_gaps,
        autocorr={2: 0.2, 1: 0.05},
        ngram_accuracy={3: 0.3, 1: 0.05},
    )
    left = AnalysisWindow(left.manifest, left_result, left.temporal)
    right = AnalysisWindow(left.manifest, right_result, left.temporal)
    comparison = compare_analysis_windows(left, right)
    assert comparison.gaps[0].count.delta.value == 1
    assert comparison.gaps[0].mean.delta.value == 2.5
    assert list(comparison.autocorrelation) == [1, 2, 3, 7]
    assert comparison.autocorrelation[2].right.state is NumericState.MISSING
    assert comparison.autocorrelation[3].left.state is NumericState.MISSING
    assert comparison.autocorrelation[7].right.state is NumericState.NAN
    assert list(comparison.ngram_accuracy) == [1, 3, 4]
    assert comparison.ngram_accuracy[3].right.state is NumericState.MISSING
    assert comparison.ngram_accuracy[4].left.state is NumericState.MISSING
    assert comparison.compression_ratio.delta.value == pytest.approx(
        2.5 - left_result.compress_ratio
    )


def test_temporal_differences_include_finite_and_missing_values() -> None:
    left = _window()
    right_temporal = _temporal(9, timed=True)
    right = AnalysisWindow(left.manifest, left.result, right_temporal)
    comparison = compare_analysis_windows(left, right)
    assert comparison.temporal.timed_event_count.delta.value == 9
    assert comparison.temporal.untimed_event_count.delta.value == -9
    assert comparison.temporal.duration_us.left.state is NumericState.MISSING
    assert comparison.temporal.duration_us.right.value == 8
    assert comparison.temporal.duration_us.delta.state is NumericState.NOT_COMPUTABLE


@pytest.mark.parametrize(
    "field",
    [
        "schema_version",
        "taxonomy_version",
        "alphabet_size",
        "digit_probe_commit",
        "analysis_config",
        "input_digest_algorithm",
    ],
)
def test_each_blocking_manifest_difference_is_rejected(field: str) -> None:
    left = _window()
    right_manifest = replace(left.manifest)
    right_temporal = _temporal(9)
    right = AnalysisWindow(right_manifest, left.result, right_temporal)
    replacement = (
        AnalysisConfigurationSnapshot(65)
        if field == "analysis_config"
        else "different"
        if field in {"taxonomy_version", "digit_probe_commit", "input_digest_algorithm"}
        else 2
    )
    object.__setattr__(right.manifest, field, replacement)
    with pytest.raises(IncompatibleAnalysisWindowsError) as error:
        compare_analysis_windows(left, right)
    assert error.value.fields == (field,)


def test_multiple_blocking_differences_are_ordered_and_threshold_blocks() -> None:
    left = _window()
    right_manifest = replace(left.manifest)
    right_temporal = _temporal(9)
    right = AnalysisWindow(right_manifest, left.result, right_temporal)
    object.__setattr__(right.manifest, "schema_version", 2)
    object.__setattr__(right.manifest, "digit_probe_commit", "c" * 40)
    object.__setattr__(right.manifest, "input_digest_algorithm", "other")
    object.__setattr__(right.temporal, "burst_threshold_us", 11)
    with pytest.raises(IncompatibleAnalysisWindowsError) as error:
        compare_analysis_windows(left, right)
    assert error.value.fields == (
        "schema_version",
        "digit_probe_commit",
        "input_digest_algorithm",
        "burst_threshold_us",
    )


def test_nonblocking_manifest_differences_are_recorded_without_hash_leakage() -> None:
    left = _window(window_id="left", input_sha256="a" * 64, input_size_bytes=100)
    right = _window(
        list(range(EVENT_ALPHABET_SIZE)) * 2,
        window_id="right",
        input_sha256="c" * 64,
        input_size_bytes=200,
        project_version="0.2.0",
    )
    comparison = compare_analysis_windows(left, right)
    assert comparison.compatibility.project_version_matches is False
    assert comparison.compatibility.window_id_matches is False
    assert comparison.compatibility.input_digest_matches is False
    assert comparison.compatibility.input_size_matches is False
    assert comparison.compatibility.sample_size_matches is False
    assert "a" * 64 not in repr(comparison)
    assert "c" * 64 not in repr(comparison)


@pytest.mark.parametrize(
    "result_update",
    [
        {"alphabet": 8},
        {"counts": {0: 9}},
        {
            "counts": dict(
                [(True, 1)] + [(symbol, 1) for symbol in range(EVENT_ALPHABET_SIZE)]
            )
        },
        {"counts": {symbol: 0 for symbol in range(EVENT_ALPHABET_SIZE)}},
        {"gaps": {0: object()}},
        {"runs": object()},
        {"autocorr": {True: 0.1}},
        {"ngram_accuracy": {1: True}},
        {"compress_ratio": True},
    ],
)
def test_malformed_digit_probe_values_are_rejected(
    result_update: dict[str, object],
) -> None:
    window = _window()
    with pytest.raises(ValueError):
        AnalysisWindow(
            window.manifest, replace(window.result, **result_update), window.temporal
        )


def test_invalid_window_relationships_and_non_windows_are_rejected() -> None:
    window = _window()
    with pytest.raises(ValueError):
        AnalysisWindow(
            replace(window.manifest, sample_size=10), window.result, window.temporal
        )
    with pytest.raises(ValueError):
        AnalysisWindow(window.manifest, window.result, _temporal(10))
    with pytest.raises(ValueError):
        compare_analysis_windows(window, object())  # type: ignore[arg-type]


def test_malformed_gap_fields_and_boolean_count_values_are_rejected() -> None:
    window = _window()
    gaps = dict(window.result.gaps)
    gaps[0] = replace(gaps[0], count=True)
    with pytest.raises(ValueError):
        AnalysisWindow(
            window.manifest, replace(window.result, gaps=gaps), window.temporal
        )
    gaps[0] = replace(gaps[0], count=0, mean=True)
    with pytest.raises(ValueError):
        AnalysisWindow(
            window.manifest, replace(window.result, gaps=gaps), window.temporal
        )
    counts = dict(window.result.counts)
    counts[0] = True
    with pytest.raises(ValueError):
        AnalysisWindow(
            window.manifest,
            replace(window.result, counts=counts),
            window.temporal,
        )


def test_output_is_ordered_immutable_defensive_and_deterministic() -> None:
    left = _window()
    right_result = replace(
        left.result,
        autocorr={5: 0.5, 1: 0.1, 3: 0.3},
        ngram_accuracy={4: 0.4, 1: 0.1, 2: 0.2},
    )
    source_autocorr = right_result.autocorr
    source_counts = dict(left.result.counts)
    source_gaps = dict(left.result.gaps)
    right = AnalysisWindow(left.manifest, right_result, left.temporal)
    first = compare_analysis_windows(left, right)
    second = compare_analysis_windows(left, right)
    assert first == second
    assert list(first.counts) == list(range(EVENT_ALPHABET_SIZE))
    assert list(first.gaps) == list(range(EVENT_ALPHABET_SIZE))
    assert list(first.autocorrelation) == [1, 2, 3, 4, 5]
    assert list(first.ngram_accuracy) == [1, 2, 3, 4]
    with pytest.raises(TypeError):
        first.counts[0] = first.counts[0]  # type: ignore[index]
    source_autocorr[9] = 0.9
    assert 9 not in first.autocorrelation
    assert left.result.counts == source_counts
    assert left.result.gaps == source_gaps


def test_analysis_window_snapshots_mutable_result_mappings() -> None:
    source_result = _result()
    window = AnalysisWindow(
        _manifest(source_result.sample_size),
        source_result,
        _temporal(source_result.sample_size),
    )

    for field_name in (
        "counts",
        "zscores",
        "gaps",
        "autocorr",
        "ngram_accuracy",
    ):
        assert getattr(window.result, field_name) is not getattr(
            source_result,
            field_name,
        )

    with pytest.raises(TypeError):
        window.result.counts[0] = -1  # type: ignore[index]

    source_result.counts[0] = 99

    assert window.result.counts[0] == 1

    assert window.result.runs is not source_result.runs
    assert window.result.gaps[0] is not source_result.gaps[0]
    assert window.result.schur is not source_result.schur

    original_run_z_score = window.result.runs.z_score
    original_gap_mean = window.result.gaps[0].mean

    object.__setattr__(
        source_result.runs,
        "z_score",
        123.5,
    )
    object.__setattr__(
        source_result.gaps[0],
        "mean",
        456.5,
    )

    assert window.result.runs.z_score == original_run_z_score
    assert window.result.gaps[0].mean == original_gap_mean

    malformed_result = _result()

    with pytest.raises(ValueError):
        AnalysisWindow(
            _manifest(malformed_result.sample_size),
            replace(
                malformed_result,
                schur=object(),
            ),
            _temporal(malformed_result.sample_size),
        )


@pytest.mark.parametrize(
    "field_name, malformed",
    [
        (
            "counts",
            {
                symbol: (-1 if symbol == 0 else 1)
                for symbol in range(EVENT_ALPHABET_SIZE)
            },
        ),
        (
            "counts",
            {symbol: 1 for symbol in range(EVENT_ALPHABET_SIZE - 1)},
        ),
        (
            "gaps",
            {
                symbol: (object() if symbol == 0 else _result().gaps[symbol])
                for symbol in range(EVENT_ALPHABET_SIZE)
            },
        ),
    ],
)
def test_comparison_revalidates_mutated_windows(
    field_name: str,
    malformed: object,
) -> None:
    window = _window()

    object.__setattr__(
        window.result,
        field_name,
        malformed,
    )

    with pytest.raises(ValueError):
        compare_analysis_windows(
            window,
            window,
        )


def test_derived_models_reject_semantically_invalid_fields() -> None:
    valid_proportion = _finite_difference(0.1, 0.2)
    valid_mean = _finite_difference(1.0, 2.0)

    with pytest.raises(ValueError):
        SymbolDifference(
            count=_finite_difference(1.5, 2.5),
            proportion=valid_proportion,
        )

    with pytest.raises(ValueError):
        GapDifference(
            count=_finite_difference(1.5, 2.5),
            mean=valid_mean,
        )

    comparison = compare_analysis_windows(
        _window(),
        _window(),
    )

    missing = NumericDifference(
        NumericValue(NumericState.MISSING, None),
        NumericValue(NumericState.MISSING, None),
        NumericValue(
            NumericState.NOT_COMPUTABLE,
            None,
        ),
    )

    with pytest.raises(ValueError):
        replace(
            comparison.temporal,
            event_count=missing,
        )


def test_compatibility_ids_and_error_fields_are_durable() -> None:
    comparison = compare_analysis_windows(
        _window(),
        _window(),
    )

    with pytest.raises(ValueError):
        replace(
            comparison.compatibility,
            left_project_version="0.1.0",
            right_project_version="0.2.0",
            project_version_matches=True,
        )

    with pytest.raises(ValueError):
        replace(
            comparison.compatibility,
            taxonomy_version="",
        )

    with pytest.raises(ValueError):
        replace(
            comparison,
            left_window_id=" padded",
        )

    with pytest.raises(ValueError):
        IncompatibleAnalysisWindowsError(
            (
                "taxonomy_version",
                "schema_version",
            )
        )

    with pytest.raises(ValueError):
        IncompatibleAnalysisWindowsError(
            (
                "schema_version",
                "schema_version",
            )
        )

    left = _window()
    right = _window()

    independent_comparison = compare_analysis_windows(
        left,
        right,
    )

    assert (
        independent_comparison.compatibility.analysis_config
        is not left.manifest.analysis_config
    )

    original_capacity = (
        independent_comparison.compatibility.analysis_config.schur_capacity
    )

    object.__setattr__(
        left.manifest.analysis_config,
        "schur_capacity",
        99,
    )

    assert (
        independent_comparison.compatibility.analysis_config.schur_capacity
        == original_capacity
    )

    corrupted_configuration = replace(
        independent_comparison.compatibility.analysis_config
    )

    object.__setattr__(
        corrupted_configuration,
        "schur_capacity",
        0,
    )

    with pytest.raises(ValueError):
        replace(
            independent_comparison.compatibility,
            analysis_config=(corrupted_configuration),
        )


def test_analysis_window_snapshots_manifest_configuration_and_temporal() -> None:
    result = _result()
    manifest = _manifest(result.sample_size)
    temporal = _temporal(result.sample_size)
    source_configuration = manifest.analysis_config

    window = AnalysisWindow(
        manifest,
        result,
        temporal,
    )

    assert window.manifest is not manifest
    assert window.manifest.analysis_config is not source_configuration
    assert window.temporal is not temporal

    object.__setattr__(
        manifest,
        "window_id",
        "mutated-window",
    )
    object.__setattr__(
        source_configuration,
        "schur_capacity",
        0,
    )
    object.__setattr__(
        temporal,
        "burst_threshold_us",
        99,
    )

    assert window.manifest.window_id == "left"
    assert window.manifest.analysis_config.schur_capacity == 64
    assert window.temporal.burst_threshold_us == 10


@pytest.mark.parametrize(
    ("target", "field_name", "malformed"),
    [
        (
            "manifest",
            "input_sha256",
            "invalid",
        ),
        (
            "manifest",
            "input_size_bytes",
            0,
        ),
        (
            "temporal",
            "longest_burst_duration_us",
            999,
        ),
    ],
)
def test_analysis_window_revalidates_corrupted_manifest_and_temporal(
    target: str,
    field_name: str,
    malformed: object,
) -> None:
    result = _result()
    manifest = _manifest(result.sample_size)
    temporal = _temporal(result.sample_size)

    candidate = manifest if target == "manifest" else temporal

    object.__setattr__(
        candidate,
        field_name,
        malformed,
    )

    with pytest.raises(ValueError):
        AnalysisWindow(
            manifest,
            result,
            temporal,
        )


@pytest.mark.parametrize(
    ("target", "field_name", "malformed"),
    [
        (
            "manifest",
            "input_sha256",
            "invalid",
        ),
        (
            "manifest",
            "input_size_bytes",
            0,
        ),
        (
            "temporal",
            "longest_burst_duration_us",
            999,
        ),
    ],
)
def test_comparison_revalidates_identically_corrupted_windows(
    target: str,
    field_name: str,
    malformed: object,
) -> None:
    left = _window()
    right = _window()

    left_candidate = left.manifest if target == "manifest" else left.temporal
    right_candidate = right.manifest if target == "manifest" else right.temporal

    object.__setattr__(
        left_candidate,
        field_name,
        malformed,
    )
    object.__setattr__(
        right_candidate,
        field_name,
        malformed,
    )

    with pytest.raises(ValueError):
        compare_analysis_windows(
            left,
            right,
        )
