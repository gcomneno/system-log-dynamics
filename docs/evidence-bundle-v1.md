# Evidence bundle v1

System Log Dynamics can emit deterministic machine-readable evidence without
requiring consumers to parse Markdown or inspect raw Linux journal messages.

This document defines the public version-1 evidence contract.

## Document kinds

Version 1 defines two document kinds:

| Bundle type | Schema name |
|---|---|
| `analysis_window` | `system-log-dynamics.analysis-evidence` |
| `window_comparison` | `system-log-dynamics.comparison-evidence` |

Both use:

- `schema_version = 1`;
- UTF-8 JSON;
- one JSON document per output;
- exactly one final newline;
- deterministic observable field ordering;
- standard JSON numeric syntax only.

The CLI selects this representation explicitly with
`--format evidence-json`.

The historical default remains `--format markdown`.

## Common envelope

Every document contains exactly four envelope fields, in this order:

1. `schema_name`
2. `schema_version`
3. `bundle_type`
4. `payload`

Unknown envelope fields, unsupported bundle types, unsupported schema
versions, duplicate JSON keys, malformed UTF-8, malformed JSON, and JSON
extensions such as bare `NaN` or `Infinity` are rejected by the public parser.

The schema name must match the bundle type.

## Numeric representation

Metrics that can be unavailable or non-finite use an explicit object:

- `state`
- `value`

Supported states are:

| State | `value` |
|---|---|
| `finite` | JSON integer or finite JSON number |
| `missing` | `null` |
| `nan` | `null` |
| `positive_infinity` | `null` |
| `negative_infinity` | `null` |
| `not_computable` | `null` |

Non-finite values are therefore never serialized as non-standard JSON number
tokens.

Finite floating-point values are canonicalized at the JSON serialization
boundary to 14 significant decimal digits. This removes runtime-specific
last-bit differences while leaving integers exact and leaving the in-memory
domain results unchanged.

`not_computable` is used for a derived comparison value when the corresponding
operation cannot be computed from its source states. It is not a statistical
or security interpretation.

## Analysis-window payload

An `analysis_window` payload contains exactly three conceptual sections:

1. `provenance`
2. `analysis`
3. `semantics`

### Provenance

The provenance section carries:

- project version;
- pinned Digit-Probe commit;
- analysis-manifest schema version;
- taxonomy version;
- optional stable window identifier;
- input digest algorithm;
- SHA-256 digest of the exact input bytes;
- exact input byte size;
- effective Schur capacity;
- temporal burst threshold.

The input path is deliberately excluded.

### Analysis

The analysis section carries:

- Digit-Probe mode;
- sample size;
- alphabet size;
- maximum observed symbol;
- complete category distribution;
- taxonomy coverage;
- statistical metrics;
- deterministic temporal summary.

The category distribution covers the complete taxonomy alphabet and contains
the stable symbol, event-type name, count, proportion, and z-score.

Taxonomy coverage includes named-event versus `other` counts and proportions,
represented and absent named symbols, corresponding event-type names, and the
structural coverage status.

Statistical evidence includes:

- chi-square;
- expected count per bin;
- runs statistics;
- per-symbol gap statistics;
- autocorrelation;
- compression ratio;
- n-gram accuracy;
- Schur aggregates.

The Schur `triples` field is a count of candidate triples, not an exported
collection of individual relations.

The temporal section carries the existing deterministic timing and burst
aggregates from the domain model.

## Comparison payload

A `window_comparison` payload contains:

1. `left`
2. `right`
3. `comparison`
4. `semantics`

`left` and `right` are evidence snapshots of the two validated analysis
windows. They contain provenance and analysis sections equivalent to the
single-window bundle.

The comparison direction is explicitly:

`right_minus_left`

The comparison section carries:

- left and right window identifiers;
- compatibility metadata;
- complete per-category count and proportion differences;
- taxonomy-coverage differences;
- statistical differences;
- temporal differences.

Each generic numeric difference contains:

- `left`;
- `right`;
- `delta`.

Each of those fields uses the explicit numeric representation above.

The compatibility section records the shared contract fields used by the
comparison domain model and descriptive equality flags for project version,
window identifier, input digest, input size, and sample size.

## Semantic limitations

Every bundle carries machine-readable semantic limitations.

System Log Dynamics evidence is descriptive only.

A bundle does not contain or imply:

- anomaly scores;
- threat scores;
- intrusion verdicts;
- confidence estimates;
- automatic actions;
- raw-event exports.

The bundle also declares that raw events, raw journal messages, and input paths
are absent.

A downstream system may derive additional interpretations, but those
interpretations are outside this schema and must remain distinguishable from
the original observations.

## Privacy boundary

Evidence bundles must not contain:

- raw journal messages;
- normalized or classified raw-event records;
- usernames;
- hostnames;
- network addresses;
- tokens;
- credentials;
- private filesystem paths.

Stable input provenance is represented by digest and byte size rather than by
the source path or raw bytes.

## Determinism

For identical input bytes, explicit window identifiers, analysis configuration,
project/dependency versions, taxonomy version, and implementation version, the
serialized evidence output is expected to be byte-identical.

Canonical serialization uses:

- UTF-8;
- compact JSON separators;
- stable insertion ordering defined by the schema;
- explicit numeric states;
- 14 significant decimal digits for finite floating-point values;
- normalized positive zero for signed floating-point zero;
- exactly one trailing newline.

The version-1 golden fixtures are:

- `fixtures/reports/experiment-001-routine.evidence.json`;
- `fixtures/reports/experiment-001-comparison.evidence.json`.

## Evolution policy

Schema version 1 is immutable once published.

A change requires a new evidence schema version when it changes the meaning,
required presence, type, or interpretation of an existing field, removes a
field, changes numeric-state semantics, or otherwise makes a version-1
consumer unable to interpret the document according to this reference.

Compatible implementation changes may retain schema version 1 when they do
not change the version-1 observable contract.

Consumers must reject unknown incompatible schema versions rather than
silently reinterpret them.

The evidence schema version is separate from:

- the System Log Dynamics project version;
- the analysis-manifest schema version;
- the taxonomy version;
- the Digit-Probe provenance commit.

Those versions travel together so that consumers can preserve provenance
without conflating their evolution.
