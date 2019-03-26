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

Conversely this module is emphatically *not* intended to be used as the
bitstream parser for a conformance-checking decoder implementation. The
structure of this module is orthogonal to the structure of the specification
making its equivalence more difficult to verify. This implementation should be
considered 'informative' only.

This module has not been designed with performance in mind. Whenever there is a
trade-off between performance and usability/clarity, the clearer or more usable
approach has been taken.


Overview
========

This module defines a number of subclasses of :py:class:`BitstreamValue`. Each
of these classes represents a deserialised piece of a VC-2 bitstream. In
general, the deserialised value is represented by a Python type (for example an
integer or enumeration).

:py:class:`BitstreamValue`\ s can be populated from a file-like object by
providing a :py:class:`BitstreamReader` instance to the
:py:meth:`BitstreamValue.read` method. Likewise, values can be seriallised into
a file-like object by passing a :py:class:`BitstreamWriter` into
:py:meth:`BitstreamValue.write`.
"""

# Low-level bitwise file reading/writing
from vc2_conformance.bitstream.io import *

# The BitstreamValue base class
from vc2_conformance.bitstream.base import *

# Pseudo-values (e.g. ConstantValue, FunctionValue)
from vc2_conformance.bitstream.pseudo import *

# Primitive bitstream types (e.g. Bool, UInt...)
from vc2_conformance.bitstream.primitive import *

# General purpose compound types (e.g. Concatenation)
from vc2_conformance.bitstream.compound import *

# General purpose wrapper types (e.g. BoundedBlock)
from vc2_conformance.bitstream.wrapper import *

# Complete VC-2 bitstream structures
from vc2_conformance.bitstream.vc2 import *
