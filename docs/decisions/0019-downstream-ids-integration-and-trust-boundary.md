# Decision 0019 — Downstream IDS integration and trust boundary

Status: Accepted

## Context

System Log Dynamics now exposes deterministic human-readable reports and
versioned machine-readable evidence bundles. That evidence can be useful to a
future security-oriented consumer, but the existence of a machine-readable
integration boundary must not turn System Log Dynamics into an intrusion
detection system.

Security interpretation, policy, alerting, incident handling, AI assistance,
triggering, and response have different trust and audit requirements from
deterministic descriptive analysis.

Those responsibilities must therefore remain outside this repository.

## Decision

System Log Dynamics is an evidence engine, not an IDS.

System Log Dynamics owns:

- bounded local journal acquisition;
- privacy-safe file handling;
- deterministic parsing and normalization;
- explicit taxonomy and symbol encoding;
- reproducible statistical analysis;
- deterministic temporal summaries and window comparisons;
- deterministic Markdown reporting;
- versioned machine-readable evidence export;
- provenance, schema versions, and semantic limitations.

A separate downstream consumer may own:

- security-domain correlation across evidence windows;
- security baselines and policies;
- signal derivation;
- alert prioritization and analyst workflow;
- incident hypotheses and incident confirmation;
- reviewed trigger definitions;
- explainable AI-assisted interpretation;
- notification;
- response authorization and response actions.

None of those downstream concepts becomes an output or hidden semantic of
System Log Dynamics.

## Accepted evidence contract

The current downstream boundary accepts only evidence schema version `1`.

The accepted document kinds are:

- `system-log-dynamics.analysis-evidence`, bundle type `analysis_window`;
- `system-log-dynamics.comparison-evidence`, bundle type
  `window_comparison`.

A consumer must perform strict complete-payload validation. Envelope-only
parsing is not sufficient for a trusted integration decision.

An unknown schema name, unknown bundle type, incompatible version, malformed
payload, duplicate key, or other version-1 contract violation must be rejected.

Support for a future evidence schema version requires an explicit consumer
change. Consumers must not silently coerce a future version into version 1.

## Provenance preservation

A downstream consumer must preserve the evidence reference and the provenance
required to reproduce its source observations.

For each analysis snapshot this includes:

- evidence schema name and version;
- bundle type;
- System Log Dynamics project version;
- Digit-Probe commit;
- analysis-manifest schema version;
- taxonomy version;
- window identifier when present;
- input digest algorithm;
- input SHA-256;
- input byte size;
- effective analysis configuration.

For a comparison, provenance for both windows and the declared comparison
direction must remain associated with downstream interpretation.

A downstream system may add its own identifiers and metadata, but it must not
replace or obscure the source provenance.

## Privacy boundary

Raw journal bytes remain private inputs.

A downstream consumer must not require raw journal messages, usernames,
hostnames, addresses, credentials, tokens, private paths, or other source
material by default.

Access to raw source material requires a separately approved workflow outside
the default evidence integration contract.

Derived evidence is not automatically safe to publish. Counts, timing,
digests, configuration, window identifiers, and other derived fields may still
be sensitive in context and require data-minimization review before sharing.

## Hash trust boundary

An input digest establishes the identity of the exact bytes used by the
analysis.

It does not establish:

- that those bytes are true;
- that the originating system is authentic;
- that collection was complete;
- that the source was not tampered with before hashing;
- that the resulting observations imply any security conclusion.

Determinism establishes reproducibility from the accepted input and
configuration, not truth or security validity.

## Observation-to-incident vocabulary

The integration boundary uses the following terms deliberately.

### Observation

A descriptive fact or metric produced by System Log Dynamics from accepted
input bytes and configuration.

An observation contains no security conclusion.

### Signal

A downstream security-relevant indication derived from one or more
observations under an explicit rule, policy, or reviewed interpretation.

System Log Dynamics does not emit signals.

### Alert

A downstream workflow object indicating that one or more signals warrant
attention under the downstream system's policy.

An alert is not a confirmed incident.

System Log Dynamics does not emit alerts.

### Incident hypothesis

A provisional downstream explanation that relates evidence and signals to a
possible security event.

It remains unconfirmed and must retain references to its source evidence.

System Log Dynamics does not emit incident hypotheses.

### Confirmed incident

A downstream organizational or analyst conclusion reached under an explicit
incident-confirmation policy.

System Log Dynamics never confirms incidents.

## AI trust boundary

AI output is untrusted advisory material.

If a downstream system uses an AI model, the AI output must remain
distinguishable from System Log Dynamics observations and from reviewed
security conclusions.

AI output cannot by itself:

- change System Log Dynamics evidence;
- become a confirmed incident;
- authorize a trigger;
- authorize a response action.

A downstream rule or analyst conclusion derived with AI assistance must be
explicitly reviewed under the downstream system's own policy.

## Trigger audit boundary

Any downstream trigger derived from System Log Dynamics evidence must be
auditable independently from the evidence bundle.

The audit record should retain at minimum:

- trigger identifier and version;
- source evidence reference;
- accepted evidence schema name and version;
- preserved source provenance;
- downstream rule or policy identifier and version;
- the observations or signals used by the trigger;
- evaluation result;
- review or approval state;
- any AI-assisted advisory reference when applicable;
- any separately authorized response decision.

An evidence bundle alone never defines, approves, or authorizes a trigger.

## Response boundary

Notification, blocking, quarantine, remediation, account changes, service
changes, or any other response action are downstream responsibilities.

No response action may be inferred as authorized merely because a System Log
Dynamics evidence bundle exists or contains a particular metric.

Response authorization must be explicit and separate from evidence production.

## Synthetic integration example

The privacy-safe synthetic analogue of the intended production flow is:

`synthetic journal bytes -> System Log Dynamics -> evidence schema v1 ->
strict downstream consumer`

In production the first element may be private journal bytes, but those bytes
remain on the System Log Dynamics side of the boundary by default.

The downstream consumer receives the validated evidence bundle and preserves
its provenance.

The example stops there.

Signal derivation, alerting, incident hypotheses, incident confirmation,
triggers, AI interpretation, and response actions are outside System Log
Dynamics and are intentionally not demonstrated by this repository.

## Consequences

A future IDS can consume stable deterministic evidence without requiring
Markdown parsing or private journal access.

The future IDS can evolve its own security semantics without changing the
meaning of System Log Dynamics observations.

System Log Dynamics remains reproducible, local-first, descriptive, and free
from runtime AI, alerting, trigger, or security-response responsibilities.
