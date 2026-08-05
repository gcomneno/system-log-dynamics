# System Log Dynamics

System Log Dynamics is a reproducible Learning in Public laboratory for
transforming Linux journal events into discrete symbolic sequences and
analyzing them through the public Python API of Digit-Probe.

## Status

The strict journal JSON Lines parser, privacy-safe normalizer,
deterministic streaming classifier, validated integer encoding, validated
Digit-Probe analysis, reproducible per-window analysis manifests, deterministic
immutable temporal burst summaries, typed structured comparison, and
deterministic Markdown reporting are implemented. Experiment 001 exercises the
complete public pipeline with two reproducible synthetic windows. The
file-based command-line interface remains deferred.

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

## Development dependency

The distributive dependency is pinned to a verified Digit-Probe Git
commit. During local development, the local Digit-Probe repository may
replace it through an editable installation.

Analysis manifests derive the reproducible Digit-Probe commit from the
installed System Log Dynamics dependency metadata, not from the currently
imported editable checkout.
