"""Deterministic taxonomy-coverage models derived from validated counts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from math import isclose, isfinite
from typing import Final

from digit_probe import AnalysisResult

from system_log_dynamics.encoding import (
    EVENT_ALPHABET_SIZE,
    EVENT_TYPE_TO_SYMBOL,
)
from system_log_dynamics.models import EventType

__all__ = [
    "CoverageStatus",
    "TaxonomyCoverage",
    "TaxonomyCoverageComparison",
    "build_taxonomy_coverage",
    "compare_taxonomy_coverage",
]


_SYMBOLS: Final = tuple(range(EVENT_ALPHABET_SIZE))
_OTHER_SYMBOL: Final = EVENT_TYPE_TO_SYMBOL[EventType.OTHER]
_NAMED_SYMBOLS: Final = tuple(symbol for symbol in _SYMBOLS if symbol != _OTHER_SYMBOL)


class CoverageStatus(StrEnum):
    """Exact structural relationship between named categories and `other`."""

    ALL_NAMED = "all_named"
    MIXED = "mixed"
    ALL_OTHER = "all_other"


def _require_non_negative_integer(
    name: str,
    value: object,
) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative concrete integer")

    return value


def _require_proportion(
    name: str,
    value: object,
) -> float:
    if type(value) is not float or not isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be a finite float proportion")

    return value


def _require_named_symbols(
    name: str,
    value: object,
) -> tuple[int, ...]:
    if not isinstance(value, tuple):
        raise ValueError(f"{name} must be a tuple")

    if any(type(symbol) is not int for symbol in value):
        raise ValueError(f"{name} must contain concrete integer symbols")

    if value != tuple(sorted(set(value))):
        raise ValueError(f"{name} must contain unique symbols in canonical order")

    if any(symbol not in _NAMED_SYMBOLS for symbol in value):
        raise ValueError(f"{name} must contain only named taxonomy symbols")

    return value


@dataclass(frozen=True, slots=True)
class TaxonomyCoverage:
    """Deterministic named-category and `other` coverage for one window."""

    sample_size: int
    named_event_count: int
    other_event_count: int
    named_event_proportion: float
    other_event_proportion: float
    represented_named_symbols: tuple[int, ...]
    absent_named_symbols: tuple[int, ...]
    status: CoverageStatus

    def __post_init__(self) -> None:
        sample_size = _require_non_negative_integer(
            "sample_size",
            self.sample_size,
        )

        if sample_size == 0:
            raise ValueError("sample_size must be positive")

        named_event_count = _require_non_negative_integer(
            "named_event_count",
            self.named_event_count,
        )
        other_event_count = _require_non_negative_integer(
            "other_event_count",
            self.other_event_count,
        )

        if named_event_count + other_event_count != sample_size:
            raise ValueError("named and other event counts must sum to sample_size")

        named_event_proportion = _require_proportion(
            "named_event_proportion",
            self.named_event_proportion,
        )
        other_event_proportion = _require_proportion(
            "other_event_proportion",
            self.other_event_proportion,
        )

        if not isclose(
            named_event_proportion,
            named_event_count / sample_size,
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            raise ValueError("named_event_proportion must match named_event_count")

        if not isclose(
            other_event_proportion,
            other_event_count / sample_size,
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            raise ValueError("other_event_proportion must match other_event_count")

        if not isclose(
            named_event_proportion + other_event_proportion,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            raise ValueError("named and other proportions must sum to one")

        represented = _require_named_symbols(
            "represented_named_symbols",
            self.represented_named_symbols,
        )
        absent = _require_named_symbols(
            "absent_named_symbols",
            self.absent_named_symbols,
        )

        if set(represented) & set(absent):
            raise ValueError("represented and absent named symbols must be disjoint")

        if set(represented) | set(absent) != set(_NAMED_SYMBOLS):
            raise ValueError(
                "represented and absent symbols must partition the named taxonomy"
            )

        if not isinstance(self.status, CoverageStatus):
            raise ValueError("status must be a CoverageStatus")

        expected_status = (
            CoverageStatus.ALL_NAMED
            if other_event_count == 0
            else CoverageStatus.ALL_OTHER
            if named_event_count == 0
            else CoverageStatus.MIXED
        )

        if self.status is not expected_status:
            raise ValueError("status must match the exact event-count relationship")

    @property
    def represented_named_category_count(self) -> int:
        """Return the number of represented non-`other` categories."""

        return len(self.represented_named_symbols)

    @property
    def absent_named_category_count(self) -> int:
        """Return the number of absent non-`other` categories."""

        return len(self.absent_named_symbols)


@dataclass(frozen=True, slots=True)
class TaxonomyCoverageComparison:
    """Exact taxonomy-coverage differences between two windows."""

    left: TaxonomyCoverage
    right: TaxonomyCoverage
    named_event_count_delta: int
    other_event_count_delta: int
    named_event_proportion_delta: float
    other_event_proportion_delta: float
    represented_named_category_count_delta: int
    newly_represented_named_symbols: tuple[int, ...]
    newly_absent_named_symbols: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.left, TaxonomyCoverage):
            raise ValueError("left must be a TaxonomyCoverage")

        if not isinstance(self.right, TaxonomyCoverage):
            raise ValueError("right must be a TaxonomyCoverage")

        integer_deltas = (
            (
                "named_event_count_delta",
                self.named_event_count_delta,
                (self.right.named_event_count - self.left.named_event_count),
            ),
            (
                "other_event_count_delta",
                self.other_event_count_delta,
                (self.right.other_event_count - self.left.other_event_count),
            ),
            (
                "represented_named_category_count_delta",
                self.represented_named_category_count_delta,
                (
                    self.right.represented_named_category_count
                    - self.left.represented_named_category_count
                ),
            ),
        )

        for name, value, expected in integer_deltas:
            if type(value) is not int:
                raise ValueError(f"{name} must be a concrete integer")

            if value != expected:
                raise ValueError(f"{name} must equal right minus left")

        float_deltas = (
            (
                "named_event_proportion_delta",
                self.named_event_proportion_delta,
                (self.right.named_event_proportion - self.left.named_event_proportion),
            ),
            (
                "other_event_proportion_delta",
                self.other_event_proportion_delta,
                (self.right.other_event_proportion - self.left.other_event_proportion),
            ),
        )

        for name, value, expected in float_deltas:
            if type(value) is not float or not isfinite(value):
                raise ValueError(f"{name} must be a finite float")

            if not isclose(
                value,
                expected,
                rel_tol=0.0,
                abs_tol=1e-15,
            ):
                raise ValueError(f"{name} must equal right minus left")

        newly_represented = _require_named_symbols(
            "newly_represented_named_symbols",
            self.newly_represented_named_symbols,
        )
        newly_absent = _require_named_symbols(
            "newly_absent_named_symbols",
            self.newly_absent_named_symbols,
        )

        expected_newly_represented = tuple(
            symbol
            for symbol in self.right.represented_named_symbols
            if symbol not in self.left.represented_named_symbols
        )
        expected_newly_absent = tuple(
            symbol
            for symbol in self.left.represented_named_symbols
            if symbol not in self.right.represented_named_symbols
        )

        if newly_represented != expected_newly_represented:
            raise ValueError("newly represented symbols must match both windows")

        if newly_absent != expected_newly_absent:
            raise ValueError("newly absent symbols must match both windows")


def _validated_counts(
    result: AnalysisResult,
) -> Mapping[int, int]:
    if not isinstance(result, AnalysisResult):
        raise ValueError("result must be an AnalysisResult")

    if type(result.alphabet) is not int or result.alphabet != EVENT_ALPHABET_SIZE:
        raise ValueError("result alphabet must match EVENT_ALPHABET_SIZE")

    if type(result.sample_size) is not int or result.sample_size <= 0:
        raise ValueError("result sample size must be positive")

    if not isinstance(result.counts, Mapping) or set(result.counts) != set(_SYMBOLS):
        raise ValueError("result counts must cover the complete event alphabet")

    for symbol, count in result.counts.items():
        if type(symbol) is not int or type(count) is not int or count < 0:
            raise ValueError(
                "result counts must contain non-negative concrete integers"
            )

    if sum(result.counts.values()) != result.sample_size:
        raise ValueError("result counts must sum to the sample size")

    return result.counts


def build_taxonomy_coverage(
    result: AnalysisResult,
) -> TaxonomyCoverage:
    """Derive exact taxonomy coverage from one validated analysis result."""

    counts = _validated_counts(result)

    other_event_count = counts[_OTHER_SYMBOL]
    named_event_count = result.sample_size - other_event_count

    represented_named_symbols = tuple(
        symbol for symbol in _NAMED_SYMBOLS if counts[symbol] > 0
    )
    absent_named_symbols = tuple(
        symbol for symbol in _NAMED_SYMBOLS if counts[symbol] == 0
    )

    status = (
        CoverageStatus.ALL_NAMED
        if other_event_count == 0
        else CoverageStatus.ALL_OTHER
        if named_event_count == 0
        else CoverageStatus.MIXED
    )

    return TaxonomyCoverage(
        sample_size=result.sample_size,
        named_event_count=named_event_count,
        other_event_count=other_event_count,
        named_event_proportion=(named_event_count / result.sample_size),
        other_event_proportion=(other_event_count / result.sample_size),
        represented_named_symbols=represented_named_symbols,
        absent_named_symbols=absent_named_symbols,
        status=status,
    )


def compare_taxonomy_coverage(
    left: AnalysisResult,
    right: AnalysisResult,
) -> TaxonomyCoverageComparison:
    """Compare exact taxonomy coverage using ``right - left`` deltas."""

    left_coverage = build_taxonomy_coverage(left)
    right_coverage = build_taxonomy_coverage(right)

    return TaxonomyCoverageComparison(
        left=left_coverage,
        right=right_coverage,
        named_event_count_delta=(
            right_coverage.named_event_count - left_coverage.named_event_count
        ),
        other_event_count_delta=(
            right_coverage.other_event_count - left_coverage.other_event_count
        ),
        named_event_proportion_delta=(
            right_coverage.named_event_proportion - left_coverage.named_event_proportion
        ),
        other_event_proportion_delta=(
            right_coverage.other_event_proportion - left_coverage.other_event_proportion
        ),
        represented_named_category_count_delta=(
            right_coverage.represented_named_category_count
            - left_coverage.represented_named_category_count
        ),
        newly_represented_named_symbols=tuple(
            symbol
            for symbol in right_coverage.represented_named_symbols
            if symbol not in left_coverage.represented_named_symbols
        ),
        newly_absent_named_symbols=tuple(
            symbol
            for symbol in left_coverage.represented_named_symbols
            if symbol not in right_coverage.represented_named_symbols
        ),
    )
