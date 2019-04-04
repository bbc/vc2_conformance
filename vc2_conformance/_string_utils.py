"""
Internal minor string formatting utility functions.
"""

try:
    # Python 3.x
    from itertools import zip_longest
except ImportError:
    # Python 2.x
    from itertools import izip_longest as zip_longest


def indent(text, prefix="  "):
    """Indent the string 'text' with the prefix string 'prefix'."""
    return "{}{}".format(
        prefix,
        ("\n{}".format(prefix)).join(text.split("\n")),
    )


def ellipsise(text, context=4, min_length=8):
    """
    Given a string which contains very long sequences of the same character
    (e.g. long mostly constant binary or hex numbers), produce an 'ellipsised'
    version with some of the repeated characters replaced with '...'.
    
    Exactly one shortening operation will be carried out (on the longest run)
    meaning that so long as the original string length is known, it is still
    possible to determine the full length string from the ellipsised version.
    
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
    
    if longest_run_length < (2*context) + min_length:
        # Too short to bother
        return text
    else:
        longest_run_start = longest_run_end - longest_run_length + 1
        return "{}...{}".format(
            text[:longest_run_start + context],
            text[longest_run_end - context + 1:],
        )


def table(table_strings, column_sep="  ", indent_prefix="  "):
    """
    Concatenate and lay out a table of strings.
    
    Takes a list-of-lists-of-strings with inner lists representing rows of
    strings.
    
    If all values fit on a single line, produces an aligned 2D layout like so::
    
        123    0    0
          1  123   12
         12    4  123
    
    If any of the values don't fit on to a single line, a flat representation
    is used::
    
        (y=0, x=0):
          multi-line
          string
        (y=0, x=1):
          multi-line
          string
        (y=0, x=2):
          multi-line
          string
        (y=1, x=0):
          multi-line
          string
        (y=1, x=1):
          multi-line
          string
        (y=1, x=2):
          multi-line
          string
    """
    if any("\n" in s for line in table_strings for s in line):
        return "\n".join(
            "(y={}, x={}):\n{}".format(y, x, indent(s, indent_prefix))
            for y, line in enumerate(table_strings)
            for x, s in enumerate(line)
        )
    else:
        cols = zip_longest(*table_strings)
        col_widths = [max(map(len, filter(None, col))) for col in cols]
        
        return "\n".join(
            column_sep.join(
                "{:>{}s}".format(s, col_widths[i])
                for i, s in enumerate(row)
            )
            for row in table_strings
        )


