# Semantic evidence v1

System Log Dynamics semantic evidence is a deterministic descriptive companion
to the primary taxonomy and Digit-Probe analysis evidence.

It exists so a downstream consumer can recover selected Linux/systemd semantics
without access to raw journal messages and without forcing the primary symbol
alphabet to grow for every descriptive action.

## Version contract

| Field | Value |
|---|---|
| schema name | `system-log-dynamics.semantic-evidence` |
| schema version | `1` |
| bundle type | `semantic_events` |
| semantic facets version | `1` |
| current primary taxonomy | `2` |

Schema version, semantic-facet version, and taxonomy version are independent
compatibility dimensions. Consumers must validate all of them explicitly.

## Version-1 actions

Semantic facet version 1 recognizes only:

- `service_lifecycle / restart_scheduled`;
- `service_lifecycle / process_exited`;
- `process_runtime / process_output`.

The two lifecycle actions require stable systemd `MESSAGE_ID` values and a
structured service subject from `UNIT` or `USER_UNIT`.

`process_output` requires a service `_SYSTEMD_UNIT` and a structured journal
transport of `stdout` or `stderr`.

No broad natural-language or free-text classifier is part of version 1.
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

## Coverage

`coverage` contains the source event count, recognized semantic event count,
and their proportion.

This is descriptive coverage only. It is not a quality score and does not imply
that unrecognized events are unimportant.

## Interpretation boundary

Semantic evidence can state what structured journal evidence supports, such as
"systemd scheduled a restart for service X" or "service X emitted process
output".

It does not state:

- whether the observation is normal or anomalous;
- whether it is malicious;
- whether one event caused another;
- whether an intrusion occurred;
- whether an alert or response is warranted.

Those remain downstream responsibilities.

## Public acceptance fixture

`fixtures/synthetic/restart-loop-semantic.jsonl` models two deterministic
restart-loop lifecycle cycles for `demo-restart.service`.

The primary taxonomy intentionally classifies all six events as `other`, while
semantic evidence recovers:

`restart_scheduled -> process_output -> process_exited`

for the same subject twice, with relative ordering and timing preserved.

The fixture is synthetic and does not copy private Ubuntu journal contents.

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

`parse_semantic_evidence_json()` performs strict version-1 validation and
rejects duplicate keys, unknown fields, unsupported versions, invalid primary
symbol/type pairs, invalid semantic family/action combinations, malformed
coverage, and incompatible semantic flags.
