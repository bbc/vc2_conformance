r"""
:py:mod:`vc2_conformance.bitstream`: VC-2 bitstream serialisation/deserialistion library
========================================================================================

This module implements facilities for for deserialising, displaying,
manipulating and serialising VC-2 bitstreams at a low-level. It is intended to
be able to both deserialise and serialise conformant and out-of-spec
bitstreams. It explicitly does *not* form part of the reference conformance
checking decoder, however.

This module is used by the VC-2 conformance software to produce human-friendly
descriptions of VC-2 bitstreams and also to generate sample bitstreams. It may
also be used by advanced external users for mechanically generating, inspecting
or manipulating bitstreams, if required.

As with the conformance checking decoder, this module prioritises correctness
over all other factors. As such, performance is usuable for development
purposes but expect several seconds-per-frame (not frames-per-second)
processing times.


Quick-start/teaser example
--------------------------

The following minimal example can be used to deserialise a complete VC-2
bitstream sequence::

    >>> from vc2_conformance.bitstream import Deserialiser, BitstreamReader, parse_sequence
    
    >>> with open("/path/to/bitstream.vc2", "rb") as f:
    ...     reader = BitstreamReader(f)
    ...     with Deserialiser(reader) as des:
    ...         parse_sequence(des)
    
    >>> # Display in pretty-printed human-readable form
    >>> str(des.context)
    Sequence:
      data_units:
        0: DataUnit:
          parse_info: ParseInfo:
            padding: 0b
            parse_info_prefix: Correct (0x42424344)
            parse_code: sequence_header (0x00)
            next_parse_offset: 17
            previous_parse_offset: 0
          sequence_header: SequenceHeader:
            padding: 0b
            parse_parameters: ParseParameters:
              major_version: 3
              minor_version: 0
    <...and so on...>
    
    >>> # Deserialised values are kept in a nested dictionary structure which can
    >>> # be accessed as usual:
    >>> des.context["data_units"][0]["parse_info"]["parse_info_prefix"]
    1111638852

New users of this module should begin by reading the introduction to the
:py:class:`serdes` module which provides the :py:class:`Deserialiser` class
described above.


API
---

This module is split into four parts:

* A low-level bitstream I/O library, :py:mod:`vc2_conformance.bitstream.io`
* The generic :py:mod:`vc2_conformance.bitstream.serdes`
  serialiser/deserialiser framework
* A VC-2 bitstream description based on the :py:mod:`~.serdes` framework (in
  :py:mod:`vc2_conformance.bitstream.vc2`)
* A set of :py:mod:`~vc2_conformance.fixeddict` dictionary types which make it
  easy to display and safely manipulate deserialised bitstreams (in
  :py:mod:`vc2_conformance.bitstream.vc2_fixeddicts`).

To encourage correctness, the provided serialiser/deserialiser was designed in
such a way as to closely match the pseudo-code of the reference VC-2 decoder in
the VC-2 specification. To facilitate this, the :py:mod:`.serdes` submodule
implements a framework for turning VC-2 pseudo-code descriptions into complete
bitstream serialisers and deserialisers.

Where possible, the same Python-translation of the VC-2 pseudo code is used as
the conformance-checking decoder. In some cases, however, deviations are
required either to support the :py:mod:`.serdes` framework or to enable
out-of-spec values to be handled. These serialisation/deserialisation specific
versions of the VC-2 pseudo code can be found in the :py:mod:`.vc2` submodule.

.. automodule:: vc2_conformance.bitstream.io
    :members:

.. automodule:: vc2_conformance.bitstream.serdes

.. automodule:: vc2_conformance.bitstream.vc2

.. automodule:: vc2_conformance.bitstream.vc2_fixeddicts
    :members:
"""

# Low-level bitwise file reading/writing
from vc2_conformance.bitstream.io import *

# Generic bitstream serialisation/deserialisation framework
from vc2_conformance.bitstream.serdes import *

# VC-2 specific parts
from vc2_conformance.bitstream.vc2 import *
from vc2_conformance.bitstream.vc2_fixeddicts import *

# Metadata for introspection purposes
from vc2_conformance.bitstream.metadata import *
