import pytest

from system_log_dynamics.journal import (
    JournalParseError,
    iter_journal_json_lines,
)


def test_decoder_preserves_event_and_physical_line_order() -> None:
    lines = [
        '{"MESSAGE":"first","PRIORITY":"6"}\n',
        "\n",
        "   \t\n",
        '{"MESSAGE":"second","VALUES":[1,2,3]}\n',
    ]

    events = list(iter_journal_json_lines(lines))

    assert [event.source_line for event in events] == [1, 4]
    assert [event.fields["MESSAGE"] for event in events] == [
        "first",
        "second",
    ]
    assert events[1].fields["VALUES"] == (1, 2, 3)


def test_decoder_accepts_empty_input() -> None:
    assert list(iter_journal_json_lines([])) == []


def test_decoder_ignores_only_blank_lines() -> None:
    assert list(iter_journal_json_lines(["\n", " \t\r\n"])) == []


def test_decoder_reports_malformed_json_line_and_column() -> None:
    lines = [
        '{"MESSAGE":"valid"}\n',
        '{"MESSAGE": }\n',
    ]

    with pytest.raises(JournalParseError) as caught:
        list(iter_journal_json_lines(lines))

    assert caught.value.source_line == 2
    assert caught.value.detail.startswith("invalid JSON at column 13:")
    assert str(caught.value).startswith("line 2:")


@pytest.mark.parametrize(
    ("payload", "type_name"),
    [
        ("[]\n", "list"),
        ('"text"\n', "str"),
        ("42\n", "int"),
        ("true\n", "bool"),
        ("null\n", "NoneType"),
    ],
)
def test_decoder_rejects_non_object_json(
    payload: str,
    type_name: str,
) -> None:
    with pytest.raises(
        JournalParseError,
        match=rf"line 1: expected a JSON object, got {type_name}",
    ):
        list(iter_journal_json_lines([payload]))


def test_decoder_rejects_duplicate_keys_at_any_depth() -> None:
    payload = '{"MESSAGE":"valid","NESTED":{"VALUE":1,"VALUE":2}}\n'

    with pytest.raises(JournalParseError) as caught:
        list(iter_journal_json_lines([payload]))

    assert caught.value.source_line == 1
    assert caught.value.detail == ("duplicate JSON object key: 'VALUE'")


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_decoder_rejects_nonstandard_json_constants(
    constant: str,
) -> None:
    payload = f'{{"VALUE":{constant}}}\n'

    with pytest.raises(JournalParseError) as caught:
        list(iter_journal_json_lines([payload]))

    assert caught.value.detail == (f"invalid JSON constant: {constant}")


def test_decoder_rejects_non_text_input_line() -> None:
    with pytest.raises(
        JournalParseError,
        match="line 1: input line must be text",
    ):
        list(
            iter_journal_json_lines(  # type: ignore[arg-type]
                [b'{"MESSAGE":"bytes"}\n']
            )
        )
