"""
Mathematical functions and operators defined in the spec (5.5.3)
"""

import math

from vc2_conformance.pseudocode.metadata import ref_pseudocode

__all__ = [
    "intlog2_float",
    "intlog2",
    "sign",
    "clip",
    "mean",
]


@ref_pseudocode(name="intlog2", deviation="inferred_implementation")
def intlog2_float(n):
    """
    (5.5.3) Implemented as described in the spec, requiring floating point
    arithmetic.

    In practice, the alternative implementation in :py:func:`intlog2` should be
    used instead since it does not rely on floating point arithmetic (and is
    therefore faster and has unlimited precision).
    """
    return int(math.ceil(math.log(n, 2)))


@ref_pseudocode(deviation="alternative_implementation")
def intlog2(n):
    """
    (5.5.3) Implemented via pure integer, arbitrary-precision operations.
    """
    return (n - 1).bit_length()


@ref_pseudocode
def sign(a):
    """(5.5.3)"""
    if a > 0:
        return 1
    elif a == 0:
        return 0
    elif a < 0:
        return -1


@ref_pseudocode
def clip(a, b, t):
    """(5.5.3)"""
    return min(max(a, b), t)


@ref_pseudocode(deviation="inferred_implementation")
def mean(*S):
    """(5.5.3)"""
    n = len(S)
    return (sum(S) + (n // 2)) // n
