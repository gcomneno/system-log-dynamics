from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from system_log_dynamics.models import (
    NormalizedJournalEvent,
    RawJournalEvent,
)


def make_normalized_event(
    **overrides: object,
) -> NormalizedJournalEvent:
    values: dict[str, object] = {
        "sequence_index": 0,
        "source_line": 1,
        "boot_index": 0,
        "relative_realtime_us": 0,
        "monotonic_us": 1_000,
        "priority": 6,
        "message": "Synthetic service started.",
        "message_id": "synthetic-message",
        "transport": "journal",
        "systemd_unit": "synthetic.service",
        "syslog_identifier": "systemd",
    }
    values.update(overrides)
    return NormalizedJournalEvent(**values)  # type: ignore[arg-type]


def test_raw_event_copies_and_recursively_freezes_json() -> None:
    source = {
        "MESSAGE": "Synthetic event.",
        "NESTED": {
            "VALUES": [1, 2],
        },
    }

    event = RawJournalEvent(
        source_line=3,
        fields=source,
    )

    nested_source = cast(dict[str, object], source["NESTED"])
    values_source = cast(list[int], nested_source["VALUES"])
    values_source.append(3)
    nested_source["NEW"] = "changed"

    nested_event = cast(
        dict[str, object],
        event.fields["NESTED"],
    )

    assert event.fields["MESSAGE"] == "Synthetic event."
    assert nested_event["VALUES"] == (1, 2)
    assert "NEW" not in nested_event

    with pytest.raises(TypeError):
        event.fields["MESSAGE"] = "Mutation attempt."  # type: ignore[index]

    with pytest.raises(TypeError):
        nested_event["NEW"] = "Mutation attempt."


def test_raw_event_rejects_invalid_line_numbers() -> None:
    for value in (0, -1, True, 1.5):
        with pytest.raises(ValueError):
            RawJournalEvent(
                source_line=value,  # type: ignore[arg-type]
                fields={},
            )


def test_raw_event_rejects_non_string_field_keys() -> None:
    with pytest.raises(
        ValueError,
        match="only string keys",
    ):
        RawJournalEvent(
            source_line=1,
            fields={1: "invalid"},  # type: ignore[dict-item]
        )


def test_raw_event_rejects_non_json_values() -> None:
    with pytest.raises(
        ValueError,
        match="JSON-compatible",
    ):
        RawJournalEvent(
            source_line=1,
            fields={"VALUE": object()},
        )


def test_normalized_event_accepts_missing_optional_fields() -> None:
    event = make_normalized_event(
        boot_index=None,
        relative_realtime_us=None,
        monotonic_us=None,
        priority=None,
        message=None,
        message_id=None,
        transport=None,
        systemd_unit=None,
        syslog_identifier=None,
    )

    assert event.sequence_index == 0
    assert event.source_line == 1
    assert event.priority is None


def test_normalized_event_is_immutable() -> None:
    event = make_normalized_event()

    with pytest.raises(FrozenInstanceError):
        event.priority = 3  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sequence_index", -1),
        ("source_line", 0),
        ("boot_index", -1),
        ("relative_realtime_us", -1),
        ("monotonic_us", -1),
        ("priority", -1),
        ("priority", 8),
    ],
)
def test_normalized_event_rejects_out_of_range_numbers(
    field: str,
    value: int,
) -> None:
    with pytest.raises(ValueError):
        make_normalized_event(**{field: value})


@pytest.mark.parametrize(
    "field",
    [
        "sequence_index",
        "source_line",
        "boot_index",
        "relative_realtime_us",
        "monotonic_us",
        "priority",
    ],
)
def test_normalized_event_rejects_boolean_numeric_values(
    field: str,
) -> None:
    with pytest.raises(ValueError):
        make_normalized_event(**{field: True})


@pytest.mark.parametrize(
    "field",
    [
        "message",
        "message_id",
        "transport",
        "systemd_unit",
        "syslog_identifier",
    ],
)
def test_normalized_event_rejects_non_string_text_values(
    field: str,
) -> None:
    with pytest.raises(ValueError):
        make_normalized_event(**{field: 123})
