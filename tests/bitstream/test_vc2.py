"""
The tests in this class are currently of the sanity-check flavour. More
detailed cross-checking of these structures with the VC-2 reference decoder
will be taken care of elsewhere.
"""

import pytest

from vc2_conformance import bitstream


def test_parse_info():
    p = bitstream.ParseInfo()
    
    # The parse_info structure is defined as being 13 bytes long (10.5.1)
    assert p.length == 13 * 8
