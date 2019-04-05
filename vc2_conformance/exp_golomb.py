"""
Utility functions relating to the unsigned and signed interleaved Exponential-Golomb
variable length codes used by VC-2.

.. note::

    For functions for actually encoding and decoding values see either
    :py:module:`vc2_conformance.bitstream.io` or the reference decoder.
"""

from vc2_conformance.exceptions import OutOfRangeError

__all__ = [
    "exp_golomb_length",
    "signed_exp_golomb_length",
]


def exp_golomb_length(value):
    """
    Return the length (in bits) of the unsigned exp-golomb representation of
    value.
    
    An :py:exc:`OutOfRangeError` will be raised if a negative value is
    provided.
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
