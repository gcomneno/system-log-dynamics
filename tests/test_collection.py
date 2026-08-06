from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

import system_log_dynamics.cli as cli
import system_log_dynamics.collection as collection

SYNTHETIC_OUTPUT = (
    b'{"__REALTIME_TIMESTAMP":"1","MESSAGE":"one"}\n'
    b'{"__REALTIME_TIMESTAMP":"2","MESSAGE":"two"}\n'
)


def successful_runner(
    command: object,
    timeout_seconds: float,
) -> collection.ProcessResult:
    assert timeout_seconds == 12.0
    return collection.ProcessResult(
        returncode=0,
        stdout=SYNTHETIC_OUTPUT,
        stderr=b"",
    )


def test_bounded_collection_uses_exact_argument_vector(
    tmp_path: Path,
) -> None:
    output = tmp_path / "journal.jsonl"
    selection = collection.JournalSelection(
        boot=-1,
        since="2026-08-06 09:00:00",
        until="2026-08-06 09:05:00",
        system_units=("sshd.service",),
        max_events=50,
        scope="system",
    )

    result = collection.collect_journal(
        output,
        selection,
        timeout_seconds=12.0,
        runner=successful_runner,
    )

    assert result.command == (
        "journalctl",
        "--no-pager",
        "--quiet",
        "--output=json",
        ("--output-fields=" + ",".join(collection.JOURNAL_FIELDS)),
        "--system",
        "--boot=-1",
        "--since=2026-08-06 09:00:00",
        "--until=2026-08-06 09:05:00",
        "--unit=sshd.service",
        "--lines=50",
    )
    assert result.byte_count == len(SYNTHETIC_OUTPUT)
    assert result.event_line_count == 2
    assert output.read_bytes() == SYNTHETIC_OUTPUT
    assert os.stat(output).st_mode & 0o777 == 0o600
    assert not tuple(tmp_path.glob(".*.tmp"))


@pytest.mark.parametrize(
    "selection",
    [
        collection.JournalSelection,
        lambda: collection.JournalSelection(
            since="today",
        ),
        lambda: collection.JournalSelection(
            max_events=0,
        ),
    ],
)
def test_unbounded_or_incomplete_selection_is_rejected(
    selection: object,
) -> None:
    with pytest.raises(collection.CollectionError) as captured:
        selection()

    assert captured.value.kind is collection.CollectionErrorKind.SELECTION


def test_existing_output_requires_overwrite(
    tmp_path: Path,
) -> None:
    output = tmp_path / "journal.jsonl"
    output.write_bytes(b"existing\n")
    selection = collection.JournalSelection(max_events=2)

    with pytest.raises(collection.CollectionError) as captured:
        collection.collect_journal(
            output,
            selection,
            runner=lambda command, timeout: collection.ProcessResult(
                0,
                SYNTHETIC_OUTPUT,
                b"",
            ),
        )

    assert captured.value.kind is collection.CollectionErrorKind.OUTPUT
    assert output.read_bytes() == b"existing\n"

    collection.collect_journal(
        output,
        selection,
        overwrite=True,
        runner=lambda command, timeout: collection.ProcessResult(
            0,
            SYNTHETIC_OUTPUT,
            b"",
        ),
    )

    assert output.read_bytes() == SYNTHETIC_OUTPUT
    assert os.stat(output).st_mode & 0o777 == 0o600


def test_symbolic_link_output_is_rejected(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.jsonl"
    target.write_bytes(b"private\n")
    output = tmp_path / "journal.jsonl"
    output.symlink_to(target)

    with pytest.raises(collection.CollectionError) as captured:
        collection.collect_journal(
            output,
            collection.JournalSelection(max_events=1),
            overwrite=True,
            runner=lambda command, timeout: collection.ProcessResult(
                0,
                SYNTHETIC_OUTPUT,
                b"",
            ),
        )

    assert captured.value.kind is collection.CollectionErrorKind.OUTPUT
    assert target.read_bytes() == b"private\n"


def test_repository_output_requires_explicit_override(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / ".git").mkdir()
    output = repository / "journal.jsonl"

    with pytest.raises(collection.CollectionError) as captured:
        collection.collect_journal(
            output,
            collection.JournalSelection(max_events=1),
            runner=lambda command, timeout: collection.ProcessResult(
                0,
                SYNTHETIC_OUTPUT,
                b"",
            ),
        )

    assert captured.value.kind is collection.CollectionErrorKind.REPOSITORY

    result = collection.collect_journal(
        output,
        collection.JournalSelection(max_events=2),
        allow_repository_output=True,
        runner=lambda command, timeout: collection.ProcessResult(
            0,
            SYNTHETIC_OUTPUT,
            b"",
        ),
    )

    assert result.event_line_count == 2


def test_max_event_count_is_enforced_after_process(
    tmp_path: Path,
) -> None:
    output = tmp_path / "journal.jsonl"

    with pytest.raises(collection.CollectionError) as captured:
        collection.collect_journal(
            output,
            collection.JournalSelection(max_events=1),
            runner=lambda command, timeout: collection.ProcessResult(
                0,
                SYNTHETIC_OUTPUT,
                b"",
            ),
        )

    assert captured.value.kind is collection.CollectionErrorKind.PROCESS
    assert "more events than requested" in str(captured.value)
    assert not output.exists()
    assert not tuple(tmp_path.glob(".*.tmp"))


@pytest.mark.parametrize(
    ("runner", "kind"),
    [
        (
            lambda command, timeout: (_ for _ in ()).throw(FileNotFoundError()),
            collection.CollectionErrorKind.EXECUTABLE,
        ),
        (
            lambda command, timeout: (_ for _ in ()).throw(PermissionError()),
            collection.CollectionErrorKind.PERMISSION,
        ),
        (
            lambda command, timeout: (_ for _ in ()).throw(
                subprocess.TimeoutExpired(command, timeout)
            ),
            collection.CollectionErrorKind.TIMEOUT,
        ),
        (
            lambda command, timeout: collection.ProcessResult(
                1,
                b'{"MESSAGE":"secret-token"}\n',
                b"secret-token",
            ),
            collection.CollectionErrorKind.PROCESS,
        ),
        (
            lambda command, timeout: collection.ProcessResult(
                0,
                b"",
                b"",
            ),
            collection.CollectionErrorKind.EMPTY,
        ),
        (
            lambda command, timeout: collection.ProcessResult(
                0,
                b"\xff",
                b"",
            ),
            collection.CollectionErrorKind.UTF8,
        ),
    ],
)
def test_process_failures_are_controlled_without_content_leakage(
    tmp_path: Path,
    runner: collection.JournalRunner,
    kind: collection.CollectionErrorKind,
) -> None:
    with pytest.raises(collection.CollectionError) as captured:
        collection.collect_journal(
            tmp_path / "journal.jsonl",
            collection.JournalSelection(max_events=1),
            runner=runner,
        )

    assert captured.value.kind is kind
    assert "secret-token" not in str(captured.value)
    assert not (tmp_path / "journal.jsonl").exists()


def test_collect_cli_reports_only_counts_and_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "journal.jsonl"

    monkeypatch.setattr(
        collection,
        "_run_journalctl",
        lambda command, timeout: collection.ProcessResult(
            0,
            SYNTHETIC_OUTPUT,
            b"",
        ),
    )

    status = cli.main(
        [
            "collect",
            str(output),
            "--max-events",
            "2",
        ]
    )
    captured = capsys.readouterr()

    assert status == cli.ExitCode.SUCCESS
    assert captured.out == (
        f"collected 2 event lines and {len(SYNTHETIC_OUTPUT)} bytes to {output}\n"
    )
    assert captured.err == ""
    assert "one" not in captured.out
    assert "two" not in captured.out
    assert output.read_bytes() == SYNTHETIC_OUTPUT


@pytest.mark.parametrize(
    "value",
    [
        "",
        "today\n--all",
        "today\r--all",
        "today\x00--all",
    ],
)
def test_time_selectors_must_be_single_line(
    value: str,
) -> None:
    with pytest.raises(collection.CollectionError) as captured:
        collection.JournalSelection(
            since=value,
            until="tomorrow",
        )

    assert captured.value.kind is collection.CollectionErrorKind.SELECTION


@pytest.mark.parametrize(
    "timeout_seconds",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        0.0,
        -1.0,
    ],
)
def test_timeout_must_be_finite_and_positive(
    tmp_path: Path,
    timeout_seconds: float,
) -> None:
    with pytest.raises(collection.CollectionError) as captured:
        collection.collect_journal(
            tmp_path / "journal.jsonl",
            collection.JournalSelection(max_events=1),
            timeout_seconds=timeout_seconds,
            runner=lambda command, timeout: collection.ProcessResult(
                0,
                SYNTHETIC_OUTPUT,
                b"",
            ),
        )

    assert captured.value.kind is collection.CollectionErrorKind.SELECTION
