.. _guide-encoder-testing:

VC-2 encoder conformance testing procedure
==========================================

The VC-2 encoder conformance testing procedure is described below. In summary,
the raw video test sequences generated in the
:ref:`guide-generating-test-cases` step will be encoded using the candidate
encoder. The resulting bitstream will then be checked using the
:ref:`vc2-bitstream-validator` and encoded pictures compared with the originals
for similarity.


Encoding the reference bitstreams
---------------------------------

For each codec feature set provided, a set of raw videos are produced. These
are located in directories matching the pattern ``<codec feature set
name>/encoder/<test-case-name>/``. The specific test cases generated will vary
depending on the codec features specified.

Each bitstream must be encoded independently by the encoder under test and the
encoded bitstreams stored on disk and the encoder must not crash or produce any
warnings.


Checking the encoded bitstreams
-------------------------------

Each encoded bitstream must be checked with the :ref:`vc2-bitstream-validator`.
This tool simultaneously verifies that the bitstream meets the requirements of
the VC-2 specification and provides a reference decoding of the stream.

The tool takes a VC-2 bitstream as argument and optionally an output name for
the decoded pictures, as illustrated below::

    $ mkdir real_pictures_decoded
    $ vc2-bitstream-validator \
        real_pictures.vc2 \
        --output real_pictures_decoded/picture_%d.raw

If the bitstream is valid, the following message will be produced::

    No errors found in bitstream. Verify decoded pictures to confirm conformance.

Otherwise, if a conformance error is found, processing will stop and a detailed
error message will be produced explaining the problem.

Once a bitstream has been validated and decoded using
:ref:`vc2-bitstream-validator`, the :ref:`vc2-raw-compare` may be used to
compare the output against the original pictures.  The script must be provided
with two raw picture filenames: an original image, and its encoded and decoded
counterpart. The similarity of the two images will be reported. For example::

    $ vc2-raw-compare \
        test_cases/encoder/real_pictures/picture_0.raw \
        real_picutres_decoded/picture_0.raw
    Pictures are different:
      Y: Different: PSNR = 55.6 dB, 1426363 pixels (68.8%) differ
      C1: Different: PSNR = 57.7 dB, 662607 pixels (63.9%) differ
      C2: Different: PSNR = 56.8 dB, 703531 pixels (67.9%) differ

For a test case to pass:

* The encoder must not raise an error condition during encoding.
* The :ref:`vc2-bitstream-validator` must not find any errors in the bit stream.
* For lossless encoders, :ref:`vc2-raw-compare` tool must report ``Pictures are
  identical``, with no warnings, for every picture in the reference decoding.
* For lossy encoders, :ref:`vc2-raw-compare` tool must report a PSNR level of
  TODO.
* Input and output pictures should be visually compared and must be
  visually indistinguishable.
* No additional pictures must have been decoded.

For an encoder to pass the conformance test, all test cases, for all supported
codec feature sets must pass. If any tests fail, this indicates that the
encoder is non-conformant to the VC-2 specification.

The section below outlines the purpose of each test case and gives advice on
what that case failing may indicate.

.. _encoder-test-cases:

Encoder Test Cases
------------------

The purpose of each test case (or group of test cases), along with advice on
debugging failing tests is provided below.

..
    The following directive automatically extracts the test case documentation
    from the test case Registry objects in ``vc2_conformance.test_cases``.  See
    the ``docs/source/_ext/test_case_documentation.py`` script for the
    definition of the auto-documentation extraction routine below.

.. test-case-documentation:: encoder
