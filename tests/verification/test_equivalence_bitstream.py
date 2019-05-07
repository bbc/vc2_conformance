import pytest

# These tests check that the VC-2 pseudocode implementations in the VC-2
# bitstream code are equivalent to the published VC-2 pseudocode.


from verification.comparators import SerdesChangesOnly
from verification.compare import compare_functions

from verification import reference_pseudocode


# Force loading of all submodules (and thus registration of metadata)
import vc2_conformance
from vc2_conformance.metadata import referenced_values


@pytest.mark.parametrize(
    # Name included to make pytest print it visible in the list of tests
    "name,referenced_value",
    [(rv.name, rv) for rv in referenced_values if rv.deviation == "serdes"],
)
def test_equivalence_of_vc2_bitstream_pseudocode(name, referenced_value):
    ref_func = getattr(reference_pseudocode, name)
    imp_func = referenced_value.value
    # Same function
    assert compare_functions(ref_func, imp_func, SerdesChangesOnly()) is True
    
    # Same reference to the spec
    assert ref_func.__doc__ == "({})".format(referenced_value.section)
