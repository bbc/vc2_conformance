.. module:: vc2_conformance

Internals overview
==================

.. note::

    Before going any further you should familiarize yourself with the
    :ref:`user-guide` which gives an detailed introduction of the general tasks
    carried out by the conformance software.

Main components
---------------

The VC-2 conformance software consists of four main components:

* A reference VC-2 decoder, including bitstream validation logic
* A flexible VC-2 encoder
* A VC-2 bitstream manipulation library
* A set of test case generation routines

The reference decoder and bitstream validator forms a key part of the
conformance testing procedures and is exposed via the
:ref:`vc2-bitstream-validator` command. The decoder will be described in
greater detail in :ref:`maintainer-decoder`.

The encoder is internally used for the generation of decoder test cases.  This
encoder is flexible enough to support all of VC-2 features but otherwise
simplistic in terms of runtime performance and picture quality. The decoder
will be described in greater detail in :ref:`maintainer-encoder`.

The bitstream manipulation library, described in :ref:`maintainer-bitstream` is
used internally for three purposes.  Firstly it is used by decoder test case
generators to produce bitstreams with specific properties. Secondly it is used
by the :ref:`vc2-bitstream-viewer` command to produce human readable
descriptions of bitstream contents. Finally it is used extensively by the VC-2
conformance software's own test suite to generate and check bitstreams.

Finally, the test case generation routines form the basis of the
:ref:`vc2-test-case-generator` tool which generates test pictures and
bitstreams used during conformance testing procedures. These will be introduced
in :ref:`maintainer-test-case-generator`.


Test suite
----------

The conformance software is accompanied by an automated test suite (which
comprises the majority of the overall codebase) which attempts to verify the
conformance software's behaviour under a wide variety of circumstances.


Use of VC-2 pseudocode
----------------------

The VC-2 conformance software design prioritises correctness and consistency
with the VC-2 specification. To achieve this, significant parts are built using
the pseudocode within the VC-2 specification.

The VC-2 specification uses pseudocode to define the nominal operation of a
VC-2 decoder. The pseudocode language used is sufficiently similar to Python
that a translation from pseudocode into executable Python is trivial. Once
translated, the pseudocode may be used as the basis for correct-by-definition
implementations of parts of a VC-2 codec.

The reference VC-2 decoder and bitstream validator consists of the VC-2
pseudocode (implementing the decoder behaviour) augmented with additional
checks (implementing the validation logic).

The VC-2 encoder, though not specified by the VC-2 standard, nevertheless makes
substantial use of the VC-2 pseudocode functions. For example routines for
computing slice dimensions are reused while other parts, such as the forward
discrete wavelet transform simple inversions of the decoder pseudocode.

The bitstream manipulation library provides routines for serialising and
deserialising binary bitstreams into easily manipulated Python data structures.
With the exception of the Python data structure definitions, this library is
based entirely on the VC-2 pseudocode.

To ensure consistency with the VC-2 pseudocode, the conformance software's test
suite automatically compares the software's source code with the pseudocode to
verify equivalence.


Performance
-----------

The major drawback of the pseudocode-driven approach used by this software is
performance. The VC-2 pseudocode is structured with comprehensibility as its
main priority and therefore often has poor algorithmic performance. Further,
the use of Python -- due to its similarity with the pseudocode and high level
of abstraction -- introduces an additional performance overhead.

Another source of slow performance is the use of infinite precision (i.e.
native Python) integers whenever possible. This helps avoid the class of bugs
relating to the use of insufficient integer bit width in most calculations. The
dynamic range of signals passing through a VC-2 codec can grow dramatically
(i.e. by many orders of magnitude) and vary significantly between superficially
similar inputs. As a consequence, this class of bug is all too easy to
introduce and so infinite precision arithmetic is valuable for ensuring
correctness.

As a result of the above factors, the conformance software may take on the
order minutes to encode or decode each picture in a stream. While this would be
unacceptable for a real encoder or decoder, the conformance software is
intended only for use with only extremely short sequences, where correctness is
the most significant factor.

The majority of test cases apply to decoders for which all necessary materials
(test bitstreams and reference decodings) may be produced in an 'overnight'
batch process after which the tools are not needed.  The remaining (encoder)
test cases generally amount to fewer than ten frames.


Test case generation
--------------------

Since VC-2 supports a great variety of configurations, a parametrised test case
generator is used rather than a 'universal' collection of bitstreams. While
this means that users of the conformance software are required to configure and
run the test case generator themselves, it also simplifies the testing process
by ensuring only relevant test cases are produced. Furthermore, it allows
certain tests to be highly tailored to a particular configuration. For example,
signal range tests are targeted specifically at the specific wavelet transform
configuration, bit width and quantization indices used.


