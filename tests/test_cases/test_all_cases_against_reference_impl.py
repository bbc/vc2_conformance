"""
Testing all test-cases against the reference implementation
===========================================================

This collection of tests will attempt to run every test case against the
conformance checking decoder in :py:mod:`vc2_conformance.decoder`.

The primary objective of these tests is to confirm that all non-xfail tests are
valid and while xfail tests are rejected.

The secondary objective of these tests is to verify that xfailed tests fail for
the intended reason.  In particular we check that the bitstream validator
throws the expected exception.

These tests *do not* check (for the most part) whether the test cases do what
they claim they do. These claims should be verified separately (either through
additional unit tests or manual inspection).

"""

import pytest

from io import BytesIO

from vc2_conformance.state import State

from vc2_conformance import bitstream
from vc2_conformance import decoder

from vc2_conformance.test_cases import test_case_registry, XFail


@pytest.mark.parametrize("name", test_case_registry.test_cases)
def test_case(name):
    sequence = test_case_registry.test_cases[name]()
    
    # Do nothing if no test case returned
    if sequence is None:
        return
    
    xfail = isinstance(sequence, XFail)
    if xfail:
        sequence, error = sequence
    
    # Seriallise the test case's bitstream
    f = BytesIO()
    bitstream.autofill_and_serialise_sequence(f, sequence)
    f.seek(0)
    
    # Validate the bitstream
    state = State()
    decoder.init_io(state, f)
    if xfail:
        with pytest.raises(error):
            decoder.parse_sequence(state)
    else:
        decoder.parse_sequence(state)
