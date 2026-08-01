from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace

import pytest

import system_log_dynamics.temporal as temporal_module
from system_log_dynamics.models import NormalizedJournalEvent
from system_log_dynamics.temporal import (
    TemporalBurstSummary,
    summarize_temporal_bursts,
)


def event(
    sequence_index: int,
    *,
    boot_index: int | None = None,
    realtime_us: int | None = None,
    monotonic_us: int | None = None,
    message: str | None = "synthetic message",
) -> NormalizedJournalEvent:
    return NormalizedJournalEvent(
        sequence_index=sequence_index,
        source_line=sequence_index + 1,
        boot_index=boot_index,
        relative_realtime_us=realtime_us,
        monotonic_us=monotonic_us,
        priority=None,
        message=message,
        message_id="synthetic-message-id",
        transport="journal",
        systemd_unit="synthetic.service",
        syslog_identifier="synthetic",
    )


def empty_summary(**changes: object) -> TemporalBurstSummary:
    values: dict[str, object] = {
        "event_count": 0,
        "timed_event_count": 0,
        "untimed_event_count": 0,
        "duration_us": None,
        "inter_event_gap_count": 0,
        "minimum_gap_us": None,
        "maximum_gap_us": None,
        "mean_gap_us": None,
        "median_gap_us": None,
        "burst_threshold_us": 10,
        "burst_count": 0,
        "burst_event_count": 0,
        "largest_burst_size": 0,
        "longest_burst_duration_us": 0,
    }
    values.update(changes)
    return TemporalBurstSummary(**values)  # type: ignore[arg-type]


def test_public_exports_and_field_order() -> None:
    assert temporal_module.__all__ == [
        "TemporalBurstSummary",
        "summarize_temporal_bursts",
    ]
    assert [field.name for field in fields(TemporalBurstSummary)] == [
        "event_count",
        "timed_event_count",
        "untimed_event_count",
        "duration_us",
        "inter_event_gap_count",
        "minimum_gap_us",
        "maximum_gap_us",
        "mean_gap_us",
        "median_gap_us",
        "burst_threshold_us",
        "burst_count",
        "burst_event_count",
        "largest_burst_size",
        "longest_burst_duration_us",
    ]


def test_summary_is_frozen_and_slotted() -> None:
    summary = empty_summary()

    assert hasattr(TemporalBurstSummary, "__slots__")
    assert not hasattr(summary, "__dict__")
    with pytest.raises(FrozenInstanceError):
        summary.event_count = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    "changes",
    [
        {"event_count": True},
        {"duration_us": -1},
        {"burst_threshold_us": 0},
        {"timed_event_count": 1},
        {"duration_us": 0},
        {"event_count": 1, "timed_event_count": 1, "duration_us": None},
        {"inter_event_gap_count": 1},
        {
            "event_count": 2,
            "timed_event_count": 2,
            "inter_event_gap_count": 1,
            "minimum_gap_us": 4,
            "maximum_gap_us": 3,
            "mean_gap_us": 3.0,
            "median_gap_us": 3.0,
        },
        {"burst_count": 1, "burst_event_count": 1, "largest_burst_size": 1},
        {"burst_event_count": 1},
    ],
)
def test_manual_summary_construction_rejects_invariant_failures(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        empty_summary(**changes)


def test_dataclasses_replace_revalidates_summary_invariants() -> None:
    with pytest.raises(ValueError):
        replace(
            empty_summary(), burst_count=1, burst_event_count=2, largest_burst_size=2
        )


@pytest.mark.parametrize(
    "threshold",
    [0, -1, True, 1.5, "10", None, object()],
)
def test_invalid_burst_thresholds_are_rejected_before_consumption(
    threshold: object,
) -> None:
    consumed = False

    def stream() -> object:
        nonlocal consumed
        consumed = True
        yield event(0)

    with pytest.raises(ValueError, match="burst_threshold_us"):
        summarize_temporal_bursts(
            stream(),  # type: ignore[arg-type]
            burst_threshold_us=threshold,  # type: ignore[arg-type]
        )

    assert not consumed


def test_empty_input() -> None:
    assert summarize_temporal_bursts([], burst_threshold_us=10) == empty_summary()


@pytest.mark.parametrize(
    "events, expected_duration",
    [([event(3, realtime_us=7)], 0), ([event(3, boot_index=1, monotonic_us=7)], 0)],
)
def test_one_timed_event_has_zero_duration(
    events: list[NormalizedJournalEvent],
    expected_duration: int,
) -> None:
    summary = summarize_temporal_bursts(events, burst_threshold_us=10)

    assert summary.event_count == 1
    assert summary.timed_event_count == 1
    assert summary.untimed_event_count == 0
    assert summary.duration_us == expected_duration
    assert summary.inter_event_gap_count == 0


def test_all_untimed_events_and_monotonic_without_boot_are_untimed() -> None:
    summary = summarize_temporal_bursts(
        [event(0), event(1, monotonic_us=10), event(2)],
        burst_threshold_us=10,
    )

    assert summary.event_count == 3
    assert summary.timed_event_count == 0
    assert summary.untimed_event_count == 3
    assert summary.duration_us is None
    assert summary.inter_event_gap_count == 0


def test_uniform_realtime_gaps_and_statistics() -> None:
    summary = summarize_temporal_bursts(
        [event(index, realtime_us=index * 10) for index in range(4)],
        burst_threshold_us=10,
    )

    assert summary.duration_us == 30
    assert summary.inter_event_gap_count == 3
    assert (summary.minimum_gap_us, summary.maximum_gap_us) == (10, 10)
    assert (summary.mean_gap_us, summary.median_gap_us) == (10.0, 10.0)
    assert (summary.burst_count, summary.burst_event_count) == (1, 4)
    assert (summary.largest_burst_size, summary.longest_burst_duration_us) == (4, 30)


def test_same_boot_monotonic_fallback_and_realtime_preference() -> None:
    fallback = summarize_temporal_bursts(
        [
            event(0, boot_index=2, monotonic_us=10),
            event(1, boot_index=2, monotonic_us=16),
        ],
        burst_threshold_us=10,
    )
    preferred = summarize_temporal_bursts(
        [
            event(0, boot_index=2, realtime_us=100, monotonic_us=10),
            event(1, boot_index=2, realtime_us=103, monotonic_us=99),
        ],
        burst_threshold_us=5,
    )

    assert (fallback.inter_event_gap_count, fallback.duration_us) == (1, 6)
    assert fallback.longest_burst_duration_us == 6
    assert (preferred.minimum_gap_us, preferred.duration_us) == (3, 3)
    assert preferred.longest_burst_duration_us == 3


def test_equal_timestamps_are_valid_zero_gaps_at_threshold_equality() -> None:
    summary = summarize_temporal_bursts(
        [event(0, realtime_us=5), event(1, realtime_us=5), event(2, realtime_us=8)],
        burst_threshold_us=3,
    )

    assert (summary.minimum_gap_us, summary.maximum_gap_us) == (0, 3)
    assert (summary.mean_gap_us, summary.median_gap_us) == (1.5, 1.5)
    assert (summary.burst_count, summary.burst_event_count) == (1, 3)
    assert summary.longest_burst_duration_us == 3


def test_isolated_and_multiple_separated_bursts() -> None:
    isolated = summarize_temporal_bursts(
        [event(0, realtime_us=0), event(1, realtime_us=2), event(2, realtime_us=20)],
        burst_threshold_us=2,
    )
    multiple = summarize_temporal_bursts(
        [
            event(0, realtime_us=0),
            event(1, realtime_us=1),
            event(2, realtime_us=20),
            event(3, realtime_us=21),
            event(4, realtime_us=22),
        ],
        burst_threshold_us=1,
    )

    assert (isolated.burst_count, isolated.burst_event_count) == (1, 2)
    assert isolated.longest_burst_duration_us == 2
    assert (multiple.burst_count, multiple.burst_event_count) == (2, 5)
    assert (multiple.largest_burst_size, multiple.longest_burst_duration_us) == (3, 2)


def test_large_missing_and_boot_boundary_gaps_terminate_without_bridging() -> None:
    large = summarize_temporal_bursts(
        [event(0, realtime_us=0), event(1, realtime_us=1), event(2, realtime_us=20)],
        burst_threshold_us=1,
    )
    missing = summarize_temporal_bursts(
        [
            event(0, realtime_us=0),
            event(1),
            event(2, realtime_us=1),
            event(3, realtime_us=2),
        ],
        burst_threshold_us=2,
    )
    boot_boundary = summarize_temporal_bursts(
        [
            event(0, boot_index=0, realtime_us=0),
            event(1, boot_index=0, realtime_us=1),
            event(2, boot_index=1, realtime_us=2),
            event(3, boot_index=1, realtime_us=3),
        ],
        burst_threshold_us=2,
    )

    assert (large.inter_event_gap_count, large.burst_event_count) == (2, 2)
    assert (missing.inter_event_gap_count, missing.burst_event_count) == (1, 2)
    assert (boot_boundary.inter_event_gap_count, boot_boundary.burst_event_count) == (
        2,
        4,
    )
    assert boot_boundary.burst_count == 2


def test_duration_policy_across_and_without_boots() -> None:
    realtime_across_boots = summarize_temporal_bursts(
        [
            event(0, boot_index=0, realtime_us=10),
            event(1, boot_index=1, realtime_us=30),
        ],
        burst_threshold_us=10,
    )
    monotonic_one_boot = summarize_temporal_bursts(
        [
            event(0, boot_index=4, monotonic_us=10),
            event(1, boot_index=4, monotonic_us=25),
        ],
        burst_threshold_us=10,
    )
    multiple_boots = summarize_temporal_bursts(
        [
            event(0, boot_index=0, monotonic_us=10),
            event(1, boot_index=1, monotonic_us=2),
        ],
        burst_threshold_us=10,
    )

    assert realtime_across_boots.duration_us == 20
    assert monotonic_one_boot.duration_us == 15
    assert multiple_boots.duration_us is None


@pytest.mark.parametrize(
    "events, pattern",
    [
        ([event(0, realtime_us=2), event(1, realtime_us=1)], "relative_realtime_us"),
        (
            [
                event(0, boot_index=1, monotonic_us=2),
                event(1, boot_index=1, monotonic_us=1),
            ],
            "monotonic_us",
        ),
        ([event(0), event(0)], "sequence_index"),
    ],
)
def test_stream_invariant_violations_are_rejected(
    events: list[NormalizedJournalEvent],
    pattern: str,
) -> None:
    with pytest.raises(ValueError, match=pattern):
        summarize_temporal_bursts(events, burst_threshold_us=10)


def test_monotonic_restart_is_accepted_for_new_boot() -> None:
    summary = summarize_temporal_bursts(
        [
            event(0, boot_index=0, monotonic_us=100),
            event(1, boot_index=1, monotonic_us=1),
        ],
        burst_threshold_us=10,
    )

    assert summary.timed_event_count == 2
    assert summary.duration_us is None
    assert summary.inter_event_gap_count == 0


def test_invalid_event_type_stops_at_first_invalid_item() -> None:
    consumed: list[int] = []

    def stream() -> object:
        consumed.append(0)
        yield event(0)
        consumed.append(1)
        yield object()
        consumed.append(2)
        yield event(2)

    with pytest.raises(ValueError, match="NormalizedJournalEvent"):
        summarize_temporal_bursts(stream(), burst_threshold_us=10)  # type: ignore[arg-type]

    assert consumed == [0, 1]


def test_input_events_are_unchanged_and_execution_is_deterministic() -> None:
    events = [
        event(0, boot_index=0, realtime_us=10, monotonic_us=5, message="private"),
        event(1, boot_index=0, realtime_us=13, monotonic_us=8, message="secret"),
    ]
    before = tuple(events)

    first = summarize_temporal_bursts(events, burst_threshold_us=3)
    second = summarize_temporal_bursts(iter(events), burst_threshold_us=3)

    assert events == list(before)
    assert first == second
    rendered = repr(first)
    for forbidden in ("private", "secret", "source_line", "boot_index"):
        assert forbidden not in rendered
