from __future__ import annotations

import json
from pathlib import Path

import pytest

import system_log_dynamics.cli as cli
from system_log_dynamics.semantics import (
    parse_semantic_evidence_json,
    render_semantic_evidence_json,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "synthetic" / "restart-loop-semantic.jsonl"


def test_analyze_semantic_evidence_json_to_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = cli.main(
        [
            "analyze",
            str(FIXTURE),
            "--window-id",
            "issue-37-cli",
            "--format",
            "semantic-evidence-json",
        ]
    )

    captured = capsys.readouterr()

    assert status == cli.ExitCode.SUCCESS
    assert captured.err == ""

    parsed = parse_semantic_evidence_json(captured.out)
    assert render_semantic_evidence_json(parsed) == captured.out

    document = json.loads(captured.out)
    assert document["schema_name"] == "system-log-dynamics.semantic-evidence"
    assert document["schema_version"] == 1
    assert document["bundle_type"] == "semantic_events"

    provenance = document["payload"]["provenance"]
    assert provenance["window_id"] == "issue-37-cli"
    assert provenance["taxonomy_version"] == "2"
    assert provenance["semantic_facets_version"] == "2"

    events = document["payload"]["events"]
    assert len(events) == 6
    assert [event["semantic"]["action"] for event in events] == [
        "restart_scheduled",
        "process_output",
        "process_exited",
        "restart_scheduled",
        "process_output",
        "process_exited",
    ]
    assert {event["semantic"]["subject"]["value"] for event in events} == {
        "demo-restart.service"
    }
    assert [event["primary"]["event_type"] for event in events] == ["other"] * 6
    assert [event["primary"]["symbol"] for event in events] == [8] * 6
    assert document["payload"]["semantics"]["flags"]["contains_raw_messages"] is False
    assert "Synthetic manager" not in captured.out
    assert "Synthetic child output" not in captured.out


def test_semantic_stdout_and_output_file_are_byte_identical(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    arguments = [
        "analyze",
        str(FIXTURE),
        "--window-id",
        "issue-37-byte-identity",
        "--format",
        "semantic-evidence-json",
    ]

    stdout_status = cli.main(arguments)
    stdout_capture = capsys.readouterr()

    output = tmp_path / "semantic.evidence.json"
    file_status = cli.main([*arguments, "--output", str(output)])
    file_capture = capsys.readouterr()

    assert stdout_status == cli.ExitCode.SUCCESS
    assert file_status == cli.ExitCode.SUCCESS
    assert stdout_capture.err == ""
    assert file_capture.out == ""
    assert file_capture.err == ""
    assert output.read_bytes() == stdout_capture.out.encode("utf-8")
    assert not tuple(tmp_path.glob(".*.tmp"))


def test_legacy_evidence_json_stays_analysis_evidence(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = cli.main(
        [
            "analyze",
            str(FIXTURE),
            "--window-id",
            "issue-37-legacy",
            "--format",
            "evidence-json",
        ]
    )

    captured = capsys.readouterr()
    document = json.loads(captured.out)

    assert status == cli.ExitCode.SUCCESS
    assert captured.err == ""
    assert document["schema_name"] == "system-log-dynamics.analysis-evidence"
    assert document["bundle_type"] == "analysis_window"


def test_compare_does_not_accept_semantic_evidence_format(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = cli.main(
        [
            "compare",
            str(FIXTURE),
            str(FIXTURE),
            "--format",
            "semantic-evidence-json",
        ]
    )

    captured = capsys.readouterr()

    assert status == cli.ExitCode.USAGE
    assert captured.out == ""
    assert "invalid choice" in captured.err
    assert "Traceback" not in captured.err
