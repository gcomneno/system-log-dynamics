# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Added

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
