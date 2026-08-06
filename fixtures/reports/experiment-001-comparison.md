# System Log Dynamics comparison — experiment\-001\-routine vs experiment\-001\-boot\-error\-burst

Results are descriptive and representation-dependent. All deltas use `right - left`. Differences are not proof of anomaly, compromise, malicious behaviour, randomness, causality, or intent. Synthetic Experiment 001 results do not establish production behaviour. Missing and non-finite metrics remain explicit rather than being coerced to zero.

## Compatibility summary

| Field | Value |
| --- | --- |
| Manifest schema | 1 |
| Taxonomy version | 1 |
| Alphabet size | 9 |
| Digit-Probe commit | 55e3eae4c55017703e023c1aaac0838b873482db |
| Schur capacity | 5000 |
| Input digest algorithm | sha256 |
| Burst threshold (µs) | 100000 |
| Project versions match | yes |
| Window identifiers match | no |
| Input digests match | no |
| Input sizes match | no |
| Sample sizes match | yes |

## Window manifests

| Field | Left | Right |
| --- | --- | --- |
| Window identifier | experiment\-001\-routine | experiment\-001\-boot\-error\-burst |
| Input SHA-256 | ee096cc33749b9d7d9dfd9ba69aa5c6fd582f433ec9cbaf5857a5335c7a5a3ee | e285f66877b904fa9c6e584f1a637d0710ebfc33fb05e4b011db4a784ff7c0d7 |
| Input size (bytes) | 4969 | 6888 |
| Project version | 0\.1\.0 | 0\.1\.0 |
| Sample size | 24 | 24 |

## Taxonomy coverage comparison

| Metric | Left | Right | Delta (right - left) |
| --- | --- | --- | --- |
| Status | mixed | mixed | not applicable |
| Named event count | 15 | 20 | 5 |
| Named event proportion | 62.5% | 83.33% | 20.83% |
| Other event count | 9 | 4 | -5 |
| Other event proportion | 37.5% | 16.67% | -20.83% |
| Represented named category count | 5 | 7 | 2 |

| Change | Event types |
| --- | --- |
| Newly represented named event types | boot\_boundary, authentication\_failure, and error |
| Newly absent named event types | authentication\_success |

Coverage differences describe changes in taxonomy representation only. They are not evidence of classifier quality, anomaly, threat, compromise, causality, safety, or intent.

## Event counts and proportions

| Symbol | Event type | Left count | Right count | Delta | Left proportion | Right proportion | Delta proportion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | boot_boundary | 0 | 2 | 2 | 0% | 8.33% | 8.33% |
| 1 | service_started | 5 | 4 | -1 | 20.83% | 16.67% | -4.17% |
| 2 | service_stopped | 4 | 3 | -1 | 16.67% | 12.5% | -4.17% |
| 3 | authentication_success | 2 | 0 | -2 | 8.33% | 0% | -8.33% |
| 4 | authentication_failure | 0 | 2 | 2 | 0% | 8.33% | 8.33% |
| 5 | session_boundary | 2 | 1 | -1 | 8.33% | 4.17% | -4.17% |
| 6 | warning | 2 | 4 | 2 | 8.33% | 16.67% | 8.33% |
| 7 | error | 0 | 4 | 4 | 0% | 16.67% | 16.67% |
| 8 | other | 9 | 4 | -5 | 37.5% | 16.67% | -20.83% |

## Runs and compression

| Metric | Left | Right | Delta (right - left) |
| --- | --- | --- | --- |
| Runs z-score | 1.22817 | 2.121384 | 0.893214 |
| Runs two-tailed p-value | 0.219383 | 0.033889 | -0.185494 |
| Compression ratio | 0.75 | 0.8125 | 0.0625 |

## Symbol gaps

| Symbol | Event type | Left count | Right count | Count delta | Left mean | Right mean | Mean delta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | boot_boundary | 0 | 1 | 1 | +infinity | 18 | not computable |
| 1 | service_started | 4 | 3 | -1 | 5.25 | 6 | 0.75 |
| 2 | service_stopped | 3 | 2 | -1 | 5.333333 | 9 | 3.666667 |
| 3 | authentication_success | 1 | 0 | -1 | 13 | +infinity | not computable |
| 4 | authentication_failure | 0 | 1 | 1 | +infinity | 7 | not computable |
| 5 | session_boundary | 1 | 0 | -1 | 8 | +infinity | not computable |
| 6 | warning | 1 | 3 | 2 | 10 | 6.333333 | -3.666667 |
| 7 | error | 0 | 3 | 3 | +infinity | 4.333333 | not computable |
| 8 | other | 8 | 3 | -5 | 2.625 | 5.666667 | 3.041667 |

## Autocorrelation

| Lag | Left | Right | Delta (right - left) |
| --- | --- | --- | --- |
| 1 | -0.181143 | 0.113297 | 0.29444 |
| 2 | -0.34094 | -0.311284 | 0.029656 |
| 3 | -0.150462 | -0.021516 | 0.128946 |
| 4 | 0.067256 | 0.015809 | -0.051447 |
| 5 | 0.149785 | -0.315001 | -0.464786 |

## N-gram accuracy

| Order | Left | Right | Delta (right - left) |
| --- | --- | --- | --- |
| 1 | 0.4 | 0.2 | -0.2 |
| 2 | 0 | 0 | 0 |
| 3 | 0 | 0 | 0 |

## Temporal and burst comparison

| Metric | Left | Right | Delta (right - left) |
| --- | --- | --- | --- |
| Event count | 24 | 24 | 0 |
| Timed event count | 24 | 24 | 0 |
| Untimed event count | 0 | 0 | 0 |
| Duration (µs) | 299000000 | 135000000 | -164000000 |
| Inter-event gap count | 23 | 22 | -1 |
| Minimum gap (µs) | 2000000 | 10000 | -1990000 |
| Maximum gap (µs) | 24000000 | 30000000 | 6000000 |
| Mean gap (µs) | 13000000 | 5681818.181818 | -7318181.818182 |
| Median gap (µs) | 13000000 | 1500000 | -11500000 |
| Burst count | 0 | 1 | 1 |
| Burst event count | 0 | 11 | 11 |
| Largest burst size | 0 | 11 | 11 |
| Longest burst duration (µs) | 0 | 100000 | 100000 |

## Descriptive conclusions

Observed count differences occur for these event types: boot_boundary, service_started, service_stopped, authentication_success, authentication_failure, session_boundary, warning, error, other. The temporal table records the corresponding observed timing and burst differences. These statements describe the supplied representations only and do not establish their cause or significance.

## Methodology and reproducibility

This report was rendered exclusively from a validated `WindowComparisonReport`. Taxonomy coverage differences are derived deterministically from the validated count snapshots. Rendering performs no file access, metadata lookup, Git inspection, network access, classifier execution, compatibility decision, or interpretive inference.
