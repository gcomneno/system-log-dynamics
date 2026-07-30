# Experiment 001 — Routine versus boot/error burst

## Status

Contract drafted; fixtures and implementation not yet created.

## Question

Which descriptive properties change when a routine synthetic session is
compared with a synthetic session containing a boot boundary, errors, and
a concentrated event burst?

## Windows

1. Routine session.
2. Boot, error, and burst session.

## Required outputs per window

- normalized events;
- classified events;
- validated integer-symbol sequence;
- structured Digit-Probe result;
- analysis manifest;
- domain-specific Markdown report.

## Required comparison

The comparison must describe differences in counts, runs, gaps,
autocorrelation, n-gram predictability, compression ratio, and temporal
burst structure.

No individual statistic or p-value may be presented as proof of anomaly,
randomness, compromise, or malicious behaviour.

## Reproducibility

Fixtures must be synthetic and deterministic. The manifest must identify
the taxonomy version, input hash, project version, Digit-Probe version or
commit, alphabet size, and analysis configuration.
