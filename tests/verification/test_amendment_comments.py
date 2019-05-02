import pytest

import tokenize

from verification.amendment_comments import *


def test_empty():
    assert undo_amendments("") == ("", {})


def test_no_amendment_comments():
    source, indent_corrections = undo_amendments(
        "# Some code\n"
        "a = b + c\n"
    )
    
    assert source == (
        "# Some code\n"
        "a = b + c\n"
    )
    assert indent_corrections == {}


def test_disabled_code():
    source, indent_corrections = undo_amendments(
        "# Some code\n"
        "a = b + c\n"
        "### with disabled_code()\n"
        "###     a += 1\n"
        "    ### a -= 1\n"
        "a += 1\n"
    )
    
    assert source == (
        "# Some code\n"
        "a = b + c\n"
        "with disabled_code()\n"
        "    a += 1\n"
        "    a -= 1\n"
        "a += 1\n"
    )
    assert indent_corrections == {
        3: 4,
        4: 4,
        5: 4,
    }


def test_not_in_spec_line():
    source, indent_corrections = undo_amendments(
        "# Some code\n"
        "a = 1\n"
        "with foo():  ## Not in spec\n"
        "    foobar()  ##not  in SPEC  at all!\n"
        "b = 2\n"
    )
    
    assert source == (
        "# Some code\n"
        "a = 1\n"
        "# with foo():  ## Not in spec\n"
        "#     foobar()  ##not  in SPEC  at all!\n"
        "b = 2\n"
    )
    assert indent_corrections == {}


def test_not_in_spec_block():
    source, indent_corrections = undo_amendments(
        "# Some code\n"
        "a = 1\n"
        "## Begin not in spec\n"
        "with foo():\n"
        "    foobar()\n"
        "    ##  end  NOT  in  spec at all either!\n"
        "b = 2\n"
    )
    
    assert source == (
        "# Some code\n"
        "a = 1\n"
        "# ## Begin not in spec\n"
        "# with foo():\n"
        "#     foobar()\n"
        "#     ##  end  NOT  in  spec at all either!\n"
        "b = 2\n"
    )
    assert indent_corrections == {}


def test_single_hashes_dont_cause_changes():
    source, indent_corrections = undo_amendments(
        "# Some code\n"
        "a = 1  # Not in spec\n"
        "# Begin not in spec\n"
        "with foo():\n"
        "    foobar()\n"
        "# End not in spec\n"
        "b = 2\n"
    )
    
    assert source == (
        "# Some code\n"
        "a = 1  # Not in spec\n"
        "# Begin not in spec\n"
        "with foo():\n"
        "    foobar()\n"
        "# End not in spec\n"
        "b = 2\n"
    )
    assert indent_corrections == {}


def test_bad_tokenization():
    with pytest.raises(tokenize.TokenError):
        undo_amendments("'''")


def test_bad_amendment_comment():
    with pytest.raises(BadAmendmentCommentError):
        undo_amendments("## Not a valid one...")
    
    with pytest.raises(BadAmendmentCommentError):
        undo_amendments("###Space after hashes is required")


def test_unmatched_not_in_spec_block():
    with pytest.raises(UnmatchedNotInSpecBlockError):
        undo_amendments("## End not in spec")


def test_unclosed_not_in_spec_block():
    with pytest.raises(UnclosedNotInSpecBlockError):
        undo_amendments("## Begin not in spec")
