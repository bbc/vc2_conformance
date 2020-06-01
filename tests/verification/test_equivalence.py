# These tests check that the VC-2 pseudocode implementations in vc2_conformance
# are equivalent to the published VC-2 pseudocode.
#
# See the introductory documentation in tests/verification/__init__.py for a
# complete introduction.

import pytest

from verification.comparators import Identical, SerdesChangesOnly
from verification.compare import compare_functions

from verification import reference_pseudocode

from vc2_conformance.pseudocode.metadata import pseudocode_derived_functions


@pytest.mark.parametrize(
    # Name included to make pytest print it visible in the list of tests
    "_name,deviation",
    [(pdf.name, pdf.deviation) for pdf in pseudocode_derived_functions],
)
def test_deviations(_name, deviation):
    # Make sure that no unexpected deviation types have been specified
    assert deviation in (
        None,
        "serdes",
        "alternative_implementation",
        "inferred_implementation",
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
