# System Log Dynamics analysis — experiment\-001\-routine

Results are descriptive and representation-dependent. They are not proof of anomaly, compromise, malicious behaviour, randomness, causality, or intent. Unavailable metrics remain unavailable rather than being coerced to zero.

## Plain-language summary

- This window contains 24 events across 6 of 9 configured event categories.
- The most frequent category is other with 9 events (37.5%).
- Absent categories: boot\_boundary, authentication\_failure, and error.
- The category counts are unevenly distributed in this window.
- The encoded sequence has a runs z-score of 1.22817 and a compression ratio of 0.75; these values describe ordering and repetition only.
- These observations are descriptive and are not proof of anomaly, compromise, malicious behaviour, randomness, causality, safety, or intent.

## Taxonomy coverage

| Metric | Value |
| --- | --- |
| Status | mixed |
| Named event count | 15 |
| Named event proportion | 62.5% |
| Other event count | 9 |
| Other event proportion | 37.5% |
| Represented named category count | 5 |
| Absent named category count | 3 |
| Represented named event types | service\_started, service\_stopped, authentication\_success, session\_boundary, and warning |
| Absent named event types | boot\_boundary, authentication\_failure, and error |

Taxonomy coverage describes how many events map to named taxonomy categories rather than `other`. It is not a classifier-quality score, anomaly score, threat score, or security conclusion.

## Provenance

| Field | Value |
| --- | --- |
| Window identifier | experiment\-001\-routine |
| Manifest schema | 1 |
| Taxonomy version | 1 |
| Input digest algorithm | sha256 |
| Input SHA-256 | ee096cc33749b9d7d9dfd9ba69aa5c6fd582f433ec9cbaf5857a5335c7a5a3ee |
| Input size (bytes) | 4969 |
| Project version | 0\.1\.0 |
| Digit-Probe commit | 55e3eae4c55017703e023c1aaac0838b873482db |
| Alphabet size | 9 |
| Schur capacity | 5000 |
| Sample size | 24 |

## Analysis summary

| Metric | Value |
| --- | --- |
| Mode | integers |
| Sample size | 24 |
| Alphabet size | 9 |
| Maximum observed symbol | 8 |
| Expected per bin | 2.666667 |
| Chi-square | 26.25 |

## Symbol distribution

| Symbol | Event type | Count | Proportion | Z-score |
| --- | --- | --- | --- | --- |
| 0 | boot_boundary | 0 | 0% | -1.632993 |
| 1 | service_started | 5 | 20.83% | 1.428869 |
| 2 | service_stopped | 4 | 16.67% | 0.816497 |
| 3 | authentication_success | 2 | 8.33% | -0.408248 |
| 4 | authentication_failure | 0 | 0% | -1.632993 |
| 5 | session_boundary | 2 | 8.33% | -0.408248 |
| 6 | warning | 2 | 8.33% | -0.408248 |
| 7 | error | 0 | 0% | -1.632993 |
| 8 | other | 9 | 37.5% | 3.878359 |

## Runs and compression

| Metric | Value |
| --- | --- |
| Runs z-score | 1.22817 |
| Runs two-tailed p-value | 0.219383 |
| Compression ratio | 0.75 |

## Symbol gaps

| Symbol | Event type | Gap count | Mean gap |
| --- | --- | --- | --- |
| 0 | boot_boundary | 0 | +infinity |
| 1 | service_started | 4 | 5.25 |
| 2 | service_stopped | 3 | 5.333333 |
| 3 | authentication_success | 1 | 13 |
| 4 | authentication_failure | 0 | +infinity |
| 5 | session_boundary | 1 | 8 |
| 6 | warning | 1 | 10 |
| 7 | error | 0 | +infinity |
| 8 | other | 8 | 2.625 |

## Autocorrelation

| Lag | Value |
| --- | --- |
| 1 | -0.181143 |
| 2 | -0.34094 |
| 3 | -0.150462 |
| 4 | 0.067256 |
| 5 | 0.149785 |

## N-gram accuracy

| Order | Accuracy |
| --- | --- |
| 1 | 0.4 |
| 2 | 0 |
| 3 | 0 |

## Schur metrics

| Metric | Value |
| --- | --- |
| Triples | 276 |
| Matching triples | 22 |
| Expected | 30.666667 |
| Fraction | 0.07971 |
| Z-score | -1.65995 |
| First matching relation index | 12 |

## Temporal and burst summary

| Metric | Value |
| --- | --- |
| Event count | 24 |
| Timed event count | 24 |
| Untimed event count | 0 |
| Duration (µs) | 299000000 |
| Inter-event gap count | 23 |
| Minimum gap (µs) | 2000000 |
| Maximum gap (µs) | 24000000 |
| Mean gap (µs) | 13000000 |
| Median gap (µs) | 13000000 |
| Burst threshold (µs) | 100000 |
| Burst count | 0 |
| Burst event count | 0 |
| Largest burst size | 0 |
| Longest burst duration (µs) | 0 |

## Methodology and reproducibility

This report was rendered exclusively from a validated `AnalysisWindow`. Taxonomy coverage is derived deterministically from its validated count snapshot. Rendering performs no file access, metadata lookup, Git inspection, network access, classifier execution, or interpretive inference.
