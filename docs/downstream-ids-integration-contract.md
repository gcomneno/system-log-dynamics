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

Version `1` is the only currently accepted evidence schema version.

Consumers should use `parse_evidence_bundle_json()` or an independently
equivalent strict validator before accepting a bundle.

Consumers must reject:

- unsupported schema names;
- unsupported bundle types;
- unsupported schema versions;
- malformed JSON;
- duplicate object keys;
- unknown or invalid version-1 fields;
- invalid numeric states;
- taxonomy or structural contract mismatches.

A future evidence version is incompatible until the downstream consumer
explicitly adds and reviews support for it.

## Required provenance

A consumer must preserve the source evidence reference together with:

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

Downstream metadata may supplement this provenance but must not replace it.

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

A deterministic metric is an observation, not a security conclusion.

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

## Synthetic end-to-end boundary example

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

The production analogue is:

```text
private journal bytes
        -> System Log Dynamics evidence
        -> downstream consumer
```

Raw private journal bytes remain on the System Log Dynamics side by default.

At the final arrow the downstream consumer may only accept or reject the
evidence and preserve its provenance for this example.

No signal, alert, incident hypothesis, confirmed incident, trigger, AI
interpretation, notification, or response action is produced by System Log
Dynamics.

## Compatibility procedure

When a future evidence schema version is introduced:

1. keep existing supported-version behavior explicit;
2. review the new schema independently;
3. add explicit downstream support for that version;
4. preserve version-specific provenance and semantics;
5. reject the new version until that work is complete.

Silent fallback to version 1 is prohibited.

## Architecture reference

The responsibility, trust, privacy, AI, trigger, and response rationale is
recorded in
[Decision 0019](decisions/0019-downstream-ids-integration-and-trust-boundary.md).
