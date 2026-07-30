# Decision 0004 — Internal event model

## Status

Accepted for issue #1 on 2026-07-30.

## Raw event

`RawJournalEvent` contains:

- the one-based source line number;
- an immutable copy of the decoded JSON object.

The raw model is an untrusted parsing boundary. It may temporarily contain
sensitive journal values and must not be emitted in public reports.

## Normalized event

`NormalizedJournalEvent` contains:

- a zero-based sequence index;
- the original one-based source line number;
- a privacy-safe ordinal boot index;
- a realtime offset in microseconds relative to the first accepted event;
- an optional monotonic timestamp in microseconds;
- an optional syslog priority from zero through seven;
- selected optional textual journal fields.

The normalized model does not contain the original realtime timestamp or boot
identifier.

## Validation

- Boolean values are never accepted as integers.
- Sequence indexes and temporal values are non-negative.
- Source line numbers are positive.
- Priorities are limited to the syslog range from zero through seven.
- Optional textual fields accept only strings or null values.

## Parser responsibility

The parser will:

- decode JSON Lines;
- assign sequence indexes;
- convert boot identifiers to first-seen ordinal indexes;
- derive relative realtime offsets;
- validate timestamp ordering;
- apply the documented policy for nulls, duplicate values, and byte arrays.
