import pytest

from vc2_conformance.bitstream._util import (
    indent,
    concat_strings,
)


@pytest.mark.parametrize("string,expected", [
    # One line
    ("", "->"),
    ("foo", "->foo"),
    # Multi-line
    ("foo\nbar\nbaz", "->foo\n->bar\n->baz"),
    # Existing whitespace
    ("foo\n bar\n  baz", "->foo\n-> bar\n->  baz"),
    # Trailing newline/empty lines
    ("foo\n\nbar\n", "->foo\n->\n->bar\n->"),
])
def test_indent(string, expected):
    assert indent(string, "->") == expected

@pytest.mark.parametrize("strings,expected", [
    # Empty
    ([], ""),
    # Simple strings
    (["ay"], "ay"),
    (["ay", "bee", "cee"], "ay bee cee"),
    # Empty strings omitted
    ([""], ""),
    (["", "ay", "", "cee", ""], "ay cee"),
    # Use newlines if any entry contains them
    (["ay\nbee"], "ay\nbee"),
    (["ay\nbee", "cee", "dee\nee"], "ay\nbee\ncee\ndee\nee"),
])
def test_indent(strings, expected):
    assert concat_strings(strings) == expected
