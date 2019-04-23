r"""
VC-2 bitstream serialisation/deserialistion library.
====================================================

This module implements a library for deserialising, manipulating and
serialising VC-2 bitstreams at a low-level. It is intended for the following
purposes:

* Displaying VC-2 bitstream-level information in a human readable form,
  including out-of-spec bitstreams.
* Manipulating existing VC-2 bitstreams.
* Hand-crafting VC-2 bitstreams from scratch.
* Creating in- and out-of-spec bitstreams.

Specifically, this module is emphatically *not* intended to be used as the
bitstream parser for a conformance-checking decoder implementation and should
be considered 'informative' only.

Implementation
--------------

This module is split into three parts.

1. The :py:module:`io` provide a simple API for performing low-level bitwise
   I/O on file-like objects.
2. The :py:module:`serdes` module implements a *generic* framework for
   serialising, deserialising and analysing bitstreams described in the
   procedural-style used in the VC-2 specification pseudo code.
3. The :py:module:`vc2` module contains all of the VC-2 specific code which
   defines the underlying bitstream format.

The :py:module:`serdes` library forms the heart of this implementation and
effectively allows pseudo code to be copied from the specification and, with
minimal transformation, be used to drive a bitstream serialiser/deserialiser.
It is strongly recommended that future implementers begin by reading the
introduction to that module.
"""

# Low-level bitwise file reading/writing
from vc2_conformance.bitstream.io import *

# Generic bitstream serialisation/deserialisation framework
from vc2_conformance.bitstream.serdes import *

# VC-2 specific parts
from vc2_conformance.bitstream.vc2 import *
