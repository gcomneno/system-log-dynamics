# Decision 0007 — Deterministic event classification

## Status

Accepted for issue #3 on 2026-07-31. The boot-boundary streaming rule is superseded by Decision 0020.

## Streaming state

Classification consumes normalized events in input order without buffering the
complete stream.

The classifier remembers the most recently observed non-null `boot_index`.

A known boot index produces `boot_boundary` when it is the first known boot or
differs from the remembered index. An event without a boot index neither
creates nor erases boot context.

## Structured service lifecycle rules

The following systemd message identifiers are recognized:

- `39f53479d3a045ac8e11786248231fbf`: unit started;
- `9d1aaa27d60140bd96365438aad20286`: unit stopped.

An exact service lifecycle match additionally requires `UNIT` or `USER_UNIT`
to identify a `.service` subject.

`_SYSTEMD_UNIT` is retained separately as the source process unit and is not
treated as the structured job subject.

Stable exact rule identifiers are:

- `service.message_id.started`
- `service.message_id.stopped`

## Heuristic service lifecycle rules

When service context exists, a message beginning with `Started ` or `Stopped `
may classify as service lifecycle evidence.

Service context requires at least one of:

- `UNIT` ending in `.service`;
- `USER_UNIT` ending in `.service`;
- `_SYSTEMD_UNIT` ending in `.service`.

Stable heuristic rule identifiers are:

- `service.message.started`
- `service.message.stopped`

Generic lifecycle words without service context do not match.

## Session rules

The following systemd session message identifiers produce exact
`session_boundary` classification:

- `8d45620c1a4348dbb17410da57c60c66`: session started;
- `3354939424b4456d9802ca8333ed424a`: session stopped.

The exact rule identifier is `session.message_id.boundary`.

Within session or authentication source context, the following bounded textual
forms provide heuristic evidence:

- `new session ` or `session opened`;
- `removed session ` or `session closed`.

The stable identifiers are:

- `session.message.opened`
- `session.message.closed`

Session rules run before authentication rules.

## Authentication rules

Authentication text rules require authentication source context derived from a
documented identifier or source unit.

Failure phrases are evaluated before success phrases. The stable identifiers
are:

- `authentication.message.failure`
- `authentication.message.success`

Generic success or failure words outside authentication context do not match.

## Severity and fallback

After semantic rules:

- priorities 0 through 3 use `severity.priority.error`;
- priority 4 uses `severity.priority.warning`;
- all remaining unmatched events use `fallback.other`.

Severity rules use exact evidence. The fallback uses fallback evidence.

## Source-domain precedence

Source-domain selection is deterministic:

1. authentication;
2. session;
3. network;
4. kernel;
5. service;
6. other.

The domain decision is independent from event-type precedence.

## Privacy and scope

Classification uses only the normalized event model. It does not access the
live journal, emit raw boot identifiers, assign integer symbols, invoke
Digit-Probe, produce reports, or infer compromise or intent.
