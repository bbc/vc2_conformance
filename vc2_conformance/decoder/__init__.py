"""
:py:mod:`vc2_conformance.decoder`: A VC-2 decoder which checks the bitstream for conformance.
=============================================================================================

This module contains the components of a VC-2 decoder based on the pseudocode
published in the VC-2 specification. Along with the basic decoding logic,
additional code is included to check all conditions enforced by the
specification.
"""

from vc2_conformance.decoder.exceptions import *

# (A) Bitstream I/O operations
from vc2_conformance.decoder.io import *

# (10) Stream syntax
from vc2_conformance.decoder.stream import *
