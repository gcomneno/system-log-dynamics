# Decision 0002 — Journal input contract

## Status

Accepted on 2026-07-30.

## Canonical format

One JSON journal object per line, compatible with journalctl output=json.

## Candidate selected fields

- __REALTIME_TIMESTAMP
- __MONOTONIC_TIMESTAMP
- _BOOT_ID
- PRIORITY
- MESSAGE
- MESSAGE_ID
- _TRANSPORT
- _SYSTEMD_UNIT
- SYSLOG_IDENTIFIER

## Normalization constraints

Journal JSON values are not guaranteed to be strings. A value may be
null, a list produced by duplicate fields, or a byte array representing
non-printable data.

The parser must therefore validate every supported field explicitly.
Unsupported representations must produce a controlled diagnostic rather
than an implicit string conversion.

Absolute timestamps and boot identifiers may be used during local
processing but must not leak into public derived reports.
