# Semantic evidence v1

System Log Dynamics semantic evidence is a deterministic descriptive companion
to the primary taxonomy and Digit-Probe analysis evidence.

It exists so a downstream consumer can recover selected Linux/systemd semantics
without access to raw journal messages and without forcing the primary symbol
alphabet to grow for every descriptive action.

The `v1` in this document title refers to the semantic-evidence **schema**.
Semantic-facet compatibility is independently versioned and is currently at
version `2`.

## Version contract

| Field | Value |
|---|---|
| schema name | `system-log-dynamics.semantic-evidence` |
| schema version | `1` |
| bundle type | `semantic_events` |
| current semantic facets version | `2` |
| current primary taxonomy | `2` |

Schema version, semantic-facet version, and taxonomy version are independent
compatibility dimensions. Consumers must validate all of them explicitly.

Semantic-facet version `1` introduced three actions. Version `2` retains those
recognition semantics and adds two structured systemd lifecycle actions without
changing the serialized evidence shape.

## Current actions — semantic facets version 2

Semantic facet version 2 recognizes:

- `service_lifecycle / restart_scheduled`;
- `service_lifecycle / process_exited`;
- `service_lifecycle / start_job_begun`;
- `service_lifecycle / unit_succeeded`;
- `process_runtime / process_output`.

### Version-1 actions retained unchanged

`restart_scheduled` and `process_exited` require their stable systemd
`MESSAGE_ID` values and a structured service subject from `UNIT` or
`USER_UNIT`.

`process_output` requires a service `_SYSTEMD_UNIT` and a structured journal
transport of `stdout` or `stderr`.

Version 2 does not retroactively change those recognition rules.

### Version-2 systemd lifecycle actions

`start_job_begun` requires all of:

- `SYSLOG_IDENTIFIER=systemd`;
- `MESSAGE_ID=7d4958e842da4a758f6c1cdc7b36dcc5`;
- a structured service subject from `UNIT` or `USER_UNIT`.

It records only the structured observation that a unit start job began
execution. It does not assert that the service became usable or healthy.

`unit_succeeded` requires all of:

- `SYSLOG_IDENTIFIER=systemd`;
- `MESSAGE_ID=7ad2d189f7e94e70a38c781354912448`;
- a structured service subject from `UNIT` or `USER_UNIT`.

It records only the structured systemd success observation. It does not assert
that a long-running service is correctly configured, healthy, secure, or
causally related to another event.

Exact lifecycle `MESSAGE_ID` rules take precedence over generic
`process_output` recognition when an event also carries stdout/stderr transport.

No broad natural-language or free-text classifier is part of semantic facets
version 2. In particular, DBus activation/timeout and CRON session open/close
text are intentionally not recognized when the journal exposes no stable
structured target/result or PAM/session anchors.

Unrecognized events simply receive no semantic facet.

## Event payload

Each recognized event carries:

- source `sequence_index`;
- privacy-safe `relative_realtime_us` when available;
- the unchanged primary taxonomy symbol and event type;
- source domain;
- primary classifier rule and evidence level;
- semantic family and action;
- normalized systemd service-unit subject;
- semantic rule and evidence level;
- transport only when the semantic action is process output.

The event does not contain the journal `MESSAGE` or an absolute timestamp.

The semantic subject is intentionally retained because a downstream system
cannot explain a service lifecycle without identifying its service. Real
semantic evidence is therefore local-sensitive derived evidence and requires
privacy review before publication.

## Provenance

A bundle includes:

- System Log Dynamics project version;
- primary taxonomy version;
- semantic facets version;
- optional window identifier;
- exact input SHA-256;
- exact input byte size.

Digit-Probe provenance is not part of this bundle because Digit-Probe does not
derive semantic facets. Statistical analysis evidence remains a separate
contract.

A strict version-2 consumer must reject semantic evidence whose
`semantic_facets_version` is not `2`; there is no silent fallback to version 1.

## Coverage

`coverage` contains the source event count, recognized semantic event count,
and their proportion.

This is descriptive coverage only. It is not a quality score and does not imply
that unrecognized events are unimportant.

## Interpretation boundary

Semantic evidence can state what structured journal evidence supports, such as
"systemd scheduled a restart for service X", "a start job began for service X",
"systemd recorded service X as succeeded", or "service X emitted process
output".

It does not state:

- whether the observation is normal or anomalous;
- whether it is malicious;
- whether one event caused another;
- whether an intrusion occurred;
- whether a service is healthy or secure;
- whether an alert or response is warranted.

Those remain downstream responsibilities.

## Public acceptance fixtures

`fixtures/synthetic/restart-loop-semantic.jsonl` models two deterministic
restart-loop lifecycle cycles for `demo-restart.service`.

The primary taxonomy intentionally classifies all six events as `other`, while
semantic evidence recovers:

`restart_scheduled -> process_output -> process_exited`

for the same subject twice, with relative ordering and timing preserved. These
version-1 actions remain unchanged under semantic facets version 2.

`fixtures/synthetic/systemd-lifecycle-semantic-v2.jsonl` adds two generic
service subjects and exercises both structured `UNIT` and `USER_UNIT` forms:

`start_job_begun -> unit_succeeded`

for each service. Its `MESSAGE` values are intentionally opaque so recognition
cannot depend on free-text wording.

Both fixtures are synthetic and do not copy private Ubuntu journal contents.

## CLI

Semantic evidence is available as an explicit `analyze` output format:

```text
system-log-dynamics analyze INPUT \
    --window-id WINDOW \
    --format semantic-evidence-json
```

The output is `system-log-dynamics.semantic-evidence` schema version 1 with
current `semantic_facets_version=2`. It may be written to standard output or to
an explicit file with `-o/--output`; existing overwrite, UTF-8, path-safety, and
atomic-write behavior applies unchanged.

`--format evidence-json` remains the existing analysis/statistical evidence
contract and still emits `system-log-dynamics.analysis-evidence` with bundle
type `analysis_window`. Semantic evidence is a separate product and does not
replace or extend that legacy CLI format in place.

`semantic-evidence-json` is intentionally available only for `analyze`.
`compare` has no semantic comparison contract and continues to accept only
`markdown` and `evidence-json`.

Semantic output remains descriptive evidence, not an IDS verdict. Normalized
service-unit subjects are retained so downstream consumers can explain the
observed lifecycle; those identifiers remain privacy-sensitive derived evidence
and require review before publication.

## Python API

```python
from system_log_dynamics.semantics import (
    build_semantic_evidence_envelope,
    iter_semantic_events,
    parse_semantic_evidence_json,
    render_semantic_evidence_json,
)
```

A caller parses and classifies an explicit journal JSON Lines input through the
existing pipeline, then passes the exact input bytes and classified events to
`build_semantic_evidence_envelope()`.

`parse_semantic_evidence_json()` performs strict schema-v1 plus current-facet
validation and rejects duplicate keys, unknown fields, unsupported versions,
invalid primary symbol/type pairs, invalid semantic family/action combinations,
malformed coverage, and incompatible semantic flags.

## Architecture decisions

The original separation of primary taxonomy, semantic facets, subject identity,
and evidence schema is recorded in
[Decision 0021](decisions/0021-versioned-semantic-facets.md).

The semantic-facet version-2 extension and its structured-only recognition
boundary are recorded in
[Decision 0022](decisions/0022-structured-systemd-lifecycle-semantic-facets-v2.md).
