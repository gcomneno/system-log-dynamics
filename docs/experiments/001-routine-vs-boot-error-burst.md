# Experiment 001 — Routine versus boot/error burst

## Status

Completed as a deterministic synthetic vertical experiment.

## Question

Which descriptive properties change when a routine synthetic session is
compared with a synthetic session containing boot boundaries, errors, and a
concentrated event burst?

The experiment describes controlled differences. It does not use any metric,
test result, or p-value as proof of anomaly, randomness, compromise,
malicious behaviour, causality, or intent.

## Windows

The experiment uses two independent JSON Lines fixtures containing 24 events
each.

### Routine session

`fixtures/synthetic/experiment-001-routine.jsonl`

The routine window models low-intensity operational activity spread over
299 seconds. It contains:

- ordinary service starts and stops;
- session boundaries;
- successful authentication;
- two priority-based warnings;
- generic operational events;
- no boot identifier;
- no error classification;
- no gap at or below the burst threshold.

The fixture is exactly 4969 bytes and has SHA-256:

```text
ee096cc33749b9d7d9dfd9ba69aa5c6fd582f433ec9cbaf5857a5335c7a5a3ee
```

Its exact symbol sequence is:

```text
8 1 5 3 8 6 8 2 1 8 5 8 1 2 8 6 3 8 1 2 8 8 1 2
```

### Boot, error, and burst session

`fixtures/synthetic/experiment-001-boot-error-burst.jsonl`

The second window models two synthetic boot contexts, service lifecycle
activity, authentication failures, priority-based warnings and errors, and
one deliberately concentrated timed cluster.

The fixture is exactly 6888 bytes and has SHA-256:

```text
e285f66877b904fa9c6e584f1a637d0710ebfc33fb05e4b011db4a784ff7c0d7
```

Its exact symbol sequence is:

```text
0 1 6 4 2 1 8 7 6 7 4 1 2 8 7 6 5 8 0 1 7 6 2 8
```

The boot identifiers, account descriptions, services, messages, and
timestamps are synthetic. No event was copied or adapted from a production
journal.

## Exact pipeline

Each fixture passes through public APIs only:

```text
exact JSON Lines bytes
    -> iter_normalized_journal_json_lines()
    -> iter_classified_events()
    -> iter_event_symbols()
    -> iter_validated_event_symbols()
    -> analyze_classified_events()
    -> build_analysis_manifest()
    -> summarize_temporal_bursts()
    -> AnalysisWindow
```

The resulting windows are compared with:

```text
compare_analysis_windows(left, right)
    -> WindowComparison
```

No private implementation helper is part of the experiment contract.

## Classification design

Service lifecycle events use the stable systemd message identifiers already
recognized by the classifier.

Warnings and errors use explicit journal priorities:

- priority 4 produces `warning`;
- priorities 0 through 3 produce `error`.

Authentication outcomes use an authentication source domain and existing
phrases recognized by the classifier.

The fixtures also include messages containing the words `Error` and
`Warning` at ordinary priority. These remain `other` through
`fallback.other`, demonstrating that generic keywords do not bypass the
classifier contract.

## Temporal threshold

Both windows use an explicit threshold of:

```text
100000 microseconds
```

The threshold was chosen to separate the designed scales of the fixtures:

- every routine gap is at least 2,000,000 microseconds;
- the concentrated cluster contains ten consecutive gaps of 10,000
  microseconds.

At this threshold the routine window contains no burst. The second window
contains one burst of 11 events lasting 100,000 microseconds.

The threshold is an experimental grouping parameter, not an anomaly or
security threshold.

## Stable per-window outputs

| Property | Routine | Boot/error/burst |
| --- | ---: | ---: |
| Events | 24 | 24 |
| Duration in microseconds | 299000000 | 135000000 |
| Adjacent timed gaps | 23 | 22 |
| Minimum gap | 2000000 | 10000 |
| Median gap | 13000000 | 1500000 |
| Burst count | 0 | 1 |
| Events in bursts | 0 | 11 |
| Largest burst | 0 | 11 |
| Longest burst duration | 0 | 100000 |
| Runs z-score | 1.2281698107390688 | 2.121384218549301 |
| Compression ratio | 0.75 | 0.8125 |

The exact source sizes, hashes, normalized coordinates, classification
metadata, symbol sequences, counts, selected structural statistics,
manifests, and temporal summaries are executable contracts in
`tests/test_experiment_001.py`.

Floating-point values that are not necessary to identify the experiment are
not exhaustively frozen.

## Stable count differences

All deltas use the convention `right - left`.

| Symbol | Event type | Count delta |
| ---: | --- | ---: |
| 0 | boot boundary | 2 |
| 1 | service started | -1 |
| 2 | service stopped | -1 |
| 3 | authentication success | -2 |
| 4 | authentication failure | 2 |
| 5 | session boundary | -1 |
| 6 | warning | 2 |
| 7 | error | 4 |
| 8 | other | -5 |

Because both windows contain 24 samples, each proportion delta is the
corresponding count delta divided by 24.

## Stable temporal differences

The structured comparison records:

- duration delta: `-164000000` microseconds;
- adjacent timed-gap-count delta: `-1`;
- minimum-gap delta: `-1990000` microseconds;
- median-gap delta: `-11500000` microseconds;
- burst-count delta: `1`;
- burst-event-count delta: `11`;
- largest-burst-size delta: `11`;
- longest-burst-duration delta: `100000` microseconds.

The comparison also covers all nine per-symbol gap results, autocorrelation
lags 1 through 5, n-gram orders 1 through 3, runs values, and compression
ratio.

## Compatibility and provenance

Both windows use:

- manifest schema version 1;
- taxonomy version 1;
- alphabet size 9;
- SHA-256 input digests;
- Digit-Probe commit
  `55e3eae4c55017703e023c1aaac0838b873482db`;
- Schur capacity 5000;
- burst threshold 100000 microseconds;
- project version 0.1.0;
- sample size 24.

The window identifiers, exact input hashes, and input sizes differ by design.
These are descriptive provenance differences and do not block comparison.

## Interpretation limits

The experiment establishes that the public pipeline can preserve and compare
deliberately different synthetic structures.

It does not establish:

- whether either sequence is anomalous;
- whether either window resembles a compromised system;
- whether the sequence is random or non-random in a general sense;
- statistical significance outside the exact synthetic construction;
- causality, malicious behaviour, or human intent.

The runs p-values and all other metrics remain descriptive outputs of this
controlled experiment.

## Presentation boundary

Experiment 001 produces structured Python values only.

Markdown report rendering, command-line presentation, live journal
collection, automatic labels, threshold policy, and security interpretation
remain outside this issue and belong to later reporting or orchestration
work.
