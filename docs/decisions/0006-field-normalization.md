# Decision 0006 — Journal field normalization

## Status

Accepted for issue #1 on 2026-07-30.

## Numeric fields

`__REALTIME_TIMESTAMP` and `__MONOTONIC_TIMESTAMP` accept:

- a non-negative JSON integer;
- a non-empty ASCII decimal string.

Booleans, floats, signed strings, whitespace-padded strings, arrays, objects,
and negative values are rejected.

`PRIORITY` accepts an integer from zero through seven or the equivalent
one-character decimal string.

## Text fields

Selected textual fields, including `_SYSTEMD_UNIT`, `UNIT`, and
`USER_UNIT`, accept only:

- a JSON string;
- null;
- an absent field.

`_SYSTEMD_UNIT` identifies the source process unit. `UNIT` and `USER_UNIT`
identify structured unit subjects and remain separate normalized fields.

Arrays created by repeated journal fields are rejected because selecting one
value would be arbitrary.

Byte arrays created by non-printable journal data are rejected because silently
decoding or replacing bytes would alter the source representation.

## Boot identifiers

A non-empty boot identifier is mapped to a zero-based ordinal according to
first-seen order. The original identifier is not retained by the normalized
model.

## Temporal coordinates

The first available realtime timestamp establishes offset zero. Later available
realtime timestamps must not decrease.

Monotonic timestamps must not decrease within the same known boot. They may
restart when a new boot identifier is encountered.

When the boot identifier is missing, the monotonic value is retained but no
cross-event monotonic ordering claim is made.

## Streaming composition

`iter_normalized_journal_json_lines` composes strict JSON Lines decoding and
field normalization without loading the complete input into memory.
