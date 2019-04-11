"""
VC-2-specific bitstream serialisation/deserialistion logic
==========================================================

This sub-module contains all of the VC-2 specific parts of a VC-2 bitstream
serialiser/deserialiser implementation.

This module is divided into two parts:

1. A set of data structure definitions (defined using
   :py:module:`vc2_conformance.fixeddict`) which should be used to
   represent deserialised VC-2 bitstreams. (the :py:module:`fixeddicts`
   sub-module)
2. A set of token-emitting generator functions (see :py:module`generator_io`)
   which are, where possible, very nearly copy-and-pasted from the VC-2
   specification pseudo-code (the rest of this sub-module).

The structure definitions largely serve to document the hierarchy of 'context'
objects assembled/used when processing bitstreams but in some cases also
provide convenience APIs for manipulating or creating deserialised bitstreams.
"""

from vc2_conformance.bitstream.vc2.fixeddicts import *

from vc2_conformance.bitstream.vc2.slice_arrays import *
from vc2_conformance.bitstream.vc2.general import *
