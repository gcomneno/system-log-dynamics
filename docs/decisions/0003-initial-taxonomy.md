# Decision 0003 — Event taxonomy

## Status

Accepted for issue #3 on 2026-07-31.

## Event types

The deterministic classifier produces exactly one of these stable string-valued
event types:

- `boot_boundary`
- `service_started`
- `service_stopped`
- `authentication_success`
- `authentication_failure`
- `session_boundary`
- `warning`
- `error`
- `other`

The taxonomy does not assign integer symbols. Integer encoding is a separate
downstream contract.

## Source domains

Every classified event also carries one source domain:

- `service`
- `authentication`
- `session`
- `kernel`
- `network`
- `other`

Source domain is metadata independent from event type. A kernel event may, for
example, classify as `warning`, `error`, `boot_boundary`, or `other`.

## Evidence levels

Every classified event records one evidence level:

- `exact`: structured journal fields or explicit stream state;
- `heuristic`: a bounded and documented textual rule;
- `fallback`: no semantic or severity rule matched.

## Rule precedence

Event-type rules use first-match precedence:

1. boot boundary;
2. service lifecycle;
3. session boundary;
4. authentication failure, then authentication success;
5. error severity;
6. warning severity;
7. fallback other.

Source-domain selection is evaluated independently and does not modify this
precedence.

## Reproducibility

Each result includes a stable rule identifier. Published rule identifiers are
part of the experiment contract and must not be silently repurposed.
