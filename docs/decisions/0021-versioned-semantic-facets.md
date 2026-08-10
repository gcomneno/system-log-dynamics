# Decision 0021 — Versioned semantic facets for downstream explanation

## Status

Accepted for issue #35 on 2026-08-10.

## Context

A real Ubuntu journal road test showed that taxonomy coverage alone can hide
useful Linux semantics without being incorrect.

Two adjacent windows contained a large `other` proportion. A privacy-safe local
investigation found that most of those events belonged to a stable three-event
cycle: systemd scheduled an automatic service restart, the service emitted
process output, and systemd recorded the unit process exit. The service then
repeated that lifecycle after its configured restart delay.

The primary taxonomy was doing what it promised: it reduced accepted journal
events to a small stable alphabet for Digit-Probe. The problem was information
loss at the downstream boundary. A future IDS consumer should not need raw
journal messages merely to recover deterministic systemd lifecycle semantics.

Expanding the primary alphabet for every useful Linux action would mix two
responsibilities and make the Digit-Probe representation unnecessarily large
and unstable.

## Decision

Keep event taxonomy version `2` and its nine-symbol mapping unchanged.

Introduce an independently versioned semantic-facet contract:

- semantic facet version `1`;
- semantic evidence schema `system-log-dynamics.semantic-evidence` version `1`;
- bundle type `semantic_events`.

Semantic facets are an additional descriptive projection of classified events.
They do not replace or alter the primary event type, source domain, classifier
rule, evidence level, or integer symbol.

Version 1 recognizes three deterministic actions:

| Family | Action | Structured basis |
|---|---|---|
| `service_lifecycle` | `restart_scheduled` | stable systemd `MESSAGE_ID` plus structured service `UNIT`/`USER_UNIT` |
| `service_lifecycle` | `process_exited` | stable systemd `MESSAGE_ID` plus structured service `UNIT`/`USER_UNIT` |
| `process_runtime` | `process_output` | service `_SYSTEMD_UNIT` plus `_TRANSPORT=stdout|stderr` |

The semantic layer prefers structured journal fields. It does not use broad
free-text message parsing for these actions.

## Subject identity

A recognized semantic event carries a normalized systemd service-unit subject.
This is intentionally more informative than the aggregate analysis evidence
contract because a downstream consumer must be able to explain which service
participated in an observed lifecycle.

Semantic evidence therefore declares
`contains_normalized_subject_identifiers=true`.

It still excludes raw journal messages and absolute timestamps. Publication of
real semantic evidence requires privacy review because a unit identifier can be
sensitive in context.

## Temporal representation

Each semantic event may carry its privacy-safe `relative_realtime_us` offset and
its source `sequence_index`.

These coordinates preserve ordering and allow downstream correlation with the
statistical evidence. The semantic layer does not infer recurrence, periodicity,
anomaly, or causality. Digit-Probe and downstream policy remain responsible for
their respective interpretations.

## Evidence separation

The existing analysis and comparison evidence schemas remain at version `1`.
They are not extended in place because their strict parsers require exact
version-specific fields.

Semantic evidence has independent schema and facet versions so consumers can
support or reject it explicitly without confusing:

- primary event-taxonomy compatibility;
- statistical evidence compatibility;
- semantic-facet compatibility.

Semantic evidence provenance includes the project version, taxonomy version,
semantic-facet version, optional window identifier, and exact input SHA-256 and
byte size. It does not claim Digit-Probe provenance because Digit-Probe is not
used to derive semantic facets.

## Interpretation boundary

System Log Dynamics may state deterministic observations such as:

- a service restart was scheduled;
- a service process exited;
- a service emitted process output;
- those observations occurred in a particular source order and at particular
  relative offsets.

It must not state that the pattern is anomalous, malicious, an intrusion,
causal, or deserving of an automated response.

A downstream IDS may combine semantic evidence with statistical evidence and
its own reviewed policy to derive security signals or explanations.

## Acceptance case

The public synthetic fixture `fixtures/synthetic/restart-loop-semantic.jsonl`
models two cycles of:

`restart_scheduled -> process_output -> process_exited`

for a generic `demo-restart.service`.

All six fixture events remain primary taxonomy `other` / symbol `8`, proving
that semantic facets do not silently change the Digit-Probe alphabet.

Semantic facet version `1` recovers the lifecycle sequence, common subject,
relative timing, exact structured rule IDs, and evidence levels without
exporting the synthetic message text.

## Consequences

Downstream consumers can receive enough deterministic Linux semantics to
explain a restart lifecycle without re-reading raw journal messages.

The primary taxonomy remains intentionally small and stable.

Future semantic actions require explicit facet-version review when their
meaning or fields are incompatible. Future primary taxonomy changes remain a
separate decision and versioning concern.

This decision does not add IDS behavior, anomaly scoring, threat scoring,
causality inference, alerting, AI interpretation, or automated response.
