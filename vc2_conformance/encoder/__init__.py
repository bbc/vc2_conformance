r"""
The :py:mod:`vc2_conformance.encoder` module implements a simple VC-2 encoder
which is used to produce test streams for conformance testing purposes (see
:py:mod:`vc2_conformance.test_cases`). It is extremely slow and performs only
simple picture compression, but is sufficiently flexible to support all VC-2
coding modes.

The encoder is principally concerned with carrying out the following tasks:

* Encoding the video and codec configuration into a sequence header
  (see :py:mod:`vc2_conformance.encoder.sequence_header`).
* Transforming, slicing and quantizing pictures (i.e. compressing them)
  (see :py:mod:`vc2_conformance.encoder.pictures`).
* Assembling sequences of data units comprising a complete VC-2 stream
  (see :py:mod:`vc2_conformance.encoder.sequence`).

This module does not generate serialised VC-2 bitstreams in binary format.
Instead, it generates a bitstream description data structure which may
subsequently be serialised by the bitstream serialiser in the
:py:mod:`vc2_conformance.bitstream` module. This design allows the generated
bitstream to be more easily manipulated prior to serialisation if required for
a particular test case.


Usage
-----

The encoder behaviour is controlled by a
:py:class:`~vc2_conformance.codec_features.CodecFeatures` dictionary. This
specifies picture/video format to be compressed (e.g. resolution etc.) along
with the coding options (e.g. wavelet transform and bitrate). See the
:py:mod:`vc2_conformance.codec_features` module for more details. There are
essentially two modes of operation, depending on the value of
:py:class:`~vc2_conformance.codec_features.CodecFeatures`\ ``["lossless"]``:

* Lossless mode: variable bitrate, qindex is always 0.
* Lossy mode: fixed bit rate, variable qindex.

A series of pictures may be encoded into a VC-2 sequence using the
:py:func:`vc2_conformance.encoder.make_sequence` function, and then serialised
into a binary bitstream as illustrated below::

    >>> # Define the video format to be encoded and basic coding options
    >>> from vc2_conformance.codec_features import CodecFeatures
    >>> codec_features = CodecFeatures(...)

    >>> # Encode a series of pictures
    >>> from vc2_conformance.encoder import make_sequence
    >>> pictures = [
    ...     {"Y": ..., "C1": ..., "C2": ..., "pic_num": 100},
    ...     # ...
    ... ]
    >>> sequence = make_sequence(codec_features, pictures)

    >>> # Serialise to a file
    >>> from vc2_conformance.bitstream import (
    ...     Stream,
    ...     autofill_and_serialise_stream,
    ... )
    >>> with open("bitstream.vc2", "wb") as f:
    ...     autofill_and_serialise_stream(f, Stream(sequences=[sequence]))


Bitstream conformance
---------------------

This encoder will produce bitstreams conformant with the VC-2 specification
whenever the coding parameters specified represent a legal combination.

In some cases, invalid coding options will cause the encoder to fail and raise
an exception in :py:mod:`vc2_conformance.encoder.exceptions`. For example, if
lossless coding and the low delay profile are requested simultaneously.

In other cases, the encoder will produce a bitstream, however this bitstream
will be non-conformant. For example, if the clean area defined is larger than
the frame size, the encoder will ignore this inconsistency of metadata and
produce a (non-conformant) bitstream anyway.

When conformant bitstreams are required, it is the responsibility of the user
of the encoder to ensure that the provided
:py:class:`~vc2_conformance.codec_features.CodecFeatures` are valid. In
practice, the easiest way to do this is to check for exceptions when the
encoder is used then use the bitstream validator
(:py:mod:`vc2_conformance.decoder`) to validate the generated bitstream.


Exceptions
----------

.. automodule:: vc2_conformance.encoder.exceptions


Sequence header generation
--------------------------

.. automodule:: vc2_conformance.encoder.sequence_header


Picture encoding & compression
------------------------------

.. automodule:: vc2_conformance.encoder.pictures


Sequence generation
-------------------

.. automodule:: vc2_conformance.encoder.sequence


Level constraints
-----------------

For the most part, all of the parameters which could be restricted by a VC-2
level are chosen in the supplied
:py:class:`~vc2_conformance.codec_features.CodecFeatures`. As such, choosing
parameters which comply with the declared level is the responsibility of the
caller (see comments above). However, some coding choices restricted by levels
are left up to this encoder, such as how video parameters are coded in a
sequence header. In these cases, the encoder makes choices which comply with
the supplied level, a process which may require a constraint solving procedure.

In principle level constaints, as expressed by constraints tables (see
:py:class:`vc2_conformance.constraint_table` and
:py:class:`vc2_conformance.level_constraints`), could require a full global
constraint solver to resolve. Fortunately, all existing VC-2 levels are
specified such that, once the level (and a few other parameters) have been
defined, almost all constrained parameters are independent meaning that global
constraint solving is not required. The only case where constraint dependencies
exist are the parameters relating to sequence headers. As a consequence the
:py:mod:`~vc2_conformance.encoder.sequence_header` generation module uses a
simple constraint solver internally.

.. note::

    The constraint parameter independence property of the VC-2 levels mentioned
    above is essential for the encoder to generate level-conforming bitstreams.
    A test in ``tests/encoder/test_level_constraints_assumptions.py`` is
    provided which will fail should a future VC-2 level not have this property.
    See the detailed documentation at the top of this file for a more thorough
    introduction and discussion of this topic.


"""

# Exceptions thrown when impossible requests are made of the encoder
from vc2_conformance.encoder.exceptions import *

# Sequence header construction
from vc2_conformance.encoder.sequence_header import *

# Picture compression
from vc2_conformance.encoder.pictures import *

# Complete sequence assembly
from vc2_conformance.encoder.sequence import *
