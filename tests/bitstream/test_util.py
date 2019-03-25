import pytest

from vc2_conformance.bitstream._util import (
    indent,
    concat_strings,
    concat_labelled_strings,
    concat_tabular_strings,
    ensure_function,
    function_property,
    ordinal_indicator,
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
    (["ay", "bee", "cee"], "ay;bee;cee"),
    # Empty strings omitted
    ([""], ""),
    (["", "ay", "", "cee", ""], "ay;cee"),
    # Use newlines if any entry contains them
    (["ay\nbee"], "ay\nbee"),
    (["ay\nbee", "cee", "dee\nee"], "ay\nbee\ncee\ndee\nee"),
])
def test_concat_strings(strings, expected):
    assert concat_strings(strings, ";") == expected

@pytest.mark.parametrize("labelled_strings,expected", [
    # Empty
    ([], ""),
    # Simple strings
    ([("a", "foo")], "a: foo"),
    ([("a", "foo"), ("b", "bar")], "a: foo, b: bar"),
    # Some multiline strings
    ([("a", "f\no\no"), ("b", "bar")], "a:\n  f\n  o\n  o\nb:\n  bar"),
    # Some empty strings
    ([("a", "foo"), ("b", "bar"), ("c", "")], "a: foo, b: bar"),
    ([("a", "f\no\no"), ("b", "bar"), ("c", "")], "a:\n  f\n  o\n  o\nb:\n  bar"),
])
def test_concat_labelled_strings(labelled_strings, expected):
    assert concat_labelled_strings(labelled_strings) == expected

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
def test_concat_tabular_strings(tabular_strings, expected):
    assert concat_tabular_strings(tabular_strings) == expected

def test_ensure_function():
    assert ensure_function(lambda: 123)() == 123
    assert ensure_function(123)() == 123

def test_function_property():
    class MyClass(object):
        prop_1 = function_property()
        prop_2 = function_property()
    
    a = MyClass()
    
    # Assigning values should work
    a.prop_1 = 123
    a.prop_2 = 321
    assert a.prop_1 == 123
    assert a.prop_2 == 321
    
    # Assigning functions should work
    a.prop_1 = lambda: 1234
    a.prop_2 = lambda: 4321
    assert a.prop_1 == 1234
    assert a.prop_2 == 4321
    
    # Should be able to have multiple instances (with different values..)
    b = MyClass()
    b.prop_1 = 123
    b.prop_2 = 321
    assert a.prop_1 == 1234
    assert a.prop_2 == 4321
    assert b.prop_1 == 123
    assert b.prop_2 == 321
    
    # Should be able to delete
    del a.prop_1
    del a.prop_2
    assert not hasattr(a, "prop_1")
    assert not hasattr(a, "prop_2")
    
    # Accessing non-existant values should fail
    with pytest.raises(AttributeError):
        a.prop_1
    
    # Including not-yet assigned values
    c = MyClass()
    with pytest.raises(AttributeError):
        c.prop_1


@pytest.mark.parametrize("value,expected", [
    # First few numbers (including 'teens')
    (0, "th"),
    (1, "st"),
    (2, "nd"),
    (3, "rd"),
    (4, "th"),
    (5, "th"),
    (6, "th"),
    (7, "th"),
    (8, "th"),
    (9, "th"),
    (10, "th"),
    (11, "th"),
    (12, "th"),
    (13, "th"),
    (14, "th"),
    (15, "th"),
    (16, "th"),
    (17, "th"),
    (18, "th"),
    (19, "th"),
    (20, "th"),
    (21, "st"),
    (22, "nd"),
    (23, "rd"),
    (24, "th"),
    (25, "th"),
    
    # Check non-ths for other ordinals
    (20, "th"),
    (21, "st"),
    (22, "nd"),
    (23, "rd"),
    (24, "th"),
    
    # Hundreds
    (100, "th"),
    (101, "st"),
    (102, "nd"),
    (103, "rd"),
    (104, "th"),
    (105, "th"),
    (106, "th"),
    (107, "th"),
    (108, "th"),
    (109, "th"),
    (110, "th"),
    (111, "th"),
    (112, "th"),
    (113, "th"),
    (114, "th"),
    (115, "th"),
    (116, "th"),
    (117, "th"),
    (118, "th"),
    (119, "th"),
    (120, "th"),
    (121, "st"),
    (122, "nd"),
    (123, "rd"),
    (124, "th"),
    (125, "th"),
    
    # Much larger order of magnitude
    (12300, "th"),
    (12301, "st"),
    (12302, "nd"),
    (12303, "rd"),
    (12304, "th"),
    (12305, "th"),
    (12306, "th"),
    (12307, "th"),
    (12308, "th"),
    (12309, "th"),
    (12310, "th"),
    (12311, "th"),
    (12312, "th"),
    (12313, "th"),
    (12314, "th"),
    (12315, "th"),
    (12316, "th"),
    (12317, "th"),
    (12318, "th"),
    (12319, "th"),
    (12320, "th"),
    (12321, "st"),
    (12322, "nd"),
    (12323, "rd"),
    (12324, "th"),
    (12325, "th"),
])
def test_ordinal_indicator(value, expected):
    assert ordinal_indicator(value) == expected
