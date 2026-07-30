# Decision 0001 — Project foundation

## Status

Accepted on 2026-07-30.

## Context

System Log Dynamics must be an autonomous public project and a real
consumer of Digit-Probe. It must not copy Digit-Probe internals or become
part of ubuntu-system-tools.

## Decisions

- Use a Python package with a src layout.
- Require Python 3.11 or newer.
- Keep a dedicated virtual environment.
- Depend on Digit-Probe through its public importable API.
- Pin the distributive dependency to a verified Git commit until an
  appropriate release is available from a package index.
- Use journal JSON Lines as the canonical input format.
- Keep event type separate from source domain.
- Treat every result as descriptive and representation-dependent.
- Keep real journal exports outside version control.

## Consequences

Installation currently requires Git access. The dependency pin must be
reviewed when Digit-Probe publishes a suitable tagged or indexed release.
