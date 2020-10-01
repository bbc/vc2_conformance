r"""
The :py:mod:`vc2_conformance.string_formatters` module contains facilities for
formatting (or pretty printing) Python values as strings.

When we say 'string formatter' we mean a function/callable which takes a value
and returns a string representation of that value. Instances of the classes in
this module act as formatters. For example, the :py:class:`Hex` class may be
used as a formatter for n-digit hexadecimal integers::

    >>> from vc2_conformance.string_formatters import Hex

    >>> # Create a formatter for producing 8-digit hex numbers
    >>> hex32_formatter = Hex(8)

    >>> # Format some values
    >>> hex32_formatter(0)
    '0x00000000'
    >>> hex32_formatter(0x1234)
    '0x00001234'

"""

from vc2_conformance.string_utils import indent, ellipsise

__all__ = [
    "Number",
    "Hex",
    "Dec",
    "Oct",
    "Bin",
    "Bool",
    "Bits",
    "Bytes",
    "Object",
    "List",
    "MultilineList",
]


class Number(object):
    """
    A formatter which uses Python's built-in :py:meth:`str.format` method to
    apply formatting.

    This formatter is quite low level, see :py:class:`Hex`, :py:class:`Dec`,
    :py:class:`Oct` and :py:class:`Bin` for ready to use derivatives.

    Parameters
    ==========
    format_code : str
        A python :py:meth:`str.format` code, e.g. "b" for binary.
    prefix : str
        A prefix to add before the formatted number
    num_digits : int
        The length to pad the number to.
    pad_digit : str
        The value to use to pad absent digits
    """

    def __init__(self, format_code, num_digits=0, pad_digit="0", prefix=""):
        self.format_code = format_code
        self.num_digits = num_digits
        self.pad_digit = pad_digit
        self.prefix = prefix

    def __call__(self, number):
        return "{}{}{:{}{}{}}".format(
            "-" if number < 0 else "",
            self.prefix,
            abs(number),
            self.pad_digit,
            self.num_digits,
            self.format_code,
        )


class Hex(Number):
    """
    Prints numbers in hexadecimal.

    Parameters
    ==========
    num_digits : int
        Minimum number of digits to show.
    pad_digit : str
        The value to use to pad absent digits
    prefix : str
        Defaults to "0x"
    """

    def __init__(self, num_digits=0, pad_digit="0", prefix="0x"):
        super(Hex, self).__init__("X", num_digits, pad_digit, prefix)


class Dec(Number):
    """
    Prints numbers in decimal.

    Parameters
    ==========
    num_digits : int
        Minimum number of digits to show.
    pad_digit : str
        The value to use to pad absent digits
    prefix : str
        Defaults to ""
    """

    def __init__(self, num_digits=0, pad_digit="0", prefix=""):
        super(Dec, self).__init__("d", num_digits, pad_digit, prefix)


class Oct(Number):
    """
    Prints numbers in octal.

    Parameters
    ==========
    num_digits : int
        Minimum number of digits to show.
    pad_digit : str
        The value to use to pad absent digits
    prefix : str
        Defaults to "0o"
    """

    def __init__(self, num_digits=0, pad_digit="0", prefix="0o"):
        super(Oct, self).__init__("o", num_digits, pad_digit, prefix)


class Bin(Number):
    """
    Prints numbers in binary.

    Parameters
    ==========
    num_digits : int
        Minimum number of digits to show.
    pad_digit : str
        The value to use to pad absent digits
    prefix : str
        Defaults to "0b"
    """

    def __init__(self, num_digits=0, pad_digit="0", prefix="0b"):
        super(Bin, self).__init__("b", num_digits, pad_digit, prefix)


class Bool(object):
    """
    A formatter for :py:class:`bool` (or bool-castable) objects. For the values
    0, 1, False and True, just shows 'True' or 'False'. For all other values,
    shows also the true value in brackets.

    For example::

        >>> bool_formatter = Bool()
        >>> bool_formatter(False)
        "False"
        >>> bool_formatter(True)
        "True"
        >>> bool_formatter(0)
        "False"
        >>> bool_formatter(1)
        "True"
        >>> bool_formatter(123)
        "True (123)"
        >>> bool_formatter(None)
        "True (None)"
    """

    def __call__(self, b):
        if b and b in (1, True):
            return "True"
        elif not b and b in (0, False):
            return "False"
        else:
            return "{} ({})".format(bool(b), b)


class Bits(object):
    """
    A formatter for :py:class:`bitarray.bitarray` objects. Shows the value as a
    string of the form '0b0101', using
    :py:func:`~vc2_conformance.string_utils.ellipsise` to shorten very long,
    values.

    Parameters
    ==========
    prefix : str
        A prefix to add to the string
    context : int
    min_length : int
        See :py:func:`~vc2_conformance.string_utils.ellipsise`.
    show_length : int or bool
        If an integer, show the length of the bitarray in brackets if above the
        specified length (in bits). If a bool, force display (or hiding) of the
        length information.
    """

    def __init__(self, prefix="0b", context=4, min_length=8, show_length=16):
        self.prefix = prefix
        self.context = context
        self.min_length = min_length
        self.show_length = show_length

    def __call__(self, ba):
        string = ellipsise(ba.to01(), self.context, self.min_length)
        if self.show_length is not False:
            if self.show_length is True or len(ba) >= self.show_length:
                string += " ({} bit{})".format(
                    len(ba),
                    "s" if len(ba) != 1 else "",
                )
        return "{}{}".format(self.prefix, string)


class Bytes(object):
    """
    A formatter for :py:class:`bytes` strings. Shows the value as a string of
    the form '0xAB_CD_EF', using
    :py:func:`~vc2_conformance.string_utils.ellipsise` to shorten very long,
    values.

    Parameters
    ==========
    prefix : str
        A prefix to add to the string
    separator : str
        A string to place between each pair of hex digits.
    context : int
    min_length : int
        See :py:func:`~vc2_conformance.string_utils.ellipsise`.
    show_length : int or bool
        If an integer, show the length of the bitarray in brackets if above the
        specified length (in bytes). If a bool, force display (or hiding) of
        the length information.
    """

    def __init__(
        self, prefix="0x", separator="_", context=2, min_length=4, show_length=8
    ):
        self.prefix = prefix
        self.separator = separator
        self.context = context
        self.min_length = min_length
        self.show_length = show_length

    def __call__(self, b):
        string = "".join("{:02X}".format(n) for n in bytearray(b))

        before, ellipses, after = ellipsise(
            string, self.context * 2, self.min_length * 2
        ).partition("...")

        # Interleave bytes with separator
        before = "".join(
            c
            if (i % 2 == 0 or i == len(before) - 1)
            else "{}{}".format(c, self.separator)
            for i, c in enumerate(before)
        )
        after = "".join(
            c
            if ((len(after) - i) % 2 == 1 or i == 0)
            else "{}{}".format(self.separator, c)
            for i, c in enumerate(after)
        )

        string = before + ellipses + after

        if self.show_length is not False:
            if self.show_length is True or len(b) >= self.show_length:
                string += " ({} byte{})".format(
                    len(b),
                    "s" if len(b) != 1 else "",
                )
        return "{}{}".format(self.prefix, string)


class Object(object):
    """
    A formatter for opaque python Objects. Shows only the object type name.
    """

    def __init__(self, prefix="<", suffix=">"):
        self.prefix = prefix
        self.suffix = suffix

    def __call__(self, o):
        return "{}{}{}".format(
            self.prefix,
            type(o).__name__,
            self.suffix,
        )


class List(object):
    """
    A formatter for lists which collapses repeated entries.

    Examples::

        >>> # Use Python-style notation for repeated entries
        >>> List()([1, 1, 1, 1])
        [1]*4

        >>> # Also displays lists with some non-repeated values
        >>> List()([1, 2, 3, 0, 0, 0, 0, 0, 4, 5])
        [1, 2, 3] + [0]*5 + [4, 5]

        >>> # A custom formatter may be supplied for formatting the list
        >>> # entries
        >>> List(formatter=Hex())([1, 2, 3, 0, 0, 0])
        [0x1, 0x2, 0x3] + [0x0]*3

        >>> # Equality is based on the string formatted value, not the raw
        >>> # value
        >>> List(formatter=Object())([1, 2, 3, 0, 0, 0])
        [<int>]*6

        >>> # The minimum run-length before truncation may be overridden
        >>> List(min_run_length=3)([1, 2, 2, 3, 3, 3])
        [1, 2, 2] + [3]*3
    """

    def __init__(self, min_run_length=3, formatter=str):
        self.min_run_length = min_run_length
        self.formatter = formatter

    def __call__(self, lst):
        # Special case (avoids complications below)
        if len(lst) == 0:
            return "[]"

        values = [self.formatter(v) for v in lst]

        # For each value in the input list, count the run length at that point
        # of that value.
        run_lengths = [1]
        for last_value, value in zip(values, values[1:]):
            if last_value == value:
                run_lengths.append(run_lengths[-1] + 1)
            else:
                run_lengths.append(1)

        # Accumulate a list of lists and tuples. For every series of
        # non-identical values, a list of values will be included. For every
        # run of values, a (value, run_length) tuple will be included.
        out = [[]]
        while values:
            run_length = run_lengths.pop()
            value = values.pop()

            if run_length < self.min_run_length:
                out[0].insert(0, value)
            else:
                if len(out[0]) == 0:
                    del out[0]
                out.insert(0, (value, run_length))
                out.insert(0, [])

                del run_lengths[-(run_length - 1) :]
                del values[-(run_length - 1) :]

        if len(out[0]) == 0:
            del out[0]

        # Format as a string
        return " + ".join(
            (
                "[{}]".format(", ".join(value_run))
                if isinstance(value_run, list)
                else "[{}]*{}".format(*value_run)
            )
            for value_run in out
        )


class MultilineList(object):
    """
    A formatter for lists which displays each value on its own line.

    Examples::

        >>> MultilineList()(["one", "two", "three"])
        0: one
        1: two
        2: three

        >>> # A custom formatter may be supplied for formatting the list
        >>> # entries
        >>> MultilineList(formatter=Hex())([1, 2, 3])
        0: 0x1
        1: 0x2
        2: 0x3

        >>> # A heading may be added
        >>> MultilineList(heading="MyList")(["one", "two", "three"])
        MyList
          0: one
          1: two
          2: three
    """

    def __init__(self, heading=None, formatter=str):
        self.heading = heading
        self.formatter = formatter

    def __call__(self, lst):
        lines = "\n".join(
            "{}: {}".format(i, self.formatter(value)) for i, value in enumerate(lst)
        )

        if self.heading is None:
            return lines
        else:
            return "{}\n{}".format(self.heading, indent(lines))
