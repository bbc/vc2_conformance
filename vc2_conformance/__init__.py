"""
The main VC-2 conformance software is contained within the
:py:mod:`vc2_conformance` module.

..
    You are currently reading VC-2 conformance documentation in its source form
    (e.g. directly from the Python source docstrings or via ``help()``). You
    may prefer to read the HTML/PDF version of this documentation where images
    and cross references will be displayed more usefully.

.. note::

    Before going any further you should familiarize yourself with the
    :ref:`user-guide` which gives an introduction of the general tasks carried
    out by the conformance software.

Below we give a general overview of the design of the conformance software.


Main components
---------------

The VC-2 conformance software consists of four main components:

* A reference VC-2 decoder, including bitstream validation logic
  (:py:mod:`vc2_conformance.decoder`)
* A flexible VC-2 encoder (:py:mod:`vc2_conformance.encoder`)
* A VC-2 bitstream manipulation library (:py:mod:`vc2_conformance.bitstream`)
* A set of test case generation routines (:py:mod:`vc2_conformance.test_cases`)

The reference decoder and bitstream validator forms a key part of the
conformance testing procedures (via the :ref:`vc2-bitstream-validator`
command). This decoder is based directly on the pseudocode published in the
VC-2 standard. Refer to the :py:mod:`vc2_conformance.decoder` module
documentation for a full introduction to this component.

The encoder is used internally to generate decoder test cases. This encoder is
flexible enough to support all of VC-2 features but otherwise simplistic in
terms of runtime performance and picture quality. Further documentation on the
encoder's design and functionality can be found in the
:py:mod:`vc2_conformance.encoder` module.

The bitstream manipulation library in the :py:mod:`vc2_conformance.bitstream`
module is used internally for three purposes.  Firstly it is used during
decoder test case generation to produce bitstreams with specific properties.
Secondly it is used by the :ref:`vc2-bitstream-viewer` command to produce human
readable descriptions of bitstream contents. Finally it is used extensively by
the VC-2 conformance software's own test suite to generate and check
bitstreams.

Finally, the test case generation routines form the basis of the
:ref:`vc2-test-case-generator` tool which generates test pictures and
bitstreams used during conformance testing procedures. These will be introduced
in :ref:`maintainer-test-case-generator`.


Use of VC-2 pseudocode
----------------------

The VC-2 conformance software design prioritises correctness and consistency
with the VC-2 specification. To achieve this, significant parts are built using
the pseudocode within the VC-2 specification.

The VC-2 specification uses pseudocode to define the nominal operation of a
VC-2 decoder. The pseudocode language used is sufficiently similar to Python
that a translation from pseudocode into executable Python is trivial. Automated
translation is also possible using the `VC-2 Pseudocode Parser tool
<https://github.com/bbc/vc2_pseudocode_parser>`_. Once translated, the
pseudocode may be used as the basis for correct-by-definition implementations
of parts of a VC-2 codec.

The reference VC-2 decoder and bitstream validator
(:py:mod:`vc2_conformance.decoder`) consists of the VC-2 pseudocode
(implementing the decoder behaviour) augmented with additional checks
(implementing the validation logic).

The VC-2 encoder (:py:mod:`vc2_conformance.encoder`), though not specified by
the VC-2 standard, nevertheless makes substantial use of the VC-2 pseudocode
functions. For example routines for computing slice dimensions are reused while
other parts, such as the forward discrete wavelet transform are simple
inversions of the decoder pseudocode. The correctness of these inversions is
relatively easily verified in the test suite thanks to the invertability of
VC-2's transforms.

The bitstream manipulation library (:py:mod:`vc2_conformance.bitstream`)
provides routines for serialising and deserialising binary bitstreams into
easily manipulated Python data structures.  With the exception of the Python
data structure definitions, this library is based entirely on the VC-2
pseudocode, using the :py:mod:`~vc2_conformance.bitstream.serdes` framework.

To ensure consistency with the VC-2 pseudocode, the conformance software's test
suite automatically compares the software's source code with the pseudocode to
verify equivalence. See the :py:mod:`verification` module for details.


Performance
-----------

The major drawback of the pseudocode-driven approach used by this software is
poor performance. The VC-2 pseudocode is structured with comprehensibility as
its main priority and therefore often has poor algorithmic performance.
Further, the use of Python -- due to its similarity with the pseudocode and
high level of abstraction -- introduces an additional performance overhead.

Another source of slow performance is the use of infinite precision (i.e.
native Python) integers whenever possible. This helps avoid the class of bugs
relating to the use of insufficient integer bit width in most calculations. The
dynamic range of signals passing through a VC-2 codec can grow dramatically
(i.e. by many orders of magnitude) and vary significantly between superficially
similar inputs. As a consequence, this class of bug is all too easy to
introduce without infinite precision arithmetic.

As a result of the above factors, the conformance software may take on the
order minutes to encode or decode each picture in a stream. While this would be
unacceptable for a production encoder or decoder, the conformance software is
intended only for use with only extremely short sequences, where correctness is
the most significant factor.

The majority of test cases apply to decoders for which all necessary materials
(test bitstreams and reference decodings) may be produced in an 'overnight'
batch process after which the tools are not needed.  The remaining (encoder)
test cases generally amount to fewer than ten frames.


Test case generation
--------------------

Since VC-2 supports a great variety of configurations, parametrised test case
generators (:py:mod:`vc2_conformance.test_cases`) are used rather than a
'universal' collection of bitstreams. While this means that users of the
conformance software are required to configure and run the test case generator
themselves, it also simplifies the testing process by ensuring only relevant
test cases are produced. Furthermore, it allows certain tests to be highly
tailored to a particular configuration.  For example, signal range tests are
targeted specifically at the specific wavelet transform configuration, bit
width and quantization matrices used.


External packages
-----------------

Some smaller, or more specialised aspects of the conformance testing software
have been split into their own separate Python packages. These are:

:py:mod:`vc2_conformance_data`
    Larger data files (including pictures and precomputed values) which are
    used to generate certain test cases.

:py:mod:`vc2_data_tables`
    General VC-2 related constants (e.g.
    :py:data:`~vc2_data_tables.PARSE_INFO_PREFIX`), enumerated values (e.g.
    :py:class:`~vc2_data_tables.ParseCodes`) and tabular data used during
    coding (e.g. :py:data:`~vc2_data_tables.PRESET_FRAME_RATES`).

:py:mod:`vc2_bit_widths`
    Computes near worst-case inputs for VC-2 encoders and decoders which
    produce very large signal values. This package is used to generate test
    cases to verify codecs have used large enough integers in their
    implementations.




"""

from vc2_conformance.version import __version__
