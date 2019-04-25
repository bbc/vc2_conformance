import pytest

from vc2_conformance._string_utils import (
    indent,
    ellipsise,
    ellipsise_lossy,
    table,
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


@pytest.mark.parametrize("string,expected", [
    # Empty string
    ("", ""),
    # Strings too short for replacement
    ("foo", "foo"),
    ("000000000000000", "000000000000000"),
    # String of minimum length for replacement but with too few characters
    # matching
    ("0123456789ABCDEF", "0123456789ABCDEF"),
    ("CCCCMMMMMMMMCCCC", "CCCCMMMMMMMMCCCC"),
    ("Fooooooooooooooo", "Fooooooooooooooo"),
    ("oooooooooooooooF", "oooooooooooooooF"),
    ("ooooooooFooooooo", "ooooooooFooooooo"),
    # Minimum-length for replacement
    ("0000000000000000", "0000...0000"),
    ("before0000000000000000after", "before0000...0000after"),
    # Longer strings should be shortened more!
    ("0b1000000000000000000000000000000001", "0b10000...00001"),
])
def test_ellipsise(string, expected):
    assert ellipsise(string) == expected

@pytest.mark.parametrize("string,max_length,expected", [
    # Empty string
    ("", 0, ""),
    ("", 5, ""),
    # Short-enough string
    ("hi", 5, "hi"),
    ("hello", 5, "hello"),
    # Truncate (odd length)
    ("hello world", 5, "h...d"),
    ("hello world", 9, "hel...rld"),
    # Truncate (even length)
    ("hello world", 6, "h...ld"),
    ("hello world", 10, "hel...orld"),
])
def test_ellipsise_lossy(string, max_length, expected):
    assert ellipsise_lossy(string, max_length) == expected


@pytest.mark.parametrize("tabular_strings,expected", [
    # Empty
    ([], ""),
    # Single line
    ([["foo"]], "foo"),
    ([["foo", "x"]], "foo  x"),
    # Multiple lines
    ([["foo"], ["x"]], "foo\n  x"),
    ([["foo", "x"], ["y", "1234"]], "foo     x\n  y  1234"),
    # Different numbers of values on each row
    ([["foo"], ["y", "1234"]], "foo\n  y  1234"),
    # Multi-line values
    ([["foo\nbar"]], "(y=0, x=0):\n  foo\n  bar"),
    (
        [["foo\nbar", "baz\nqux"], ["quo\nqak"]],
        (
            "(y=0, x=0):\n  foo\n  bar\n"
            "(y=0, x=1):\n  baz\n  qux\n"
            "(y=1, x=0):\n  quo\n  qak"
        ),
    ),
])
def test_table(tabular_strings, expected):
    assert table(tabular_strings) == expected
