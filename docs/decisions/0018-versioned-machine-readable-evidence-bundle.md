# Decision 0018 — Versioned machine-readable evidence bundle

Status: Accepted

## Context

System Log Dynamics already produces deterministic analysis windows,
structured comparisons, taxonomy coverage, provenance manifests, temporal
summaries, and Markdown reports.

Markdown is suitable for human review but is not an appropriate integration
contract for downstream software. Requiring another program to parse Markdown
would couple it to presentation details. Requiring access to the original
journal would also cross the project's privacy boundary and expose raw event
material that the descriptive evidence layer does not need to redistribute.

The project therefore needs a stable machine-readable representation while
remaining an evidence-producing system rather than an IDS.

## Decision

System Log Dynamics defines evidence schema version `1` with two bundle types:

- `analysis_window`, using schema name
  `system-log-dynamics.analysis-evidence`;
- `window_comparison`, using schema name
  `system-log-dynamics.comparison-evidence`.

The existing CLI gains an explicit format selector:

- `--format markdown`;
- `--format evidence-json`.

Markdown remains the default. Existing Markdown output is not silently
changed.

The Python evidence API provides:

- deterministic builders for analysis and comparison bundles;
- canonical JSON rendering;
- envelope-only parsing;
- strict complete version-1 bundle parsing.

The strict parser rejects malformed JSON, duplicate keys, incompatible schema
identity or version, unexpected version-1 payload fields, invalid structural
types, invalid numeric states, inconsistent taxonomy symbols, and other
version-1 contract violations.

## Provenance

Every analysis snapshot carries:

- System Log Dynamics project version;
- pinned Digit-Probe commit;
- manifest schema version;
- taxonomy version;
- input SHA-256 digest and byte size;
- optional stable window identifier;
- effective analysis configuration.

Comparison bundles preserve both input-window snapshots and the deterministic
`right_minus_left` comparison.

The input pathname is not evidence and is not exported.

## Numeric representation

Values that may be unavailable or non-finite are represented explicitly by a
state/value object.

Version 1 supports:

- `finite`;
- `missing`;
- `nan`;
- `positive_infinity`;
- `negative_infinity`;
- `not_computable`.

Non-finite values are never emitted as non-standard JSON numeric tokens.

## Privacy boundary

The evidence bundle does not export raw events or journal messages.

It must not expose usernames, hostnames, addresses, credentials, tokens,
private paths, or other raw source material. Exact-byte provenance is retained
through digest and byte size instead.

## Semantic boundary

Evidence is descriptive.

Machine-readable limitations and flags explicitly state that the bundle does
not contain or imply:

- anomaly scores;
- threat scores;
- intrusion verdicts;
- confidence estimates;
- automatic actions.

A separate downstream system may derive interpretations, but it must preserve
the original provenance and distinguish its conclusions from System Log
Dynamics observations.

## Determinism

For identical input bytes, stable identifiers, configuration, taxonomy,
project/dependency versions, and implementation version, canonical
serialization is byte-identical.

Finite floating-point values are canonicalized at serialization to
14 significant decimal digits. This deliberately removes insignificant
runtime-specific binary tail differences while preserving the original
in-memory domain values and exact integer evidence.

Version-1 golden analysis and comparison bundles are maintained alongside the
existing Experiment 001 Markdown golden reports.

## Evolution

Evidence schema version 1 is immutable once published.

A breaking change to field meaning, required presence, type, numeric-state
semantics, or consumer interpretation requires a new evidence schema version.

Consumers must reject unknown incompatible versions rather than silently
interpreting them as version 1.

The evidence schema version remains distinct from the project version,
analysis-manifest schema version, taxonomy version, and Digit-Probe provenance
commit.

## Consequences

Downstream consumers can use structured descriptive evidence without parsing
Markdown or reading private journal bytes.

The Markdown contract remains independently stable.

System Log Dynamics acquires a public integration boundary without acquiring
IDS, AI, security-verdict, triggering, or automatic-response responsibilities.
