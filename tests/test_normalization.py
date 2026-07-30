from pathlib import Path

import pytest

from system_log_dynamics.journal import (
    JournalNormalizationError,
    iter_normalized_events,
    iter_normalized_journal_json_lines,
)
from system_log_dynamics.models import RawJournalEvent


def raw_event(
    source_line: int = 1,
    **fields: object,
) -> RawJournalEvent:
    return RawJournalEvent(
        source_line=source_line,
        fields=fields,
    )


def test_normalizes_selected_fields_and_relative_time() -> None:
    events = [
        raw_event(
            __REALTIME_TIMESTAMP="1000000",
            __MONOTONIC_TIMESTAMP="100",
            _BOOT_ID="synthetic-a",
            PRIORITY="6",
            MESSAGE="Started.",
            MESSAGE_ID=None,
            _TRANSPORT="journal",
            _SYSTEMD_UNIT="synthetic.service",
            SYSLOG_IDENTIFIER="systemd",
        ),
        raw_event(
            source_line=2,
            __REALTIME_TIMESTAMP=1000250,
            __MONOTONIC_TIMESTAMP=350,
            _BOOT_ID="synthetic-a",
            PRIORITY=5,
            MESSAGE="Warning.",
        ),
    ]

    normalized = list(iter_normalized_events(events))

    assert [event.sequence_index for event in normalized] == [0, 1]
    assert [event.source_line for event in normalized] == [1, 2]
    assert [event.boot_index for event in normalized] == [0, 0]
    assert [event.relative_realtime_us for event in normalized] == [0, 250]
    assert [event.monotonic_us for event in normalized] == [
        100,
        350,
    ]
    assert [event.priority for event in normalized] == [6, 5]
    assert normalized[0].message == "Started."
    assert normalized[0].message_id is None
    assert normalized[0].systemd_unit == "synthetic.service"


def test_boot_indexes_follow_first_seen_order() -> None:
    events = [
        raw_event(_BOOT_ID="boot-b"),
        raw_event(source_line=2, _BOOT_ID="boot-a"),
        raw_event(source_line=3, _BOOT_ID="boot-b"),
        raw_event(source_line=4),
    ]

    normalized = list(iter_normalized_events(events))

    assert [event.boot_index for event in normalized] == [
        0,
        1,
        0,
        None,
    ]


def test_missing_and_null_fields_remain_none() -> None:
    events = [
        raw_event(),
        raw_event(
            source_line=2,
            __REALTIME_TIMESTAMP=None,
            __MONOTONIC_TIMESTAMP=None,
            _BOOT_ID=None,
            PRIORITY=None,
            MESSAGE=None,
        ),
    ]

    normalized = list(iter_normalized_events(events))

    for event in normalized:
        assert event.boot_index is None
        assert event.relative_realtime_us is None
        assert event.monotonic_us is None
        assert event.priority is None
        assert event.message is None


@pytest.mark.parametrize(
    "field",
    [
        "__REALTIME_TIMESTAMP",
        "__MONOTONIC_TIMESTAMP",
        "PRIORITY",
    ],
)
def test_boolean_numeric_fields_are_rejected(
    field: str,
) -> None:
    with pytest.raises(
        JournalNormalizationError,
        match=rf"line 7, field {field}: must not be a boolean",
    ):
        list(
            iter_normalized_events(
                [
                    RawJournalEvent(
                        source_line=7,
                        fields={field: True},
                    )
                ]
            )
        )


@pytest.mark.parametrize(
    "value",
    [
        "",
        " 100",
        "+100",
        "-1",
        "1.5",
        "\uff11\uff12",
        1.5,
        -1,
        [],
    ],
)
def test_invalid_realtime_values_are_rejected(
    value: object,
) -> None:
    with pytest.raises(JournalNormalizationError):
        list(
            iter_normalized_events(
                [
                    raw_event(
                        __REALTIME_TIMESTAMP=value,
                    )
                ]
            )
        )


@pytest.mark.parametrize(
    "value",
    ["8", "06", -1, 8, 1.5, [], {}],
)
def test_invalid_priorities_are_rejected(
    value: object,
) -> None:
    with pytest.raises(JournalNormalizationError):
        list(iter_normalized_events([raw_event(PRIORITY=value)]))


def test_realtime_must_not_decrease() -> None:
    events = [
        raw_event(__REALTIME_TIMESTAMP="200"),
        raw_event(
            source_line=2,
            __REALTIME_TIMESTAMP="199",
        ),
    ]

    with pytest.raises(
        JournalNormalizationError,
        match=(
            "line 2, field __REALTIME_TIMESTAMP: "
            "must not decrease across accepted events"
        ),
    ):
        list(iter_normalized_events(events))


def test_monotonic_must_not_decrease_within_same_boot() -> None:
    events = [
        raw_event(
            _BOOT_ID="synthetic-a",
            __MONOTONIC_TIMESTAMP="200",
        ),
        raw_event(
            source_line=2,
            _BOOT_ID="synthetic-a",
            __MONOTONIC_TIMESTAMP="199",
        ),
    ]

    with pytest.raises(
        JournalNormalizationError,
        match=(
            "line 2, field __MONOTONIC_TIMESTAMP: "
            "must not decrease within the same boot"
        ),
    ):
        list(iter_normalized_events(events))


def test_monotonic_may_restart_for_new_boot() -> None:
    events = [
        raw_event(
            _BOOT_ID="synthetic-a",
            __MONOTONIC_TIMESTAMP="200",
        ),
        raw_event(
            source_line=2,
            _BOOT_ID="synthetic-b",
            __MONOTONIC_TIMESTAMP="10",
        ),
    ]

    normalized = list(iter_normalized_events(events))

    assert [event.boot_index for event in normalized] == [0, 1]
    assert [event.monotonic_us for event in normalized] == [
        200,
        10,
    ]


@pytest.mark.parametrize(
    ("value", "diagnostic"),
    [
        (
            ["first", "second"],
            "repeated-value array representation is unsupported",
        ),
        (
            [255, 0, 10],
            "byte-array representation is unsupported",
        ),
        (
            {"nested": "value"},
            "must be a string or null",
        ),
        (
            42,
            "must be a string or null",
        ),
    ],
)
def test_unsupported_text_representations_are_rejected(
    value: object,
    diagnostic: str,
) -> None:
    event = raw_event(MESSAGE=value)

    with pytest.raises(
        JournalNormalizationError,
        match=diagnostic,
    ):
        list(iter_normalized_events([event]))


def test_empty_boot_identifier_is_rejected() -> None:
    with pytest.raises(
        JournalNormalizationError,
        match="field _BOOT_ID: must not be empty",
    ):
        list(iter_normalized_events([raw_event(_BOOT_ID="")]))


def test_synthetic_fixture_decodes_and_normalizes() -> None:
    fixture = (
        Path(__file__).parents[1] / "fixtures" / "synthetic" / "parser-valid.jsonl"
    )

    with fixture.open(encoding="utf-8") as stream:
        events = list(iter_normalized_journal_json_lines(stream))

    assert [event.sequence_index for event in events] == [0, 1, 2]
    assert [event.source_line for event in events] == [1, 3, 4]
    assert [event.boot_index for event in events] == [0, 0, 1]
    assert [event.relative_realtime_us for event in events] == [0, 500, 1_000]
    assert [event.monotonic_us for event in events] == [
        100,
        600,
        10,
    ]
    assert [event.priority for event in events] == [6, 5, 3]


def test_empty_stream_normalizes_to_no_events() -> None:
    assert list(iter_normalized_journal_json_lines([])) == []
