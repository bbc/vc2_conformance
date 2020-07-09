"""
VC-2 style 2D array functions (5.5).
"""

from vc2_conformance.pseudocode.metadata import ref_pseudocode


__all__ = [
    "new_array",
    "width",
    "height",
    "row",
    "column",
    "delete_rows_after",
    "delete_columns_after",
]


@ref_pseudocode(deviation="inferred_implementation")
def new_array(*dimensions):
    """
    (5.4.2) Makes an N-dimensional array out of nested lists. Dimensions are
    given in the same order as they are indexed, e.g. ``new_array(height,
    width)``, like ``array[y][x]``.
    """
    if len(dimensions) == 0:
        return None
    else:
        return [new_array(*dimensions[1:]) for _ in range(dimensions[0])]


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
    by :py:func:`new_array()`.
    """
    return a[k]


@ref_pseudocode(deviation="inferred_implementation")
class column(object):
    """
    (15.4.1) A 1D-array-like view into a column of a (2D) nested list as
    returned by :py:func:`new_array()`.
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


def delete_rows_after(a, k):
    """
    (15.4.5) Delete rows 'k' and after in 'a'.
    """
    del a[k:]


def delete_columns_after(a, k):
    """
    (15.4.5) Delete columns 'k' and after in 'a'.
    """
    for row in a:
        del row[k:]
