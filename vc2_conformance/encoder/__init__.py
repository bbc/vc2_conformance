"""
A simple VC-2 encoder
=====================

This module implements a simple VC-2 encoder which is used to produce test
streams for conformance testing purposes. It is fairly slow and performs only
simple picture compression.

Example usage
-------------

    >>> from vc2_conformance.codec_features import CodecFeatures
    >>> from vc2_conformance.bitstream import (
    ...     Stream,
    ...     autofill_and_serialise_stream,
    ... )
    >>> from vc2_conformance.encoder import make_sequence

    >>> # Create a Sequence containing a particular set of pictures for a
    >>> # particular video codec configuration.
    >>> codec_features = CodecFeatures(...)
    >>> pictures = [
    ...     {"Y": ..., "C1": ..., "C2": ..., "pic_num": 100},
    ...     # ...
    ... ]
    >>> sequence = make_sequence(codec_features, pictures)

    >>> # Serialise to a file
    >>> with open("bitstream.vc2", "wb") as f:
    ...     autofill_and_serialise_stream(f, Stream(sequences=[sequence]))

Level constraints
-----------------

For the most part, all of the parameters which could be restricted by a VC-2
level are chosen in the supplied
:py:class:`~vc2_conformance.codec_features.CodecFeatures`. As such, choosing
parameters which comply with the declared level is the responsibility of the
caller, perhaps by subsequently decoding the sequence with the bitstream
validator (:py:mod:`vc2_conformance.decoder`).

Some choices are left up to this encoder, such as how best to encode a set of
video parameters in a sequence header. In these cases, the encoder must make
choices which comply with the supplied level. Since levels are expressed as a
table of constraints (see :py:class:`vc2_conformance.level_constraints` and
:py:class:`vc2_conformance.constraint_table`), this process potentially
requires the use of a global constraint solver.

Fortunately, all existing VC-2 levels are specified such that, once the level
(and a few other parameters) have been defined, allmost all constrained
parameters are independent meaning that global constraint solving is not
required. The only case where dependencies exist are the parameters relating to
sequence headers. As a conseiquence the
:py:mod:`~vc2_conformance.encoder.sequence_header` generation module uses a
simple constraint solver internally.

.. note::

    The parameter independence property of the VC-2 levels mentioned above is
    essential for the encoder to generate level-conforming bitstreams. A test
    in ``tests/encoder/test_level_constraints_assumptions.py`` is provided
    which will fail should a future VC-2 level not have this property. See the
    documentation at the top of this file for a more thorough introduction and
    discussion of this topic.
"""

# Exceptions thrown when impossible requests are made of the encoder
from vc2_conformance.encoder.exceptions import *

# Sequence header construction
from vc2_conformance.encoder.sequence_header import *

# Picture compression
from vc2_conformance.encoder.pictures import *

# Complete sequence assembly
from vc2_conformance.encoder.sequence import *
