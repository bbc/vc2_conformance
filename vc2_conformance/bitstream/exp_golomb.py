"""
:py:mod:`vc2_conformance.bitstream.exp_golomb`: Exp-golomb code length calculators
==================================================================================
"""

from vc2_conformance.bitstream.exceptions import OutOfRangeError

__all__ = [
    "exp_golomb_length",
    "signed_exp_golomb_length",
]


def exp_golomb_length(value):
    """
    Return the length (in bits) of the unsigned exp-golomb representation of
    value.

    An :py:exc:`~.OutOfRangeError` will be raised if
    a negative value is provided.
    """
    if value < 0:
        raise OutOfRangeError(value)

    return (((value + 1).bit_length() - 1) * 2) + 1


def signed_exp_golomb_length(value):
    """
    Return the length (in bits) of the signed exp-golomb representation of
    value.
    """
    length = exp_golomb_length(abs(value))
    if value != 0:
        length += 1
    return length
