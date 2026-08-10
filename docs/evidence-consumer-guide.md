# Evidence consumer guide

System Log Dynamics evidence bundles are intended for programs that need stable,
reproducible descriptive facts without parsing Markdown or accessing private
journal content.

## Produce one analysis bundle

Use the normal `analyze` command and select the evidence format explicitly:

    system-log-dynamics analyze input.jsonl \
        --window-id my-window \
        --format evidence-json \
        --output evidence.json

Without `--output`, the canonical JSON document is written to standard output.

## Produce one comparison bundle

A comparison keeps the existing `right - left` direction:

    system-log-dynamics compare left.jsonl right.jsonl \
        --left-window-id left-window \
        --right-window-id right-window \
        --format evidence-json \
        --output comparison.evidence.json

## Validate before consuming

Consumers should validate at least:

1. `schema_name`;
2. `schema_version`;
3. `bundle_type`;
4. the expected payload contract;
5. explicit numeric states.

Do not treat unknown versions as if they were version 1.

The Python API exposes two parsing levels:

- `parse_evidence_envelope_json()` validates only the common envelope;
- `parse_evidence_bundle_json()` validates the complete version-1 payload.

Consumers that rely on the version-1 contract should use
`parse_evidence_bundle_json()`.

## Preserve provenance

When evidence is stored, forwarded, enriched, correlated, or transformed,
preserve the original provenance fields:

- project version;
- Digit-Probe commit;
- manifest schema version;
- taxonomy version;
- input digest algorithm and digest;
- input byte size;
- analysis configuration;
- stable window identifier when supplied.

Do not replace the input digest with a pathname or with a downstream
identifier.

## Preserve observations versus conclusions

Fields emitted by System Log Dynamics are observations or deterministic
derivations from its declared representation.

A downstream IDS, investigation system, research tool, dashboard, or other
consumer may derive additional conclusions.

Those conclusions must not be written back as though System Log Dynamics had
emitted them.

In particular, category counts, high or low taxonomy coverage, statistical
values, burst summaries, and differences between windows are not themselves:

- anomalies;
- threats;
- intrusions;
- confidence estimates;
- recommended responses.

## Numeric states

Never coerce an explicit non-finite state to an arbitrary ordinary number.

For example, a gap mean with:

    {"state":"positive_infinity","value":null}

must remain distinguishable from a finite gap mean.

Likewise, a comparison delta marked `not_computable` must not be silently
converted to zero.

Finite floating-point values in serialized evidence are canonicalized to
14 significant decimal digits. Consumers should treat the serialized evidence
value as authoritative for the versioned interchange contract rather than
attempting to reconstruct binary floating-point tail bits from another Python
runtime.

## Privacy

A consumer should not need the original journal file after receiving a bundle
unless its own separate workflow explicitly requires that source.

The evidence format deliberately excludes raw messages, event records, private
paths, usernames, hosts, addresses, tokens, and credentials.

If a downstream product combines the evidence with private raw material, that
new artifact has a different privacy boundary and must not be presented as an
unaltered System Log Dynamics evidence bundle.

## Golden fixtures

Two canonical examples are shipped with the project:

- single-window analysis evidence;
- structured window-comparison evidence.

They are useful for parser regression tests, compatibility checks, and
byte-level deterministic serialization tests.
