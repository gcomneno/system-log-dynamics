# Decision 0003 — Initial event taxonomy

## Status

Provisional for experiment 001.

## Primary symbol alphabet

- 0: boot_boundary
- 1: service_started
- 2: service_stopped
- 3: authentication_success
- 4: authentication_failure
- 5: session_boundary
- 6: warning
- 7: error
- 8: other

The alphabet size is 9.

## Source domains

Source domains are retained as metadata and are not encoded directly in
the primary symbol:

- service
- authentication
- session
- kernel
- network
- other

## Classification evidence

Every classified event must record the rule identifier and one of these
evidence levels:

- exact
- heuristic
- fallback

## Encoding boundary

Before calling Digit-Probe, every symbol must be a non-boolean integer in
the interval from zero, inclusive, to the alphabet size, exclusive.
