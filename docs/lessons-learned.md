# Lessons Learned

## 2026-07-30 — Verify installed code independently

An existing Digit-Probe virtual environment contained installed files
that differed from the clean repository source. Clean installation tests
from both the local repository and the pinned Git commit succeeded.

Consumer projects must use their own environment and verify dependencies
from a clean installation rather than trusting a neighbouring project
environment.

## 2026-07-30 — Validate before modulo normalization

Digit-Probe intentionally maps integer symbols through modulo alphabet.
System Log Dynamics requires stricter classifier integrity, so it must
reject negative and out-of-range symbols before invoking Digit-Probe.

## 2026-07-30 — Journal JSON is structurally wider than strings

Journal JSON fields may be null, arrays caused by repeated fields, or byte
arrays caused by non-printable data. Normalization must handle or reject
these representations explicitly.
