# Decision 0013 — Deterministic Markdown reporting boundary

## Status

Accepted for issue #14 on 2026-08-05.

## Context

`AnalysisWindow` retains the manifest, Digit-Probe result, and temporal summary
for one completed window. `WindowComparison` deliberately retains only
compatibility metadata and structured numeric differences. It does not copy
input hashes, byte sizes, complete manifests, or the two original windows.

A deterministic comparison report must present both per-window provenance and
the already computed differences. The renderer cannot recover omitted
provenance from `WindowComparison` without reading files, package metadata,
Git state, or another external source. Those operations are outside the pure
presentation boundary.

## Decision

`system_log_dynamics.reporting` introduces a frozen, slotted
`WindowComparisonReport`. It retains independent validated snapshots of the
left and right `AnalysisWindow` values together with their deterministic
`WindowComparison`.

`build_window_comparison_report` is the public composition boundary. It accepts
two completed windows, snapshots them through their existing validation
contract, calculates their structured comparison, and returns one coherent
presentation input.

The report model validates that its comparison is exactly the deterministic
comparison of its retained windows. This prevents callers from combining
provenance from one pair of windows with differences calculated from another
pair.

Markdown renderers will consume only validated structured objects. They will
not read files, package metadata, environment variables, Git state, terminal
properties, locale configuration, or the network. They will not recalculate
Digit-Probe metrics, temporal aggregates, classifications, manifests, or
comparison semantics.

The comparison renderer will use `WindowComparisonReport`, rather than adding
presentation-only provenance to `WindowComparison`. This preserves the
structured comparison contract established by Decision 0012.

## Consequences

Presentation can include complete per-window provenance without weakening the
minimal analytical comparison model or introducing hidden I/O.

The reporting layer owns deterministic ordering, numeric formatting, Markdown
escaping, unavailable-value representation, interpretation notices, section
composition, and final-newline policy.

Finite floats use at most six decimal places with trailing zeroes removed.
Percentages use at most two decimal places. Negative zero is rendered as zero.
Missing, NaN, positive infinity, negative infinity, and not-computable states
remain textually distinct.

Event symbols use canonical ascending numeric order and include their stable
taxonomy labels. Autocorrelation lags and n-gram orders use ascending numeric
order independently of mapping insertion order. Markdown tables use a compact
fixed structure that does not depend on terminal width or locale.

Caller-provided window identifiers are escaped for Markdown, including table
delimiters. Reports end with exactly one newline.

It remains descriptive and representation-dependent. It must not infer
anomalies, compromise, malicious behaviour, randomness, causality, or intent.

This decision adds no command-line interface, file writing, JSON or YAML
serialization, live journal collection, charts, HTML, PDF, or interactive
output.
