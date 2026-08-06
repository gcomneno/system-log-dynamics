# Decision 0015 — Privacy-safe local journal acquisition

## Status

Accepted for issue #16 on 2026-08-06.

## Context

System Log Dynamics can analyze deterministic journal JSON Lines files, but
real journal data may contain usernames, hostnames, addresses, paths, tokens,
identifiers, message contents, and other sensitive information.

Local collection therefore requires a separate boundary with explicit
selection, data minimization, controlled process execution, restrictive file
handling, and no automatic publication.

Collection must not become part of analysis and must not silently alter the
bytes later used for provenance.

## Decision

The installed console script exposes:

```text
system-log-dynamics collect OUTPUT.jsonl [selection options]
```

The output path is mandatory. Collection is accepted only when bounded by at
least one of these policies:

- exactly one boot through `--boot`;
- a positive maximum event count through `--max-events`;
- a complete `--since` and `--until` pair.

System and user units may be selected through repeatable explicit options.
System and user journal scopes are mutually exclusive.

No arbitrary journal query or shell fragment is accepted.

### Process execution

`journalctl` is invoked through an explicit argument vector with no shell.

The command requests JSON Lines and only the fields consumed by the existing
parser:

- `__REALTIME_TIMESTAMP`;
- `__MONOTONIC_TIMESTAMP`;
- `_BOOT_ID`;
- `PRIORITY`;
- `MESSAGE`;
- `MESSAGE_ID`;
- `_TRANSPORT`;
- `_SYSTEMD_UNIT`;
- `SYSLOG_IDENTIFIER`;
- `UNIT`;
- `USER_UNIT`.

Collection does not parse, normalize, classify, encode, analyze, compare,
report, or construct manifests.

Executable lookup failures, permission failures, non-zero process outcomes,
timeouts, empty output, invalid UTF-8, and output failures are converted into
controlled diagnostics without tracebacks.

Captured event contents and `journalctl` standard error are never copied into
normal diagnostics.

### Privacy boundary

Collected bytes remain local. The collector performs no network access,
upload, Git command, staging, commit, or publication.

Output inside a Git worktree is refused by default. A caller may override that
guard only through `--allow-repository-output`, which emits a strong warning.

The recommended destination is a private directory outside every repository.

No redaction or anonymization is performed. The file contains the exact bytes
returned by `journalctl`; any later transformation must be explicit and would
represent a different provenance source.

### File safety

The final output path must not be a symbolic link.

Output is first written to a same-directory temporary file with mode `0600`,
flushed, synchronized, and then published atomically.

Existing output is refused unless `--overwrite` is supplied. Explicit
overwrite replaces the destination atomically. Temporary files are removed
after controlled failures.

Successful collection prints only:

- final destination;
- byte count;
- event-line count.

It never prints event contents.

### Exit codes

Collection reuses the established CLI contract:

| Code | Meaning |
| ---: | --- |
| 0 | success |
| 2 | invalid or unbounded selection |
| 4 | collected output is not valid UTF-8 |
| 7 | destination or repository-path policy failure |
| 8 | local acquisition process failure |

## Consequences

A collected file can later be supplied explicitly to `analyze` or `compare`,
but acquisition and analysis remain independent operations.

The repository contains no real journal export. Automated tests use synthetic
process results and never depend on the host journal.

Restrictive output permissions reduce accidental disclosure but do not make
journal contents safe to publish.

The repository-path override exists for deliberate local workflows; it never
adds the resulting file to Git automatically.

## Exclusions

This decision adds no remote access, SSH collection, continuous monitoring,
daemon, scheduler, upload, automatic Git operation, redaction, anomaly
inference, or security interpretation.
