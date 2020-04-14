"""
:py:mod:`verification.amendment_comments`
=========================================

.. py:currentmodule:: verification.amendment_comments

In  the :py:mod:`vc2_conformance` module it is sometimes necessary to make
amendments to the pseudocode. For example, validity checks may be added or
unneeded steps removed (such as performing a wavelet transform while simply
deserialising a bitstream).

To make changes made to a VC-2 function implementations explicit, the following
conventions are used:

* When code present in the spec is removed or disabled, it is commented out
  using triple-hash comments like so::

        def example_1(a, b):
            # Code as-per the VC-2 spec
            c = a + b

            # No need to actually perform wavelet transform
            ### if c > 1:
            ###     wavelet_transform()
            ###     display_picture()

            # More code per the spec
            return c

* When code is added, it should be indicated using either a ``## Not in spec``
  double-hash comment::

        def example_2(a, b):
            assert b > 0  ## Not in spec

            return a / b

  Or within a ``## Begin not in spec``, ``## End not in spec`` block::

        def example_2(a, b):
            ## Begin not in spec
            if b < 0:
                raise Exception("Negative 'b' not allowed")
            elif b == 0:
                raise Exception("Can't divide by 'b' when it is 0")
            ## End not in spec

            return a / b

To enable the automated verification that implemented functions match the VC-2
spec (e.g. using :py:mod:`verification.comparators`), any amendments to the
code must first be undone. The :py:func:`undo_amendments` function may be used
to performs this step.

.. autofunction:: undo_amendments

The following exception custom exception types are defined:

.. autoexception:: BadAmendmentCommentError

.. autoexception:: UnmatchedNotInSpecBlockError

.. autoexception:: UnclosedNotInSpecBlockError

"""

import re

from tokenize import COMMENT

try:
    # Python 2.x
    from tokenize import generate_tokens as tokenize
except ImportError:
    # Python 3.x
    from tokenize import tokens

from functools import partial

__all__ = [
    "undo_amendments",
    "BadAmendmentCommentError",
    "UnmatchedNotInSpecBlockError",
    "UnclosedNotInSpecBlockError",
]


class BadAmendmentCommentError(Exception):
    """
    An unrecognised amendment comment (a comment with two or more hashes) was
    found.

    Attributes
    ==========
    comment : str
        The contents of the comment
    row, col : int
        The position in the source where the unrecognised comment starts
    """

    def __init__(self, comment, row, col):
        self.comment = comment
        self.row = row
        self.col = col

        super(BadAmendmentCommentError, self).__init__(
            "{!r} at line {}, col {}".format(comment, row, col),
        )


class UnmatchedNotInSpecBlockError(Exception):
    """
    An 'End not in spec' amendment comment block was encountered without a
    corresponding 'Begin not in spec' block.

    Attributes
    ==========
    row : int
        The line in the source where the 'end' comment was encounterd
    """

    def __init__(self, row):
        self.row = row

        super(UnmatchedNotInSpecBlockError, self).__init__("line {}".format(row),)


class UnclosedNotInSpecBlockError(Exception):
    """
    A 'Begin not in spec' amendment comment block was not closed.

    Attributes
    ==========
    row : int
        The line in the source where the block was started.
    """

    def __init__(self, row):
        self.row = row

        super(UnclosedNotInSpecBlockError, self).__init__("line {}".format(row),)


_RE_DISABLED_COMMENT = re.compile(r"^###(| .*)$")
_RE_LINE_NOT_IN_SPEC_COMMENT = re.compile(r"^##\s*Not\s+in\s+spec", re.IGNORECASE)
_RE_BEGIN_NOT_IN_SPEC_COMMENT = re.compile(
    r"^##\s*Begin\s+not\s+in\s+spec", re.IGNORECASE
)
_RE_END_NOT_IN_SPEC_COMMENT = re.compile(r"^##\s*End\s+not\s+in\s+spec", re.IGNORECASE)


def undo_amendments(source):
    """
    Given a Python source snippet, undo all amendments marked by special
    'amendment comments' (comments starting with ``##`` and ``###``).

    The following actions will be taken:

    * Disabled code prefixed ``### ...`` (three hashes and a space) will be
      uncommented.
    * Lines ending with a ``## Not in spec`` comment will be commented out.
    * Blocks of code starting with a ``## Begin not in spec`` line and ending
      with a ``## End not in spec`` line will be commented out.

    Returns
    =======
    (source, indent_corrections)
        The modified source is returned along with a dictionary mapping line
        number to an indentation correction. These corrections may be used to
        map column numbers in the new source to column numbers in the old
        source.

    Raises
    ======
    :py:exc:`tokenize.TokenError`
    :py:exc:`BadAmendmentCommentError`
    :py:exc:`UnmatchedNotInSpecBlockError`
    :py:exc:`UnclosedNotInSpecBlockError`
    """
    # Will be mutated as required
    source_lines = source.splitlines(True)

    indent_corrections = {}  # {row: offset, ...}

    # Disabled lines, to be uncommented.
    disabled_lines = []  # [(row, col, prefix_length), ...]

    # Not-in-spec blocks ranges (begin/end comment lines given) to be 'passed
    # out'
    not_in_spec_blocks = []  # [(srow, erow), ...]

    # Find the amendment comments in the source
    not_in_spec_stack = []  # [srow, ...]
    readline = partial(next, iter(source_lines))
    for type, string, (srow, scol), (erow, ecol), lineno in tokenize(readline):
        if type == COMMENT:
            comment_only_line = source_lines[srow - 1][:scol].strip() == ""

            if _RE_DISABLED_COMMENT.match(string) and comment_only_line:
                disabled_lines.append((srow, scol, min(len(string), 4)))
            elif _RE_BEGIN_NOT_IN_SPEC_COMMENT.match(string) and comment_only_line:
                not_in_spec_stack.append(srow)
            elif _RE_END_NOT_IN_SPEC_COMMENT.match(string) and comment_only_line:
                if not_in_spec_stack:
                    not_in_spec_blocks.append((not_in_spec_stack.pop(), srow))
                else:
                    raise UnmatchedNotInSpecBlockError(srow)
            elif _RE_LINE_NOT_IN_SPEC_COMMENT.match(string):
                not_in_spec_blocks.append((srow, srow))
            elif string.startswith("##"):
                raise BadAmendmentCommentError(string, srow, scol)

    if not_in_spec_stack:
        raise UnclosedNotInSpecBlockError(not_in_spec_stack[-1])

    # Uncomment triple-hash disabled lines
    for row, col, prefix_length in disabled_lines:
        line = source_lines[row - 1]
        source_lines[row - 1] = line[:col] + line[col + prefix_length :]
        indent_corrections[row] = prefix_length

    # Comment-out "Not in spec" lines
    for srow, erow in not_in_spec_blocks:
        for row in range(srow, erow + 1):
            source_lines[row - 1] = "# " + source_lines[row - 1]

    return ("".join(source_lines), indent_corrections)
