"""Immutable reproducibility manifests for analyzed event windows."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from importlib import metadata
from typing import Final

from digit_probe import AnalysisConfig, AnalysisResult
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from system_log_dynamics import __version__
from system_log_dynamics.encoding import (
    EVENT_ALPHABET_SIZE,
    EVENT_TAXONOMY_VERSION,
)

ANALYSIS_MANIFEST_SCHEMA_VERSION: Final = 1
INPUT_DIGEST_ALGORITHM: Final = "sha256"

_DISTRIBUTION_NAME: Final = "system-log-dynamics"
_DIGIT_PROBE_NAME: Final = "digit-probe"
_DIGIT_PROBE_URL_PREFIX: Final = "git+https://github.com/gcomneno/digit-probe.git@"
_SHA1_PATTERN: Final = re.compile(r"[0-9a-f]{40}")
_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")


def _require_positive_integer(
    name: str,
    value: object,
) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")

    return value


def _validated_window_id(
    value: object,
) -> str | None:
    if value is None:
        return None

    if (
        not isinstance(value, str)
        or not value
        or not value.strip()
        or value != value.strip()
    ):
        raise ValueError(
            "window_id must be a non-empty string "
            "without surrounding whitespace or None"
        )

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
            f"{name} must be a non-empty string without surrounding whitespace"
        )

    return value


@dataclass(frozen=True, slots=True)
class AnalysisConfigurationSnapshot:
    """Immutable effective Digit-Probe configuration."""

    schur_capacity: int

    def __post_init__(self) -> None:
        _require_positive_integer(
            "schur_capacity",
            self.schur_capacity,
        )


@dataclass(frozen=True, slots=True)
class AnalysisManifest:
    """Reproducibility metadata for one analyzed input window."""

    schema_version: int
    window_id: str | None
    taxonomy_version: str
    input_digest_algorithm: str
    input_sha256: str
    input_size_bytes: int
    project_version: str
    digit_probe_commit: str
    alphabet_size: int
    analysis_config: AnalysisConfigurationSnapshot
    sample_size: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.schema_version, int)
            or isinstance(self.schema_version, bool)
            or self.schema_version != ANALYSIS_MANIFEST_SCHEMA_VERSION
        ):
            raise ValueError(
                "schema_version must match ANALYSIS_MANIFEST_SCHEMA_VERSION"
            )

        _validated_window_id(self.window_id)

        if self.taxonomy_version != EVENT_TAXONOMY_VERSION:
            raise ValueError("taxonomy_version must match EVENT_TAXONOMY_VERSION")

        if self.input_digest_algorithm != INPUT_DIGEST_ALGORITHM:
            raise ValueError("input_digest_algorithm must be 'sha256'")

        if (
            not isinstance(self.input_sha256, str)
            or _SHA256_PATTERN.fullmatch(self.input_sha256) is None
        ):
            raise ValueError(
                "input_sha256 must be a lowercase 64-character hexadecimal digest"
            )

        _require_positive_integer(
            "input_size_bytes",
            self.input_size_bytes,
        )
        _require_non_empty_text(
            "project_version",
            self.project_version,
        )

        if (
            not isinstance(self.digit_probe_commit, str)
            or _SHA1_PATTERN.fullmatch(self.digit_probe_commit) is None
        ):
            raise ValueError(
                "digit_probe_commit must be a lowercase 40-character hexadecimal commit"
            )

        if (
            not isinstance(self.alphabet_size, int)
            or isinstance(self.alphabet_size, bool)
            or self.alphabet_size != EVENT_ALPHABET_SIZE
        ):
            raise ValueError("alphabet_size must match EVENT_ALPHABET_SIZE")

        if not isinstance(
            self.analysis_config,
            AnalysisConfigurationSnapshot,
        ):
            raise ValueError("analysis_config must be an AnalysisConfigurationSnapshot")

        _require_positive_integer(
            "sample_size",
            self.sample_size,
        )


def _extract_digit_probe_commit(
    requirements: list[str] | None,
) -> str:
    if not requirements:
        raise RuntimeError(
            "System Log Dynamics distribution metadata "
            "must contain Requires-Dist entries"
        )

    matches: list[Requirement] = []

    for raw_requirement in requirements:
        try:
            requirement = Requirement(raw_requirement)
        except (InvalidRequirement, TypeError) as error:
            raise RuntimeError(
                "System Log Dynamics contains malformed Requires-Dist metadata"
            ) from error

        if canonicalize_name(requirement.name) == _DIGIT_PROBE_NAME:
            matches.append(requirement)

    if len(matches) != 1:
        raise RuntimeError(
            "System Log Dynamics must declare exactly one Digit-Probe requirement"
        )

    requirement = matches[0]

    if (
        requirement.url is None
        or requirement.extras
        or requirement.marker is not None
        or str(requirement.specifier)
    ):
        raise RuntimeError(
            "Digit-Probe must be an unconditional pinned Git URL requirement"
        )

    if not requirement.url.startswith(_DIGIT_PROBE_URL_PREFIX):
        raise RuntimeError(
            "Digit-Probe must use the canonical pinned Git repository URL"
        )

    commit = requirement.url[len(_DIGIT_PROBE_URL_PREFIX) :]

    if _SHA1_PATTERN.fullmatch(commit) is None:
        raise RuntimeError(
            "Digit-Probe requirement must pin one full lowercase 40-character commit"
        )

    return commit


def _distribution_contract() -> tuple[str, str]:
    try:
        distribution = metadata.distribution(_DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError as error:
        raise RuntimeError(
            "System Log Dynamics distribution metadata is unavailable"
        ) from error

    project_version = distribution.version

    if project_version != __version__:
        raise RuntimeError(
            "System Log Dynamics package and distribution versions must match"
        )

    commit = _extract_digit_probe_commit(distribution.requires)

    return project_version, commit


def _validated_analysis_result(
    result: object,
) -> AnalysisResult:
    if not isinstance(result, AnalysisResult):
        raise RuntimeError("result must be an AnalysisResult")

    if result.mode != "integers":
        raise RuntimeError("analysis result mode must be 'integers'")

    if (
        not isinstance(result.alphabet, int)
        or isinstance(result.alphabet, bool)
        or result.alphabet != EVENT_ALPHABET_SIZE
    ):
        raise RuntimeError("analysis result alphabet must match EVENT_ALPHABET_SIZE")

    if (
        not isinstance(result.sample_size, int)
        or isinstance(result.sample_size, bool)
        or result.sample_size <= 0
    ):
        raise RuntimeError("analysis result sample size must be positive")

    if (
        not isinstance(result.max_observed, int)
        or isinstance(result.max_observed, bool)
        or result.max_observed < 0
        or result.max_observed >= EVENT_ALPHABET_SIZE
    ):
        raise RuntimeError("analysis result max_observed must be in the event alphabet")

    if not isinstance(result.counts, dict):
        raise RuntimeError("analysis result counts must be a dictionary")

    expected_symbols = set(range(EVENT_ALPHABET_SIZE))

    if set(result.counts) != expected_symbols:
        raise RuntimeError(
            "analysis result counts must cover the complete event alphabet"
        )

    for symbol, count in result.counts.items():
        if (
            not isinstance(symbol, int)
            or isinstance(symbol, bool)
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count < 0
        ):
            raise RuntimeError(
                "analysis result counts must contain non-negative integer counts"
            )

    if sum(result.counts.values()) != result.sample_size:
        raise RuntimeError("analysis result counts must sum to the sample size")

    return result


def _effective_configuration_snapshot(
    config: AnalysisConfig | None,
) -> AnalysisConfigurationSnapshot:
    if config is None:
        effective_config = AnalysisConfig()
    elif isinstance(config, AnalysisConfig):
        effective_config = config
    else:
        raise TypeError("config must be an AnalysisConfig or None")

    return AnalysisConfigurationSnapshot(
        schur_capacity=effective_config.schur_capacity,
    )


def build_analysis_manifest(
    input_bytes: bytes,
    result: AnalysisResult,
    config: AnalysisConfig | None = None,
    *,
    window_id: str | None = None,
) -> AnalysisManifest:
    """Build one immutable exact-input analysis manifest."""

    if type(input_bytes) is not bytes:
        raise TypeError("input_bytes must be concrete immutable bytes")

    if not input_bytes:
        raise ValueError("input_bytes must not be empty")

    validated_window_id = _validated_window_id(window_id)
    validated_result = _validated_analysis_result(result)
    configuration = _effective_configuration_snapshot(config)
    project_version, digit_probe_commit = _distribution_contract()

    return AnalysisManifest(
        schema_version=(ANALYSIS_MANIFEST_SCHEMA_VERSION),
        window_id=validated_window_id,
        taxonomy_version=EVENT_TAXONOMY_VERSION,
        input_digest_algorithm=(INPUT_DIGEST_ALGORITHM),
        input_sha256=hashlib.sha256(input_bytes).hexdigest(),
        input_size_bytes=len(input_bytes),
        project_version=project_version,
        digit_probe_commit=digit_probe_commit,
        alphabet_size=EVENT_ALPHABET_SIZE,
        analysis_config=configuration,
        sample_size=validated_result.sample_size,
    )


__all__ = [
    "ANALYSIS_MANIFEST_SCHEMA_VERSION",
    "INPUT_DIGEST_ALGORITHM",
    "AnalysisConfigurationSnapshot",
    "AnalysisManifest",
    "build_analysis_manifest",
]
