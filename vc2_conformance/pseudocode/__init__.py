"""
VC-2 pseudocode functions and data structures
=============================================

This module contains implementations of many of the VC-2 pseudocode functions
and associated data structures. In particular, it includes everything which can
be used as-is in the construction of encoders, decoders and so on without any
alterations.

The VC-2 pseudocode is augmented by a modest number of additional functions or
data structure fields. For instance, additional fields are added to
:py:class:`~vc2_conformance.pseudocode.state.State` which are used by
conformance checking routines and forward wavelet transform routines.


"""

from vc2_conformance.pseudocode.arrays import *
from vc2_conformance.pseudocode.offsetting import *
from vc2_conformance.pseudocode.parse_code_functions import *
from vc2_conformance.pseudocode.picture_decoding import *
from vc2_conformance.pseudocode.picture_encoding import *
from vc2_conformance.pseudocode.quantization import *
from vc2_conformance.pseudocode.slice_sizes import *
from vc2_conformance.pseudocode.state import *
from vc2_conformance.pseudocode.vc2_math import *
from vc2_conformance.pseudocode.video_parameters import *

from vc2_conformance.pseudocode.metadata import *
