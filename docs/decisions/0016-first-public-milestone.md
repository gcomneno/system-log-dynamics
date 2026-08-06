# Decision 0016 — First public milestone release boundary

## Status

Accepted on 2026-08-06 for the 0.1.0 release candidate.

## Context

The project now has a deterministic file-based pipeline, Experiment 001,
structured comparison, deterministic Markdown reporting, installed analyze
and compare commands, and bounded privacy-safe local acquisition. These
features need a coherent public milestone without overstating what the
analysis can establish.

## Decision

Use 0.1.0 as the first public milestone. The project remains pre-1.0 because
its outputs are descriptive and representation-dependent; they do not support
claims about randomness, compromise, malicious behaviour, user intent, or
administrator intent.

Digit-Probe has a public `v0.1.0` release at commit
`86867d600fb8c8836bed43b7543270d6ffd93aa8`, but that release predates the packaged public API consumed
by this project. Its `pyproject.toml` contains tooling configuration but no
`[project]` package metadata, while the selected commit is fourteen commits
ahead and declares Digit-Probe version `1.0.0`.

Keep Digit-Probe at immutable full commit
`55e3eae4c55017703e023c1aaac0838b873482db`. The older release is not a compatible distributive replacement, and
a branch, tag name, or floating dependency range is not acceptable. Analysis
manifests retain the installed dependency commit as provenance.

Publication requires separate maintainer approval after a final release
commit or pull request, complete validation, squash merge, an annotated
`v0.1.0` tag, and GitHub Release notes. Artifact publication is optional and
separate from tagging.

## Consequences

The release documentation and contract tests keep package, distribution, and
manifest version surfaces aligned. Public release material carries only
synthetic fixtures and descriptive documentation. A discovered defect is
handled through a new corrective release rather than rewriting public history.
