# Decision 0008 — Validated event-symbol encoding

## Status

Accepted for issue #5 on 2026-07-31.

## Boundary

Integer encoding is a deterministic downstream transformation:

    ClassifiedJournalEvent
        -> validated integer symbol

The encoder consumes the semantic `event_type` only. Source domain, evidence,
rule identifier, normalized fields, message content, priority, and classifier
implementation details do not affect the symbol.

Encoding does not invoke Digit-Probe or perform analysis.

## Alphabet

The alphabet size is exactly `9`.

| Event type | Symbol |
| --- | ---: |
| `boot_boundary` | `0` |
| `service_started` | `1` |
| `service_stopped` | `2` |
| `authentication_success` | `3` |
| `authentication_failure` | `4` |
| `session_boundary` | `5` |
| `warning` | `6` |
| `error` | `7` |
| `other` | `8` |

This mapping is explicit and does not depend on enum declaration order,
mapping insertion order, or classifier rule precedence.

## Bijection and immutability

Every event type maps to exactly one symbol and every symbol maps to exactly one
event type.

The public forward and reverse mappings are read-only views. Callers cannot
replace, remove, or add mapping entries at runtime.

The mapping is part of the reproducibility contract. A future incompatible
mapping requires a new documented contract rather than silent reuse of the
existing symbols.

## Validation

A valid symbol:

- has concrete type `int`;
- is not a boolean;
- is greater than or equal to `0`;
- is less than `9`.

Booleans are rejected even though Python treats `bool` as a subclass of `int`.

Negative integers, integers greater than or equal to `9`, strings, floats,
null values, and arbitrary objects are rejected.

The boundary performs no coercion, parsing, truncation, silent fallback, or
modulo normalization.

This validation occurs both for externally supplied symbols and for symbols
returned by the event encoder.

## Streaming behaviour

The streaming APIs:

- preserve input order;
- emit one symbol for each accepted input;
- remain lazy;
- do not buffer the complete iterable;
- stop at the first invalid input;
- do not consume later inputs after an error;
- accept empty iterables.

## Synthetic fixture

`fixtures/synthetic/encoding-expected.jsonl` records:

- alphabet size;
- complete event-to-symbol mapping;
- exact expected symbol sequence for the synthetic classification fixture.

The end-to-end contract is:

    journal JSON Lines
        -> normalized events
        -> classified events
        -> validated integer symbols

The expected sequence is:

    0, 1, 5, 5, 4, 3, 6, 7, 8, 8, 1, 2, 0, 6

## Digit-Probe boundary

Digit-Probe is downstream from this decision.

This unit neither imports nor calls Digit-Probe. A later integration step may
pass only already validated symbols together with the explicit alphabet size
of `9`.
