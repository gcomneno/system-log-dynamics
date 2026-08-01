# Decision 0011 — Deterministic temporal burst summaries

## Status

Accepted for issue #11 on 2026-08-01.

## Context

Digit-Probe owns symbolic analysis, while normalized journal events expose
privacy-safe relative realtime and indexed boot-local monotonic coordinates.
The project needs a small descriptive temporal summary without making timing
part of the symbolic-analysis contract.

## Decision

`summarize_temporal_bursts` consumes one validated iterable of normalized
events and returns a frozen, slotted `TemporalBurstSummary`. It retains only
numeric aggregates, never messages, source lines, absolute timestamps, or
original boot identifiers.

Relative realtime is the primary coordinate. For adjacent events without two
realtime values, same-boot monotonic time is the fallback. A known transition
between different boot indexes is an explicit boundary: it produces no gap and
ends a burst even if realtime values exist. Missing or incomparable coordinates
also produce no gap, end a burst, and are never bridged. Equal timestamps yield
valid zero gaps.

Duration is the observation span rather than a sum of bursts. It is the last
minus first available relative realtime value when any exist, including across
boot boundaries. Otherwise it is the first-to-last monotonic span only when
all usable observations are from one known boot; otherwise it is unavailable.

A burst is a run of at least two adjacent events joined by valid gaps no larger
than the caller's positive integer threshold. Larger, missing, incomparable,
and boot-boundary gaps terminate it. Burst event membership is disjoint across
completed bursts. The summary records the number of bursts, total participating
events, largest membership, and greatest sum of connecting gaps. Gap statistics
cover every valid adjacent gap, including gaps too large for a burst.

The function validates exact normalized-event inputs, strictly increasing
sequence indexes, nondecreasing relative realtime values, and nondecreasing
same-boot monotonic values. The summary constructor validates its aggregate
invariants, including values created through `dataclasses.replace`; booleans
and malformed numeric values are rejected rather than normalized.

## Consequences

The result describes only timing density and observed spacing. It does not
infer anomalies, causality, security relevance, behaviour, or intent.

This decision adds no window comparison, reporting, command-line interface,
live journal access, or anomaly inference. It neither changes Digit-Probe nor
makes temporal data part of its symbolic analysis.
