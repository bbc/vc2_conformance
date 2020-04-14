"""
A simple VC-2 encoder
=====================

This module implements a simple VC-2 encoder which is used to produce test
streams for conformance testing purposes. It is fairly slow and performs only
simple picture compression.

Example usage
-------------

    >>> from vc2_conformance.codec_features import CodecFeatures
    >>> from vc2_conformance.bitstream import autofill_and_serialise_sequence
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
    ...     autofill_and_serialise_sequence(f, sequence)

"""

# Sequence header construction
from vc2_conformance.encoder.sequence_header import *

# Picture compression
from vc2_conformance.encoder.pictures import *

# Complete sequence assembly
from vc2_conformance.encoder.sequence import *
