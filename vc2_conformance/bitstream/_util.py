"""
Internal minor utility functions; mainly relating to string formatting.
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

def concat_strings(strings, one_line_seperator=" "):
    """
    Sensibly concatenate a series of strings, with the following 'smart'
    behaviours:
    
    * If any string contains a newline, concatenate with newlines, not spaces
    * If any string is empty, omit it entirely
    
    The ``one_line_seperator`` argument specifies the separator to add between
    strings when they're shown on the same line. This defaults to a single
    space.
    """
    if any("\n" in s for s in strings):
        seperator = "\n"
    else:
        seperator = one_line_seperator
    
    return seperator.join(filter(None, strings))


def concat_labelled_strings(labels_strings):
    """
    Given a list of (label, string) tuples, concatenate these in one of the
    following forms (depending on the strings)::
    
        label: string, label: string, label: string
    
    Or when any of the strings contain multiple lines::
        
        label:
          multi-line
          string
        label:
          multi-line
          string
        label:
          multi-line
          string
    
    In either case, empty strings will be omitted (no label will be shown).
    """
    if any("\n" in s for (l, s) in labels_strings):
        return "\n".join(
            "{}:\n{}".format(label, indent(string))
            for (label, string) in labels_strings
            if string
        )
    else:
        return ", ".join(
            "{}: {}".format(label, string)
            for (label, string) in labels_strings
            if string
        )


def concat_tabular_strings(table_strings, column_sep="  "):
    """
    Concatenate a table of strings.
    
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
        return concat_labelled_strings([
            ("(y={}, x={})".format(y, x), s)
            for y, line in enumerate(table_strings)
            for x, s in enumerate(line)
        ])
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


def ensure_function(value_or_function):
    """
    If the passed value is not a function, wrap it in a zero-argument function
    which returns that value. Otherwise, return the function.
    """
    if callable(value_or_function):
        return value_or_function
    else:
        return lambda: value_or_function


class function_property(object):
    """
    This descriptor class may be used as a short-hand for creating properties
    which follow the following pattern::
    
        >>> class MyClass(object):
        ...
        ...     @property
        ...     def value(self):
        ...         return self._value()
        ...
        ...     @value.setter
        ...     def value(self, value):
        ...         self._value = ensure_function(value)
    
    Instead of the above, it is sufficient to write:
    
        >>> class MyClass(object):
        ...
        ...     value = function_property()
    
    In this pattern, a property may be assigned either a function or a constant
    as its value. When the property is read, the read value will be the result
    of calling the function (or just returning the constant if not a function).
    """
    
    def __init__(self, internal_name=None):
        self._internal_name = internal_name or "_function_property_{}".format(id(self))
    
    def __get__(self, obj, owner_type=None):
        return getattr(obj, self._internal_name)()
    
    def __set__(self, obj, value):
        setattr(obj, self._internal_name, ensure_function(value))
    
    def __delete__(self, obj):
        delattr(obj, self._internal_name)


def ordinal_indicator(value):
    """
    Return the (English) ordinal indicator (e.g. 'st', 'nd', 'rd' or 'th') for
    provided integer value.
    """
    value = abs(value)
    
    # Special case
    if 11 <= (value % 100) <= 13:
        return "th"
    
    # Non-th cases
    if (value % 10) == 1:
        return "st"
    if (value % 10) == 2:
        return "nd"
    if (value % 10) == 3:
        return "rd"
    
    return "th"
