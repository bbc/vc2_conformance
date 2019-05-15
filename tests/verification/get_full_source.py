r"""
:py:mod:`verification.get_full_source`
======================================

Alternative implementations of :py:mod:`inspect`\ 's  source-finding functions
which also include trailing comments (which may be important if using
:py:mod:`verification.amendment_comments`.
"""

import re
import inspect

from itertools import takewhile


def get_full_source(func):
    """
    Given a function reference, return the filename, starting line number and
    source lines (including all trailing comments).
    """
    # NB: Source lines specified don't include trailing comments
    truncated_source_lines, first_lineno = inspect.getsourcelines(func)
    last_lineno = first_lineno + len(truncated_source_lines)
    
    filename = inspect.getsourcefile(func)
    
    lines = list(open(filename, "r"))
    full_source_lines = (
        lines[first_lineno - 1: last_lineno - 1] +
        list(takewhile(
            # Include all trailing blank lines and all trailing indented
            # comment-only lines.
            lambda line: re.match(r"^(\s+(#.*))|(\s*)$", line),
            lines[last_lineno - 1:],
        ))
    )
    
    return (filename, first_lineno, full_source_lines)
