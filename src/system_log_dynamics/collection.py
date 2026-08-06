"""Privacy-safe local acquisition of bounded Linux journal windows."""

from __future__ import annotations

import math
import os
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal

JOURNAL_FIELDS = (
    "__REALTIME_TIMESTAMP",
    "__MONOTONIC_TIMESTAMP",
    "_BOOT_ID",
    "PRIORITY",
    "MESSAGE",
    "MESSAGE_ID",
    "_TRANSPORT",
    "_SYSTEMD_UNIT",
    "SYSLOG_IDENTIFIER",
    "UNIT",
    "USER_UNIT",
)


class CollectionErrorKind(Enum):
    """Stable categories for controlled acquisition failures."""

    SELECTION = "selection"
    EXECUTABLE = "executable"
    PERMISSION = "permission"
    PROCESS = "process"
    TIMEOUT = "timeout"
    EMPTY = "empty"
    UTF8 = "utf8"
    OUTPUT = "output"
    REPOSITORY = "repository"


class CollectionError(RuntimeError):
    """Controlled journal acquisition failure without captured contents."""

    def __init__(
        self,
        kind: CollectionErrorKind,
        detail: str,
    ) -> None:
        self.kind = kind
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class JournalSelection:
    """Reviewed bounded subset of supported journalctl selectors."""

    boot: int | None = None
    since: str | None = None
    until: str | None = None
    system_units: tuple[str, ...] = ()
    user_units: tuple[str, ...] = ()
    max_events: int | None = None
    scope: Literal["system", "user"] | None = None

    def __post_init__(self) -> None:
        if (self.since is None) != (self.until is None):
            raise CollectionError(
                CollectionErrorKind.SELECTION,
                "--since and --until must be supplied together",
            )

        for option, value in (
            ("--since", self.since),
            ("--until", self.until),
        ):
            if value is not None and (
                not value or any(character in value for character in "\x00\n\r")
            ):
                raise CollectionError(
                    CollectionErrorKind.SELECTION,
                    f"{option} must be a non-empty single-line value",
                )

        if self.max_events is not None and self.max_events <= 0:
            raise CollectionError(
                CollectionErrorKind.SELECTION,
                "--max-events must be a positive integer",
            )

        if self.boot is None and self.max_events is None and self.since is None:
            raise CollectionError(
                CollectionErrorKind.SELECTION,
                (
                    "collection must be bounded by --boot, "
                    "--max-events, or both --since and --until"
                ),
            )

        if self.scope == "user" and self.system_units:
            raise CollectionError(
                CollectionErrorKind.SELECTION,
                "--system-unit cannot be combined with --user scope",
            )

        if self.scope == "system" and self.user_units:
            raise CollectionError(
                CollectionErrorKind.SELECTION,
                "--user-unit cannot be combined with --system scope",
            )

        for unit in (*self.system_units, *self.user_units):
            if not unit or "\x00" in unit or "\n" in unit or "\r" in unit:
                raise CollectionError(
                    CollectionErrorKind.SELECTION,
                    "unit selectors must be non-empty single-line values",
                )


@dataclass(frozen=True, slots=True)
class ProcessResult:
    """Minimal process result retained by the acquisition boundary."""

    returncode: int
    stdout: bytes
    stderr: bytes


@dataclass(frozen=True, slots=True)
class CollectionResult:
    """Safe collection summary that never retains event contents."""

    output_path: Path
    byte_count: int
    event_line_count: int
    command: tuple[str, ...]


JournalRunner = Callable[[Sequence[str], float], ProcessResult]


def build_journalctl_command(
    selection: JournalSelection,
) -> tuple[str, ...]:
    """Build one explicit shell-free journalctl argument vector."""

    command = [
        "journalctl",
        "--no-pager",
        "--quiet",
        "--output=json",
        f"--output-fields={','.join(JOURNAL_FIELDS)}",
    ]

    if selection.scope is not None:
        command.append(f"--{selection.scope}")

    if selection.boot is not None:
        command.append(f"--boot={selection.boot}")

    if selection.since is not None:
        command.extend(
            (
                f"--since={selection.since}",
                f"--until={selection.until}",
            )
        )

    command.extend(f"--unit={unit}" for unit in selection.system_units)
    command.extend(f"--user-unit={unit}" for unit in selection.user_units)

    if selection.max_events is not None:
        command.append(f"--lines={selection.max_events}")

    return tuple(command)


def detect_repository_root(
    output_path: Path,
) -> Path | None:
    """Detect a containing Git worktree without invoking Git."""

    try:
        parent = output_path.parent.resolve(strict=False)
    except OSError:
        return None

    for candidate in (parent, *parent.parents):
        if (candidate / ".git").exists():
            return candidate

    return None


def _run_journalctl(
    command: Sequence[str],
    timeout_seconds: float,
) -> ProcessResult:
    completed = subprocess.run(
        list(command),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    return ProcessResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _validate_output_destination(
    output_path: Path,
    *,
    overwrite: bool,
) -> None:
    if output_path.is_symlink():
        raise CollectionError(
            CollectionErrorKind.OUTPUT,
            f"refusing symbolic-link output path: {output_path}",
        )

    if output_path.exists() and not overwrite:
        raise CollectionError(
            CollectionErrorKind.OUTPUT,
            f"output file already exists: {output_path}",
        )


def _publish_bytes(
    output_path: Path,
    data: bytes,
    *,
    overwrite: bool,
) -> None:
    temporary_path: Path | None = None

    if output_path.is_symlink():
        raise CollectionError(
            CollectionErrorKind.OUTPUT,
            f"refusing symbolic-link output path: {output_path}",
        )

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            dir=output_path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            os.chmod(temporary_path, 0o600)
            temporary.write(data)
            temporary.flush()
            os.fsync(temporary.fileno())

        if overwrite:
            if output_path.is_symlink():
                raise CollectionError(
                    CollectionErrorKind.OUTPUT,
                    f"refusing symbolic-link output path: {output_path}",
                )

            os.replace(temporary_path, output_path)
            temporary_path = None
            return

        try:
            os.link(temporary_path, output_path)
        except FileExistsError as error:
            raise CollectionError(
                CollectionErrorKind.OUTPUT,
                f"output file already exists: {output_path}",
            ) from error

        temporary_path.unlink()
        temporary_path = None
    except CollectionError:
        raise
    except OSError as error:
        raise CollectionError(
            CollectionErrorKind.OUTPUT,
            f"output file could not be written: {output_path}",
        ) from error
    finally:
        if temporary_path is not None:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)


def collect_journal(
    output_path: Path,
    selection: JournalSelection,
    *,
    overwrite: bool = False,
    allow_repository_output: bool = False,
    timeout_seconds: float = 30.0,
    runner: JournalRunner | None = None,
) -> CollectionResult:
    """Collect one bounded journal window without analyzing its contents."""

    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise CollectionError(
            CollectionErrorKind.SELECTION,
            "--timeout-seconds must be positive",
        )

    repository_root = detect_repository_root(output_path)
    if repository_root is not None and not allow_repository_output:
        raise CollectionError(
            CollectionErrorKind.REPOSITORY,
            (
                "refusing output inside a Git worktree; "
                "use a private directory outside the repository"
            ),
        )

    _validate_output_destination(
        output_path,
        overwrite=overwrite,
    )

    command = build_journalctl_command(selection)
    process_runner = runner or _run_journalctl

    try:
        result = process_runner(command, timeout_seconds)
    except FileNotFoundError as error:
        raise CollectionError(
            CollectionErrorKind.EXECUTABLE,
            "journalctl executable was not found",
        ) from error
    except PermissionError as error:
        raise CollectionError(
            CollectionErrorKind.PERMISSION,
            "journalctl could not be executed due to permissions",
        ) from error
    except subprocess.TimeoutExpired as error:
        raise CollectionError(
            CollectionErrorKind.TIMEOUT,
            "journalctl timed out",
        ) from error
    except OSError as error:
        raise CollectionError(
            CollectionErrorKind.PROCESS,
            "journalctl could not be executed",
        ) from error

    if result.returncode != 0:
        raise CollectionError(
            CollectionErrorKind.PROCESS,
            f"journalctl failed with exit status {result.returncode}",
        )

    if not result.stdout.strip():
        raise CollectionError(
            CollectionErrorKind.EMPTY,
            "journalctl returned no events",
        )

    try:
        decoded = result.stdout.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CollectionError(
            CollectionErrorKind.UTF8,
            "journalctl output is not valid UTF-8",
        ) from error

    lines = decoded.splitlines()
    if not lines or any(not line.strip() for line in lines):
        raise CollectionError(
            CollectionErrorKind.PROCESS,
            "journalctl returned invalid JSON Lines framing",
        )

    if selection.max_events is not None and len(lines) > selection.max_events:
        raise CollectionError(
            CollectionErrorKind.PROCESS,
            "journalctl returned more events than requested",
        )

    _publish_bytes(
        output_path,
        result.stdout,
        overwrite=overwrite,
    )

    return CollectionResult(
        output_path=output_path,
        byte_count=len(result.stdout),
        event_line_count=len(lines),
        command=command,
    )
