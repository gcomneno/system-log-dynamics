import math
from collections.abc import Mapping
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from pathlib import Path

import pytest
from test_comparison import _window

from system_log_dynamics.comparison import (
    AnalysisWindow,
    NumericState,
    NumericValue,
    compare_analysis_windows,
)
from system_log_dynamics.reporting import (
    WindowComparisonReport,
    build_window_comparison_report,
)


def _stable_public_contract(value: object) -> object:
    """Return a canonical public-field representation without deepcopy."""

    if type(value) is float:
        if math.isnan(value):
            return ("float", "nan")
        if math.isinf(value):
            return (
                "float",
                "positive_infinity" if value > 0 else "negative_infinity",
            )
        return value

    if is_dataclass(value) and not isinstance(value, type):
        return (
            type(value).__qualname__,
            tuple(
                (
                    field.name,
                    _stable_public_contract(getattr(value, field.name)),
                )
                for field in fields(value)
            ),
        )

    if isinstance(value, Mapping):
        return tuple(
            sorted(
                (
                    _stable_public_contract(key),
                    _stable_public_contract(item),
                )
                for key, item in value.items()
            )
        )

    if isinstance(value, tuple):
        return tuple(_stable_public_contract(item) for item in value)

    return value


def test_public_exports_and_report_field_order() -> None:
    import system_log_dynamics.reporting as reporting

    assert reporting.__all__ == [
        "WindowComparisonReport",
        "build_window_comparison_report",
        "render_analysis_window_markdown",
        "render_window_comparison_markdown",
    ]
    assert [field.name for field in fields(WindowComparisonReport)] == [
        "left",
        "right",
        "comparison",
    ]


def test_comparison_report_is_frozen_and_slotted() -> None:
    report = build_window_comparison_report(
        _window(window_id="left"),
        _window(window_id="right"),
    )

    assert type(report).__slots__
    assert type(report).__dataclass_params__.frozen

    with pytest.raises(FrozenInstanceError):
        report.left = report.right  # type: ignore[misc]


def test_builder_retains_coherent_independent_window_snapshots() -> None:
    left = _window(window_id="left")
    right = _window(window_id="right")

    report = build_window_comparison_report(left, right)

    assert _stable_public_contract(report.left) == _stable_public_contract(left)
    assert _stable_public_contract(report.right) == _stable_public_contract(right)
    assert report.left is not left
    assert report.right is not right
    assert report.comparison == compare_analysis_windows(left, right)


def test_report_rejects_a_comparison_for_different_windows() -> None:
    left = _window(window_id="left")
    right = _window(window_id="right")
    unrelated = _window(window_id="unrelated")
    wrong_comparison = compare_analysis_windows(left, unrelated)

    with pytest.raises(
        ValueError,
        match=("comparison must equal the deterministic comparison of left and right"),
    ):
        WindowComparisonReport(
            left=left,
            right=right,
            comparison=wrong_comparison,
        )


@pytest.mark.parametrize(
    ("field_name", "invalid"),
    [
        ("left", object()),
        ("right", object()),
        ("comparison", object()),
    ],
)
def test_report_rejects_invalid_public_field_types(
    field_name: str,
    invalid: object,
) -> None:
    left = _window(window_id="left")
    right = _window(window_id="right")
    report = build_window_comparison_report(left, right)

    with pytest.raises(ValueError):
        replace(report, **{field_name: invalid})


def test_builder_requires_analysis_windows() -> None:
    window = _window()

    with pytest.raises(
        ValueError,
        match="left and right must be AnalysisWindow instances",
    ):
        build_window_comparison_report(object(), window)  # type: ignore[arg-type]

    with pytest.raises(
        ValueError,
        match="left and right must be AnalysisWindow instances",
    ):
        build_window_comparison_report(window, object())  # type: ignore[arg-type]


def test_report_fields_use_public_comparison_models() -> None:
    report = build_window_comparison_report(
        _window(window_id="left"),
        _window(window_id="right"),
    )

    assert isinstance(report.left, AnalysisWindow)
    assert isinstance(report.right, AnalysisWindow)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "0"),
        (-12, "-12"),
        (1.0, "1"),
        (1.2345674, "1.234567"),
        (1.2345678, "1.234568"),
        (0.000001, "0.000001"),
        (0.0000004, "0"),
        (-0.0, "0"),
        (None, "missing"),
        (float("nan"), "NaN"),
        (float("inf"), "+infinity"),
        (float("-inf"), "-infinity"),
    ],
)
def test_number_formatting_is_deterministic(
    value: int | float | None,
    expected: str,
) -> None:
    import system_log_dynamics.reporting as reporting

    assert reporting._format_number(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, "0%"),
        (0.125, "12.5%"),
        (1.0, "100%"),
        (-0.0625, "-6.25%"),
        (1 / 3, "33.33%"),
        (-0.0, "0%"),
    ],
)
def test_percentage_formatting_is_deterministic(
    value: float,
    expected: str,
) -> None:
    import system_log_dynamics.reporting as reporting

    assert reporting._format_percentage(value) == expected


@pytest.mark.parametrize(
    ("state", "value", "expected"),
    [
        (NumericState.FINITE, 12, "12"),
        (NumericState.FINITE, 1.25, "1.25"),
        (NumericState.MISSING, None, "missing"),
        (NumericState.NAN, None, "NaN"),
        (NumericState.POSITIVE_INFINITY, None, "+infinity"),
        (NumericState.NEGATIVE_INFINITY, None, "-infinity"),
        (NumericState.NOT_COMPUTABLE, None, "not computable"),
    ],
)
def test_numeric_value_states_remain_distinct(
    state: NumericState,
    value: int | float | None,
    expected: str,
) -> None:
    import system_log_dynamics.reporting as reporting

    assert reporting._format_numeric_value(NumericValue(state, value)) == expected


@pytest.mark.parametrize(
    "value",
    [
        True,
        "1",
        object(),
    ],
)
def test_number_formatting_rejects_implicit_coercion(value: object) -> None:
    import system_log_dynamics.reporting as reporting

    with pytest.raises(
        ValueError,
        match="value must be an integer, float, or None",
    ):
        reporting._format_number(value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_percentage_formatting_rejects_non_finite_values(value: float) -> None:
    import system_log_dynamics.reporting as reporting

    with pytest.raises(
        ValueError,
        match="percentage value must be a finite float",
    ):
        reporting._format_percentage(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("plain-window", r"plain\-window"),
        ("left|right", r"left\|right"),
        ("a_b*c", r"a\_b\*c"),
        ("[window](target)", r"\[window\]\(target\)"),
        ("`code`", r"\`code\`"),
        ("# heading!", r"\# heading\!"),
        ("<tag>", r"\<tag\>"),
        (r"path\name", r"path\\name"),
        ("unicode-àèìòù", r"unicode\-àèìòù"),
        ("", ""),
    ],
)
def test_markdown_text_escaping_is_deterministic(
    value: str,
    expected: str,
) -> None:
    import system_log_dynamics.reporting as reporting

    assert reporting._escape_markdown_text(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "unidentified"),
        ("routine", "routine"),
        ("window|one", r"window\|one"),
        ("window_[one]", r"window\_\[one\]"),
    ],
)
def test_window_identifier_formatting(
    value: str | None,
    expected: str,
) -> None:
    import system_log_dynamics.reporting as reporting

    assert reporting._format_window_id(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        " leading",
        "trailing ",
    ],
)
def test_window_identifier_rejects_invalid_text(value: str) -> None:
    import system_log_dynamics.reporting as reporting

    with pytest.raises(
        ValueError,
        match=(
            "window identifier must be non-empty text "
            "without surrounding whitespace or None"
        ),
    ):
        reporting._format_window_id(value)


def test_markdown_table_has_fixed_compact_structure() -> None:
    import system_log_dynamics.reporting as reporting

    assert reporting._markdown_table(
        ("Metric", "Value"),
        (
            ("sample size", "24"),
            ("ratio", "0.75"),
        ),
    ) == ("| Metric | Value |\n| --- | --- |\n| sample size | 24 |\n| ratio | 0.75 |")


def test_markdown_table_supports_no_data_rows() -> None:
    import system_log_dynamics.reporting as reporting

    assert reporting._markdown_table(
        ("Metric", "Value"),
        (),
    ) == ("| Metric | Value |\n| --- | --- |")


@pytest.mark.parametrize(
    ("headers", "rows"),
    [
        ((), ()),
        (("",), ()),
        (("A", "B"), (("one",),)),
        (("A",), (("one", "two"),)),
        (("A",), (("one",), ["two"])),
    ],
)
def test_markdown_table_rejects_invalid_shapes(
    headers: object,
    rows: object,
) -> None:
    import system_log_dynamics.reporting as reporting

    with pytest.raises(ValueError):
        reporting._markdown_table(  # type: ignore[arg-type]
            headers,
            rows,
        )


def test_markdown_helpers_reject_implicit_coercion() -> None:
    import system_log_dynamics.reporting as reporting

    with pytest.raises(ValueError, match="value must be a string"):
        reporting._escape_markdown_text(1)  # type: ignore[arg-type]

    with pytest.raises(
        ValueError,
        match=(
            "window identifier must be non-empty text "
            "without surrounding whitespace or None"
        ),
    ):
        reporting._format_window_id(1)  # type: ignore[arg-type]


def test_analysis_window_renderer_is_public() -> None:
    import system_log_dynamics.reporting as reporting

    assert reporting.__all__ == [
        "WindowComparisonReport",
        "build_window_comparison_report",
        "render_analysis_window_markdown",
        "render_window_comparison_markdown",
    ]


def test_analysis_window_renderer_requires_a_validated_window() -> None:
    from system_log_dynamics.reporting import render_analysis_window_markdown

    with pytest.raises(
        ValueError,
        match="window must be an AnalysisWindow",
    ):
        render_analysis_window_markdown(object())  # type: ignore[arg-type]


def test_analysis_window_markdown_has_exact_compact_contract() -> None:
    from system_log_dynamics.reporting import render_analysis_window_markdown

    rendered = render_analysis_window_markdown(_window(window_id="window_[one]"))

    assert rendered.startswith(
        "# System Log Dynamics analysis — window\\_\\[one\\]\n\n"
    )
    assert rendered.endswith("interpretive inference.\n")
    assert rendered.count("\n# ") == 0
    assert rendered.count("\n## ") == 11
    assert rendered.endswith("\n")
    assert not rendered.endswith("\n\n")

    expected_fragments = (
        "## Plain-language summary",
        "All configured event categories are represented.",
        "The category counts are evenly distributed in this window.",
        "## Provenance",
        "| Window identifier | window\\_\\[one\\] |",
        "| Input SHA-256 | " + ("a" * 64) + " |",
        "| Digit-Probe commit | " + ("b" * 40) + " |",
        "| Schur capacity | 64 |",
        "## Analysis summary",
        "| Maximum observed symbol | 8 |",
        "| Chi-square | 0 |",
        "## Symbol distribution",
        "| 0 | boot_boundary | 1 | 11.11% | 0 |",
        "| 8 | other | 1 | 11.11% | 0 |",
        "## Runs and compression",
        "## Symbol gaps",
        "| 0 | boot_boundary | 0 | +infinity |",
        "## Autocorrelation",
        "## N-gram accuracy",
        "## Schur metrics",
        "## Temporal and burst summary",
        "| Duration (µs) | missing |",
        "| Mean gap (µs) | missing |",
        "| Burst threshold (µs) | 10 |",
        "## Methodology and reproducibility",
    )

    for fragment in expected_fragments:
        assert fragment in rendered


def test_plain_language_summary_reports_dominant_other_and_absent_categories() -> None:
    from system_log_dynamics.reporting import render_analysis_window_markdown

    rendered = render_analysis_window_markdown(
        _window(
            symbols=[8, 8, 8, 8, 1, 6],
            window_id="dominant-other",
        )
    )

    assert (
        "- This window contains 6 events across 3 of 9 configured event categories."
    ) in rendered
    assert ("- The most frequent category is other with 4 events (66.67%).") in rendered
    assert ("- The `other` category contains 4 events (66.67%).") not in rendered
    assert rendered.count("4 events (66.67%)") == 1
    assert (
        "- Absent categories: boot\\_boundary, service\\_stopped, "
        "authentication\\_success, authentication\\_failure, "
        "session\\_boundary, and error."
    ) in rendered
    assert (
        "- The category counts are unevenly distributed in this window."
    ) in rendered
    assert (
        "These observations are descriptive and are not proof of anomaly, "
        "compromise, malicious behaviour, randomness, causality, safety, "
        "or intent."
    ) in rendered


def test_plain_language_summary_handles_one_represented_category() -> None:
    from system_log_dynamics.reporting import render_analysis_window_markdown

    rendered = render_analysis_window_markdown(
        _window(
            symbols=[7],
            window_id="one-category",
        )
    )

    assert (
        "- This window contains 1 event across 1 of 9 configured event categories."
    ) in rendered
    assert ("- The most frequent category is error with 1 event (100%).") in rendered
    assert "- The `other` category contains 0 events (0%)." in rendered


def test_plain_language_summary_reports_named_dominant_category() -> None:
    from system_log_dynamics.reporting import render_analysis_window_markdown

    rendered = render_analysis_window_markdown(
        _window(
            symbols=[1, 1, 1, 8],
            window_id="named-dominant",
        )
    )

    assert (
        "- The most frequent category is service\\_started with 3 events (75%)."
    ) in rendered
    assert "- The `other` category contains 1 event (25%)." in rendered


def test_plain_language_summary_orders_tied_dominant_categories() -> None:
    from system_log_dynamics.reporting import render_analysis_window_markdown

    window = _window(
        symbols=[6, 1, 8, 6, 1],
        window_id="tied-dominant",
    )

    first = render_analysis_window_markdown(window)
    second = render_analysis_window_markdown(window)

    assert first == second
    assert (
        "- The most frequent categories are service\\_started and warning, "
        "each with 2 events (40%)."
    ) in first
    assert first.index("service\\_started") < first.index("warning")


def test_analysis_window_markdown_without_identifier() -> None:
    from system_log_dynamics.reporting import render_analysis_window_markdown

    rendered = render_analysis_window_markdown(_window(window_id=None))

    assert rendered.startswith("# System Log Dynamics analysis — unidentified\n\n")
    assert "| Window identifier | unidentified |" in rendered


def test_analysis_window_renderer_is_exactly_repeatable() -> None:
    from system_log_dynamics.reporting import render_analysis_window_markdown

    window = _window(window_id="repeatable")

    assert render_analysis_window_markdown(window) == render_analysis_window_markdown(
        window
    )


def test_analysis_window_renderer_orders_mapping_keys() -> None:
    from dataclasses import replace

    from system_log_dynamics.comparison import AnalysisWindow
    from system_log_dynamics.reporting import render_analysis_window_markdown

    window = _window(window_id="ordered")
    result = replace(
        window.result,
        autocorr={5: 0.5, 1: 0.1, 3: 0.3},
        ngram_accuracy={3: 0.3, 1: 0.1, 2: 0.2},
    )
    reordered = AnalysisWindow(
        window.manifest,
        result,
        window.temporal,
    )

    rendered = render_analysis_window_markdown(reordered)

    assert rendered.index("| 1 | 0.1 |") < rendered.index("| 3 | 0.3 |")
    assert rendered.index("| 3 | 0.3 |") < rendered.index("| 5 | 0.5 |")

    ngram_section = rendered.split("## N-gram accuracy", 1)[1]
    assert ngram_section.index("| 1 | 0.1 |") < ngram_section.index("| 2 | 0.2 |")
    assert ngram_section.index("| 2 | 0.2 |") < ngram_section.index("| 3 | 0.3 |")


def test_analysis_window_renderer_preserves_non_finite_metrics() -> None:
    from dataclasses import replace
    from math import inf, nan

    from system_log_dynamics.comparison import AnalysisWindow
    from system_log_dynamics.reporting import render_analysis_window_markdown

    window = _window(window_id="non-finite")
    gaps = dict(window.result.gaps)
    gaps[0] = replace(gaps[0], mean=inf)
    result = replace(
        window.result,
        chi_square=nan,
        compress_ratio=-inf,
        gaps=gaps,
    )
    non_finite = AnalysisWindow(
        window.manifest,
        result,
        window.temporal,
    )

    rendered = render_analysis_window_markdown(non_finite)

    assert "| Chi-square | NaN |" in rendered
    assert "| Compression ratio | -infinity |" in rendered
    assert "| 0 | boot_boundary | 0 | +infinity |" in rendered


def test_comparison_renderer_is_public() -> None:
    import system_log_dynamics.reporting as reporting

    assert reporting.__all__ == [
        "WindowComparisonReport",
        "build_window_comparison_report",
        "render_analysis_window_markdown",
        "render_window_comparison_markdown",
    ]


def test_comparison_renderer_requires_report_model() -> None:
    from system_log_dynamics.reporting import render_window_comparison_markdown

    with pytest.raises(
        ValueError,
        match="report must be a WindowComparisonReport",
    ):
        render_window_comparison_markdown(object())  # type: ignore[arg-type]


def test_comparison_markdown_has_deterministic_contract() -> None:
    from system_log_dynamics.reporting import (
        build_window_comparison_report,
        render_window_comparison_markdown,
    )

    report = build_window_comparison_report(
        _window(window_id="left_[one]"),
        _window(
            [0, 0, 1, 2, 3, 4, 5, 6, 7],
            window_id="right|two",
            input_sha256="c" * 64,
            input_size_bytes=200,
        ),
    )

    rendered = render_window_comparison_markdown(report)

    assert rendered.startswith(
        "# System Log Dynamics comparison — left\\_\\[one\\] vs right\\|two\n\n"
    )
    assert "All deltas use `right - left`." in rendered
    assert (
        "Synthetic Experiment 001 results do not establish production behaviour."
        in rendered
    )
    assert "| Window identifier | left\\_\\[one\\] | right\\|two |" in rendered
    assert "| Input SHA-256 | " + ("a" * 64) + " | " + ("c" * 64) + " |" in rendered
    assert "## Event counts and proportions" in rendered
    assert "| 0 | boot_boundary | 1 | 2 | 1 | 11.11% | 22.22% | 11.11% |" in rendered
    assert "## Temporal and burst comparison" in rendered
    assert "## Descriptive conclusions" in rendered
    assert rendered.endswith("interpretive inference.\n")
    assert not rendered.endswith("\n\n")


def test_comparison_markdown_supports_missing_identifiers() -> None:
    from system_log_dynamics.reporting import (
        build_window_comparison_report,
        render_window_comparison_markdown,
    )

    rendered = render_window_comparison_markdown(
        build_window_comparison_report(
            _window(window_id=None),
            _window(window_id=None),
        )
    )

    assert rendered.startswith(
        "# System Log Dynamics comparison — unidentified vs unidentified\n\n"
    )


def test_comparison_renderer_is_exactly_repeatable() -> None:
    from system_log_dynamics.reporting import (
        build_window_comparison_report,
        render_window_comparison_markdown,
    )

    report = build_window_comparison_report(
        _window(window_id="left"),
        _window(window_id="right"),
    )

    assert render_window_comparison_markdown(
        report
    ) == render_window_comparison_markdown(report)


def test_comparison_renderer_preserves_non_finite_states() -> None:
    from dataclasses import replace
    from math import nan

    from system_log_dynamics.comparison import AnalysisWindow
    from system_log_dynamics.reporting import (
        build_window_comparison_report,
        render_window_comparison_markdown,
    )

    left = _window(window_id="left")
    right_result = replace(
        left.result,
        runs=replace(left.result.runs, z_score=nan),
    )
    right = AnalysisWindow(
        replace(left.manifest, window_id="right"),
        right_result,
        left.temporal,
    )

    rendered = render_window_comparison_markdown(
        build_window_comparison_report(left, right)
    )

    assert "| Runs z-score | 2.570302 | NaN | not computable |" in rendered


def test_comparison_renderer_orders_union_mappings() -> None:
    from dataclasses import replace

    from system_log_dynamics.comparison import AnalysisWindow
    from system_log_dynamics.reporting import (
        build_window_comparison_report,
        render_window_comparison_markdown,
    )

    left = _window(window_id="left")
    right_result = replace(
        left.result,
        autocorr={5: 0.5, 1: 0.1, 3: 0.3},
        ngram_accuracy={3: 0.3, 1: 0.1, 2: 0.2},
    )
    right = AnalysisWindow(
        replace(left.manifest, window_id="right"),
        right_result,
        left.temporal,
    )

    rendered = render_window_comparison_markdown(
        build_window_comparison_report(left, right)
    )

    autocorrelation_section = rendered.split("## Autocorrelation", 1)[1].split(
        "## N-gram accuracy",
        1,
    )[0]
    assert autocorrelation_section.index("| 1 |") < autocorrelation_section.index(
        "| 3 |"
    )
    assert autocorrelation_section.index("| 3 |") < autocorrelation_section.index(
        "| 5 |"
    )


def test_experiment_001_routine_report_matches_golden_bytes() -> None:
    import hashlib

    from test_experiment_001 import ROUTINE_PATH, build_artifacts

    from system_log_dynamics.reporting import render_analysis_window_markdown

    golden_path = Path("fixtures/reports/experiment-001-routine.md")
    golden_bytes = golden_path.read_bytes()
    rendered_bytes = render_analysis_window_markdown(
        build_artifacts(
            ROUTINE_PATH,
            "experiment-001-routine",
        ).window
    ).encode("utf-8")

    assert len(golden_bytes) == 3753
    assert hashlib.sha256(golden_bytes).hexdigest() == (
        "f6dcfb5761981a4f21a14e8a1774af8238f99aa74c6da450357d0542ea3443f8"
    )
    assert rendered_bytes == golden_bytes


def test_experiment_001_comparison_report_matches_golden_bytes() -> None:
    import hashlib

    from test_experiment_001 import (
        BURST_PATH,
        ROUTINE_PATH,
        build_artifacts,
    )

    from system_log_dynamics.reporting import (
        build_window_comparison_report,
        render_window_comparison_markdown,
    )

    routine = build_artifacts(
        ROUTINE_PATH,
        "experiment-001-routine",
    )
    burst = build_artifacts(
        BURST_PATH,
        "experiment-001-boot-error-burst",
    )

    golden_path = Path("fixtures/reports/experiment-001-comparison.md")
    golden_bytes = golden_path.read_bytes()
    rendered_bytes = render_window_comparison_markdown(
        build_window_comparison_report(
            routine.window,
            burst.window,
        )
    ).encode("utf-8")

    assert len(golden_bytes) == 4872
    assert hashlib.sha256(golden_bytes).hexdigest() == (
        "9effbd6986663dbae37ff1e450406ad9842843f74e25e834291c8aae9ca68ba5"
    )
    assert rendered_bytes == golden_bytes
