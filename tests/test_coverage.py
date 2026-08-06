"""Focused contracts for deterministic taxonomy coverage."""

from __future__ import annotations

from dataclasses import (
    FrozenInstanceError,
    fields,
    replace,
)

import pytest
from digit_probe import AnalysisResult, analyze_integer_symbols

from system_log_dynamics.coverage import (
    CoverageStatus,
    TaxonomyCoverage,
    TaxonomyCoverageComparison,
    build_taxonomy_coverage,
    compare_taxonomy_coverage,
)
from system_log_dynamics.encoding import EVENT_ALPHABET_SIZE


def _result(symbols: list[int]) -> AnalysisResult:
    return analyze_integer_symbols(
        symbols,
        alphabet=EVENT_ALPHABET_SIZE,
    )


def test_public_exports_and_dataclass_field_order() -> None:
    import system_log_dynamics.coverage as coverage

    assert coverage.__all__ == [
        "CoverageStatus",
        "TaxonomyCoverage",
        "TaxonomyCoverageComparison",
        "build_taxonomy_coverage",
        "compare_taxonomy_coverage",
    ]

    assert [field.name for field in fields(TaxonomyCoverage)] == [
        "sample_size",
        "named_event_count",
        "other_event_count",
        "named_event_proportion",
        "other_event_proportion",
        "represented_named_symbols",
        "absent_named_symbols",
        "status",
    ]

    assert [field.name for field in fields(TaxonomyCoverageComparison)] == [
        "left",
        "right",
        "named_event_count_delta",
        "other_event_count_delta",
        "named_event_proportion_delta",
        "other_event_proportion_delta",
        "represented_named_category_count_delta",
        "newly_represented_named_symbols",
        "newly_absent_named_symbols",
    ]


def test_all_named_window_has_exact_coverage() -> None:
    coverage = build_taxonomy_coverage(_result(list(range(8))))

    assert coverage == TaxonomyCoverage(
        sample_size=8,
        named_event_count=8,
        other_event_count=0,
        named_event_proportion=1.0,
        other_event_proportion=0.0,
        represented_named_symbols=tuple(range(8)),
        absent_named_symbols=(),
        status=CoverageStatus.ALL_NAMED,
    )
    assert coverage.represented_named_category_count == 8
    assert coverage.absent_named_category_count == 0


def test_mixed_window_has_exact_coverage() -> None:
    coverage = build_taxonomy_coverage(_result([0, 1, 8, 8]))

    assert coverage.sample_size == 4
    assert coverage.named_event_count == 2
    assert coverage.other_event_count == 2
    assert coverage.named_event_proportion == 0.5
    assert coverage.other_event_proportion == 0.5
    assert coverage.represented_named_symbols == (0, 1)
    assert coverage.absent_named_symbols == tuple(range(2, 8))
    assert coverage.status is CoverageStatus.MIXED


def test_non_binary_proportions_are_stable() -> None:
    coverage = build_taxonomy_coverage(_result([0, 8, 8]))

    assert coverage.named_event_count == 1
    assert coverage.other_event_count == 2
    assert coverage.named_event_proportion == 1 / 3
    assert coverage.other_event_proportion == 2 / 3
    assert coverage.status is CoverageStatus.MIXED


def test_all_other_window_has_exact_coverage() -> None:
    coverage = build_taxonomy_coverage(_result([8, 8, 8]))

    assert coverage == TaxonomyCoverage(
        sample_size=3,
        named_event_count=0,
        other_event_count=3,
        named_event_proportion=0.0,
        other_event_proportion=1.0,
        represented_named_symbols=(),
        absent_named_symbols=tuple(range(8)),
        status=CoverageStatus.ALL_OTHER,
    )


def test_coverage_is_frozen_slotted_and_deterministic() -> None:
    result = _result([8, 0, 8, 1])

    first = build_taxonomy_coverage(result)
    second = build_taxonomy_coverage(result)

    assert first == second
    assert type(first).__slots__
    assert type(first).__dataclass_params__.frozen

    with pytest.raises(FrozenInstanceError):
        first.sample_size = 5  # type: ignore[misc]


@pytest.mark.parametrize(
    "replacement",
    [
        {"sample_size": 0},
        {"named_event_count": 3},
        {"other_event_count": 3},
        {"named_event_proportion": 0.25},
        {"other_event_proportion": 0.25},
        {"represented_named_symbols": (1, 0)},
        {"represented_named_symbols": (0, 0)},
        {"represented_named_symbols": (8,)},
        {"absent_named_symbols": ()},
        {"status": CoverageStatus.ALL_NAMED},
    ],
)
def test_model_rejects_inconsistent_fields(
    replacement: dict[str, object],
) -> None:
    valid = build_taxonomy_coverage(_result([0, 1, 8, 8]))

    with pytest.raises(ValueError):
        replace(valid, **replacement)


def test_coverage_comparison_reports_exact_deltas() -> None:
    comparison = compare_taxonomy_coverage(
        _result([0, 8, 8]),
        _result([0, 1, 1, 8]),
    )

    assert comparison.left.status is CoverageStatus.MIXED
    assert comparison.right.status is CoverageStatus.MIXED
    assert comparison.named_event_count_delta == 2
    assert comparison.other_event_count_delta == -1
    assert comparison.named_event_proportion_delta == pytest.approx(0.75 - (1 / 3))
    assert comparison.other_event_proportion_delta == pytest.approx(0.25 - (2 / 3))
    assert comparison.represented_named_category_count_delta == 1
    assert comparison.newly_represented_named_symbols == (1,)
    assert comparison.newly_absent_named_symbols == ()


def test_coverage_comparison_reports_newly_absent_categories() -> None:
    comparison = compare_taxonomy_coverage(
        _result([0, 1]),
        _result([8, 8]),
    )

    assert comparison.left.status is CoverageStatus.ALL_NAMED
    assert comparison.right.status is CoverageStatus.ALL_OTHER
    assert comparison.named_event_count_delta == -2
    assert comparison.other_event_count_delta == 2
    assert comparison.newly_represented_named_symbols == ()
    assert comparison.newly_absent_named_symbols == (0, 1)


def test_coverage_comparison_is_frozen_and_deterministic() -> None:
    left = _result([0, 8])
    right = _result([1, 8, 8])

    first = compare_taxonomy_coverage(left, right)
    second = compare_taxonomy_coverage(left, right)

    assert first == second
    assert type(first).__slots__
    assert type(first).__dataclass_params__.frozen

    with pytest.raises(FrozenInstanceError):
        first.named_event_count_delta = 10  # type: ignore[misc]

    with pytest.raises(ValueError):
        replace(first, named_event_count_delta=10)

    with pytest.raises(ValueError):
        replace(
            first,
            newly_represented_named_symbols=(0,),
        )


def test_coverage_comparison_revalidates_results() -> None:
    left = _result([0, 8])
    right = _result([1, 8])

    object.__setattr__(right, "counts", {0: 2})

    with pytest.raises(ValueError):
        compare_taxonomy_coverage(left, right)


def test_builder_rejects_non_results() -> None:
    with pytest.raises(ValueError):
        build_taxonomy_coverage(object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "mutation",
    [
        ("alphabet", 8),
        ("sample_size", 0),
        ("counts", {0: 1}),
        (
            "counts",
            {
                symbol: (True if symbol == 0 else 0)
                for symbol in range(EVENT_ALPHABET_SIZE)
            },
        ),
        (
            "counts",
            {symbol: 0 for symbol in range(EVENT_ALPHABET_SIZE)},
        ),
    ],
)
def test_builder_revalidates_analysis_result(
    mutation: tuple[str, object],
) -> None:
    result = _result([0, 1, 8, 8])
    field_name, value = mutation

    object.__setattr__(result, field_name, value)

    with pytest.raises(ValueError):
        build_taxonomy_coverage(result)
