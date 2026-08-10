# Decision 0022 — Structured systemd lifecycle semantic facets v2

## Status

Accepted for issue #39 on 2026-08-10.

## Context

After semantic facets version 1 was validated against a real Ubuntu restart
loop, the host-specific `arp-detector.service` was disabled and a new clean
30-minute journal window was collected.

The clean window contained 116 source events and 94 primary taxonomy `other`
events. A privacy-safe structural audit showed that most remaining events had
structured journal metadata, but only one previously unrecognized lifecycle
family had stable semantics that did not require parsing journal `MESSAGE`
text.

Systemd emitted two stable `MESSAGE_ID` values with structured `UNIT` or
`USER_UNIT` subjects across multiple unrelated services:

- `7d4958e842da4a758f6c1cdc7b36dcc5` for a unit start job beginning execution;
- `7ad2d189f7e94e70a38c781354912448` for a unit succeeding and entering the
  dead state.

The same audit found larger DBus activation/timeout and CRON session-open/close
clusters, but those records exposed no structured target, result, PAM, or
session fields beyond generic journal metadata. Recognizing those clusters
would therefore require free-text message parsing.

## Decision

Keep primary event taxonomy version `2` and its nine-symbol Digit-Probe mapping
unchanged.

Keep semantic evidence schema `system-log-dynamics.semantic-evidence` at
version `1` because the serialized document shape is unchanged.

Bump the independently versioned semantic-facet contract from version `1` to
version `2` and add two actions to the existing `service_lifecycle` family:

| Action | Structured basis |
|---|---|
| `start_job_begun` | `SYSLOG_IDENTIFIER=systemd`, exact start-job `MESSAGE_ID`, structured service `UNIT`/`USER_UNIT` |
| `unit_succeeded` | `SYSLOG_IDENTIFIER=systemd`, exact unit-succeeded `MESSAGE_ID`, structured service `UNIT`/`USER_UNIT` |

Version 2 retains all version-1 actions and their recognition semantics:

- `service_lifecycle / restart_scheduled`;
- `service_lifecycle / process_exited`;
- `process_runtime / process_output`.

The two new rules are additive. They do not retroactively impose a new
`SYSLOG_IDENTIFIER` requirement on version-1 lifecycle recognition.

## Recognition boundary

The new actions require all of their structured anchors. Missing `UNIT` and
`USER_UNIT` means no semantic facet. A matching message ID from a source whose
`SYSLOG_IDENTIFIER` is not `systemd` means no semantic facet.

Exact lifecycle rules take precedence over generic service stdout/stderr
`process_output` recognition.

Host-specific service names do not participate in rule selection.

The semantic layer must not recognize DBus activation/timeout or CRON session
open/close from free-text `MESSAGE` patterns. Similar text paired with an
unrelated message ID must also remain unrecognized.

## Meaning boundary

`start_job_begun` records only that systemd's structured evidence identifies a
unit start job beginning execution. It does not assert that the service later
became usable or healthy.

`unit_succeeded` records only the structured systemd success observation. It
does not assert that a long-running service was correctly configured, secure,
healthy, or causally related to another observation.

Neither action implies recurrence, anomaly, threat, intrusion, intent,
causality, alerting, or response policy.

## Evidence compatibility

The semantic evidence payload remains schema version `1` and continues to
carry:

- primary taxonomy symbol and event type;
- source domain and primary classifier evidence;
- semantic family/action and exact semantic rule evidence;
- normalized systemd service subject;
- privacy-safe source order and relative timing;
- project, taxonomy, semantic-facet, window, and exact-input provenance.

Raw journal messages and absolute timestamps remain excluded.

Strict consumers must explicitly support semantic-facet version `2`. Silent
fallback to semantic-facet version `1` is prohibited.

## Acceptance evidence

The public synthetic fixture
`fixtures/synthetic/systemd-lifecycle-semantic-v2.jsonl` uses two generic
service subjects and both `UNIT` and `USER_UNIT` forms. Its message text is
opaque so recognition cannot depend on natural-language wording.

Negative tests cover:

- missing structured subject;
- non-systemd identifiers;
- unrelated message IDs with similar lifecycle text;
- lifecycle IDs combined with stdout/stderr, proving exact-rule precedence;
- DBus activation/timeout text without structured target/result anchors;
- CRON session text without structured PAM/session anchors.

The preserved private post-ARP Ubuntu window is the real acceptance case. It
must gain the newly structured lifecycle observations while keeping DBus and
CRON text-only patterns intentionally unrecognized.

## Consequences

Semantic coverage improves without expanding the primary Digit-Probe alphabet
or weakening the structured-evidence boundary.

The semantic evidence schema remains stable while consumers receive an explicit
facet-version compatibility signal.

Future semantic actions still require stable structured evidence. High-volume
free-text patterns alone are not sufficient justification for a new facet.
