from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import system_log_dynamics.cli as cli
from system_log_dynamics.comparison import (
    IncompatibleAnalysisWindowsError,
)

ROOT = Path(__file__).resolve().parents[1]
ROUTINE = ROOT / "fixtures" / "synthetic" / "experiment-001-routine.jsonl"
BURST = ROOT / "fixtures" / "synthetic" / "experiment-001-boot-error-burst.jsonl"
ROUTINE_REPORT = ROOT / "fixtures" / "reports" / "experiment-001-routine.md"
COMPARISON_REPORT = ROOT / "fixtures" / "reports" / "experiment-001-comparison.md"


def test_analyze_writes_exact_golden_to_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = cli.main(
        [
            "analyze",
            str(ROUTINE),
            "--window-id",
            "experiment-001-routine",
        ]
    )

    captured = capsys.readouterr()

    assert status == cli.ExitCode.SUCCESS
    assert captured.out == ROUTINE_REPORT.read_text(encoding="utf-8")
    assert captured.err == ""


def test_compare_writes_exact_golden_to_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = cli.main(
        [
            "compare",
            str(ROUTINE),
            str(BURST),
            "--left-window-id",
            "experiment-001-routine",
            "--right-window-id",
            "experiment-001-boot-error-burst",
        ]
    )

    captured = capsys.readouterr()

    assert status == cli.ExitCode.SUCCESS
    assert captured.out == COMPARISON_REPORT.read_text(encoding="utf-8")
    assert captured.err == ""


def test_analyze_writes_explicit_output_atomically(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "routine.md"

    status = cli.main(
        [
            "analyze",
            str(ROUTINE),
            "--window-id",
            "experiment-001-routine",
            "--output",
            str(output),
        ]
    )

    captured = capsys.readouterr()

    assert status == cli.ExitCode.SUCCESS
    assert captured.out == ""
    assert captured.err == ""
    assert output.read_bytes() == ROUTINE_REPORT.read_bytes()
    assert not tuple(tmp_path.glob(".*.tmp"))


def test_existing_output_requires_explicit_overwrite(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "routine.md"
    output.write_text("existing\n", encoding="utf-8")

    refused = cli.main(
        [
            "analyze",
            str(ROUTINE),
            "--output",
            str(output),
        ]
    )
    refused_output = capsys.readouterr()

    assert refused == cli.ExitCode.OUTPUT
    assert refused_output.out == ""
    assert "already exists" in refused_output.err
    assert "Traceback" not in refused_output.err
    assert output.read_text(encoding="utf-8") == "existing\n"

    replaced = cli.main(
        [
            "analyze",
            str(ROUTINE),
            "--window-id",
            "experiment-001-routine",
            "--output",
            str(output),
            "--overwrite",
        ]
    )
    replaced_output = capsys.readouterr()

    assert replaced == cli.ExitCode.SUCCESS
    assert replaced_output.out == ""
    assert replaced_output.err == ""
    assert output.read_bytes() == ROUTINE_REPORT.read_bytes()


@pytest.mark.parametrize(
    ("arguments", "expected_code", "message"),
    [
        (
            ["analyze", "missing.jsonl"],
            cli.ExitCode.INPUT,
            "input file unavailable",
        ),
        (
            [
                "analyze",
                str(ROUTINE),
                "--burst-threshold-us",
                "0",
            ],
            cli.ExitCode.USAGE,
            "must be a positive integer",
        ),
        (
            [
                "analyze",
                str(ROUTINE),
                "--schur-capacity",
                "-1",
            ],
            cli.ExitCode.USAGE,
            "must be a positive integer",
        ),
    ],
)
def test_controlled_failures_have_stable_exit_codes(
    arguments: list[str],
    expected_code: cli.ExitCode,
    message: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = cli.main(arguments)
    captured = capsys.readouterr()

    assert status == expected_code
    assert captured.out == ""
    assert message in captured.err
    assert "Traceback" not in captured.err


def test_invalid_utf8_is_controlled(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "invalid.jsonl"
    source.write_bytes(b"\xff\xfe")

    status = cli.main(["analyze", str(source)])
    captured = capsys.readouterr()

    assert status == cli.ExitCode.UTF8
    assert captured.out == ""
    assert "not valid UTF-8" in captured.err
    assert "Traceback" not in captured.err


def test_malformed_json_lines_is_controlled(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "malformed.jsonl"
    source.write_text("{not-json}\n", encoding="utf-8")

    status = cli.main(["analyze", str(source)])
    captured = capsys.readouterr()

    assert status == cli.ExitCode.JOURNAL
    assert captured.out == ""
    assert "journal input rejected" in captured.err
    assert "Traceback" not in captured.err


def test_empty_window_is_controlled(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "empty.jsonl"
    source.write_bytes(b"")

    status = cli.main(["analyze", str(source)])
    captured = capsys.readouterr()

    assert status == cli.ExitCode.PIPELINE
    assert captured.out == ""
    assert "must not be empty" in captured.err
    assert "Traceback" not in captured.err


def test_incompatible_comparison_is_controlled(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def reject_comparison(
        left: object,
        right: object,
    ) -> object:
        del left, right
        raise IncompatibleAnalysisWindowsError(("taxonomy_version",))

    monkeypatch.setattr(
        cli,
        "build_window_comparison_report",
        reject_comparison,
    )

    status = cli.main(
        [
            "compare",
            str(ROUTINE),
            str(BURST),
        ]
    )
    captured = capsys.readouterr()

    assert status == cli.ExitCode.PIPELINE
    assert captured.out == ""
    assert "comparison pipeline failed" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("input_index", [0, 1])
def test_output_must_not_replace_an_input(
    tmp_path: Path,
    input_index: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    left = tmp_path / "left.jsonl"
    right = tmp_path / "right.jsonl"
    left.write_bytes(ROUTINE.read_bytes())
    right.write_bytes(BURST.read_bytes())

    inputs = (left, right)
    hashes_before = tuple(
        hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs
    )

    status = cli.main(
        [
            "compare",
            str(left),
            str(right),
            "--output",
            str(inputs[input_index]),
            "--overwrite",
        ]
    )
    captured = capsys.readouterr()

    hashes_after = tuple(
        hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs
    )

    assert status == cli.ExitCode.OUTPUT
    assert captured.out == ""
    assert "must not replace an input file" in captured.err
    assert "Traceback" not in captured.err
    assert hashes_after == hashes_before


def test_default_window_identifier_is_not_path_dependent(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    first.write_bytes(ROUTINE.read_bytes())
    second.write_bytes(ROUTINE.read_bytes())

    first_status = cli.main(["analyze", str(first)])
    first_output = capsys.readouterr()

    second_status = cli.main(["analyze", str(second)])
    second_output = capsys.readouterr()

    assert first_status == cli.ExitCode.SUCCESS
    assert second_status == cli.ExitCode.SUCCESS
    assert first_output.err == ""
    assert second_output.err == ""
    assert first_output.out == second_output.out
    assert "unidentified" in first_output.out
    assert str(first) not in first_output.out
    assert str(second) not in second_output.out


def test_classification_contract_failure_is_controlled(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def reject_classification(
        events: object,
    ) -> object:
        del events
        raise ValueError("synthetic classification failure")

    monkeypatch.setattr(
        cli,
        "iter_classified_events",
        reject_classification,
    )

    status = cli.main(["analyze", str(ROUTINE)])
    captured = capsys.readouterr()

    assert status == cli.ExitCode.PIPELINE
    assert captured.out == ""
    assert "analysis pipeline failed" in captured.err
    assert "synthetic classification failure" in captured.err
    assert "Traceback" not in captured.err


def test_reporting_contract_failure_is_controlled(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def reject_rendering(
        window: object,
    ) -> str:
        del window
        raise ValueError("synthetic reporting failure")

    monkeypatch.setattr(
        cli,
        "render_analysis_window_markdown",
        reject_rendering,
    )

    status = cli.main(["analyze", str(ROUTINE)])
    captured = capsys.readouterr()

    assert status == cli.ExitCode.PIPELINE
    assert captured.out == ""
    assert "reporting pipeline failed" in captured.err
    assert "synthetic reporting failure" in captured.err
    assert "Traceback" not in captured.err


def test_stdout_failure_is_controlled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingStdout:
        def write(self, value: str) -> int:
            del value
            raise BrokenPipeError("synthetic broken pipe")

        def flush(self) -> None:
            pass

    error_stream = __import__("io").StringIO()

    monkeypatch.setattr(
        cli.sys,
        "stdout",
        FailingStdout(),
    )
    monkeypatch.setattr(
        cli.sys,
        "stderr",
        error_stream,
    )

    status = cli.main(["analyze", str(ROUTINE)])

    assert status == cli.ExitCode.OUTPUT
    assert error_stream.getvalue() == ("standard output could not be written\n")
    assert "Traceback" not in error_stream.getvalue()


def test_missing_command_is_controlled_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = cli.main([])
    captured = capsys.readouterr()

    assert status == cli.ExitCode.USAGE
    assert captured.out == ""
    assert captured.err.startswith("usage: system-log-dynamics")
    assert "required: command" in captured.err
    assert "Traceback" not in captured.err


def test_overwrite_requires_output_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = cli.main(
        [
            "analyze",
            str(ROUTINE),
            "--overwrite",
        ]
    )
    captured = capsys.readouterr()

    assert status == cli.ExitCode.USAGE
    assert captured.out == ""
    assert captured.err == "error: --overwrite requires --output\n"
    assert "Traceback" not in captured.err


def test_non_utf8_report_to_stdout_is_controlled(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "render_analysis_window_markdown",
        lambda window: "\udcff",
    )

    status = cli.main(["analyze", str(ROUTINE)])
    captured = capsys.readouterr()

    assert status == cli.ExitCode.OUTPUT
    assert captured.out == ""
    assert captured.err == ("standard output could not be written\n")
    assert "Traceback" not in captured.err


def test_non_utf8_report_to_file_is_controlled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "invalid.md"

    monkeypatch.setattr(
        cli,
        "render_analysis_window_markdown",
        lambda window: "\udcff",
    )

    status = cli.main(
        [
            "analyze",
            str(ROUTINE),
            "--output",
            str(output),
        ]
    )
    captured = capsys.readouterr()

    assert status == cli.ExitCode.OUTPUT
    assert captured.out == ""
    assert "could not be written" in captured.err
    assert "Traceback" not in captured.err
    assert not output.exists()
    assert not tuple(tmp_path.glob(".*.tmp"))
