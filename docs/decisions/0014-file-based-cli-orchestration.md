# Decision 0014 — File-based CLI orchestration and atomic output

## Status

Accepted for issue #15 on 2026-08-06.

## Context

System Log Dynamics already exposes validated public boundaries for strict
journal JSON Lines parsing and normalization, deterministic classification,
event-symbol encoding, Digit-Probe analysis, exact-byte manifests, temporal
summaries, structured window comparison, and deterministic Markdown
reporting.

A command-line interface is needed to compose those boundaries for ordinary
file-based use. It must not become a second analytical implementation,
reinterpret errors, weaken provenance, access the live journal, or introduce
environment-dependent output.

File output also requires an explicit safety contract. A failure during
rendering or writing must not leave a partial report, silently replace an
existing destination, or modify either input file.

## Decision

The package exposes this console script:

```toml
[project.scripts]
system-log-dynamics = "system_log_dynamics.cli:main"
```

It provides two commands:

```text
system-log-dynamics analyze INPUT.jsonl
system-log-dynamics compare LEFT.jsonl RIGHT.jsonl
```

The CLI remains a thin adapter. For each input it:

1. reads the file once as exact immutable bytes;
2. decodes those bytes with strict UTF-8;
3. normalizes and materializes the journal events;
4. classifies the normalized events;
5. invokes the existing Digit-Probe analysis boundary;
6. builds the manifest from the original exact bytes;
7. calculates the temporal summary;
8. constructs a validated `AnalysisWindow`;
9. renders the existing deterministic Markdown contract.

The compare command builds both windows with the same explicit
`AnalysisConfig` and burst threshold, then delegates compatibility,
comparison, report composition, and rendering to their existing public
boundaries.

Input paths are never used as implicit window identifiers. Callers may
provide stable identifiers explicitly; otherwise the established
`unidentified` presentation remains path-independent.

Standard output is the default destination and is written as explicit UTF-8.
File output is prepared completely in a temporary file created in the
destination directory. The temporary file is flushed and synchronized
before publication.

Without `--overwrite`, publication uses a hard-link operation that succeeds
only when the destination does not exist. With `--overwrite`, publication
uses `os.replace` for atomic replacement. A resolved output path equal to an
input path is always rejected, including when overwrite was requested.
Temporary files are removed after controlled failures.

The stable exit-code contract is:

| Code | Meaning |
| ---: | --- |
| 0 | success |
| 2 | command-line usage failure |
| 3 | input file access failure |
| 4 | UTF-8 decoding failure |
| 5 | journal parsing or normalization failure |
| 6 | analytical or reporting contract failure |
| 7 | standard-output or output-file failure |

Expected failures emit concise diagnostics to standard error and do not
print tracebacks. The CLI does not inspect Git state, package source paths,
terminal width, locale, environment metadata, or the network.

## Consequences

Identical input bytes and arguments produce the same report bytes as the
public Python pipeline and reviewed golden fixtures.

The CLI preserves exact-byte manifest provenance while still using decoded
text for the strict journal parser. Renaming an input file does not alter a
report unless the caller also changes an explicit window identifier.

Analysis and presentation semantics remain owned by their existing modules.
The CLI owns only argument validation, orchestration, controlled diagnostic
classification, destination selection, and safe publication.

Atomic publication relies on filesystem support for same-directory hard
links or replacement. Unsupported filesystem operations produce exit code
7 rather than weakening overwrite safety.

This decision adds no live `journalctl` execution, stdin streaming,
configuration files, JSON or YAML output, background operation, network
access, anomaly detection, or security inference.
