"""
VC-2 Conformance Testing Tools
==============================

These tools are intended to be used to verify the conformance of VC-2 encoder
and decoder designs to the VC-2 specifications. A normative statement of their
use is prescribed in SMPTE Recommended Practice RP2042-3.

This Python package includes the following key components:

* A conformance checking VC-2 decoder which validates VC-2 bitstream
  conformance and produces reference pictures.
* Tools for displaying VC-2 bitstreams in a human-readable form as a debugging
  aid for codec implementors.
* Tools for generating VC-2 bitstreams to test VC-2 decoder implementations.
* Tools for generating reference pictures to test VC-2 encoder implementations.
"""

from vc2_conformance import exceptions

# VC-2 pseudocode functions
from vc2_conformance import vc2_math
from vc2_conformance import parse_code_functions
from vc2_conformance import slice_sizes
from vc2_conformance import video_parameters

# VC-2 datastructures
from vc2_conformance import state

# VC-2 constants and tables
import vc2_conformance.tables

# Conformance-checking VC-2 decoder implementation
from vc2_conformance import decoder

# Bitstream seriallisation and deseriallisation utilities (for generating and
# displaying bitstreams -- not used by the decoder)
from vc2_conformance import bitstream
