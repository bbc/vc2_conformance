r"""
Functions which produce human-readable string representations of values.
Convenience functions for passing to the ``formatter`` argument of
:py:class:`BitstreamValue`\ s.

A formatter is a callable which takes a value and returns a string
representation of that value. Various formatter classes are provided in this
class for displaying numbers. For example::

    >>> hex_formatter = Hex()
    >>> hex_formatter(0x1234)
    '0x1234'
    
    >>> hex32_formatter = Hex(8)
    >>> hex32_formatter(0x1234)
    '0x00001234'
"""

from attr import attrs, attrib

__all__ = [
    "Number",
    "Hex",
    "Dec",
    "Oct",
    "Bin",
]


@attrs(frozen=True)
class Number(object):
    """
    A formatter which uses Python's built-in :py:meth:`str.format` method to
    apply formatting.
    
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
    
    format_code = attrib()
    num_digits = attrib(default=0)
    pad_digit = attrib(default="0")
    prefix = attrib(default="")
    
    def __call__(self, number):
        return "{}{}{:{}{}{}}".format(
            "-" if number < 0 else "",
            self.prefix,
            abs(number),
            self.pad_digit,
            self.num_digits,
            self.format_code,
        )

@attrs(frozen=True)
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
    
    num_digits = attrib(default=0)
    pad_digit = attrib(default="0")
    prefix = attrib(default="0x")
    format_code = attrib(default="X", repr=False, init=False)

@attrs(frozen=True)
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
    
    num_digits = attrib(default=0)
    pad_digit = attrib(default="0")
    prefix = attrib(default="")
    format_code = attrib(default="d", repr=False, init=False)

@attrs(frozen=True)
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
    
    num_digits = attrib(default=0)
    pad_digit = attrib(default="0")
    prefix = attrib(default="0o")
    format_code = attrib(default="o", repr=False, init=False)

@attrs(frozen=True)
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
    
    num_digits = attrib(default=0)
    pad_digit = attrib(default="0")
    prefix = attrib(default="0b")
    format_code = attrib(default="b", repr=False, init=False)
