r"""
VC-2 bitstream serialisation/deserialistion library.
====================================================

This module implements facilities for for deserialising, displaying,
manipulating and serialising VC-2 bitstreams at a low-level. It is intended to
be able to handle both conformant and out-of-spec bitstreams. It explicitly
does *not* form part of the reference conformance checking decoder, however.

This module is used by the VC-2 conformance software to produce human-friendly
descriptions of VC-2 bitstreams and also to generate sample bitstreams. It may
also be used by advanced external users for mechanically generating, inspecting
or manipulating bitstreams, if required.

As with the conformance checking decoder, this module prioritises correctness
over all other factors. As such, performance is usuable for development
purposes but expect several seconds-per-frame (not frames-per-second)
processing times.


Implementation
--------------

This module is split into three parts:

* The generic :py:mod:`serdes` serialiser/deserialiser framework
* A VC-2 bitstream description based on the :py:mod:`serdes` framework (in
  :py:mod:`vc2`)
* A set of :py:mod:`fixeddict` dictionary types which make it easy to display
  and safely manipulate deserialised bitstreams (in :py:mod:`vc2_fixeddicts`).

To encourage correctness, the provided serialiser/deserialiser was designed in
such a way as to closely match the pseudo-code of the reference VC-2 decoder in
the VC-2 specification. To facilitate this, the :py:mod:`serdes` submodule
implements a framework for turning VC-2 pseudo-code descriptions into complete
bitstream serialisers and deserialisers.

Where possible, the same Python-translation of the VC-2 pseudo code is used as
the conformance-checking decoder. In some cases, however, deviations are
required either to support the :py:mod:`serdes` framework or to enable
out-of-spec values to be handled. These serialisation/deserialisation specific
versions of the VC-2 pseudo code can be found in the :py:mod:`vc2` submodule.

"""

# Low-level bitwise file reading/writing
from vc2_conformance.bitstream.io import *

# Generic bitstream serialisation/deserialisation framework
from vc2_conformance.bitstream.serdes import *

# VC-2 specific parts
from vc2_conformance.bitstream.vc2 import *
from vc2_conformance.bitstream.vc2_fixeddicts import *
