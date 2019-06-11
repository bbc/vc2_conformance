"""
:py:mod:`vc2_conformance.arrays`: VC-2 style 2D array functions.
================================================================
"""

from vc2_conformance.metadata import ref_pseudocode


__all__ = [
    "array",
    "width",
    "height",
    "row",
    "column",
]


@ref_pseudocode(deviation="inferred_implementation")
def array(width, height, initial_value=0):
    """
    (5.4.2) Makes a 2D array out of nested lists which may be indexed as
    arr[y][x].
    """
    return [
        [initial_value] * width
        for _ in range(height)
    ]


@ref_pseudocode(deviation="inferred_implementation")
def width(a):
    """(5.5.4)"""
    # NB: In zero-height arrays this will give the wrong answer (0), but such
    # arrays are not expected in reality.
    if len(a) == 0:
        return 0
    else:
        return len(a[0])


@ref_pseudocode(deviation="inferred_implementation")
def height(a):
    """(5.5.4)"""
    return len(a)


@ref_pseudocode(deviation="inferred_implementation")
def row(a, k):
    """
    (15.4.1) A 1D-array-like view into a row of a (2D) nested list as returned
    by 'array()'.
    """
    return a[k]


@ref_pseudocode(deviation="inferred_implementation")
class column(object):
    """
    (15.4.1) A 1D-array-like view into a column of a (2D) nested list as
    returned by 'array()'.
    """
    
    def __init__(self, a, k):
        self._a = a
        self._k = k
    
    def __getitem__(self, key):
        assert isinstance(key, int)
        return self._a[key][self._k]
    
    def __setitem__(self, key, value):
        assert isinstance(key, int)
        self._a[key][self._k] = value
    
    def __len__(self):
        return len(self._a)
