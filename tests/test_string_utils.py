import pytest

from vc2_conformance._string_utils import (
    indent,
    ellipsise,
    ellipsise_lossy,
    table,
    split_into_line_wrap_blocks,
    wrap_blocks,
    wrap_paragraphs,
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


class TestSplitIntoLineWrapBlocks(object):
    
    def test_empty(self):
        assert split_into_line_wrap_blocks("") == []
    
    def test_simple_string(self):
        assert split_into_line_wrap_blocks("foo bar") == [("", "", "foo bar")]
    
    def test_removes_common_indentation_and_excess_newlines(self):
        assert split_into_line_wrap_blocks("""
            
            Foo, bar.
            
            Baz.
            
            
            Qux!
            
        """) == [
            ("", "", "Foo, bar."),
            ("", "", ""),
            ("", "", "Baz."),
            ("", "", ""),
            ("", "", "Qux!"),
        ]
    
    def test_combines_hard_wrapped_lines(self):
        assert split_into_line_wrap_blocks("""
            Foo, bar,
            baz.
            
            Qux,
            quo,
            qac!
        """) == [
            ("", "", "Foo, bar, baz."),
            ("", "", ""),
            ("", "", "Qux, quo, qac!"),
        ]
    
    def test_markdown_style_titles(self):
        assert split_into_line_wrap_blocks("""
            A heading
            =========
            
            A subheading
            ------------
            
            ==== Not an underline!
            ---- Not an underline!
        """) == [
            ("", "", "A heading"),
            ("", "", "========="),
            ("", "", ""),
            ("", "", "A subheading"),
            ("", "", "------------"),
            ("", "", ""),
            ("", "", "==== Not an underline! ---- Not an underline!"),
        ]
    
    def test_bullets(self):
        assert split_into_line_wrap_blocks("""
            Bullets:
            
            * Foo
            * Bar,
              baz.
            * Qux.
            
            The end.
        """) == [
            ("", "", "Bullets:"),
            ("", "", ""),
            ("* ", "  ", "Foo"),
            ("* ", "  ", "Bar, baz."),
            ("* ", "  ", "Qux."),
            ("", "", ""),
            ("", "", "The end."),
        ]
    
    def test_numbers(self):
        assert split_into_line_wrap_blocks("""
            Numbered:
            
            1. Foo
            2. Bar,
               baz.
            100. Qux.
            
            The end.
        """) == [
            ("", "", "Numbered:"),
            ("", "", ""),
            ("1. ", "   ", "Foo"),
            ("2. ", "   ", "Bar, baz."),
            ("100. ", "     ", "Qux."),
            ("", "", ""),
            ("", "", "The end."),
        ]
    
    def test_intented_block_wrap_indented_blocks(self):
        assert split_into_line_wrap_blocks("""
            Indentation time:
            
                Indented block.
                
                A second
                one.
            
            The end.
        """, wrap_indented_blocks=True) == [
            ("", "", "Indentation time:"),
            ("", "", ""),
            ("    ", "    ", "Indented block."),
            ("", "", ""),
            ("    ", "    ", "A second one."),
            ("", "", ""),
            ("", "", "The end."),
        ]
    
    def test_intented_block_no_wrap_indented_blocks(self):
        assert split_into_line_wrap_blocks("""
            Indentation time:
            
                Indented block.
                
                A second
                one.
            
            The end.
        """, wrap_indented_blocks=False) == [
            ("", "", "Indentation time:"),
            ("", "", ""),
            ("    ", "    ", "Indented block."),
            ("", "", ""),
            ("    ", "    ", "A second"),
            ("    ", "    ", "one."),
            ("", "", ""),
            ("", "", "The end."),
        ]

class TestWrapBlocks(object):

    def test_empty(self):
        assert wrap_blocks([]) == ""
    
    def test_no_wrapping(self):
        assert wrap_blocks([
            ("", "", "A quick"),
            ("", "", ""),
            ("* ", "  ", "Test"),
        ], 40) == (
            "A quick\n"
            "\n"
            "* Test"
        )

    def test_wrapping(self):
        assert wrap_blocks([
            ("", "", "No need to wrap me."),
            ("", "", ""),
            ("", "", ("Wrap me. "*10).strip()),
            ("", "", ""),
            ("* ", "  ", "Bullet point me."),
            ("* ", "  ", ("Wrapped bullet point me. " * 3).strip()),
        ], 40) == (
            #| -------------- 40 chars ------------ |
            "No need to wrap me.\n"
            "\n"
            "Wrap me. Wrap me. Wrap me. Wrap me. Wrap\n"
            "me. Wrap me. Wrap me. Wrap me. Wrap me.\n"
            "Wrap me.\n"
            "\n"
            "* Bullet point me.\n"
            "* Wrapped bullet point me. Wrapped\n"
            "  bullet point me. Wrapped bullet point\n"
            "  me."
        )

    def test_no_wrap_indent_blocks(self):
        assert wrap_blocks([
            ("  ", "  ", ("Don't wrap me. "*4).strip()),
        ], 40, wrap_indented_blocks=False) == (
            #| -------------- 40 chars ------------ |
            "  Don't wrap me. Don't wrap me. Don't wrap me. Don't wrap me."
        )
    
    def test_wrap_indent_blocks(self):
        assert wrap_blocks([
            ("  ", "  ", ("Do wrap me. "*5).strip()),
        ], 40, wrap_indented_blocks=True) == (
            #| -------------- 40 chars ------------ |
            "  Do wrap me. Do wrap me. Do wrap me. Do\n"
            "  wrap me. Do wrap me."
        )


def test_wrap_paragraphs():
    assert wrap_paragraphs("""
        Markdown style title
        ====================
        
        Hello there, this is some text with some hard line wrapping in it. All
        of the key functionality is tested elsewhere.
        
        This is a:
        
        * Sanity check that everything seems to work when put together.
        * A demo...
        
        With some numbered items:
        
        1. One
        2. Two
        3. Three is the longest of the numbers I've been looking at.
        
        Some code
        ---------
        
            int main(int argc, const char *argv) {
                return 0;
            }
    """, 20) == (
        #|---- 20 chars ----|
        "Markdown style title\n"
        "====================\n"
        "\n"
        "Hello there, this is\n"
        "some text with some\n"
        "hard line wrapping\n"
        "in it. All of the\n"
        "key functionality is\n"
        "tested elsewhere.\n"
        "\n"
        "This is a:\n"
        "\n"
        "* Sanity check that\n"
        "  everything seems\n"
        "  to work when put\n"
        "  together.\n"
        "* A demo...\n"
        "\n"
        "With some numbered\n"
        "items:\n"
        "\n"
        "1. One\n"
        "2. Two\n"
        "3. Three is the\n"
        "   longest of the\n"
        "   numbers I've been\n"
        "   looking at.\n"
        "\n"
        "Some code\n"
        "---------\n"
        "\n"
        "    int main(int argc, const char *argv) {\n"
        "        return 0;\n"
        "    }"
    )
