# System Log Dynamics

System Log Dynamics is a reproducible Learning in Public laboratory for
transforming Linux journal events into discrete symbolic sequences and
analyzing them through the public Python API of Digit-Probe.

## Status

The strict journal JSON Lines parser, privacy-safe normalizer,
deterministic streaming classifier, validated integer encoding, validated
Digit-Probe analysis, reproducible per-window analysis manifests, deterministic
immutable temporal burst summaries, typed structured comparison,
deterministic Markdown reporting, and file-based command-line interface are
implemented.

Experiment 001 exercises the complete public pipeline with two reproducible
synthetic windows through both the Python API and the installed console
script.

## Purpose

The project studies descriptive properties of event sequences, including
operational routines, periodicity, bursts, recurring patterns, local
predictability, and changes between temporal windows.

It does not attempt to certify randomness, security, compromise, user
behaviour, or administrator intent.

## Data policy

The public repository contains only synthetic or carefully anonymized
fixtures. Real journal exports, usernames, hostnames, addresses, tokens,
identifiers, private paths, and other sensitive material must not be
committed.

## Initial pipeline

Linux journal export → normalization → anonymization → classification →
integer symbols → Digit-Probe analysis → structured window comparison →
deterministic Markdown reporting.

## Experiment 001

Experiment 001 compares a low-intensity routine synthetic window with a
synthetic window containing boot boundaries, service lifecycle activity,
warnings, errors, authentication failures, and a concentrated event burst.

Both 24-event fixtures pass through the public pipeline from exact JSON Lines
bytes to `WindowComparison`. Their byte lengths, SHA-256 digests, normalized
coordinates, classification metadata, symbol sequences, manifests, temporal
summaries, and selected comparison values are executable contracts.

See
`docs/experiments/001-routine-vs-boot-error-burst.md`
for the completed specification, interpretation limits, and exact generated
report contracts.

The reporting API exposes:

```python
render_analysis_window_markdown(window)
build_window_comparison_report(left, right)
render_window_comparison_markdown(report)
```

Reviewed golden outputs are stored in:

```text
fixtures/reports/experiment-001-routine.md
fixtures/reports/experiment-001-comparison.md
```

## Command-line interface

After installation, the file-based pipeline is available through:

```text
system-log-dynamics analyze INPUT.jsonl
system-log-dynamics compare LEFT.jsonl RIGHT.jsonl
```

Both commands:

- read each input as exact immutable bytes;
- decode JSON Lines with strict UTF-8;
- use only the existing public analysis and reporting pipeline;
- write deterministic UTF-8 Markdown to standard output by default;
- never access the live journal, Git state, environment metadata, or the
  network;
- never modify an input file.

A single window can be analyzed with an explicit stable identifier:

```console
system-log-dynamics analyze \
    fixtures/synthetic/experiment-001-routine.jsonl \
    --window-id experiment-001-routine
```

Two windows can be compared with independent identifiers:

```console
system-log-dynamics compare \
    fixtures/synthetic/experiment-001-routine.jsonl \
    fixtures/synthetic/experiment-001-boot-error-burst.jsonl \
    --left-window-id experiment-001-routine \
    --right-window-id experiment-001-boot-error-burst
```

Common options are:

- `--burst-threshold-us MICROSECONDS`, a positive temporal threshold with
  default `100000`;
- `--schur-capacity COUNT`, a positive Digit-Probe Schur capacity with
  default `5000`;
- `--output PATH`, which writes the complete report atomically;
- `--overwrite`, which requires `--output` and permits atomic replacement
  of an existing destination.

Without `--overwrite`, an existing output path is refused. Even with
`--overwrite`, an output path resolving to either input file is rejected.
Temporary output files are created in the destination directory and removed
after failures.

Controlled outcomes use stable process exit codes:

| Code | Meaning |
| ---: | --- |
| 0 | Success |
| 2 | Command-line usage error |
| 3 | Input file access error |
| 4 | UTF-8 decoding error |
| 5 | Journal parsing or normalization error |
| 6 | Classification, analysis, manifest, temporal, comparison, or reporting contract error |
| 7 | Standard-output or output-file error |

Expected user and data errors are written concisely to standard error without
a traceback.

## Development dependency

The distributive dependency is pinned to a verified Digit-Probe Git
commit. During local development, the local Digit-Probe repository may
replace it through an editable installation.

Analysis manifests derive the reproducible Digit-Probe commit from the
installed System Log Dynamics dependency metadata, not from the currently
imported editable checkout.
