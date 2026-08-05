"""Deterministic presentation models and Markdown reporting."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, isnan
from typing import Final

from system_log_dynamics.comparison import (
    AnalysisWindow,
    NumericState,
    NumericValue,
    WindowComparison,
    compare_analysis_windows,
)
from system_log_dynamics.encoding import decode_event_symbol

__all__ = [
    "WindowComparisonReport",
    "build_window_comparison_report",
    "render_analysis_window_markdown",
    "render_window_comparison_markdown",
]


_FLOAT_DECIMAL_PLACES: Final = 6
_PERCENTAGE_DECIMAL_PLACES: Final = 2

_NUMERIC_STATE_TEXT: Final = {
    NumericState.MISSING: "missing",
    NumericState.NAN: "NaN",
    NumericState.POSITIVE_INFINITY: "+infinity",
    NumericState.NEGATIVE_INFINITY: "-infinity",
    NumericState.NOT_COMPUTABLE: "not computable",
}


def _format_finite_float(
    value: float,
    *,
    decimal_places: int = _FLOAT_DECIMAL_PLACES,
) -> str:
    if type(value) is not float or not isfinite(value):
        raise ValueError("value must be a finite float")
    if type(decimal_places) is not int or decimal_places < 0:
        raise ValueError("decimal_places must be a non-negative integer")

    rendered = f"{value:.{decimal_places}f}".rstrip("0").rstrip(".")

    if rendered in {"-0", ""}:
        return "0"

    return rendered


def _format_number(value: int | float | None) -> str:
    if value is None:
        return "missing"
    if type(value) is int:
        return str(value)
    if type(value) is not float:
        raise ValueError("value must be an integer, float, or None")
    if isnan(value):
        return "NaN"
    if value == float("inf"):
        return "+infinity"
    if value == float("-inf"):
        return "-infinity"

    return _format_finite_float(value)


def _format_percentage(value: float) -> str:
    if type(value) is not float or not isfinite(value):
        raise ValueError("percentage value must be a finite float")

    return (
        _format_finite_float(
            value * 100.0,
            decimal_places=_PERCENTAGE_DECIMAL_PLACES,
        )
        + "%"
    )


def _format_numeric_value(value: NumericValue) -> str:
    if not isinstance(value, NumericValue):
        raise ValueError("value must be a NumericValue")

    if value.state is NumericState.FINITE:
        assert value.value is not None
        return _format_number(value.value)

    return _NUMERIC_STATE_TEXT[value.state]


_MARKDOWN_ESCAPE_CHARACTERS: Final = frozenset("\\`*_{}[]<>()#+-.!|")


def _escape_markdown_text(value: str) -> str:
    if type(value) is not str:
        raise ValueError("value must be a string")

    return "".join(
        f"\\{character}" if character in _MARKDOWN_ESCAPE_CHARACTERS else character
        for character in value
    )


def _format_window_id(value: str | None) -> str:
    if value is None:
        return "unidentified"
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(
            "window identifier must be non-empty text "
            "without surrounding whitespace or None"
        )

    return _escape_markdown_text(value)


def _format_boolean(value: bool) -> str:
    if type(value) is not bool:
        raise ValueError("value must be a boolean")

    return "yes" if value else "no"


def _metric_row(label: str, value: int | float | None) -> tuple[str, str]:
    return (label, _format_number(value))


def _symbol_label(symbol: int) -> str:
    return decode_event_symbol(symbol).value


def _markdown_table(
    headers: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
) -> str:
    if (
        not isinstance(headers, tuple)
        or not headers
        or any(type(header) is not str or not header for header in headers)
    ):
        raise ValueError("headers must be a non-empty tuple of non-empty strings")
    if not isinstance(rows, tuple):
        raise ValueError("rows must be a tuple")

    width = len(headers)

    for row in rows:
        if (
            not isinstance(row, tuple)
            or len(row) != width
            or any(type(cell) is not str for cell in row)
        ):
            raise ValueError(
                "each row must be a tuple of strings matching the header width"
            )

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)

    return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class WindowComparisonReport:
    """Presentation input retaining both windows and their exact comparison."""

    left: AnalysisWindow
    right: AnalysisWindow
    comparison: WindowComparison

    def __post_init__(self) -> None:
        if not isinstance(self.left, AnalysisWindow):
            raise ValueError("left must be an AnalysisWindow")
        if not isinstance(self.right, AnalysisWindow):
            raise ValueError("right must be an AnalysisWindow")
        if not isinstance(self.comparison, WindowComparison):
            raise ValueError("comparison must be a WindowComparison")

        left = AnalysisWindow(
            manifest=self.left.manifest,
            result=self.left.result,
            temporal=self.left.temporal,
        )
        right = AnalysisWindow(
            manifest=self.right.manifest,
            result=self.right.result,
            temporal=self.right.temporal,
        )
        expected = compare_analysis_windows(left, right)

        if self.comparison != expected:
            raise ValueError(
                "comparison must equal the deterministic comparison of left and right"
            )

        object.__setattr__(self, "left", left)
        object.__setattr__(self, "right", right)
        object.__setattr__(self, "comparison", expected)


def build_window_comparison_report(
    left: AnalysisWindow,
    right: AnalysisWindow,
) -> WindowComparisonReport:
    """Build one coherent immutable presentation input for two windows."""

    if not isinstance(left, AnalysisWindow) or not isinstance(right, AnalysisWindow):
        raise ValueError("left and right must be AnalysisWindow instances")

    left_snapshot = AnalysisWindow(
        manifest=left.manifest,
        result=left.result,
        temporal=left.temporal,
    )
    right_snapshot = AnalysisWindow(
        manifest=right.manifest,
        result=right.result,
        temporal=right.temporal,
    )

    return WindowComparisonReport(
        left=left_snapshot,
        right=right_snapshot,
        comparison=compare_analysis_windows(
            left_snapshot,
            right_snapshot,
        ),
    )


def render_analysis_window_markdown(window: AnalysisWindow) -> str:
    """Render one validated analysis window as deterministic Markdown."""

    if not isinstance(window, AnalysisWindow):
        raise ValueError("window must be an AnalysisWindow")

    manifest = window.manifest
    result = window.result
    temporal = window.temporal
    window_id = _format_window_id(manifest.window_id)

    provenance = _markdown_table(
        ("Field", "Value"),
        (
            ("Window identifier", window_id),
            ("Manifest schema", str(manifest.schema_version)),
            ("Taxonomy version", _escape_markdown_text(manifest.taxonomy_version)),
            ("Input digest algorithm", manifest.input_digest_algorithm),
            ("Input SHA-256", manifest.input_sha256),
            ("Input size (bytes)", str(manifest.input_size_bytes)),
            ("Project version", _escape_markdown_text(manifest.project_version)),
            ("Digit-Probe commit", manifest.digit_probe_commit),
            ("Alphabet size", str(manifest.alphabet_size)),
            (
                "Schur capacity",
                str(manifest.analysis_config.schur_capacity),
            ),
            ("Sample size", str(manifest.sample_size)),
        ),
    )

    analysis_summary = _markdown_table(
        ("Metric", "Value"),
        (
            ("Mode", result.mode),
            ("Sample size", str(result.sample_size)),
            ("Alphabet size", str(result.alphabet)),
            ("Maximum observed symbol", str(result.max_observed)),
            ("Expected per bin", _format_number(result.expected_per_bin)),
            ("Chi-square", _format_number(result.chi_square)),
        ),
    )

    symbol_rows = tuple(
        (
            str(symbol),
            _symbol_label(symbol),
            str(result.counts[symbol]),
            _format_percentage(result.counts[symbol] / result.sample_size),
            _format_number(result.zscores[symbol]),
        )
        for symbol in range(result.alphabet)
    )
    symbols = _markdown_table(
        ("Symbol", "Event type", "Count", "Proportion", "Z-score"),
        symbol_rows,
    )

    runs_and_compression = _markdown_table(
        ("Metric", "Value"),
        (
            ("Runs z-score", _format_number(result.runs.z_score)),
            (
                "Runs two-tailed p-value",
                _format_number(result.runs.p_two_tailed),
            ),
            ("Compression ratio", _format_number(result.compress_ratio)),
        ),
    )

    gap_rows = tuple(
        (
            str(symbol),
            _symbol_label(symbol),
            str(result.gaps[symbol].count),
            _format_number(result.gaps[symbol].mean),
        )
        for symbol in range(result.alphabet)
    )
    gaps = _markdown_table(
        ("Symbol", "Event type", "Gap count", "Mean gap"),
        gap_rows,
    )

    autocorrelation = _markdown_table(
        ("Lag", "Value"),
        tuple(
            (str(lag), _format_number(result.autocorr[lag]))
            for lag in sorted(result.autocorr)
        ),
    )

    ngram_accuracy = _markdown_table(
        ("Order", "Accuracy"),
        tuple(
            (str(order), _format_number(result.ngram_accuracy[order]))
            for order in sorted(result.ngram_accuracy)
        ),
    )

    schur = _markdown_table(
        ("Metric", "Value"),
        (
            ("Triples", str(result.schur.triples)),
            ("Matching triples", str(result.schur.count)),
            ("Expected", _format_number(result.schur.expected)),
            ("Fraction", _format_number(result.schur.fraction)),
            ("Z-score", _format_number(result.schur.z_score)),
            (
                "First matching relation index",
                _format_number(result.schur.first_matching_relation_index),
            ),
        ),
    )

    temporal_summary = _markdown_table(
        ("Metric", "Value"),
        (
            _metric_row("Event count", temporal.event_count),
            _metric_row("Timed event count", temporal.timed_event_count),
            _metric_row("Untimed event count", temporal.untimed_event_count),
            _metric_row("Duration (µs)", temporal.duration_us),
            _metric_row(
                "Inter-event gap count",
                temporal.inter_event_gap_count,
            ),
            _metric_row("Minimum gap (µs)", temporal.minimum_gap_us),
            _metric_row("Maximum gap (µs)", temporal.maximum_gap_us),
            _metric_row("Mean gap (µs)", temporal.mean_gap_us),
            _metric_row("Median gap (µs)", temporal.median_gap_us),
            _metric_row(
                "Burst threshold (µs)",
                temporal.burst_threshold_us,
            ),
            _metric_row("Burst count", temporal.burst_count),
            _metric_row(
                "Burst event count",
                temporal.burst_event_count,
            ),
            _metric_row(
                "Largest burst size",
                temporal.largest_burst_size,
            ),
            _metric_row(
                "Longest burst duration (µs)",
                temporal.longest_burst_duration_us,
            ),
        ),
    )

    sections = (
        f"# System Log Dynamics analysis — {window_id}",
        (
            "Results are descriptive and representation-dependent. "
            "They are not proof of anomaly, compromise, malicious behaviour, "
            "randomness, causality, or intent. Unavailable metrics remain "
            "unavailable rather than being coerced to zero."
        ),
        "## Provenance",
        provenance,
        "## Analysis summary",
        analysis_summary,
        "## Symbol distribution",
        symbols,
        "## Runs and compression",
        runs_and_compression,
        "## Symbol gaps",
        gaps,
        "## Autocorrelation",
        autocorrelation,
        "## N-gram accuracy",
        ngram_accuracy,
        "## Schur metrics",
        schur,
        "## Temporal and burst summary",
        temporal_summary,
        "## Methodology and reproducibility",
        (
            "This report was rendered exclusively from a validated "
            "`AnalysisWindow`. It performs no file access, metadata lookup, "
            "Git inspection, network access, metric recalculation, or "
            "interpretive inference."
        ),
    )

    return "\n\n".join(sections) + "\n"


def _difference_cells(
    difference: object,
) -> tuple[str, str, str]:
    from system_log_dynamics.comparison import NumericDifference

    if not isinstance(difference, NumericDifference):
        raise ValueError("difference must be a NumericDifference")

    return (
        _format_numeric_value(difference.left),
        _format_numeric_value(difference.right),
        _format_numeric_value(difference.delta),
    )


def _format_numeric_percentage(value: NumericValue) -> str:
    if not isinstance(value, NumericValue):
        raise ValueError("value must be a NumericValue")

    if value.state is NumericState.FINITE:
        if type(value.value) is not float:
            raise ValueError("finite percentage values must be floats")
        return _format_percentage(value.value)

    return _NUMERIC_STATE_TEXT[value.state]


def _percentage_difference_cells(
    difference: object,
) -> tuple[str, str, str]:
    from system_log_dynamics.comparison import NumericDifference

    if not isinstance(difference, NumericDifference):
        raise ValueError("difference must be a NumericDifference")

    return (
        _format_numeric_percentage(difference.left),
        _format_numeric_percentage(difference.right),
        _format_numeric_percentage(difference.delta),
    )


def render_window_comparison_markdown(
    report: WindowComparisonReport,
) -> str:
    """Render one coherent two-window comparison as deterministic Markdown."""

    if not isinstance(report, WindowComparisonReport):
        raise ValueError("report must be a WindowComparisonReport")

    left = report.left
    right = report.right
    comparison = report.comparison
    compatibility = comparison.compatibility

    left_id = _format_window_id(comparison.left_window_id)
    right_id = _format_window_id(comparison.right_window_id)

    compatibility_table = _markdown_table(
        ("Field", "Value"),
        (
            ("Manifest schema", str(compatibility.schema_version)),
            (
                "Taxonomy version",
                _escape_markdown_text(compatibility.taxonomy_version),
            ),
            ("Alphabet size", str(compatibility.alphabet_size)),
            ("Digit-Probe commit", compatibility.digit_probe_commit),
            (
                "Schur capacity",
                str(compatibility.analysis_config.schur_capacity),
            ),
            (
                "Input digest algorithm",
                compatibility.input_digest_algorithm,
            ),
            (
                "Burst threshold (µs)",
                str(compatibility.burst_threshold_us),
            ),
            (
                "Project versions match",
                _format_boolean(compatibility.project_version_matches),
            ),
            (
                "Window identifiers match",
                _format_boolean(compatibility.window_id_matches),
            ),
            (
                "Input digests match",
                _format_boolean(compatibility.input_digest_matches),
            ),
            (
                "Input sizes match",
                _format_boolean(compatibility.input_size_matches),
            ),
            (
                "Sample sizes match",
                _format_boolean(compatibility.sample_size_matches),
            ),
        ),
    )

    manifest_table = _markdown_table(
        ("Field", "Left", "Right"),
        (
            ("Window identifier", left_id, right_id),
            (
                "Input SHA-256",
                left.manifest.input_sha256,
                right.manifest.input_sha256,
            ),
            (
                "Input size (bytes)",
                str(left.manifest.input_size_bytes),
                str(right.manifest.input_size_bytes),
            ),
            (
                "Project version",
                _escape_markdown_text(left.manifest.project_version),
                _escape_markdown_text(right.manifest.project_version),
            ),
            (
                "Sample size",
                str(left.manifest.sample_size),
                str(right.manifest.sample_size),
            ),
        ),
    )

    count_rows = []
    for symbol in sorted(comparison.counts):
        item = comparison.counts[symbol]
        count_left, count_right, count_delta = _difference_cells(item.count)
        proportion_left, proportion_right, proportion_delta = (
            _percentage_difference_cells(item.proportion)
        )
        count_rows.append(
            (
                str(symbol),
                _symbol_label(symbol),
                count_left,
                count_right,
                count_delta,
                proportion_left,
                proportion_right,
                proportion_delta,
            )
        )

    counts = _markdown_table(
        (
            "Symbol",
            "Event type",
            "Left count",
            "Right count",
            "Delta",
            "Left proportion",
            "Right proportion",
            "Delta proportion",
        ),
        tuple(count_rows),
    )

    runs_rows = []
    for label, difference in (
        ("Runs z-score", comparison.runs.z_score),
        ("Runs two-tailed p-value", comparison.runs.p_two_tailed),
        ("Compression ratio", comparison.compression_ratio),
    ):
        runs_rows.append((label, *_difference_cells(difference)))

    runs = _markdown_table(
        ("Metric", "Left", "Right", "Delta (right - left)"),
        tuple(runs_rows),
    )

    gap_rows = []
    for symbol in sorted(comparison.gaps):
        item = comparison.gaps[symbol]
        count_values = _difference_cells(item.count)
        mean_values = _difference_cells(item.mean)
        gap_rows.append(
            (
                str(symbol),
                _symbol_label(symbol),
                *count_values,
                *mean_values,
            )
        )

    gaps = _markdown_table(
        (
            "Symbol",
            "Event type",
            "Left count",
            "Right count",
            "Count delta",
            "Left mean",
            "Right mean",
            "Mean delta",
        ),
        tuple(gap_rows),
    )

    autocorrelation = _markdown_table(
        ("Lag", "Left", "Right", "Delta (right - left)"),
        tuple(
            (str(lag), *_difference_cells(comparison.autocorrelation[lag]))
            for lag in sorted(comparison.autocorrelation)
        ),
    )

    ngram_accuracy = _markdown_table(
        ("Order", "Left", "Right", "Delta (right - left)"),
        tuple(
            (str(order), *_difference_cells(comparison.ngram_accuracy[order]))
            for order in sorted(comparison.ngram_accuracy)
        ),
    )

    temporal_fields = (
        ("Event count", "event_count"),
        ("Timed event count", "timed_event_count"),
        ("Untimed event count", "untimed_event_count"),
        ("Duration (µs)", "duration_us"),
        ("Inter-event gap count", "inter_event_gap_count"),
        ("Minimum gap (µs)", "minimum_gap_us"),
        ("Maximum gap (µs)", "maximum_gap_us"),
        ("Mean gap (µs)", "mean_gap_us"),
        ("Median gap (µs)", "median_gap_us"),
        ("Burst count", "burst_count"),
        ("Burst event count", "burst_event_count"),
        ("Largest burst size", "largest_burst_size"),
        (
            "Longest burst duration (µs)",
            "longest_burst_duration_us",
        ),
    )
    temporal = _markdown_table(
        ("Metric", "Left", "Right", "Delta (right - left)"),
        tuple(
            (
                label,
                *_difference_cells(getattr(comparison.temporal, field_name)),
            )
            for label, field_name in temporal_fields
        ),
    )

    changed_symbols = tuple(
        _symbol_label(symbol)
        for symbol in sorted(comparison.counts)
        if comparison.counts[symbol].count.delta.value not in (0, None)
    )
    changed_symbol_text = ", ".join(changed_symbols) if changed_symbols else "none"

    conclusions = (
        "Observed count differences occur for these event types: "
        f"{changed_symbol_text}. "
        "The temporal table records the corresponding observed timing and "
        "burst differences. These statements describe the supplied "
        "representations only and do not establish their cause or significance."
    )

    sections = (
        (f"# System Log Dynamics comparison — {left_id} vs {right_id}"),
        (
            "Results are descriptive and representation-dependent. "
            "All deltas use `right - left`. Differences are not proof of "
            "anomaly, compromise, malicious behaviour, randomness, causality, "
            "or intent. Synthetic Experiment 001 results do not establish "
            "production behaviour. Missing and non-finite metrics remain "
            "explicit rather than being coerced to zero."
        ),
        "## Compatibility summary",
        compatibility_table,
        "## Window manifests",
        manifest_table,
        "## Event counts and proportions",
        counts,
        "## Runs and compression",
        runs,
        "## Symbol gaps",
        gaps,
        "## Autocorrelation",
        autocorrelation,
        "## N-gram accuracy",
        ngram_accuracy,
        "## Temporal and burst comparison",
        temporal,
        "## Descriptive conclusions",
        conclusions,
        "## Methodology and reproducibility",
        (
            "This report was rendered exclusively from a validated "
            "`WindowComparisonReport`. It performs no file access, metadata "
            "lookup, Git inspection, network access, metric recalculation, "
            "compatibility decision, or interpretive inference."
        ),
    )

    return "\n\n".join(sections) + "\n"
