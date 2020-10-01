"""
The :py:mod:`vc2_conformance.string_utils` module contains a selection of
general purpose string formatting routines.
"""

from textwrap import wrap, dedent

import re


def indent(text, prefix="  "):
    """
    Indent the string 'text' with the prefix string 'prefix'.

    .. note::

        This function is provided partly because Python 2.x doesn't include
        :py:func:`textwrap.indent` in its standard library and partly to
        provide an indent function with sensible defaults (i.e. 2 character
        indent, and always indent every line).
    """
    return "{}{}".format(prefix, ("\n{}".format(prefix)).join(text.split("\n")))


def ellipsise(text, context=4, min_length=8):
    """
    Given a string which contains very long sequences of the same character
    (e.g. long mostly constant binary or hex numbers), produce an 'ellipsised'
    version with some of the repeated characters replaced with '...'.

    Exactly one shortening operation will be carried out (on the longest run)
    meaning that so long as the original string length is known, no ambiguity
    is introduced in the ellipsised version.

    For example::

        >>> ellipsise("0b10100000000000000000000000000000000000001")
        "0b1010000...00001"

    Parameters
    ==========
    text : str
        String to ellipsise.
    context : int
        The number of repeated characters to retain before and after the
        ellipses.
    min_length : int
        The minimum number of characters to bother replacing with '...'. This
        means that no change will be made until 2*context + min_length
        character repetitions.
    """
    # Special case to avoid handling it later
    if len(text) == 0:
        return text

    repeats = []
    num_repeats = 0
    last_char = None
    for char in text:
        if char == last_char:
            num_repeats += 1
        else:
            num_repeats = 1
        repeats.append(num_repeats)
        last_char = char

    longest_run_end, longest_run_length = max(
        enumerate(repeats),
        key=lambda pos_count: pos_count[1],
    )

    if longest_run_length < (2 * context) + min_length:
        # Too short to bother
        return text
    else:
        longest_run_start = longest_run_end - longest_run_length + 1
        return "{}...{}".format(
            text[: longest_run_start + context],
            text[longest_run_end - context + 1 :],
        )


def ellipsise_lossy(text, max_length=80):
    """
    Given a string which may not fit within a given line length, trnucate the
    string by adding ellipses in the middle.
    """
    if len(text) <= max_length:
        # Already short enough
        return text
    else:
        before_length = (max_length - 3) // 2
        after_length = (max_length - 3) - before_length
        return "{}...{}".format(text[:before_length], text[-after_length:])


RE_HEADING_UNDERLINE = re.compile(r"^[-=]+$")
RE_BULLET_OR_NUMBER = re.compile(r"^([*]\s+|[0-9]+[.]\s+)(.*)$")
RE_PREFIX_AND_BLOCK = re.compile(r"^([*]\s+|[0-9]+[.]\s+|\s*)(.*)$")


def split_into_line_wrap_blocks(text, wrap_indented_blocks=False):
    """
    Deindent and split a multi-line markdown-style string into blocks of text
    which can be line-wrapped independently.

    For example given a markdown-style string defined like so::

        '''
            A markdown style title
            ======================

            This is a string with some initial indentation
            and also some hard line-wraps inserted too. This
            paragraph ought to be line-wrapped as an
            independent unit.

            Here's a second paragraph which also ought to be
            line wrapped as its own unit.

            * This is a bulleted list
            * Each bullet point should be line wrapped as an
              individual unit (with the wrapping indented
              as shown here).
            * Notice that bullets don't have a newline
              between them like paragraphs do.

            1. Numbered lists are also supported.
            2. Here long lines will be line wrapped in much
               the same way as a bulleted list.

            Finally:

                An intended block will also remain indented.
                However, if wrap_indented_blocks is False, the
                existing linebreaks will be retained (e.g. for
                markdown-style code blocks). If set to True,
                the indented block will be line-wrapped.
        '''

    This will be split into independently line wrappable segments (as
    described).

    Returns
    -------
    blocks : [(first_indent, rest_indent, text), ...]
        A series of wrappable blocks. In each tuple:

        * first_indent contains a string which should be used to indent the
          first line of the wrapped block.
        * rest_indent should be a string which should be used to indent all
          subsequent lines in the wrapped block. This will be the same length
          as first_indent.
        * text will be an indentation and newline-free string

        An empty block (i.e. ``("", "", "")``) will be included between
        each paragraph in the input so that the output maintains the same
        vertical whitespace profile.
    """
    # Remove common leading whitespace.
    text = dedent(text)

    block_lines = [""]
    for line in text.splitlines():
        # Start a new block if we encounter an empty line (between paragraphs)
        # or a bullet point/number. The first bullet/number must have a blank
        # line before it.
        if line.rstrip() == "":
            block_lines.append("")
            block_lines.append("")
        elif RE_HEADING_UNDERLINE.match(line):
            block_lines.append("")
        elif RE_BULLET_OR_NUMBER.match(line) and (
            # Don't match asterisks and number-dots midway through
            # paragraphs -- require that they appear after a blank line or
            # after another bullet/number.
            block_lines[-1] == ""
            or RE_BULLET_OR_NUMBER.match(block_lines[-1])
        ):
            block_lines.append("")
        elif not wrap_indented_blocks and re.match(r"^\s+", block_lines[-1]):
            # When block wrapping is disabled, start a new line for every line
            # in the block
            block_lines.append("")

        # Retain indentation of first non-empty line in block
        if block_lines[-1].strip() == "":
            block_lines[-1] = line.rstrip() + " "
        else:
            block_lines[-1] += line.strip() + " "

    # Remove leading and repeating blank lines
    index = 0
    previous_line_is_blank = True
    while index < len(block_lines):
        is_blank = block_lines[index].strip() == ""

        if is_blank and previous_line_is_blank:
            del block_lines[index]
        else:
            index += 1

        previous_line_is_blank = is_blank

    # Remove trailing blank lines
    while block_lines and block_lines[-1].strip() == "":
        del block_lines[-1]

    out = []
    for block_line in block_lines:
        prefix, text = RE_PREFIX_AND_BLOCK.match(block_line).groups((1, 2))
        if len(prefix.strip()) > 0:
            out.append((prefix, " " * len(prefix), text.rstrip()))
        else:
            out.append((prefix, prefix, text.rstrip()))

    return out


def wrap_blocks(blocks, width=None, wrap_indented_blocks=False):
    """
    Return a line-wrapped version of a series of text blocks as produced by
    :py:func:`split_into_line_wrap_blocks`.

    Expects a list of (first_line_indent, remaining_line_indent, text) tuples
    to output.

    If 'width' is None, assumes an infinite line width.

    If 'wrap_indented_blocks' is False (the default) indented (markdown-style)
    code blocks will not be line wrapped while other indented blocks (e.g.
    bullets) will be.
    """
    return "\n".join(
        first_indent
        + ("\n" + rest_indent).join(
            (
                wrap(text, width - len(first_indent))
                if (
                    wrap_indented_blocks
                    or len(first_indent) == 0
                    or first_indent != rest_indent
                )
                else [text]
            )
            if width is not None
            else [text]
        )
        for first_indent, rest_indent, text in blocks
    )


def wrap_paragraphs(text, width=None, wrap_indented_blocks=False):
    """
    Re-line-wrap a markdown-style string with hard-line-wrapped paragraphs,
    bullet points, numbered lists and code blocks (see
    :py:func:`split_into_line_wrap_blocks`).

    If 'width' is None, assumes an infinite line width.

    If 'wrap_indented_blocks' is False (the default) indented (markdown-style)
    code blocks will not be line wrapped while other indented blocks (e.g.
    bullets) will be.
    """
    return wrap_blocks(
        split_into_line_wrap_blocks(text, wrap_indented_blocks),
        width,
        wrap_indented_blocks,
    )
