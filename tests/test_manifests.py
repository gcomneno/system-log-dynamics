from __future__ import annotations

import hashlib
import tomllib
from dataclasses import FrozenInstanceError, replace
from importlib import metadata
from pathlib import Path
from types import SimpleNamespace

import pytest
from digit_probe import (
    AnalysisConfig,
    AnalysisResult,
    analyze_integer_symbols,
)

import system_log_dynamics
import system_log_dynamics.manifests as manifests_module
from system_log_dynamics.encoding import (
    EVENT_ALPHABET_SIZE,
    EVENT_TAXONOMY_VERSION,
)
from system_log_dynamics.manifests import (
    ANALYSIS_MANIFEST_SCHEMA_VERSION,
    INPUT_DIGEST_ALGORITHM,
    AnalysisConfigurationSnapshot,
    AnalysisManifest,
    build_analysis_manifest,
)

EXPECTED_COMMIT = "55e3eae4c55017703e023c1aaac0838b873482db"
EXPECTED_REQUIREMENT = (
    f"digit-probe @ git+https://github.com/gcomneno/digit-probe.git@{EXPECTED_COMMIT}"
)


def make_result(
    symbols: list[int] | None = None,
    *,
    config: AnalysisConfig | None = None,
) -> AnalysisResult:
    return analyze_integer_symbols(
        symbols or [0, 1, 5, 8],
        alphabet=EVENT_ALPHABET_SIZE,
        config=config,
    )


def patch_distribution(
    monkeypatch: pytest.MonkeyPatch,
    *,
    version: str = "0.1.0",
    requirements: list[str] | None = None,
) -> None:
    selected_requirements = (
        [EXPECTED_REQUIREMENT] if requirements is None else requirements
    )
    distribution = SimpleNamespace(
        version=version,
        requires=selected_requirements,
    )

    def fake_distribution(
        name: str,
    ) -> SimpleNamespace:
        assert name == "system-log-dynamics"
        return distribution

    monkeypatch.setattr(
        manifests_module.metadata,
        "distribution",
        fake_distribution,
    )


def build_valid_manifest(
    monkeypatch: pytest.MonkeyPatch,
    *,
    input_bytes: bytes = b'{"synthetic":true}\n',
    result: AnalysisResult | None = None,
    config: AnalysisConfig | None = None,
    window_id: str | None = "routine-session",
) -> AnalysisManifest:
    patch_distribution(monkeypatch)

    return build_analysis_manifest(
        input_bytes,
        result or make_result(config=config),
        config=config,
        window_id=window_id,
    )


def test_manifest_constants_are_explicit() -> None:
    assert ANALYSIS_MANIFEST_SCHEMA_VERSION == 1
    assert EVENT_TAXONOMY_VERSION == "1"
    assert INPUT_DIGEST_ALGORITHM == "sha256"


def test_packaging_is_a_direct_runtime_dependency() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert "packaging>=24" in data["project"]["dependencies"]


def test_package_and_installed_versions_match() -> None:
    assert metadata.version("system-log-dynamics") == system_log_dynamics.__version__


def test_configuration_snapshot_is_immutable() -> None:
    snapshot = AnalysisConfigurationSnapshot(schur_capacity=64)

    with pytest.raises(FrozenInstanceError):
        snapshot.schur_capacity = 32  # type: ignore[misc]


@pytest.mark.parametrize(
    "value",
    [0, -1, True, 1.5, "64", None],
)
def test_configuration_snapshot_rejects_invalid_capacity(
    value: object,
) -> None:
    with pytest.raises(ValueError):
        AnalysisConfigurationSnapshot(
            schur_capacity=value,  # type: ignore[arg-type]
        )


def test_builder_records_default_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_bytes = b'{"synthetic":true}\n'
    result = make_result()

    manifest = build_valid_manifest(
        monkeypatch,
        input_bytes=input_bytes,
        result=result,
    )

    assert manifest == AnalysisManifest(
        schema_version=1,
        window_id="routine-session",
        taxonomy_version="1",
        input_digest_algorithm="sha256",
        input_sha256=hashlib.sha256(input_bytes).hexdigest(),
        input_size_bytes=len(input_bytes),
        project_version="0.1.0",
        digit_probe_commit=EXPECTED_COMMIT,
        alphabet_size=9,
        analysis_config=(AnalysisConfigurationSnapshot(schur_capacity=5000)),
        sample_size=4,
    )


def test_builder_snapshots_explicit_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = AnalysisConfig(schur_capacity=64)
    result = make_result(config=config)
    original_counts = dict(result.counts)

    manifest = build_valid_manifest(
        monkeypatch,
        result=result,
        config=config,
    )

    assert manifest.analysis_config == (
        AnalysisConfigurationSnapshot(schur_capacity=64)
    )
    assert result.counts == original_counts
    assert config.schur_capacity == 64


def test_manifest_is_immutable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = build_valid_manifest(monkeypatch)

    with pytest.raises(FrozenInstanceError):
        manifest.sample_size = 99  # type: ignore[misc]


def test_builder_hashes_exact_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compact = b'{"value":1}\n'
    formatted = b'{ "value": 1 }\n'

    first = build_valid_manifest(
        monkeypatch,
        input_bytes=compact,
    )
    second = build_valid_manifest(
        monkeypatch,
        input_bytes=formatted,
    )

    assert first.input_sha256 == hashlib.sha256(compact).hexdigest()
    assert second.input_sha256 == hashlib.sha256(formatted).hexdigest()
    assert first.input_sha256 != second.input_sha256


class DerivedBytes(bytes):
    pass


@pytest.mark.parametrize(
    "value",
    [
        bytearray(b"data"),
        memoryview(b"data"),
        "data",
        DerivedBytes(b"data"),
    ],
)
def test_builder_requires_concrete_bytes(
    monkeypatch: pytest.MonkeyPatch,
    value: object,
) -> None:
    patch_distribution(monkeypatch)

    with pytest.raises(
        TypeError,
        match="concrete immutable bytes",
    ):
        build_analysis_manifest(
            value,  # type: ignore[arg-type]
            make_result(),
        )


def test_builder_rejects_empty_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_distribution(monkeypatch)

    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        build_analysis_manifest(
            b"",
            make_result(),
        )


@pytest.mark.parametrize(
    "value",
    ["", " ", " padded", "padded ", 1, True],
)
def test_builder_rejects_invalid_window_id(
    monkeypatch: pytest.MonkeyPatch,
    value: object,
) -> None:
    patch_distribution(monkeypatch)

    with pytest.raises(ValueError):
        build_analysis_manifest(
            b"input",
            make_result(),
            window_id=value,  # type: ignore[arg-type]
        )


def test_builder_preserves_window_id_exactly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = build_valid_manifest(
        monkeypatch,
        window_id="boot-error-burst",
    )

    assert manifest.window_id == "boot-error-burst"


def test_builder_accepts_missing_window_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = build_valid_manifest(
        monkeypatch,
        window_id=None,
    )

    assert manifest.window_id is None


def test_builder_rejects_non_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_distribution(monkeypatch)

    with pytest.raises(RuntimeError):
        build_analysis_manifest(
            b"input",
            object(),  # type: ignore[arg-type]
        )


def test_builder_rejects_digit_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_distribution(monkeypatch)
    result = replace(
        make_result(),
        mode="digits",
    )

    with pytest.raises(
        RuntimeError,
        match="mode",
    ):
        build_analysis_manifest(
            b"input",
            result,
        )


@pytest.mark.parametrize(
    "alphabet",
    [8, 10, 9.0, True],
)
def test_builder_rejects_invalid_result_alphabet(
    monkeypatch: pytest.MonkeyPatch,
    alphabet: object,
) -> None:
    patch_distribution(monkeypatch)
    result = replace(
        make_result(),
        alphabet=alphabet,  # type: ignore[arg-type]
    )

    with pytest.raises(
        RuntimeError,
        match="alphabet",
    ):
        build_analysis_manifest(
            b"input",
            result,
        )


@pytest.mark.parametrize(
    "sample_size",
    [0, -1, True, 1.5],
)
def test_builder_rejects_invalid_sample_size(
    monkeypatch: pytest.MonkeyPatch,
    sample_size: object,
) -> None:
    patch_distribution(monkeypatch)
    result = replace(
        make_result(),
        sample_size=sample_size,  # type: ignore[arg-type]
    )

    with pytest.raises(
        RuntimeError,
        match="sample size",
    ):
        build_analysis_manifest(
            b"input",
            result,
        )


@pytest.mark.parametrize(
    "max_observed",
    [None, -1, 9, True, 1.5],
)
def test_builder_rejects_invalid_max_observed(
    monkeypatch: pytest.MonkeyPatch,
    max_observed: object,
) -> None:
    patch_distribution(monkeypatch)
    result = replace(
        make_result(),
        max_observed=max_observed,  # type: ignore[arg-type]
    )

    with pytest.raises(
        RuntimeError,
        match="max_observed",
    ):
        build_analysis_manifest(
            b"input",
            result,
        )


def test_builder_rejects_incomplete_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_distribution(monkeypatch)
    counts = dict(make_result().counts)
    counts.pop(8)
    result = replace(
        make_result(),
        counts=counts,
    )

    with pytest.raises(
        RuntimeError,
        match="complete event alphabet",
    ):
        build_analysis_manifest(
            b"input",
            result,
        )


def test_builder_rejects_invalid_count_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_distribution(monkeypatch)
    counts = dict(make_result().counts)
    counts[0] = True
    result = replace(
        make_result(),
        counts=counts,
    )

    with pytest.raises(
        RuntimeError,
        match="non-negative integer",
    ):
        build_analysis_manifest(
            b"input",
            result,
        )


def test_builder_rejects_count_sum_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_distribution(monkeypatch)
    counts = dict(make_result().counts)
    counts[0] += 1
    result = replace(
        make_result(),
        counts=counts,
    )

    with pytest.raises(
        RuntimeError,
        match="sum to",
    ):
        build_analysis_manifest(
            b"input",
            result,
        )


def test_builder_rejects_invalid_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_distribution(monkeypatch)

    with pytest.raises(TypeError):
        build_analysis_manifest(
            b"input",
            make_result(),
            config=object(),  # type: ignore[arg-type]
        )


def test_builder_rejects_missing_distribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_distribution(
        name: str,
    ) -> None:
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(
        manifests_module.metadata,
        "distribution",
        missing_distribution,
    )

    with pytest.raises(
        RuntimeError,
        match="metadata is unavailable",
    ):
        build_analysis_manifest(
            b"input",
            make_result(),
        )


def test_builder_rejects_version_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_distribution(
        monkeypatch,
        version="9.9.9",
    )

    with pytest.raises(
        RuntimeError,
        match="versions must match",
    ):
        build_analysis_manifest(
            b"input",
            make_result(),
        )


@pytest.mark.parametrize(
    "requirements",
    [
        [],
        ["pytest>=8"],
        [
            EXPECTED_REQUIREMENT,
            EXPECTED_REQUIREMENT,
        ],
        ["digit-probe>=1"],
        ["digit-probe @ "],
        [
            "digit-probe @ "
            "https://github.com/gcomneno/"
            f"digit-probe.git@{EXPECTED_COMMIT}"
        ],
        ["digit-probe @ git+https://github.com/gcomneno/digit-probe.git"],
        ["digit-probe @ git+https://github.com/gcomneno/digit-probe.git@abc123"],
    ],
)
def test_builder_rejects_invalid_dependency_metadata(
    monkeypatch: pytest.MonkeyPatch,
    requirements: list[str],
) -> None:
    patch_distribution(
        monkeypatch,
        requirements=requirements,
    )

    with pytest.raises(RuntimeError):
        build_analysis_manifest(
            b"input",
            make_result(),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", 2),
        ("taxonomy_version", "2"),
        ("input_digest_algorithm", "sha1"),
        ("input_sha256", "A" * 64),
        ("input_size_bytes", 0),
        ("project_version", ""),
        ("digit_probe_commit", "abc123"),
        ("alphabet_size", 8),
        ("analysis_config", object()),
        ("sample_size", 0),
        ("window_id", " padded"),
    ],
)
def test_manifest_rejects_invalid_manual_state(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    manifest = build_valid_manifest(monkeypatch)

    with pytest.raises(ValueError):
        replace(
            manifest,
            **{field: value},
        )
