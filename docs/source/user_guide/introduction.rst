.. _guide-introduction:

Introduction
============

In this guide we'll walk through the steps involved in testing a VC-2
implementation for conformance to SMPTE ST 2042-family of specifications.


Testing procedure overview
--------------------------

The conformance testing processes for decoders and encoders is outlined below.

.. image:: /_static/user_guide/overview_decoder.svg

Decoders are tested using a series of test bitstreams (generated using
:ref:`vc2-test-case-generator`). The pictures produced by the decoder are then
compared against reference decodings. If the decoded pictures are bit-for-bit
identical (as checked by :ref:`vc2-picture-compare`), and the decoder did not
crash, the decoder passes the test.


.. image:: /_static/user_guide/overview_encoder.svg

Encoders are tested using a series of test pictures (generated using
:ref:`vc2-test-case-generator`). The encoded bitstreams are then fed to a
bitstream validator (:ref:`vc2-bitstream-validator`) which simultaneously
validates the bitstream against the specification and decodes the encoded
pictures. If the bitstream is free from technical errors, the decoded pictures
are then compared with the input pictures (both visually and using
:ref:`vc2-picture-compare`). If the decoded pictures are sufficiently similar to
the inputs, the encoder passes the test.


Guide outline
-------------

In :ref:`guide-installation` we will walk through the process of installing the
VC-2 conformance software on your computer.

In :ref:`guide-file-format` the simple planar raw video file format used by the
conformance software is introduced. You are responsible for converting between
this format and the format natively accepted by the codec under test.

In :ref:`guide-generating-test-cases` we will use the
:ref:`vc2-test-case-generator` tool to generate a set of test pictures and
bitstreams. Because VC-2 supports such a wide variety of video formats and
coding behaviours, test cases are generated on demand to suit the particular
features of a codec under test.

In :ref:`guide-decoder-testing` and :ref:`guide-encoder-testing` we describe
how the test pictures and bitstreams should be processed by the codec under
test. We also describe the procedures for verifying that the codecs behaved as
expected. Additionally, in :ref:`guide-bitstream-testing` we explain how
bitstreams produced outside of the conformance testing procedures can also be
tested for conformance.

In :ref:`guide-debugging` we provide some advice on how to approach the problem
of debugging failing tests.

Finally, in :ref:`guide-limitations` some of the limitations of the conformance
test cases and procedures are enumerated.

So, lets move on to :ref:`guide-installation`...
