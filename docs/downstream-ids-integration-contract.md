# Downstream IDS integration contract

System Log Dynamics is an evidence engine, not an intrusion detection system.

This document defines the public boundary for a separate downstream
security-oriented consumer.

It does not add security interpretation, AI, triggering, alerting, incident
handling, or response behavior to System Log Dynamics.

## Current accepted inputs

A downstream consumer may accept these System Log Dynamics evidence documents:

| Schema name | Version | Bundle type |
|---|---:|---|
| `system-log-dynamics.analysis-evidence` | `1` | `analysis_window` |
| `system-log-dynamics.comparison-evidence` | `1` | `window_comparison` |
| `system-log-dynamics.semantic-evidence` | `1` | `semantic_events` |

Version `1` is the only currently accepted schema version for each listed
bundle.

The current producer emits taxonomy version `2`. Taxonomy version is
independent provenance: consumers must explicitly support the taxonomy
semantics carried by a bundle and reject unsupported taxonomy versions rather
than inferring compatibility from evidence schema version alone.

Semantic evidence additionally carries semantic-facet version `1`. Semantic
facet compatibility is independent from both taxonomy version and the existing
analysis/comparison evidence schemas.

Consumers should use `parse_evidence_bundle_json()` for analysis/comparison
evidence, `parse_semantic_evidence_json()` for semantic evidence, or an
independently equivalent strict validator before accepting a bundle.

Consumers must reject:

- unsupported schema names;
- unsupported bundle types;
- unsupported schema versions;
- unsupported semantic-facet versions when present;
- malformed JSON;
- duplicate object keys;
- unknown or invalid version-specific fields;
- invalid numeric states;
- taxonomy or structural contract mismatches.

A future evidence or semantic-facet version is incompatible until the
downstream consumer explicitly adds and reviews support for it.

## Required provenance

For analysis and comparison evidence, a consumer must preserve the source
evidence reference together with:

- `schema_name`;
- `schema_version`;
- `bundle_type`;
- `project_version`;
- `digit_probe_commit`;
- `manifest_schema_version`;
- `taxonomy_version`;
- `window_id` when present;
- input `digest_algorithm`;
- input `sha256`;
- input `size_bytes`;
- effective `analysis_configuration`.

For comparison evidence, the consumer must preserve the provenance of both
windows and the `right_minus_left` direction.

For semantic evidence, a consumer must preserve:

- `schema_name` and `schema_version`;
- `bundle_type`;
- `project_version`;
- `taxonomy_version`;
- `semantic_facets_version`;
- `window_id` when present;
- input `digest_algorithm`, `sha256`, and `size_bytes`.

Digit-Probe provenance is intentionally absent from semantic evidence because
Digit-Probe does not derive semantic facets.

Downstream metadata may supplement this provenance but must not replace it.

## Semantic evidence boundary

Semantic evidence is a descriptive companion to the small primary event
alphabet. It may preserve selected structured Linux/systemd meaning that would
otherwise be lost when the primary event remains `other`.

Semantic facet version 1 recognizes only:

- service restart scheduling;
- service process exit;
- service process output through `stdout` or `stderr`.

The first two actions require stable systemd `MESSAGE_ID` values and structured
service subjects. Process output requires a service `_SYSTEMD_UNIT` and a
structured stdout/stderr transport.

Semantic evidence preserves the normalized systemd service-unit subject so a
downstream consumer can explain which service participated in the observed
lifecycle. It also preserves source ordering and privacy-safe relative temporal
offsets.

Those facts remain observations. System Log Dynamics does not infer recurrence,
causality, anomaly, threat, intrusion, intent, or response policy from them.

## Data-minimization contract

The default integration does not require or transfer raw journal messages.

A downstream consumer must not demand by default:

- raw journal bytes;
- message text;
- usernames;
- hostnames;
- network addresses;
- credentials;
- tokens;
- private paths;
- other private source fields.

Semantic evidence is deliberately more identifying than aggregate analysis
evidence because it can contain normalized systemd service-unit names. Those
identifiers are derived structured evidence, not raw messages, but can still be
sensitive in context. Real semantic evidence therefore requires privacy review
before publication.

A separately approved workflow may establish additional access, but that is
outside this contract.

Derived evidence still requires privacy review before publication. A digest,
timing pattern, identifier, aggregate count, or configuration value can remain
sensitive in context.

## Trust model

The evidence bundle is deterministic descriptive evidence.

An input hash establishes byte identity for the analyzed input. It does not
prove truth, authenticity, completeness, source integrity before hashing, or
absence of tampering.

A deterministic metric or semantic facet is an observation, not a security
conclusion.

The downstream consumer is responsible for any security interpretation it
adds.

## Vocabulary and ownership

| Term | Meaning | Owner |
|---|---|---|
| Observation | Descriptive fact or metric produced from accepted input and configuration. | System Log Dynamics |
| Signal | Security-relevant indication derived under an explicit downstream rule, policy, or reviewed interpretation. | Downstream consumer |
| Alert | Workflow object stating that one or more signals warrant attention; not incident confirmation. | Downstream consumer |
| Incident hypothesis | Provisional explanation connecting evidence and signals to a possible security event. | Downstream consumer |
| Confirmed incident | Organizational or analyst conclusion reached under an explicit incident-confirmation policy. | Downstream consumer |

System Log Dynamics emits observations and evidence only.

It never emits signals, alerts, incident hypotheses, or confirmed incidents.

## AI advisory boundary

AI output is untrusted advisory material.

A downstream AI interpretation must remain distinguishable from both:

- the original System Log Dynamics observations;
- any reviewed downstream rule or analyst conclusion.

AI output cannot by itself authorize a trigger, confirm an incident, or
authorize a response.

Any promotion from AI advice to a rule or analyst conclusion requires explicit
downstream review.

## Trigger audit requirements

A downstream trigger derived from System Log Dynamics evidence must retain an
auditable record containing at least:

1. trigger identifier and version;
2. source evidence reference;
3. evidence schema name and version;
4. preserved System Log Dynamics provenance;
5. downstream policy or rule identifier and version;
6. observations or signals used;
7. evaluation result;
8. review or approval state;
9. AI advisory reference when AI contributed;
10. separate response authorization when an action is proposed.

The evidence bundle itself never authorizes the trigger.

## Response boundary

System Log Dynamics never authorizes or performs:

- notification;
- blocking;
- quarantine;
- remediation;
- account changes;
- service changes;
- automatic response.

A downstream response requires an explicit authorization path independent from
the existence or contents of an evidence bundle.

## Synthetic end-to-end boundary examples

The repository's synthetic Experiment 001 routine fixture can stand in for
private journal bytes without exposing private data:

```text
fixtures/synthetic/experiment-001-routine.jsonl
        |
        | local deterministic System Log Dynamics pipeline
        v
system-log-dynamics.analysis-evidence / schema version 1
        |
        | strict validation + provenance preservation
        v
separate downstream consumer
        |
        X  boundary stops here
```

The semantic acceptance fixture exercises the complementary descriptive path:

```text
fixtures/synthetic/restart-loop-semantic.jsonl
        |
        | deterministic classification + semantic facets
        v
system-log-dynamics.semantic-evidence / schema version 1
        |
        | strict validation + provenance preservation
        v
separate downstream consumer
        |
        X  security interpretation begins only downstream
```

The semantic fixture retains primary taxonomy `other` while exposing the
structured lifecycle sequence `restart_scheduled -> process_output ->
process_exited` for one generic service subject.

The production analogue is:

```text
private journal bytes
        -> System Log Dynamics evidence
        -> downstream consumer
```

Raw private journal bytes remain on the System Log Dynamics side by default.

At the final arrow the downstream consumer may only accept or reject the
evidence and preserve its provenance for these examples.

No signal, alert, incident hypothesis, confirmed incident, trigger, AI
interpretation, notification, or response action is produced by System Log
Dynamics.

## Compatibility procedure

When a future evidence schema or semantic-facet version is introduced:

1. keep existing supported-version behavior explicit;
2. review the new contract independently;
3. add explicit downstream support for that version;
4. preserve version-specific provenance and semantics;
5. reject the new version until that work is complete.

Silent fallback to a previous version is prohibited.

## Architecture reference

The responsibility, trust, privacy, AI, trigger, and response rationale is
recorded in
[Decision 0019](decisions/0019-downstream-ids-integration-and-trust-boundary.md).

The independent semantic-facet versioning, subject-identity, and descriptive
lifecycle boundary are recorded in
[Decision 0021](decisions/0021-versioned-semantic-facets.md).
