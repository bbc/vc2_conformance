import pytest

import sys
import inspect

# These tests check that the VC-2 pseudocode implementations in vc2_conformance
# are equivalent to the published VC-2 pseudocode.
#
# See the introductory documentation in tests/verification/__init__.py for a
# complete introduction.

import os
from types import FunctionType


from verification.comparators import Identical, SerdesChangesOnly
from verification.compare import compare_functions

from verification import reference_pseudocode


# Force loading of all submodules (and thus registration of metadata)
from vc2_conformance.pseudocode.metadata import referenced_values

# The directory the test scripts reside in
test_dir = os.path.normcase(
    os.path.normpath(
        os.path.join(inspect.getsourcefile(sys.modules[__name__]), "..", "..",)
    )
)


def is_function_with_deviation(referenced_value, deviation):
    """
    Test if a :py:class:`vc2_conformance.pseudocode.metadata.ReferencedValue` refers to a
    function with the specified deviation (and isn't part of the test suite).
    """
    if not isinstance(referenced_value.value, FunctionType):
        return False

    if referenced_value.deviation != deviation:
        return False

    # Also filter out any functions defined within this test suite.
    ref_filename = os.path.normcase(referenced_value.filename)
    if ref_filename.startswith(test_dir):
        return False

    return True


@pytest.mark.parametrize(
    # Name included to make pytest print it visible in the list of tests
    "name,referenced_value",
    [(rv.name, rv) for rv in referenced_values if is_function_with_deviation(rv, None)],
)
def test_equivalence_of_vc2_pseudocode(name, referenced_value):
    ref_func = getattr(reference_pseudocode, name)
    imp_func = referenced_value.value
    # Same function
    assert compare_functions(ref_func, imp_func, Identical()) is True

    # Same reference to the spec
    assert ref_func.__doc__ == "({})".format(referenced_value.section)


@pytest.mark.parametrize(
    # Name included to make pytest print it visible in the list of tests
    "name,referenced_value",
    [
        (rv.name, rv)
        for rv in referenced_values
        if is_function_with_deviation(rv, "serdes")
    ],
)
def test_equivalence_of_vc2_bitstream_pseudocode(name, referenced_value):
    ref_func = getattr(reference_pseudocode, name)
    imp_func = referenced_value.value
    # Same function
    assert compare_functions(ref_func, imp_func, SerdesChangesOnly()) is True

    # Same reference to the spec
    assert ref_func.__doc__ == "({})".format(referenced_value.section)
