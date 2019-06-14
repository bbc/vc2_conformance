"""
:py:mod:`vc2_conformance.decoder`: A VC-2 decoder which checks the bitstream for conformance.
=============================================================================================

This module contains the components of a VC-2 decoder based on the pseudocode
published in the VC-2 specification. Along with the basic decoding logic,
additional code is included to check all conditions enforced by the
specification.


Module usage
------------

The following snippet illustrates how a VC-2 bitstream might be decoded and
verified using this module::

    >>> from vc2_conformance._string_utils import wrap_paragraphs
    >>> from vc2_conformance.state import State
    >>> from vc2_conformance.decoder import init_io, parse_sequence, ConformanceError
    
    >>> # Create a callback to be called with picture data whenever a picture
    >>> # is decoded from the bitstream.
    >>> def output_picture_callback(picture, video_parameters):
    >>>     print("A picture was decoded...")
    
    >>> # Create an initial state object ready to read the bitstream
    >>> state = State(_output_picture_callback=output_picture_callback)
    >>> f = open("path/to/bitstream.vc2", "rb")
    >>> init_io(state, f)
    
    >>> # Decode and validate!
    >>> try:
    ...     parse_sequence(state)
    ...     print("Bitstream is valid!")
    ... except ConformanceError as e:
    ...     print("Bitstream is NOT valid:")
    ...     print(wrap_paragraphs(e.explain(), 80))
    Bitstream is NOT valid:
    An invalid parse code, 0x0A, was provided to a parse info header (10.5.1).
    <BLANKLINE>
    See (Table 10.1) for the list of allowed parse codes.
    <BLANKLINE>
    Perhaps this bitstream conforms to an earlier or later version of the VC-2
    standard?

The implementations of the VC-2 pseudocode functions in this module are
augmented with checks which throw :py:mod:`vc2_conformance.decoder.exceptions`
whenever a conformance issue is found. These exceptions include a selection of
methods produce detailed, human readable explanations of the reasons for
conformance failure and references to the specification sections of relevance.
"""

from vc2_conformance.decoder.exceptions import *

# (A) Bitstream I/O operations
from vc2_conformance.decoder.io import *

# (10) Stream syntax
from vc2_conformance.decoder.stream import *

# (11) Sequence Header
from vc2_conformance.decoder.sequence_header import *

# (12) Picture Syntax
from vc2_conformance.decoder.picture_syntax import *

# (13) Transform Data Syntax
from vc2_conformance.decoder.transform_data_syntax import *

# (14) Fragment Syntax
from vc2_conformance.decoder.fragment_syntax import *
