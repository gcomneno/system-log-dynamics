"""Deterministic descriptive temporal summaries for normalized journal events."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite
from statistics import fmean, median

from system_log_dynamics.models import NormalizedJournalEvent

__all__ = ["TemporalBurstSummary", "summarize_temporal_bursts"]


def _require_non_negative_integer(name: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")

    return value


def _require_positive_integer(name: str, value: object) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer")

    return value


def _require_optional_non_negative_integer(
    name: str,
    value: object,
) -> int | None:
    if value is None:
        return None

    return _require_non_negative_integer(name, value)


def _require_optional_finite_float(name: str, value: object) -> float | None:
    if value is None:
        return None

    if type(value) is not float or not isfinite(value):
        raise ValueError(f"{name} must be a finite float or None")

    return value


@dataclass(frozen=True, slots=True)
class TemporalBurstSummary:
    """Immutable descriptive timing and burst aggregates for one event stream."""

    event_count: int
    timed_event_count: int
    untimed_event_count: int
    duration_us: int | None
    inter_event_gap_count: int
    minimum_gap_us: int | None
    maximum_gap_us: int | None
    mean_gap_us: float | None
    median_gap_us: float | None
    burst_threshold_us: int
    burst_count: int
    burst_event_count: int
    largest_burst_size: int
    longest_burst_duration_us: int

    def __post_init__(self) -> None:
        event_count = _require_non_negative_integer(
            "event_count",
            self.event_count,
        )
        timed_event_count = _require_non_negative_integer(
            "timed_event_count",
            self.timed_event_count,
        )
        untimed_event_count = _require_non_negative_integer(
            "untimed_event_count",
            self.untimed_event_count,
        )
        duration_us = _require_optional_non_negative_integer(
            "duration_us",
            self.duration_us,
        )
        inter_event_gap_count = _require_non_negative_integer(
            "inter_event_gap_count",
            self.inter_event_gap_count,
        )
        minimum_gap_us = _require_optional_non_negative_integer(
            "minimum_gap_us",
            self.minimum_gap_us,
        )
        maximum_gap_us = _require_optional_non_negative_integer(
            "maximum_gap_us",
            self.maximum_gap_us,
        )
        mean_gap_us = _require_optional_finite_float(
            "mean_gap_us",
            self.mean_gap_us,
        )
        median_gap_us = _require_optional_finite_float(
            "median_gap_us",
            self.median_gap_us,
        )
        burst_threshold_us = _require_positive_integer(
            "burst_threshold_us",
            self.burst_threshold_us,
        )
        burst_count = _require_non_negative_integer("burst_count", self.burst_count)
        burst_event_count = _require_non_negative_integer(
            "burst_event_count",
            self.burst_event_count,
        )
        largest_burst_size = _require_non_negative_integer(
            "largest_burst_size",
            self.largest_burst_size,
        )
        longest_burst_duration_us = _require_non_negative_integer(
            "longest_burst_duration_us",
            self.longest_burst_duration_us,
        )

        if timed_event_count + untimed_event_count != event_count:
            raise ValueError(
                "timed_event_count plus untimed_event_count must equal event_count"
            )
        if timed_event_count == 0 and duration_us is not None:
            raise ValueError("duration_us requires at least one timed event")
        if timed_event_count == 1 and duration_us != 0:
            raise ValueError("one timed event requires a zero duration_us")

        if inter_event_gap_count > max(event_count - 1, 0):
            raise ValueError("inter_event_gap_count cannot exceed adjacent pairs")
        if inter_event_gap_count > max(timed_event_count - 1, 0):
            raise ValueError("inter_event_gap_count cannot exceed timed adjacent pairs")

        statistics = (
            minimum_gap_us,
            maximum_gap_us,
            mean_gap_us,
            median_gap_us,
        )
        if inter_event_gap_count == 0:
            if any(value is not None for value in statistics):
                raise ValueError("gap statistics must be None when no gaps exist")
        elif any(value is None for value in statistics):
            raise ValueError("gap statistics must exist when gaps exist")
        else:
            if not minimum_gap_us <= median_gap_us <= maximum_gap_us:
                raise ValueError("median_gap_us must lie between gap bounds")
            if not minimum_gap_us <= mean_gap_us <= maximum_gap_us:
                raise ValueError("mean_gap_us must lie between gap bounds")

        if burst_event_count > timed_event_count:
            raise ValueError("burst_event_count cannot exceed timed_event_count")

        if burst_count == 0:
            if (
                burst_event_count != 0
                or largest_burst_size != 0
                or longest_burst_duration_us != 0
            ):
                raise ValueError("zero bursts require zero burst aggregate fields")
            return

        if burst_event_count < 2 * burst_count:
            raise ValueError("each burst must contain at least two events")
        if largest_burst_size < 2 or largest_burst_size > burst_event_count:
            raise ValueError("largest_burst_size is inconsistent with burst events")
        if largest_burst_size > burst_event_count - 2 * (burst_count - 1):
            raise ValueError("largest_burst_size is inconsistent with burst_count")
        if largest_burst_size * burst_count < burst_event_count:
            raise ValueError("largest_burst_size is inconsistent with burst events")
        if burst_event_count - burst_count > inter_event_gap_count:
            raise ValueError("bursts require enough valid connecting gaps")
        if longest_burst_duration_us > burst_threshold_us * (largest_burst_size - 1):
            raise ValueError("longest_burst_duration_us is inconsistent with bursts")


def _is_timed(event: NormalizedJournalEvent) -> bool:
    return event.relative_realtime_us is not None or (
        event.boot_index is not None and event.monotonic_us is not None
    )


def _adjacent_gap_us(
    previous: tuple[int | None, int | None, int | None],
    current: tuple[int | None, int | None, int | None],
) -> int | None:
    previous_boot, previous_realtime, previous_monotonic = previous
    current_boot, current_realtime, current_monotonic = current

    if (
        previous_boot is not None
        and current_boot is not None
        and previous_boot != current_boot
    ):
        return None

    if previous_realtime is not None and current_realtime is not None:
        return current_realtime - previous_realtime

    if (
        previous_boot is not None
        and previous_boot == current_boot
        and previous_monotonic is not None
        and current_monotonic is not None
    ):
        return current_monotonic - previous_monotonic

    return None


def summarize_temporal_bursts(
    events: Iterable[NormalizedJournalEvent],
    *,
    burst_threshold_us: int,
) -> TemporalBurstSummary:
    """Summarize adjacent temporal gaps and dense bursts in one event stream."""

    _require_positive_integer("burst_threshold_us", burst_threshold_us)

    event_count = 0
    timed_event_count = 0
    gaps: list[int] = []
    previous_sequence_index: int | None = None
    previous_coordinates: tuple[int | None, int | None, int | None] | None = None
    first_realtime_us: int | None = None
    last_realtime_us: int | None = None
    first_monotonic_us: int | None = None
    last_monotonic_us: int | None = None
    monotonic_boot_indexes: set[int] = set()
    previous_realtime_us: int | None = None
    previous_monotonic_by_boot: dict[int, int] = {}
    burst_count = 0
    burst_event_count = 0
    largest_burst_size = 0
    longest_burst_duration_us = 0
    active_burst_size = 0
    active_burst_duration_us = 0

    def finish_burst() -> None:
        nonlocal burst_count
        nonlocal burst_event_count
        nonlocal largest_burst_size
        nonlocal longest_burst_duration_us
        nonlocal active_burst_size
        nonlocal active_burst_duration_us

        if active_burst_size == 0:
            return

        burst_count += 1
        burst_event_count += active_burst_size
        largest_burst_size = max(largest_burst_size, active_burst_size)
        longest_burst_duration_us = max(
            longest_burst_duration_us,
            active_burst_duration_us,
        )
        active_burst_size = 0
        active_burst_duration_us = 0

    for event in events:
        if type(event) is not NormalizedJournalEvent:
            raise ValueError(
                "events must contain only NormalizedJournalEvent instances"
            )

        if (
            previous_sequence_index is not None
            and event.sequence_index <= previous_sequence_index
        ):
            raise ValueError("sequence_index values must strictly increase")

        if (
            previous_realtime_us is not None
            and event.relative_realtime_us is not None
            and event.relative_realtime_us < previous_realtime_us
        ):
            raise ValueError("relative_realtime_us values must not decrease")

        if event.boot_index is not None and event.monotonic_us is not None:
            previous_monotonic_us = previous_monotonic_by_boot.get(event.boot_index)
            if (
                previous_monotonic_us is not None
                and event.monotonic_us < previous_monotonic_us
            ):
                raise ValueError(
                    "monotonic_us values must not decrease within the same boot_index"
                )
            previous_monotonic_by_boot[event.boot_index] = event.monotonic_us

        event_count += 1
        timed_event_count += _is_timed(event)
        previous_sequence_index = event.sequence_index

        if event.relative_realtime_us is not None:
            if first_realtime_us is None:
                first_realtime_us = event.relative_realtime_us
            last_realtime_us = event.relative_realtime_us
            previous_realtime_us = event.relative_realtime_us

        if event.boot_index is not None and event.monotonic_us is not None:
            monotonic_boot_indexes.add(event.boot_index)
            if first_monotonic_us is None:
                first_monotonic_us = event.monotonic_us
            last_monotonic_us = event.monotonic_us

        current_coordinates = (
            event.boot_index,
            event.relative_realtime_us,
            event.monotonic_us,
        )
        if previous_coordinates is not None:
            gap_us = _adjacent_gap_us(previous_coordinates, current_coordinates)
            if gap_us is None:
                finish_burst()
            else:
                gaps.append(gap_us)
                if gap_us > burst_threshold_us:
                    finish_burst()
                else:
                    if active_burst_size == 0:
                        active_burst_size = 2
                        active_burst_duration_us = gap_us
                    else:
                        active_burst_size += 1
                        active_burst_duration_us += gap_us

        previous_coordinates = current_coordinates

    finish_burst()

    if first_realtime_us is not None:
        duration_us: int | None = last_realtime_us - first_realtime_us
    elif len(monotonic_boot_indexes) == 1:
        duration_us = last_monotonic_us - first_monotonic_us
    else:
        duration_us = None

    if gaps:
        minimum_gap_us: int | None = min(gaps)
        maximum_gap_us: int | None = max(gaps)
        mean_gap_us: float | None = fmean(gaps)
        median_gap_us: float | None = float(median(gaps))
    else:
        minimum_gap_us = None
        maximum_gap_us = None
        mean_gap_us = None
        median_gap_us = None

    return TemporalBurstSummary(
        event_count=event_count,
        timed_event_count=timed_event_count,
        untimed_event_count=event_count - timed_event_count,
        duration_us=duration_us,
        inter_event_gap_count=len(gaps),
        minimum_gap_us=minimum_gap_us,
        maximum_gap_us=maximum_gap_us,
        mean_gap_us=mean_gap_us,
        median_gap_us=median_gap_us,
        burst_threshold_us=burst_threshold_us,
        burst_count=burst_count,
        burst_event_count=burst_event_count,
        largest_burst_size=largest_burst_size,
        longest_burst_duration_us=longest_burst_duration_us,
    )
