# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

## [0.1.0] - 2026-08-06

### Added

- Added the explicit `system-log-dynamics collect OUTPUT.jsonl` boundary for
  bounded local Linux journal acquisition.
- Added shell-free `journalctl` execution with reviewed boot, time, unit,
  scope, event-count, and timeout selectors.
- Added privacy-minimized JSON Lines export, controlled acquisition failures,
  and diagnostics that never echo collected contents.
- Added restrictive `0600` temporary files, atomic publication, overwrite
  control, symbolic-link refusal, and default rejection of Git-worktree
  destinations.
- Added synthetic acquisition tests that never access or commit a real
  journal export.
- Added Decision 0015 documenting local-only collection, privacy, file safety,
  provenance, and the strict separation from analysis.

- Added the installed `system-log-dynamics analyze` and
  `system-log-dynamics compare` commands as thin adapters over the existing
  public pipeline.
- Added strict UTF-8 input handling, exact-byte manifest provenance, shared
  comparison configuration, optional stable window identifiers, and
  deterministic Markdown output.
- Added stable controlled exit codes and concise standard-error diagnostics
  without tracebacks for expected failures.
- Added atomic output-file creation, explicit overwrite control, input-file
  replacement protection, temporary-file cleanup, and UTF-8 output
  validation.
- Added isolated-wheel verification proving that the installed console
  script reproduces both Experiment 001 golden reports byte for byte.

- Added deterministic Markdown rendering for validated analysis windows and
  structured two-window comparisons.
- Added an immutable `WindowComparisonReport` presentation boundary retaining
  both complete window manifests and their exact `right - left` comparison.
- Added explicit numeric formatting, Markdown escaping, unavailable-value
  representation, stable table ordering, and final-newline policies.
- Added exact golden Markdown contracts for the Experiment 001 routine window
  and complete routine-versus-boot/error/burst comparison.
- Added report fixtures to source-distribution and wheel data-file contracts.

- Completed Experiment 001 with two deterministic, privacy-safe synthetic
  windows and an exact public-API contract from JSON Lines bytes through
  structured window comparison.
- Added stable routine-versus-boot/error/burst fixture hashes, symbol
  sequences, classification metadata, temporal summaries, and descriptive
  comparison expectations.
- Added wheel data files for the changelog, experiment documentation, and
  synthetic JSON Lines fixtures.

- Added typed, deterministic, immutable comparisons for completed analysis
  windows, including manifest compatibility, Digit-Probe metrics, and temporal
  aggregates.
- Added deterministic, immutable temporal burst summaries over privacy-safe
  normalized temporal coordinates.
- Added immutable per-window analysis manifests with exact-byte SHA-256 provenance.
- Added explicit manifest-schema and event-taxonomy versions.
- Added effective Digit-Probe configuration snapshots and pinned-commit extraction from installed dependency metadata.
- Added a synthetic vertical manifest contract over the exact 3387-byte classification fixture.
- Added a validated, non-empty analysis boundary for the public Digit-Probe integer API.
- Added a synthetic end-to-end contract from journal JSON Lines to structured analysis results.
- Added validated, immutable, bijective event-symbol encoding for the nine-event alphabet.
- Added lazy symbol validation and an exact synthetic end-to-end encoding fixture.
- Initial project boundaries and architectural decisions.
- First experiment contract.
- Minimal package and Digit-Probe integration test.
- Immutable raw and normalized journal event models.
- Contract tests for model validation and immutability.
- Strict streaming decoder for journal JSON Lines with line-aware errors.
- Immutable classified-event model with stable event, domain, and evidence types.
- Deterministic streaming classification with explicit precedence and rule IDs.
- Structured `UNIT` and `USER_UNIT` normalization for systemd lifecycle events.
- Synthetic end-to-end classification fixture with exact expected metadata.
- Rejection of non-finite JSON numbers, including exponent overflow.
- Field normalization with privacy-safe boot and temporal coordinates.
- Synthetic parser fixture covering multiple boot windows.
