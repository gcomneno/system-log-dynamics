# Decision 0020 — Observed boot-transition semantics

## Status

Accepted for issue #33 on 2026-08-10.

This decision supersedes the boot-boundary streaming rule in Decision 0007.

## Context

A production road test analyzed two adjacent bounded journal windows from the
same Linux boot.

Each window independently produced one `boot_boundary` at its first event even
though no boot transition occurred inside either window.

The cause was deterministic but semantically misleading: classification began
without prior boot context, so the first known `boot_index` was treated as if a
boot change had been observed.

When both windows were classified as one continuous stream, only the first
window produced that synthetic boundary and the second window began with its
normal event classification.

A bounded analysis must not claim to have observed an event that occurred
before the beginning of its evidence window.

## Decision

The classifier remembers the most recently observed non-null `boot_index`.

The first known boot index initializes stream context only. It does not emit a
`boot_boundary`.

A later known boot index emits `boot_boundary` only when it differs from the
most recently observed known boot index.

An event without a boot index neither creates nor erases boot context.

The event that initializes boot context continues through the normal
classification precedence and may therefore become a service, session,
authentication, severity, or fallback event.

The stable exact rule identifier for an observed transition remains
`boot.index.changed`.

## Taxonomy version

This change narrows the semantic meaning of `boot_boundary`.

Taxonomy version `1` allowed the first known boot in a bounded stream to be
classified as a boundary.

Taxonomy version `2` defines `boot_boundary` exclusively as a transition
between two distinct known boot indexes observed within the accepted stream.

The event names, alphabet size, and integer symbol mapping remain unchanged.
`boot_boundary` remains symbol `0`.

Because event meaning changes even though the symbol mapping does not, evidence
and manifests produced under taxonomy version `1` and taxonomy version `2`
must remain distinguishable through provenance.

## Consequences

A window beginning in the middle of a running boot no longer invents a
boundary at sequence index zero.

A stream containing a real transition between two known boots still emits one
exact `boot_boundary` at the first event carrying the new boot index.

Missing boot identifiers do not create false transitions.

Previously generated deterministic reports and machine-readable evidence may
change because the first event of affected windows now receives its normal
classification instead of symbol `0`.

Only artifacts derived from affected classification sequences should be
regenerated.

This decision changes no IDS, anomaly, threat, causality, or intent semantics.
System Log Dynamics remains descriptive only.
