# Decision 0009 — Validated Digit-Probe analysis boundary

## Status

Accepted for issue #7 on 2026-07-31.

## Context

Digit-Probe exposes a public function that accepts a sequence of integers and
an explicit alphabet.

Its integer mode deliberately normalizes every supplied symbol using modulo
arithmetic. With alphabet `9`, for example, the integer `17` is analyzed as
symbol `8`.

That behaviour is valid inside Digit-Probe, but it is too permissive for the
System Log Dynamics event alphabet. In this project, symbols outside `0–8`
represent invalid domain data and must never be silently reinterpreted.

## Decision

System Log Dynamics owns a controlled analysis boundary:

```text
candidate symbols
    -> complete domain validation
    -> one-time materialization
    -> Digit-Probe public API
    -> verified AnalysisResult
```

Digit-Probe is invoked only after the complete input sequence has passed the
existing event-symbol validation contract.

## Validation before analysis

The boundary accepts an iterable of candidate values and validates every item
through `iter_validated_event_symbols`.

It rejects:

- booleans;
- negative integers;
- integers greater than or equal to `9`;
- strings;
- floating-point values;
- null values;
- arbitrary objects.

It performs no parsing, coercion, truncation, fallback, or modulo
normalization.

If validation fails, Digit-Probe is not invoked.

Consumption stops at the first invalid value, and later iterable elements are
not consumed.

## Materialization

Digit-Probe requires a `Sequence[int]`, while the System Log Dynamics boundary
accepts any iterable.

The validated sequence is therefore materialized into one list exactly once.

This materialization also establishes an atomic boundary: Digit-Probe receives
either the complete validated sequence or no sequence at all.

## Empty sequences

Although Digit-Probe can calculate an `AnalysisResult` for an empty sequence,
that result contains several undefined descriptive values such as `NaN` and
infinite gaps.

System Log Dynamics rejects empty event sequences with a controlled
`ValueError` before invoking Digit-Probe.

An analysis window must contain at least one validated event.

## Alphabet ownership

System Log Dynamics always invokes Digit-Probe with:

```python
alphabet = EVENT_ALPHABET_SIZE
```

The current alphabet size is exactly `9`.

Callers cannot supply a different alphabet through the analysis API. Alphabet
selection remains coupled to the documented event-symbol taxonomy.

## Configuration

The boundary accepts the public `digit_probe.AnalysisConfig` or `None`.

A supplied configuration object is passed to Digit-Probe unchanged. System Log
Dynamics neither copies nor mutates it.

No Digit-Probe private helper or statistical implementation is duplicated.

## Result contract

The public Digit-Probe `AnalysisResult` is returned unchanged.

Before returning it, the boundary verifies that:

- the result is an `AnalysisResult`;
- `mode` is `integers`;
- `alphabet` is `9`;
- `sample_size` matches the validated input length;
- `max_observed` is an integer between `0` and `8`.

These checks detect dependency-contract drift or an invalid result without
rewriting the result.

## Classified-event composition

The convenience API for classified events is deliberately thin:

```text
ClassifiedJournalEvent iterable
    -> existing event encoder
    -> validated analysis boundary
```

It does not introduce a second mapping or an alternative validation path.

## End-to-end fixture

The existing synthetic journal fixture verifies the complete vertical slice:

```text
journal JSON Lines
    -> normalized events
    -> classified events
    -> validated integer symbols
    -> Digit-Probe AnalysisResult
```

The resulting stable structural contract is:

- mode: `integers`;
- sample size: `14`;
- alphabet: `9`;
- counts:
  - `0: 2`
  - `1: 2`
  - `2: 1`
  - `3: 1`
  - `4: 1`
  - `5: 2`
  - `6: 2`
  - `7: 1`
  - `8: 2`
- maximum observed symbol: `8`.

Floating-point statistics are not all frozen as compatibility assertions.
They remain descriptive outputs owned by Digit-Probe.

## Interpretation

Digit-Probe results are descriptive and representation-dependent.

This boundary does not claim that any statistic proves anomaly, randomness,
compromise, malicious behaviour, or intent.

## Scope exclusions

This decision does not introduce:

- Markdown or JSON reporting;
- result serialization;
- analysis manifests;
- comparison between analysis windows;
- temporal burst metrics;
- anomaly or security inference;
- command-line interfaces;
- live journal access.
