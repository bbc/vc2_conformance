"""
Mathematical functions/operators defined by VC-2 in (5.5.3).
"""

import math

from vc2_conformance.metadata import ref_pseudocode

__all__ = [
    "intlog2_float",
    "intlog2",
    "sign",
    "clip",
    "mean",
]


@ref_pseudocode(name="intlog2", verbatim=True)
def intlog2_float(n):
    """
    (5.5.3) Implemented as described in the spec, requiring floating point
    arithmetic.
    
    In practice, :py:func:`intlog2` should be used instead.
    """
    return int(math.ceil(math.log(n, 2)))


@ref_pseudocode(verbatim=False)
def intlog2(n):
    """
    (5.5.3) Implemented via pure integer, arbitrary-precision operations.
    """
    return (n-1).bit_length()


@ref_pseudocode
def sign(n):
    """(5.5.3)"""
    if n < 0:
        return -1
    elif n == 0:
        return 0
    elif n > 0:
        return 1


@ref_pseudocode
def clip(a, b, t):
    """(5.5.3)"""
    return min(max(a, b), t)


@ref_pseudocode
def mean(S):
    """(5.5.3)"""
    n = len(S)
    return (sum(S) + (n//2)) // n
