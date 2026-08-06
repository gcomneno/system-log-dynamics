"""Deterministic file-based command-line orchestration."""

from __future__ import annotations

import argparse
import io
import os
import sys
import tempfile
from collections.abc import Sequence
from contextlib import suppress
from enum import IntEnum
from pathlib import Path
from typing import NoReturn

from digit_probe import AnalysisConfig

from .analysis import analyze_classified_events
from .classification import iter_classified_events
from .comparison import AnalysisWindow
from .journal import (
    JournalNormalizationError,
    JournalParseError,
    iter_normalized_journal_json_lines,
)
from .manifests import build_analysis_manifest
from .reporting import (
    build_window_comparison_report,
    render_analysis_window_markdown,
    render_window_comparison_markdown,
)
from .temporal import summarize_temporal_bursts

__all__ = ["ExitCode", "main"]

DEFAULT_BURST_THRESHOLD_US = 100_000
DEFAULT_SCHUR_CAPACITY = 5_000


class ExitCode(IntEnum):
    """Stable process exit codes for controlled CLI outcomes."""

    SUCCESS = 0
    USAGE = 2
    INPUT = 3
    UTF8 = 4
    JOURNAL = 5
    PIPELINE = 6
    OUTPUT = 7


class _CliFailure(Exception):
    """Controlled failure carrying a stable exit code."""

    def __init__(self, exit_code: ExitCode, detail: str) -> None:
        super().__init__(detail)
        self.exit_code = exit_code
        self.detail = detail


class _ArgumentParser(argparse.ArgumentParser):
    """Argument parser that reports usage errors without exiting."""

    def error(self, message: str) -> NoReturn:
        raise _CliFailure(
            ExitCode.USAGE,
            f"{self.format_usage().strip()}\nerror: {message}",
        )


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value, 10)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error

    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")

    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="system-log-dynamics",
        description=(
            "Analyze and compare Linux journal JSON Lines files "
            "without accessing the live journal."
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    analyze = subparsers.add_parser(
        "analyze",
        help="analyze one JSON Lines file",
    )
    analyze.add_argument(
        "input",
        type=Path,
        help="journal JSON Lines input file",
    )
    analyze.add_argument(
        "--window-id",
        help="optional stable window identifier",
    )
    _add_common_arguments(analyze)

    compare = subparsers.add_parser(
        "compare",
        help="compare two JSON Lines files",
    )
    compare.add_argument(
        "left",
        type=Path,
        help="left journal JSON Lines input file",
    )
    compare.add_argument(
        "right",
        type=Path,
        help="right journal JSON Lines input file",
    )
    compare.add_argument(
        "--left-window-id",
        help="optional stable identifier for the left window",
    )
    compare.add_argument(
        "--right-window-id",
        help="optional stable identifier for the right window",
    )
    _add_common_arguments(compare)

    return parser


def _add_common_arguments(
    parser: argparse.ArgumentParser,
) -> None:
    parser.add_argument(
        "--burst-threshold-us",
        type=_positive_integer,
        default=DEFAULT_BURST_THRESHOLD_US,
        metavar="MICROSECONDS",
        help=(
            f"positive temporal burst threshold (default: {DEFAULT_BURST_THRESHOLD_US})"
        ),
    )
    parser.add_argument(
        "--schur-capacity",
        type=_positive_integer,
        default=DEFAULT_SCHUR_CAPACITY,
        metavar="COUNT",
        help=(
            f"positive Digit-Probe Schur capacity (default: {DEFAULT_SCHUR_CAPACITY})"
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="write UTF-8 Markdown to this file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing output file atomically",
    )


def _read_input_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise _CliFailure(
            ExitCode.INPUT,
            f"input file unavailable: {path}",
        ) from error


def _decode_utf8(
    input_bytes: bytes,
    path: Path,
) -> str:
    try:
        return input_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _CliFailure(
            ExitCode.UTF8,
            f"input is not valid UTF-8: {path}",
        ) from error


def _build_analysis_window(
    path: Path,
    *,
    window_id: str | None,
    config: AnalysisConfig,
    burst_threshold_us: int,
) -> AnalysisWindow:
    input_bytes = _read_input_bytes(path)
    source_text = _decode_utf8(input_bytes, path)

    try:
        with io.StringIO(source_text) as source:
            normalized = tuple(iter_normalized_journal_json_lines(source))
    except (
        JournalParseError,
        JournalNormalizationError,
    ) as error:
        raise _CliFailure(
            ExitCode.JOURNAL,
            f"journal input rejected: {path}: {error}",
        ) from error

    try:
        classified = tuple(iter_classified_events(normalized))
        result = analyze_classified_events(
            classified,
            config=config,
        )
        manifest = build_analysis_manifest(
            input_bytes,
            result,
            config=config,
            window_id=window_id,
        )
        temporal = summarize_temporal_bursts(
            normalized,
            burst_threshold_us=burst_threshold_us,
        )
        return AnalysisWindow(
            manifest=manifest,
            result=result,
            temporal=temporal,
        )
    except (TypeError, ValueError, RuntimeError) as error:
        raise _CliFailure(
            ExitCode.PIPELINE,
            f"analysis pipeline failed: {error}",
        ) from error


def _resolved_path(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except OSError as error:
        raise _CliFailure(
            ExitCode.OUTPUT,
            f"output path cannot be resolved: {path}",
        ) from error


def _validate_output_path(
    output_path: Path,
    input_paths: Sequence[Path],
) -> None:
    resolved_output = _resolved_path(output_path)

    for input_path in input_paths:
        if resolved_output == _resolved_path(input_path):
            raise _CliFailure(
                ExitCode.OUTPUT,
                (f"output path must not replace an input file: {output_path}"),
            )


def _write_stdout(markdown: str) -> None:
    try:
        data = markdown.encode("utf-8")
        buffer = getattr(sys.stdout, "buffer", None)

        if buffer is None:
            sys.stdout.write(markdown)
            sys.stdout.flush()
            return

        buffer.write(data)
        buffer.flush()
    except (OSError, UnicodeError, ValueError) as error:
        raise _CliFailure(
            ExitCode.OUTPUT,
            "standard output could not be written",
        ) from error


def _write_output_file(
    path: Path,
    markdown: str,
    *,
    overwrite: bool,
) -> None:
    temporary_path: Path | None = None

    try:
        data = markdown.encode("utf-8")
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(data)
            temporary.flush()
            os.fsync(temporary.fileno())

        if overwrite:
            os.replace(temporary_path, path)
            temporary_path = None
            return

        try:
            os.link(temporary_path, path)
        except FileExistsError as error:
            raise _CliFailure(
                ExitCode.OUTPUT,
                f"output file already exists: {path}",
            ) from error

        temporary_path.unlink()
        temporary_path = None
    except _CliFailure:
        raise
    except (OSError, UnicodeError) as error:
        raise _CliFailure(
            ExitCode.OUTPUT,
            f"output file could not be written: {path}",
        ) from error
    finally:
        if temporary_path is not None:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)


def _emit_markdown(
    markdown: str,
    *,
    output_path: Path | None,
    overwrite: bool,
    input_paths: Sequence[Path],
) -> None:
    if output_path is None:
        _write_stdout(markdown)
        return

    _validate_output_path(
        output_path,
        input_paths,
    )
    _write_output_file(
        output_path,
        markdown,
        overwrite=overwrite,
    )


def _run_analyze(arguments: argparse.Namespace) -> None:
    config = AnalysisConfig(
        schur_capacity=arguments.schur_capacity,
    )
    window = _build_analysis_window(
        arguments.input,
        window_id=arguments.window_id,
        config=config,
        burst_threshold_us=arguments.burst_threshold_us,
    )

    try:
        markdown = render_analysis_window_markdown(window)
    except (TypeError, ValueError, RuntimeError) as error:
        raise _CliFailure(
            ExitCode.PIPELINE,
            f"reporting pipeline failed: {error}",
        ) from error

    _emit_markdown(
        markdown,
        output_path=arguments.output,
        overwrite=arguments.overwrite,
        input_paths=(arguments.input,),
    )


def _run_compare(arguments: argparse.Namespace) -> None:
    config = AnalysisConfig(
        schur_capacity=arguments.schur_capacity,
    )

    left = _build_analysis_window(
        arguments.left,
        window_id=arguments.left_window_id,
        config=config,
        burst_threshold_us=arguments.burst_threshold_us,
    )
    right = _build_analysis_window(
        arguments.right,
        window_id=arguments.right_window_id,
        config=config,
        burst_threshold_us=arguments.burst_threshold_us,
    )

    try:
        report = build_window_comparison_report(
            left,
            right,
        )
        markdown = render_window_comparison_markdown(report)
    except (TypeError, ValueError, RuntimeError) as error:
        raise _CliFailure(
            ExitCode.PIPELINE,
            f"comparison pipeline failed: {error}",
        ) from error

    _emit_markdown(
        markdown,
        output_path=arguments.output,
        overwrite=arguments.overwrite,
        input_paths=(arguments.left, arguments.right),
    )


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Run the command-line interface and return a stable exit code."""

    parser = _build_parser()

    try:
        arguments = parser.parse_args(argv)

        if arguments.overwrite and arguments.output is None:
            raise _CliFailure(
                ExitCode.USAGE,
                "error: --overwrite requires --output",
            )

        if arguments.command == "analyze":
            _run_analyze(arguments)
        elif arguments.command == "compare":
            _run_compare(arguments)
        else:
            raise _CliFailure(
                ExitCode.USAGE,
                f"unsupported command: {arguments.command}",
            )
    except _CliFailure as error:
        sys.stderr.write(f"{error.detail}\n")
        sys.stderr.flush()
        return int(error.exit_code)

    return int(ExitCode.SUCCESS)
