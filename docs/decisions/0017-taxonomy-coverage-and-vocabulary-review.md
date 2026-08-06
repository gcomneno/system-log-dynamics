# Decision 0017 — Taxonomy coverage and Linux vocabulary review

## Status

Accepted for issue #26 on 2026-08-06.

## Context

A bounded real-journal road test classified a substantial proportion of its
events as `other`. That proportion does not by itself indicate danger,
classifier failure, or inadequate event semantics.

The project nevertheless needs an explicit measure of how much of an analyzed
window maps to named taxonomy categories and a reviewable decision about
security-relevant Linux vocabulary.

## Taxonomy coverage

Coverage is derived only from the complete validated symbol counts already
contained in an analysis result.

The `other` symbol partitions every non-empty window into:

- named-event count and proportion;
- `other` count and proportion;
- represented named categories;
- absent named categories.

Coverage status has exactly three structural values:

- `all_named`: no event is classified as `other`;
- `mixed`: named categories and `other` are both present;
- `all_other`: every event is classified as `other`.

These values use no thresholds and express no quality or security judgement.

Two-window coverage comparisons use `right - left` deltas and report named
categories that become represented or become absent.

## Linux vocabulary review

The issue #26 synthetic review fixture evaluates the requested concepts against
the existing taxonomy.

| Linux concept | Existing representation |
| --- | --- |
| SSH authentication success | `authentication_success` |
| SSH authentication failure | `authentication_failure` |
| `sudo` session open or close | `session_boundary` when bounded session wording occurs in authentication context |
| Generic session open or close | `session_boundary` only in supported session or authentication context |
| Service start | `service_started` |
| Service stop | `service_stopped` |
| Service restart | one observed stop followed by one observed start |
| Service failure | `error` or `warning` when supported severity evidence exists; otherwise `other` |
| Account or authorization denial | `authentication_failure` only in authentication source context |
| Repeated access denials | repeated classified events; repetition remains an analysis property, not a new event type |

The review does not infer privilege, intent, compromise, or causality from a
`sudo` source. It also does not collapse two lifecycle observations into an
invented restart event.

Security-adjacent phrases outside supported source context remain `other`
unless an independent severity rule applies.

## Decision

The event taxonomy remains at version `1`.

No event type, integer symbol, rule precedence, manifest schema, or
classification meaning changes in issue #26.

The review found missing fixture exercise for existing rules, not a requirement
for additional event semantics.

The public synthetic evidence is:

- `fixtures/synthetic/taxonomy-coverage-review.jsonl`;
- `fixtures/synthetic/taxonomy-coverage-review-expected.jsonl`;
- `tests/test_taxonomy_coverage_review_fixture.py`.

## Downstream boundary

Coverage may help a downstream consumer assess how much evidence is represented
by named SLD categories. It must not be treated as an anomaly score, threat
score, intrusion verdict, classifier-quality score, safety claim, or automatic
response trigger.
