from __future__ import annotations

import hashlib
import io
import math
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path

import pytest
from digit_probe import AnalysisResult

from system_log_dynamics.analysis import (
    analyze_classified_events,
)
from system_log_dynamics.classification import (
    iter_classified_events,
)
from system_log_dynamics.comparison import (
    AnalysisWindow,
    NumericState,
    compare_analysis_windows,
)
from system_log_dynamics.encoding import (
    EVENT_ALPHABET_SIZE,
    EVENT_TAXONOMY_VERSION,
    iter_event_symbols,
    iter_validated_event_symbols,
)
from system_log_dynamics.journal import (
    iter_normalized_journal_json_lines,
)
from system_log_dynamics.manifests import (
    ANALYSIS_MANIFEST_SCHEMA_VERSION,
    INPUT_DIGEST_ALGORITHM,
    AnalysisConfigurationSnapshot,
    AnalysisManifest,
    build_analysis_manifest,
)
from system_log_dynamics.models import (
    ClassifiedJournalEvent,
    NormalizedJournalEvent,
)
from system_log_dynamics.temporal import (
    TemporalBurstSummary,
    summarize_temporal_bursts,
)

FIXTURE_DIRECTORY = Path("fixtures/synthetic")
ROUTINE_PATH = FIXTURE_DIRECTORY / "experiment-001-routine.jsonl"
BURST_PATH = FIXTURE_DIRECTORY / "experiment-001-boot-error-burst.jsonl"

BURST_THRESHOLD_US = 100_000
DIGIT_PROBE_COMMIT = "55e3eae4c55017703e023c1aaac0838b873482db"

ROUTINE_SIZE = 4969
ROUTINE_SHA256 = "ee096cc33749b9d7d9dfd9ba69aa5c6fd582f433ec9cbaf5857a5335c7a5a3ee"
BURST_SIZE = 6888
BURST_SHA256 = "e285f66877b904fa9c6e584f1a637d0710ebfc33fb05e4b011db4a784ff7c0d7"

ROUTINE_SYMBOLS = (
    8,
    1,
    5,
    3,
    8,
    6,
    8,
    2,
    1,
    8,
    5,
    8,
    1,
    2,
    8,
    6,
    3,
    8,
    1,
    2,
    8,
    8,
    1,
    2,
)

BURST_SYMBOLS = (
    0,
    1,
    6,
    4,
    2,
    1,
    8,
    7,
    6,
    7,
    4,
    1,
    2,
    8,
    7,
    6,
    5,
    8,
    0,
    1,
    7,
    6,
    2,
    8,
)

ROUTINE_COUNTS = {
    0: 0,
    1: 5,
    2: 4,
    3: 2,
    4: 0,
    5: 2,
    6: 2,
    7: 0,
    8: 9,
}

BURST_COUNTS = {
    0: 2,
    1: 4,
    2: 3,
    3: 0,
    4: 2,
    5: 1,
    6: 4,
    7: 4,
    8: 4,
}

ROUTINE_REALTIME_US = (
    0,
    2_000_000,
    5_000_000,
    9_000_000,
    14_000_000,
    20_000_000,
    27_000_000,
    35_000_000,
    44_000_000,
    54_000_000,
    65_000_000,
    77_000_000,
    90_000_000,
    104_000_000,
    119_000_000,
    135_000_000,
    152_000_000,
    170_000_000,
    189_000_000,
    209_000_000,
    230_000_000,
    252_000_000,
    275_000_000,
    299_000_000,
)

BURST_REALTIME_US = (
    0,
    2_000_000,
    5_000_000,
    8_000_000,
    11_000_000,
    14_000_000,
    15_000_000,
    15_010_000,
    15_020_000,
    15_030_000,
    15_040_000,
    15_050_000,
    15_060_000,
    15_070_000,
    15_080_000,
    15_090_000,
    15_100_000,
    20_000_000,
    30_000_000,
    45_000_000,
    60_000_000,
    80_000_000,
    105_000_000,
    135_000_000,
)

BURST_MONOTONIC_US = (
    100_000,
    2_100_000,
    5_100_000,
    8_100_000,
    11_100_000,
    14_100_000,
    15_100_000,
    15_110_000,
    15_120_000,
    15_130_000,
    15_140_000,
    15_150_000,
    15_160_000,
    15_170_000,
    15_180_000,
    15_190_000,
    15_200_000,
    20_100_000,
    10_000,
    15_010_000,
    30_010_000,
    50_010_000,
    75_010_000,
    105_010_000,
)

ROUTINE_CLASSIFICATION = (
    ("other", "other", "fallback.other", "fallback"),
    (
        "service_started",
        "service",
        "service.message_id.started",
        "exact",
    ),
    (
        "session_boundary",
        "session",
        "session.message_id.boundary",
        "exact",
    ),
    (
        "authentication_success",
        "authentication",
        "authentication.message.success",
        "heuristic",
    ),
    ("other", "other", "fallback.other", "fallback"),
    (
        "warning",
        "network",
        "severity.priority.warning",
        "exact",
    ),
    ("other", "other", "fallback.other", "fallback"),
    (
        "service_stopped",
        "service",
        "service.message_id.stopped",
        "exact",
    ),
    (
        "service_started",
        "service",
        "service.message_id.started",
        "exact",
    ),
    ("other", "other", "fallback.other", "fallback"),
    (
        "session_boundary",
        "session",
        "session.message_id.boundary",
        "exact",
    ),
    ("other", "other", "fallback.other", "fallback"),
    (
        "service_started",
        "service",
        "service.message_id.started",
        "exact",
    ),
    (
        "service_stopped",
        "service",
        "service.message_id.stopped",
        "exact",
    ),
    ("other", "other", "fallback.other", "fallback"),
    (
        "warning",
        "kernel",
        "severity.priority.warning",
        "exact",
    ),
    (
        "authentication_success",
        "authentication",
        "authentication.message.success",
        "heuristic",
    ),
    ("other", "other", "fallback.other", "fallback"),
    (
        "service_started",
        "service",
        "service.message_id.started",
        "exact",
    ),
    (
        "service_stopped",
        "service",
        "service.message_id.stopped",
        "exact",
    ),
    ("other", "other", "fallback.other", "fallback"),
    ("other", "other", "fallback.other", "fallback"),
    (
        "service_started",
        "service",
        "service.message_id.started",
        "exact",
    ),
    (
        "service_stopped",
        "service",
        "service.message_id.stopped",
        "exact",
    ),
)

BURST_CLASSIFICATION = (
    (
        "boot_boundary",
        "kernel",
        "boot.index.changed",
        "exact",
    ),
    (
        "service_started",
        "service",
        "service.message_id.started",
        "exact",
    ),
    (
        "warning",
        "service",
        "severity.priority.warning",
        "exact",
    ),
    (
        "authentication_failure",
        "authentication",
        "authentication.message.failure",
        "heuristic",
    ),
    (
        "service_stopped",
        "service",
        "service.message_id.stopped",
        "exact",
    ),
    (
        "service_started",
        "service",
        "service.message_id.started",
        "exact",
    ),
    ("other", "other", "fallback.other", "fallback"),
    (
        "error",
        "service",
        "severity.priority.error",
        "exact",
    ),
    (
        "warning",
        "service",
        "severity.priority.warning",
        "exact",
    ),
    (
        "error",
        "service",
        "severity.priority.error",
        "exact",
    ),
    (
        "authentication_failure",
        "authentication",
        "authentication.message.failure",
        "heuristic",
    ),
    (
        "service_started",
        "service",
        "service.message_id.started",
        "exact",
    ),
    (
        "service_stopped",
        "service",
        "service.message_id.stopped",
        "exact",
    ),
    ("other", "other", "fallback.other", "fallback"),
    (
        "error",
        "service",
        "severity.priority.error",
        "exact",
    ),
    (
        "warning",
        "service",
        "severity.priority.warning",
        "exact",
    ),
    (
        "session_boundary",
        "session",
        "session.message_id.boundary",
        "exact",
    ),
    ("other", "other", "fallback.other", "fallback"),
    (
        "boot_boundary",
        "kernel",
        "boot.index.changed",
        "exact",
    ),
    (
        "service_started",
        "service",
        "service.message_id.started",
        "exact",
    ),
    (
        "error",
        "service",
        "severity.priority.error",
        "exact",
    ),
    (
        "warning",
        "service",
        "severity.priority.warning",
        "exact",
    ),
    (
        "service_stopped",
        "service",
        "service.message_id.stopped",
        "exact",
    ),
    ("other", "other", "fallback.other", "fallback"),
)


@dataclass(frozen=True, slots=True)
class ExperimentArtifacts:
    input_bytes: bytes
    normalized: tuple[NormalizedJournalEvent, ...]
    classified: tuple[ClassifiedJournalEvent, ...]
    symbols: tuple[int, ...]
    result: AnalysisResult
    manifest: AnalysisManifest
    temporal: TemporalBurstSummary
    window: AnalysisWindow


def build_artifacts(
    path: Path,
    window_id: str,
) -> ExperimentArtifacts:
    input_bytes = path.read_bytes()

    with io.StringIO(input_bytes.decode("utf-8")) as source:
        normalized = tuple(iter_normalized_journal_json_lines(source))

    classified = tuple(iter_classified_events(normalized))
    symbols = tuple(iter_event_symbols(classified))
    result = analyze_classified_events(classified)
    manifest = build_analysis_manifest(
        input_bytes,
        result,
        window_id=window_id,
    )
    temporal = summarize_temporal_bursts(
        normalized,
        burst_threshold_us=(BURST_THRESHOLD_US),
    )
    window = AnalysisWindow(
        manifest=manifest,
        result=result,
        temporal=temporal,
    )

    return ExperimentArtifacts(
        input_bytes=input_bytes,
        normalized=normalized,
        classified=classified,
        symbols=symbols,
        result=result,
        manifest=manifest,
        temporal=temporal,
        window=window,
    )


def stable_public_contract(
    value: object,
) -> object:
    """Return a deterministic public-field representation without deepcopy."""

    if type(value) is float:
        if math.isnan(value):
            return ("float", "nan")

        if math.isinf(value):
            return (
                "float",
                ("positive-infinity" if value > 0 else "negative-infinity"),
            )

        return value

    if is_dataclass(value) and not isinstance(value, type):
        return (
            type(value).__qualname__,
            tuple(
                (
                    field.name,
                    stable_public_contract(getattr(value, field.name)),
                )
                for field in fields(value)
            ),
        )

    if isinstance(value, Mapping):
        return tuple(
            sorted(
                (
                    (
                        stable_public_contract(key),
                        stable_public_contract(item),
                    )
                    for key, item in value.items()
                ),
                key=repr,
            )
        )

    if isinstance(value, tuple):
        return tuple(stable_public_contract(item) for item in value)

    if isinstance(value, list):
        return (
            "list",
            tuple(stable_public_contract(item) for item in value),
        )

    if isinstance(value, (set, frozenset)):
        return (
            type(value).__qualname__,
            tuple(
                sorted(
                    (stable_public_contract(item) for item in value),
                    key=repr,
                )
            ),
        )

    return value


def classification_contract(
    artifacts: ExperimentArtifacts,
) -> tuple[tuple[str, str, str, str], ...]:
    return tuple(
        (
            event.event_type.value,
            event.source_domain.value,
            event.rule_id,
            event.evidence.value,
        )
        for event in artifacts.classified
    )


@pytest.fixture(scope="module")
def routine() -> ExperimentArtifacts:
    return build_artifacts(
        ROUTINE_PATH,
        "experiment-001-routine",
    )


@pytest.fixture(scope="module")
def burst() -> ExperimentArtifacts:
    return build_artifacts(
        BURST_PATH,
        "experiment-001-boot-error-burst",
    )


@pytest.mark.parametrize(
    ("path", "expected_size", "expected_sha256"),
    [
        (
            ROUTINE_PATH,
            ROUTINE_SIZE,
            ROUTINE_SHA256,
        ),
        (
            BURST_PATH,
            BURST_SIZE,
            BURST_SHA256,
        ),
    ],
)
def test_exact_fixture_bytes_are_privacy_safe(
    path: Path,
    expected_size: int,
    expected_sha256: str,
) -> None:
    payload = path.read_bytes()
    lowered = payload.lower()

    assert len(payload) == expected_size
    assert payload.count(b"\n") == 24
    assert hashlib.sha256(payload).hexdigest() == expected_sha256

    for forbidden in (
        b"giancarlo",
        b"baltimora",
        b"no-one-server",
        b"/home/",
        b"_hostname",
        b"_machine_id",
        b"_uid",
        b"192.168.",
    ):
        assert forbidden not in lowered


@pytest.mark.parametrize(
    (
        "fixture_name",
        "expected_symbols",
        "expected_counts",
        "expected_realtime",
        "expected_boot_indexes",
        "expected_monotonic",
        "expected_classification",
    ),
    [
        (
            "routine",
            ROUTINE_SYMBOLS,
            ROUTINE_COUNTS,
            ROUTINE_REALTIME_US,
            (None,) * 24,
            (None,) * 24,
            ROUTINE_CLASSIFICATION,
        ),
        (
            "burst",
            BURST_SYMBOLS,
            BURST_COUNTS,
            BURST_REALTIME_US,
            (0,) * 18 + (1,) * 6,
            BURST_MONOTONIC_US,
            BURST_CLASSIFICATION,
        ),
    ],
)
def test_complete_per_window_contract(
    request: pytest.FixtureRequest,
    fixture_name: str,
    expected_symbols: tuple[int, ...],
    expected_counts: dict[int, int],
    expected_realtime: tuple[int, ...],
    expected_boot_indexes: tuple[int | None, ...],
    expected_monotonic: tuple[int | None, ...],
    expected_classification: tuple[
        tuple[str, str, str, str],
        ...,
    ],
) -> None:
    artifacts = request.getfixturevalue(fixture_name)

    assert isinstance(
        artifacts,
        ExperimentArtifacts,
    )
    assert len(artifacts.normalized) == 24
    assert tuple(event.sequence_index for event in artifacts.normalized) == tuple(
        range(24)
    )
    assert tuple(event.source_line for event in artifacts.normalized) == tuple(
        range(1, 25)
    )
    assert (
        tuple(event.relative_realtime_us for event in artifacts.normalized)
        == expected_realtime
    )
    assert (
        tuple(event.boot_index for event in artifacts.normalized)
        == expected_boot_indexes
    )
    assert (
        tuple(event.monotonic_us for event in artifacts.normalized)
        == expected_monotonic
    )

    assert classification_contract(artifacts) == expected_classification
    assert artifacts.symbols == expected_symbols
    assert tuple(iter_validated_event_symbols(artifacts.symbols)) == expected_symbols

    result = artifacts.result

    assert isinstance(result, AnalysisResult)
    assert result.mode == "integers"
    assert result.sample_size == 24
    assert result.alphabet == (EVENT_ALPHABET_SIZE)
    assert result.counts == expected_counts
    assert result.max_observed == 8
    assert set(result.gaps) == set(range(9))
    assert list(result.autocorr) == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert list(result.ngram_accuracy) == [
        1,
        2,
        3,
    ]

    manifest = artifacts.manifest

    assert manifest.schema_version == (ANALYSIS_MANIFEST_SCHEMA_VERSION)
    assert manifest.schema_version == 1
    assert manifest.taxonomy_version == (EVENT_TAXONOMY_VERSION)
    assert manifest.taxonomy_version == "1"
    assert manifest.input_digest_algorithm == (INPUT_DIGEST_ALGORITHM)
    assert manifest.input_digest_algorithm == ("sha256")
    assert manifest.project_version == "0.1.0"
    assert manifest.digit_probe_commit == (DIGIT_PROBE_COMMIT)
    assert manifest.alphabet_size == 9
    assert manifest.analysis_config == (
        AnalysisConfigurationSnapshot(schur_capacity=5000)
    )
    assert manifest.sample_size == 24
    assert manifest.input_size_bytes == len(artifacts.input_bytes)
    assert manifest.input_sha256 == (hashlib.sha256(artifacts.input_bytes).hexdigest())


def test_routine_structural_and_temporal_contract(
    routine: ExperimentArtifacts,
) -> None:
    assert routine.result.runs.z_score == (pytest.approx(1.2281698107390688))
    assert routine.result.runs.p_two_tailed == (pytest.approx(0.21938322896025414))
    assert routine.result.compress_ratio == 0.75

    assert routine.temporal == (
        TemporalBurstSummary(
            event_count=24,
            timed_event_count=24,
            untimed_event_count=0,
            duration_us=299_000_000,
            inter_event_gap_count=23,
            minimum_gap_us=2_000_000,
            maximum_gap_us=24_000_000,
            mean_gap_us=13_000_000.0,
            median_gap_us=13_000_000.0,
            burst_threshold_us=(BURST_THRESHOLD_US),
            burst_count=0,
            burst_event_count=0,
            largest_burst_size=0,
            longest_burst_duration_us=0,
        )
    )


def test_boot_error_burst_structural_contract(
    burst: ExperimentArtifacts,
) -> None:
    assert burst.result.runs.z_score == (pytest.approx(2.121384218549301))
    assert burst.result.runs.p_two_tailed == (pytest.approx(0.03388948223103002))
    assert burst.result.compress_ratio == (0.8125)

    assert burst.temporal == (
        TemporalBurstSummary(
            event_count=24,
            timed_event_count=24,
            untimed_event_count=0,
            duration_us=135_000_000,
            inter_event_gap_count=22,
            minimum_gap_us=10_000,
            maximum_gap_us=30_000_000,
            mean_gap_us=(5_681_818.181818182),
            median_gap_us=1_500_000.0,
            burst_threshold_us=(BURST_THRESHOLD_US),
            burst_count=1,
            burst_event_count=11,
            largest_burst_size=11,
            longest_burst_duration_us=(100_000),
        )
    )


def test_generic_keywords_do_not_bypass_rules(
    routine: ExperimentArtifacts,
    burst: ExperimentArtifacts,
) -> None:
    sentinels = (
        routine.classified[11],
        routine.classified[20],
        burst.classified[6],
        burst.classified[13],
    )

    assert all(
        event.event_type.value == "other"
        and event.rule_id == "fallback.other"
        and event.evidence.value == "fallback"
        for event in sentinels
    )


def test_structured_window_comparison_contract(
    routine: ExperimentArtifacts,
    burst: ExperimentArtifacts,
) -> None:
    comparison = compare_analysis_windows(
        routine.window,
        burst.window,
    )
    repeated = compare_analysis_windows(
        routine.window,
        burst.window,
    )

    assert comparison == repeated
    assert comparison.left_window_id == ("experiment-001-routine")
    assert comparison.right_window_id == ("experiment-001-boot-error-burst")

    compatibility = comparison.compatibility

    assert compatibility.schema_version == 1
    assert compatibility.taxonomy_version == "1"
    assert compatibility.alphabet_size == 9
    assert compatibility.digit_probe_commit == (DIGIT_PROBE_COMMIT)
    assert compatibility.analysis_config == (
        AnalysisConfigurationSnapshot(schur_capacity=5000)
    )
    assert compatibility.input_digest_algorithm == ("sha256")
    assert compatibility.burst_threshold_us == (BURST_THRESHOLD_US)
    assert compatibility.project_version_matches
    assert not compatibility.window_id_matches
    assert not compatibility.input_digest_matches
    assert not compatibility.input_size_matches
    assert compatibility.sample_size_matches

    expected_count_deltas = {
        symbol: (BURST_COUNTS[symbol] - ROUTINE_COUNTS[symbol]) for symbol in range(9)
    }

    for symbol, delta in expected_count_deltas.items():
        item = comparison.counts[symbol]

        assert item.count.delta.state is (NumericState.FINITE)
        assert item.count.delta.value == delta
        assert item.proportion.delta.value == (pytest.approx(delta / 24))

    assert comparison.runs.z_score.delta.value == (pytest.approx(0.8932144078102322))
    assert comparison.runs.p_two_tailed.delta.value == pytest.approx(
        -0.18549374672922412
    )
    assert comparison.compression_ratio.delta.value == pytest.approx(0.0625)

    assert list(comparison.gaps) == list(range(9))

    expected_gap_count_deltas = {
        symbol: (
            max(BURST_COUNTS[symbol] - 1, 0)
            - max(
                ROUTINE_COUNTS[symbol] - 1,
                0,
            )
        )
        for symbol in range(9)
    }

    for symbol, delta in expected_gap_count_deltas.items():
        assert comparison.gaps[symbol].count.delta.value == delta

    assert comparison.gaps[0].mean.left.state is NumericState.POSITIVE_INFINITY
    assert comparison.gaps[0].mean.delta.state is NumericState.NOT_COMPUTABLE
    assert comparison.gaps[1].mean.delta.state is NumericState.FINITE
    assert comparison.gaps[7].mean.left.state is NumericState.POSITIVE_INFINITY

    assert list(comparison.autocorrelation) == [1, 2, 3, 4, 5]
    assert all(
        item.left.state is not NumericState.MISSING
        and item.right.state is not NumericState.MISSING
        for item in (comparison.autocorrelation.values())
    )

    assert list(comparison.ngram_accuracy) == [1, 2, 3]
    assert all(
        item.left.state is not NumericState.MISSING
        and item.right.state is not NumericState.MISSING
        for item in (comparison.ngram_accuracy.values())
    )

    temporal = comparison.temporal

    assert temporal.event_count.delta.value == 0
    assert temporal.duration_us.delta.value == -164_000_000
    assert temporal.inter_event_gap_count.delta.value == -1
    assert temporal.minimum_gap_us.delta.value == -1_990_000
    assert temporal.median_gap_us.delta.value == -11_500_000.0
    assert temporal.burst_count.delta.value == 1
    assert temporal.burst_event_count.delta.value == 11
    assert temporal.largest_burst_size.delta.value == 11
    assert temporal.longest_burst_duration_us.delta.value == 100_000


def test_repeated_pipeline_execution_is_exact(
    routine: ExperimentArtifacts,
    burst: ExperimentArtifacts,
) -> None:
    repeated_routine = build_artifacts(
        ROUTINE_PATH,
        "experiment-001-routine",
    )
    repeated_burst = build_artifacts(
        BURST_PATH,
        "experiment-001-boot-error-burst",
    )

    assert stable_public_contract(repeated_routine) == stable_public_contract(routine)
    assert stable_public_contract(repeated_burst) == stable_public_contract(burst)
    assert compare_analysis_windows(
        repeated_routine.window,
        repeated_burst.window,
    ) == compare_analysis_windows(
        routine.window,
        burst.window,
    )


def test_wheel_data_files_cover_experiment_assets() -> None:
    configuration = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    data_files = configuration["tool"]["setuptools"]["data-files"]

    assert data_files == {
        "share/system-log-dynamics": ["CHANGELOG.md"],
        ("share/system-log-dynamics/docs/decisions"): ["docs/decisions/*.md"],
        ("share/system-log-dynamics/docs/experiments"): ["docs/experiments/*.md"],
        ("share/system-log-dynamics/fixtures/reports"): ["fixtures/reports/*.md"],
        ("share/system-log-dynamics/fixtures/synthetic"): [
            "fixtures/synthetic/*.jsonl"
        ],
    }
