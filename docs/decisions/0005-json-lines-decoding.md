# Decision 0005 — Strict JSON Lines decoding

## Status

Accepted for issue #1 on 2026-07-30.

## Streaming boundary

`iter_journal_json_lines` consumes an iterable of text lines and yields
`RawJournalEvent` instances in input order.

Physical source line numbers are preserved even when some lines do not produce
events.

## Blank lines

Whitespace-only lines are ignored. Empty input is valid and produces no events.

## Strict JSON policy

Each non-blank line must contain exactly one JSON object.

The decoder rejects:

- malformed JSON;
- top-level arrays, strings, numbers, booleans, and null values;
- duplicate object keys, including duplicates inside nested objects;
- non-standard constants such as `NaN` and positive or negative infinity;
- input lines that are not text.

Every rejection produces `JournalParseError` with the physical source line
number and a stable diagnostic.

## Value preservation

The decoder does not interpret journal fields. Strings, null values, numbers,
booleans, arrays, and nested objects remain raw JSON values.

The resulting JSON tree is copied and recursively frozen:

- objects become immutable mappings;
- arrays become tuples;
- scalar values remain scalars.

Field-specific validation and normalization occur after decoding.
