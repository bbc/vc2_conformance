"""
The :py:mod:`vc2_conformance.decoder` module contains the components of a VC-2
decoder and bitstream validator. Along with the basic decoding logic,
additional tests are included to check all conditions imposed on bitstreams by
the VC-2 specification.

Usage
-----

The bitstream decoder/validator is exposed to end-users via the
:ref:`vc2-bitstream-validator` command line utility.

This module may also be used directly. The following snippet illustrates how a
VC-2 bitstream might be decoded and verified using this module::

    >>> from vc2_conformance.string_utils import wrap_paragraphs
    >>> from vc2_conformance.pseudocode import State
    >>> from vc2_conformance.decoder import init_io, parse_stream, ConformanceError

    >>> # Create a callback to be called with picture data whenever a picture
    >>> # is decoded from the bitstream.
    >>> def output_picture_callback(picture, video_parameters, picture_coding_mode):
    >>>     print("A picture was decoded...")

    >>> # Create an initial state object ready to read the bitstream
    >>> state = State(_output_picture_callback=output_picture_callback)
    >>> f = open("path/to/bitstream.vc2", "rb")
    >>> init_io(state, f)

    >>> # Decode and validate!
    >>> try:
    ...     parse_stream(state)
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


Overview
--------

This decoder is based on the pseudocode published in the VC-2 specification and
consequently follows the same structure as the pseudocode with the
:py:func:`~vc2_conformance.decoder.stream.parse_stream` function being used to
decode a complete stream.

The pseudocode is automatically verified for consistency with the VC-2
specification by the conformance software test suite. Verified pseudocode
functions are annotated with the
:py:func:`~vc2_conformance.pseudocode.metadata.ref_pseudocode` decorator. See
:py:mod:`verification` (in the ``tests/`` directory) for details on the
automated verification process. All bitstream validation logic, which doesn't
form part of the specified pseudocode, appears between ``## Begin not in spec``
and ``## End not in spec`` comments.

All global state is passed around via the
:py:class:`~vc2_conformance.pseudocode.state.State` dictionary. This dictionary
is augmented with a number of additional entries not included in the VC-2
specification but which are necessary for a 'real' decoder implementation (e.g.
an input file handle) and for validation purposes (e.g. recorded offsets of
previous data units). See :py:class:`vc2_conformance.pseudocode.state.State`
for a complete enumeration of these.

Underlying I/O operations are not specified by the VC-2 specification. This
decoder reads streams from file-like objects. See
the :py:mod:`vc2_conformance.decoder.io` module for details. As illustrated in
the example above, the :py:func:`~vc2_conformance.decoder.io.init_io` function
is used to specify the file-like object the stream will be read from.

When conformance errors are detected,
:py:exc:`~vc2_conformance.decoder.exceptions.ConformanceError` exceptions are
thrown. These exceptions provide in-depth human readable explanations of
conformance issues along with suggested invocations of the
:ref:`vc2-bitstream-viewer` tool for diagnosing issues. See the
:py:mod:`vc2_conformance.decoder.exceptions` module for details. These
exceptions are largely thrown directly by validation code spliced into the
pseudocode routines. Some common checks are factored out into their own
'assertions' in the :py:mod:`vc2_conformance.decoder.assertions`.

The decoder logic is organised in line with the sections of the VC-2
specification:

* :py:mod:`vc2_conformance.decoder.io`: (A) Bitstream I/O
* :py:mod:`vc2_conformance.decoder.stream`: (10) Stream syntax
* :py:mod:`vc2_conformance.decoder.sequence_header`: (11) Sequence header
* :py:mod:`vc2_conformance.decoder.picture_syntax`: (12) Picture syntax
* :py:mod:`vc2_conformance.decoder.transform_data_syntax`: (13) Transform data
  syntax
* :py:mod:`vc2_conformance.decoder.fragment_syntax`: (14) Fragment syntax

The :py:mod:`vc2_conformance.decoder` module only includes pseudocode functions
which define additional behaviour not defined by the spec.  Specifically, this
includes performing I/O or additional checks for bitstream validation purposes.
All other pseudocode routines are used 'verbatim' and can be found in
:py:mod:`vc2_conformance.pseudocode`.


Stream I/O
----------

.. automodule:: vc2_conformance.decoder.io


Conformance exceptions
----------------------

.. automodule:: vc2_conformance.decoder.exceptions


Sequence composition restrictions
---------------------------------

Various restrictions may be imposed on choice and order of data unit types in a
sequence. For example, all sequences must start with a sequence header and end
with an end of sequence. Some levels impose additional restrictions such as
prohibiting the mixing of fragments and pictures or requiring sequence headers
to be interleaved between every picture.

Rather than using ad-hoc logic to enforce these restrictions, regular
expressions are used to check the pattern of data unit types. See the
:py:mod:`vc2_conformance.symbol_re` module for details on the regular
expression matching system.


Level constraints
-----------------

VC-2's levels impose additional constraints on bitstreams, for example
restricting some fields to particular ranges of values. Rather than including
ad-hoc validation logic for each level, a 'constraints table' is used.
Bitstream values which may be constrained are checked using
:py:func:`vc2_conformance.decoder.assertions.assert_level_constraint`.

See the :py:mod:`vc2_conformance.constraint_table` module for an introduction
to constraint tables. See the :py:mod:`vc2_conformance.level_constraints`
module for level-related constraint data, including documentation on the
entries included in the levels constraints table.
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
