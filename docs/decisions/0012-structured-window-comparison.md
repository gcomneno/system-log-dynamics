# Decision 0012 — Structured window comparison

## Status

Accepted for issue #12 on 2026-08-01.

## Context

Completed System Log Dynamics windows already have three independent,
privacy-safe products: a Digit-Probe `AnalysisResult`, an `AnalysisManifest`,
and a `TemporalBurstSummary`. Consumers need a deterministic way to compare
two such completed windows without coupling comparison to presentation or
interpretation.

## Decision

`system_log_dynamics.comparison` combines those products in a frozen, slotted
`AnalysisWindow` and returns a frozen, slotted `WindowComparison`. The window
boundary validates the public Digit-Probe shape and its relationship to the
manifest and temporal event total; it does not inspect private Digit-Probe
implementation details or mutate the supplied objects. Because the public Digit-Probe result contains mutable dictionaries and nested frozen dataclasses, `AnalysisWindow` records defensive snapshots of every mapping and nested result value. It also reconstructs and validates independent snapshots of the manifest, its nested configuration, and the temporal summary. `ManifestCompatibility` independently snapshots its analysis configuration. After classifying cross-window compatibility, comparison reconstructs both complete windows before reading any metric.

Comparison is blocked, in this order, by different manifest schema versions,
taxonomy versions, alphabet sizes, Digit-Probe commits, analysis configuration,
input digest algorithms, or temporal burst thresholds. A project-version
difference is allowed and recorded. Window identifiers, input digest equality,
input byte-size equality, and sample-size equality are descriptive only. Input
hashes themselves are never copied into the comparison result.

Numeric sources are canonicalized as finite, missing, NaN, positive infinity,
or negative infinity. Public comparison models never retain raw NaN. Deltas
use `right - left`; a delta involving a missing or non-finite source is
explicitly not computable. Autocorrelation lags and n-gram orders use the
sorted union of keys, with an absent side represented as missing.

Count and gap mappings cover the canonical event alphabet, and all returned
mappings are defensively copied, immutable, and ascending by integer key.
The comparison includes count proportions, runs, gaps, autocorrelation,
n-gram accuracy, compression ratio, and temporal aggregates. It excludes
chi-square, expected-per-bin, z-scores, Schur metrics, and max-observed.

## Consequences

The result retains no journal content, messages, raw input bytes, input hashes,
source lines, or original boot identifiers. It is a structured descriptive
comparison only: it makes no claims about anomalies, significance, security,
compromise, causality, behaviour, or intent.

This decision adds no Markdown, JSON, or YAML rendering; command-line
behaviour; live journal access; threshold selection; or inference layer.
