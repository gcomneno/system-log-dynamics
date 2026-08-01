from __future__ import annotations

import io
from pathlib import Path

from system_log_dynamics.analysis import (
    analyze_classified_events,
)
from system_log_dynamics.classification import (
    iter_classified_events,
)
from system_log_dynamics.encoding import (
    EVENT_ALPHABET_SIZE,
    EVENT_TAXONOMY_VERSION,
)
from system_log_dynamics.journal import (
    iter_normalized_journal_json_lines,
)
from system_log_dynamics.manifests import (
    ANALYSIS_MANIFEST_SCHEMA_VERSION,
    INPUT_DIGEST_ALGORITHM,
    AnalysisConfigurationSnapshot,
    build_analysis_manifest,
)

EVENTS_PATH = Path("fixtures/synthetic/classification.jsonl")

EXPECTED_INPUT_SHA256 = (
    "fc837024bb502246441e81724a047e9ab74433ca34923d631a1a5170c7cdad64"
)
EXPECTED_DIGIT_PROBE_COMMIT = "55e3eae4c55017703e023c1aaac0838b873482db"
EXPECTED_COUNTS = {
    0: 2,
    1: 2,
    2: 1,
    3: 1,
    4: 1,
    5: 2,
    6: 2,
    7: 1,
    8: 2,
}


def test_complete_pipeline_builds_exact_input_manifest() -> None:
    input_bytes = EVENTS_PATH.read_bytes()

    with io.StringIO(input_bytes.decode("utf-8")) as source:
        normalized = iter_normalized_journal_json_lines(source)
        classified = iter_classified_events(normalized)
        result = analyze_classified_events(classified)

    manifest = build_analysis_manifest(
        input_bytes,
        result,
        window_id="classification-fixture",
    )

    assert result.mode == "integers"
    assert result.sample_size == 14
    assert result.alphabet == EVENT_ALPHABET_SIZE
    assert result.counts == EXPECTED_COUNTS
    assert result.max_observed == 8

    assert manifest.schema_version == (ANALYSIS_MANIFEST_SCHEMA_VERSION)
    assert manifest.schema_version == 1
    assert manifest.window_id == ("classification-fixture")
    assert manifest.taxonomy_version == (EVENT_TAXONOMY_VERSION)
    assert manifest.taxonomy_version == "1"
    assert manifest.input_digest_algorithm == (INPUT_DIGEST_ALGORITHM)
    assert manifest.input_digest_algorithm == "sha256"
    assert manifest.input_sha256 == (EXPECTED_INPUT_SHA256)
    assert manifest.input_size_bytes == 3387
    assert manifest.project_version == "0.1.0"
    assert manifest.digit_probe_commit == (EXPECTED_DIGIT_PROBE_COMMIT)
    assert manifest.alphabet_size == 9
    assert manifest.analysis_config == (
        AnalysisConfigurationSnapshot(schur_capacity=5000)
    )
    assert manifest.sample_size == 14
