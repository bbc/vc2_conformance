import pytest

import sys
import inspect

# These tests check that the VC-2 pseudocode implementations in vc2_conformance
# are equivalent to the published VC-2 pseudocode.
#
# See the introductory documentation in tests/verification/__init__.py for a
# complete introduction.

import os


from verification.comparators import Identical, SerdesChangesOnly
from verification.compare import compare_functions

from verification import reference_pseudocode


from vc2_conformance.pseudocode.metadata import pseudocode_derived_functions

# The directory the test scripts reside in
test_dir = os.path.normcase(
    os.path.normpath(
        os.path.join(inspect.getsourcefile(sys.modules[__name__]), "..", "..",)
    )
)


@pytest.mark.parametrize(
    # Name included to make pytest print it visible in the list of tests
    "name,pseudocode_derived_function",
    [(pdf.name, pdf) for pdf in pseudocode_derived_functions if pdf.deviation is None],
)
def test_equivalence_of_vc2_pseudocode(name, pseudocode_derived_function):
    ref_func = getattr(reference_pseudocode, name)
    imp_func = pseudocode_derived_function.function
    # Same function
    assert compare_functions(ref_func, imp_func, Identical()) is True

    # Same reference to the spec
    assert ref_func.__doc__ == "({})".format(pseudocode_derived_function.section)


@pytest.mark.parametrize(
    # Name included to make pytest print it visible in the list of tests
    "name,pseudocode_derived_function",
    [
        (pdf.name, pdf)
        for pdf in pseudocode_derived_functions
        if pdf.deviation == "serdes"
    ],
)
def test_equivalence_of_vc2_bitstream_pseudocode(name, pseudocode_derived_function):
    ref_func = getattr(reference_pseudocode, name)
    imp_func = pseudocode_derived_function.function
    # Same function
    assert compare_functions(ref_func, imp_func, SerdesChangesOnly()) is True

    # Same reference to the spec
    assert ref_func.__doc__ == "({})".format(pseudocode_derived_function.section)
