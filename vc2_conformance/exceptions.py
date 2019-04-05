"""
Exception types used in this library.
"""

class OutOfRangeError(ValueError):
    """
    An exception thrown whenever an out-of-range value is passed to a bitstream
    writing function.
    """
