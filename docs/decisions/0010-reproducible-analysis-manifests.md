# Decision 0010 — Reproducible per-window analysis manifests

## Status

Accepted for issue #9 on 2026-08-01.

## Context

A structured `AnalysisResult` describes the statistics calculated by
Digit-Probe, but it does not identify the exact source bytes, event taxonomy,
project release, dependency revision, or effective analysis configuration that
produced those statistics.

System Log Dynamics requires these provenance details before results can be
compared or rendered in domain-specific reports.

The manifest is therefore a separate immutable contract associated with one
analyzed input window.

It describes how an analysis was produced without serializing, copying, or
interpreting the `AnalysisResult`.

## Decision

System Log Dynamics provides:

```python
build_analysis_manifest(
    input_bytes,
    result,
    config=None,
    *,
    window_id=None,
)
```

The builder returns an immutable `AnalysisManifest` containing:

- manifest schema version;
- optional window identifier;
- event-taxonomy version;
- input digest algorithm;
- exact input SHA-256;
- exact input size in bytes;
- System Log Dynamics project version;
- pinned Digit-Probe commit;
- event alphabet size;
- immutable effective configuration snapshot;
- analyzed sample size.

The manifest belongs to one input window. It does not compare windows.

## Exact-byte input identity

The manifest hashes the concrete immutable `bytes` supplied by the caller:

```text
input_sha256 = SHA256(input_bytes)
```

The builder performs no:

- JSON parsing;
- key ordering;
- whitespace normalization;
- newline normalization;
- character decoding or re-encoding;
- semantic canonicalization.

Inputs that decode to equivalent JSON but differ byte-for-byte intentionally
produce different digests.

The manifest also records the exact byte length.

Empty input is rejected because a manifest must identify a concrete analyzed
source.

## Separation between source bytes and parsing

The manifest builder does not parse journal data.

Callers own the association between:

1. the exact source bytes;
2. the text decoded from those bytes;
3. the normalized and classified event stream;
4. the resulting Digit-Probe analysis;
5. the manifest built from the original bytes and that result.

The synthetic vertical test reads the fixture once as bytes. Those same bytes
provide the digest and byte size, while their UTF-8 decoding feeds the existing
journal pipeline.

## Manifest schema version

The manifest schema is explicitly versioned:

```python
ANALYSIS_MANIFEST_SCHEMA_VERSION = 1
```

This version identifies the names and meanings of manifest fields.

It is not inferred from the project version, ADR number, source-file order, or
Git history.

An incompatible change to manifest structure or field semantics requires a
deliberate schema-version change.

## Event-taxonomy version

The event contract is explicitly versioned:

```python
EVENT_TAXONOMY_VERSION = "2"
```

The version covers the combined semantics of:

- event types;
- source domains;
- evidence levels;
- classifier precedence;
- stable classifier rule identifiers;
- event-to-symbol mapping;
- alphabet size.

It is not derived from enum declaration order, mapping insertion order, an ADR
number, or a generated hash.

An incompatible change to classification or encoding semantics requires a
deliberate taxonomy-version change.

## Effective configuration snapshot

Digit-Probe currently exposes:

```python
AnalysisConfig(schur_capacity=5000)
```

The manifest stores a project-owned immutable
`AnalysisConfigurationSnapshot`.

When callers pass `None`, the builder instantiates the public Digit-Probe
default and records its effective value.

When callers provide an `AnalysisConfig`, the builder records the public value
without retaining or mutating the external configuration object.

The manifest does not store an opaque representation or inspect undocumented
private state.

## Project version

The project version comes from installed System Log Dynamics distribution
metadata.

The builder verifies that this version equals the public package
`__version__`.

A mismatch is treated as a broken runtime contract rather than silently
recording either value.

The local Git branch and commit are not used as the project version.

## Digit-Probe commit provenance

Local development may import Digit-Probe from a newer editable checkout while
the distributive contract remains pinned to a previously verified commit.

The manifest therefore does not inspect:

- the imported Digit-Probe package version;
- the imported module path;
- a local Digit-Probe repository;
- the current Digit-Probe branch or `HEAD`;
- the network.

Instead, the builder reads the installed System Log Dynamics `Requires-Dist`
metadata and parses it as a PEP 508 requirement.

Exactly one unconditional Digit-Probe dependency must point to the canonical
Git repository and pin a full lowercase 40-character commit.

The current distributive commit is:

```text
55e3eae4c55017703e023c1aaac0838b873482db
```

Missing, duplicate, malformed, indirect, non-Git, conditional, or incompletely
pinned requirements produce a controlled runtime error.

The PEP 508 parser is a direct runtime dependency rather than an accidental
transitive dependency.

## Analysis result validation

The builder accepts only a public Digit-Probe `AnalysisResult` satisfying the
System Log Dynamics analysis contract:

- mode is `integers`;
- alphabet equals `EVENT_ALPHABET_SIZE`;
- sample size is a positive integer;
- maximum observed symbol belongs to the event alphabet;
- counts cover the complete event alphabet;
- every count is a non-negative integer;
- the count total equals the sample size.

The sample size stored in the manifest is derived from the validated result.

The builder does not mutate or serialize the result.

## Window identifier

A window identifier is optional descriptive metadata.

When supplied, it must be a non-empty string without surrounding whitespace.
It is preserved exactly.

The identifier does not influence the input digest or analysis.

## Immutability

`AnalysisManifest` and `AnalysisConfigurationSnapshot` are frozen, slotted
dataclasses.

Their constructors validate their public invariants so manually constructed or
dataclass-replaced instances cannot represent incompatible manifest state.

## Synthetic vertical contract

The existing classification fixture verifies:

```text
exact journal JSON Lines bytes
    -> normalized events
    -> classified events
    -> validated Digit-Probe analysis
    -> analysis manifest
```

The stable manifest values include:

- input size: `3387` bytes;
- input SHA-256:
  `fc837024bb502246441e81724a047e9ab74433ca34923d631a1a5170c7cdad64`;
- project version: `0.1.0`;
- Digit-Probe commit:
  `55e3eae4c55017703e023c1aaac0838b873482db`;
- manifest schema version: `1`;
- taxonomy version: `1`;
- alphabet size: `9`;
- sample size: `14`;
- effective default Schur capacity: `5000`.

The fixture contains only synthetic data.

## Consequences

Analysis provenance can now be carried independently from the statistical
result.

Later comparison and reporting layers can require compatible manifest schema,
taxonomy, alphabet, project, dependency, and configuration contracts before
describing differences between windows.

Exact-byte hashing also means harmless-looking source formatting changes are
reproducibly visible. This is intentional because the manifest identifies an
input artifact, not merely its parsed meaning.

## Scope exclusions

This decision does not introduce:

- JSON or YAML serialization;
- conversion of Digit-Probe results;
- Markdown rendering;
- comparison between windows;
- temporal burst metrics;
- complete experiment fixtures;
- anomaly, security, compromise, or intent inference;
- command-line interfaces;
- live journal collection;
- network access;
- changes to Digit-Probe;
- changes to classification or encoding semantics.
