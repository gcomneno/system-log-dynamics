# System Log Dynamics

System Log Dynamics is a reproducible Learning in Public laboratory for
transforming Linux journal events into discrete symbolic sequences and
analyzing them through the public Python API of Digit-Probe.

## Status

Version 0.1.0 is the first public milestone. It packages the completed
deterministic file-based pipeline, Experiment 001, structured comparisons,
Markdown reporting, installed analyze and compare commands, and bounded local
journal acquisition. See the [0.1.0 release notes](docs/releases/0.1.0.md)
and the [release process](docs/release-process.md).

The strict journal JSON Lines parser, privacy-safe normalizer,
deterministic streaming classifier, validated integer encoding, validated
Digit-Probe analysis, reproducible per-window analysis manifests, deterministic
immutable temporal burst summaries, typed structured comparison,
deterministic Markdown reporting, file-based command-line analysis, and
privacy-safe bounded local journal acquisition are implemented.

Experiment 001 exercises the complete public pipeline with two reproducible
synthetic windows through both the Python API and the installed console
script.

## Purpose

The project studies descriptive properties of event sequences, including
operational routines, periodicity, bursts, recurring patterns, local
predictability, and changes between temporal windows.

It does not attempt to certify randomness, security, compromise, user
behaviour, or administrator intent.

The output is descriptive and depends on the accepted journal fields,
normalization, classifier, encoding, configuration, and selected windows. It
does not establish that a system is random, compromised, malicious, safe, or
operated with any particular user or administrator intent.

## Data policy

The public repository contains only synthetic or carefully anonymized
fixtures. Real journal exports, usernames, hostnames, addresses, tokens,
identifiers, private paths, and other sensitive material must not be
committed.

Local collection writes exact journal bytes and performs no redaction. Treat a
collected file as private: keep it outside a repository, review it before any
sharing, and do not use it as a public fixture.

## Initial pipeline

optional bounded local acquisition → JSON Lines file → normalization →
classification → integer symbols → Digit-Probe analysis → structured window
comparison → deterministic Markdown reporting.

## Installation and quick start

The 0.1.0 distribution depends on an immutable Digit-Probe Git commit, so
installation requires Git until a separately reviewed immutable Digit-Probe
release is adopted. To install a checked-out release candidate:

```console
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install .
```

When an artifact is deliberately published, install that exact published
artifact through the selected release channel; publication is optional and is
not implied by a Git tag.

From the repository root, reproduce the routine synthetic report without
reading a live journal:

```console
.venv/bin/system-log-dynamics analyze \
    fixtures/synthetic/experiment-001-routine.jsonl \
    --window-id experiment-001-routine \
    --output /tmp/experiment-001-routine.md

cmp fixtures/reports/experiment-001-routine.md /tmp/experiment-001-routine.md
```

The command reads only the named synthetic file and produces deterministic
Markdown. Remove the temporary report when it is no longer needed.

## Experiment 001

Experiment 001 compares a low-intensity routine synthetic window with a
synthetic window containing boot boundaries, service lifecycle activity,
warnings, errors, authentication failures, and a concentrated event burst.

Both 24-event fixtures pass through the public pipeline from exact JSON Lines
bytes to `WindowComparison`. Their byte lengths, SHA-256 digests, normalized
coordinates, classification metadata, symbol sequences, manifests, temporal
summaries, and selected comparison values are executable contracts.

See
`docs/experiments/001-routine-vs-boot-error-burst.md`
for the completed specification, interpretation limits, and exact generated
report contracts.

The reporting API exposes:

```python
render_analysis_window_markdown(window)
build_window_comparison_report(left, right)
render_window_comparison_markdown(report)
```

Each single-window report begins with a deterministic plain-language
summary. It states the sample size, represented and absent categories,
dominant categories, the `other` proportion, and the existing runs and
compression values. The summary is descriptive rather than diagnostic: it
does not infer anomaly, compromise, malicious behaviour, safety, causality,
randomness, or intent.

Reviewed golden outputs are stored in:

```text
fixtures/reports/experiment-001-routine.md
fixtures/reports/experiment-001-comparison.md
```

## Command-line interface

After installation, the file-based pipeline is available through:

```text
system-log-dynamics analyze INPUT.jsonl
system-log-dynamics compare LEFT.jsonl RIGHT.jsonl
```

Both commands:

- read each input as exact immutable bytes;
- decode JSON Lines with strict UTF-8;
- use only the existing public analysis and reporting pipeline;
- write deterministic UTF-8 Markdown to standard output by default;
- never access the live journal, Git state, environment metadata, or the
  network;
- never modify an input file.

A single window can be analyzed with an explicit stable identifier:

```console
system-log-dynamics analyze \
    fixtures/synthetic/experiment-001-routine.jsonl \
    --window-id experiment-001-routine
```

Two windows can be compared with independent identifiers:

```console
system-log-dynamics compare \
    fixtures/synthetic/experiment-001-routine.jsonl \
    fixtures/synthetic/experiment-001-boot-error-burst.jsonl \
    --left-window-id experiment-001-routine \
    --right-window-id experiment-001-boot-error-burst
```

Common options are:

- `--burst-threshold-us MICROSECONDS`, a positive temporal threshold with
  default `100000`;
- `--schur-capacity COUNT`, a positive Digit-Probe Schur capacity with
  default `5000`;
- `--output PATH`, which writes the complete report atomically;
- `--overwrite`, which requires `--output` and permits atomic replacement
  of an existing destination.

Without `--overwrite`, an existing output path is refused. Even with
`--overwrite`, an output path resolving to either input file is rejected.
Temporary output files are created in the destination directory and removed
after failures.

Controlled outcomes use stable process exit codes:

| Code | Meaning |
| ---: | --- |
| 0 | Success |
| 2 | Command-line usage error |
| 3 | Input file access error |
| 4 | UTF-8 decoding error |
| 5 | Journal parsing or normalization error |
| 6 | Classification, analysis, manifest, temporal, comparison, or reporting contract error |
| 7 | Standard-output, output-file, or repository-path error |
| 8 | Local journal acquisition process error |

Expected user and data errors are written concisely to standard error without
a traceback.

### CLI overview

`analyze` turns one explicit JSON Lines file into a deterministic Markdown
window report. `compare` turns two explicit JSON Lines files into a
deterministic structured comparison report. Neither command invokes
`journalctl`. `collect` is the separate, opt-in local acquisition boundary and
does not analyze its output. Run the installed help without accessing a
journal:

```console
system-log-dynamics --help
system-log-dynamics analyze --help
system-log-dynamics compare --help
system-log-dynamics collect --help
```

## Optional local journal acquisition

Collection is deliberately separate from analysis:

```text
system-log-dynamics collect OUTPUT.jsonl [selection options]
```

The output path is mandatory, and collection must be bounded by at least one
of:

- `--boot OFFSET`, selecting exactly one boot;
- `--max-events COUNT`, limiting the exported event count;
- both `--since VALUE` and `--until VALUE`.

Optional repeatable filters are `--system-unit UNIT` and
`--user-unit UNIT`. Journal scope can be selected with either `--system` or
`--user`.

For example, collect at most 5,000 events from the previous boot into a private
directory outside the repository:

```console
mkdir -p "$HOME/.local/share/system-log-dynamics"

system-log-dynamics collect \
    "$HOME/.local/share/system-log-dynamics/previous-boot.jsonl" \
    --boot=-1 \
    --max-events 5000
```

A bounded service window can be collected with:

```console
system-log-dynamics collect \
    "$HOME/.local/share/system-log-dynamics/sshd-window.jsonl" \
    --since "2026-08-06 09:00:00" \
    --until "2026-08-06 09:15:00" \
    --system-unit sshd.service \
    --max-events 1000
```

Journal data may contain usernames, hostnames, addresses, paths, tokens,
identifiers, and message contents. Collected files must be treated as private.

The collector:

- invokes `journalctl` without a shell;
- requests only fields consumed by the existing parser;
- never analyzes or transforms collected events;
- never sends data to the network;
- never performs Git operations;
- refuses output inside a Git worktree by default;
- refuses symbolic-link output paths;
- writes atomically with restrictive `0600` permissions;
- never prints collected contents in normal output or diagnostics.

`--allow-repository-output` overrides the Git-worktree guard only after an
explicit warning. It does not stage, commit, or otherwise publish the file.

`--overwrite` permits atomic replacement of an existing regular destination.

Success reports only the destination, byte count, and event-line count. The
resulting file may later be passed explicitly to `analyze` or `compare`.

See
`docs/decisions/0015-privacy-safe-local-journal-acquisition.md`
for the complete security, privacy, file-safety, and provenance policy.

## Architecture decisions

The accepted boundaries and their rationale are indexed in
[docs/decisions/README.md](docs/decisions/README.md). In particular,
Decision 0016 records why 0.1.0 is the first public milestone and why the
Digit-Probe commit pin remains in place.

## Development

Install the development tools into an isolated environment, then run the
same checks required before a release candidate:

```console
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/pytest -q
.venv/bin/python -m compileall -q src tests
```

For the artifact, isolated-install, and release checks, follow the executable
commands in [docs/release-process.md](docs/release-process.md). All automated
collection checks must replace `journalctl` with a synthetic executable; do
not run validation against the host journal.

## Development dependency

The distributive dependency is pinned to a verified Digit-Probe Git
commit. During local development, the local Digit-Probe repository may
replace it through an editable installation.

Analysis manifests derive the reproducible Digit-Probe commit from the
installed System Log Dynamics dependency metadata, not from the currently
imported editable checkout.
