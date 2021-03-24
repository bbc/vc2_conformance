.. _guide-encoder-testing:

VC-2 encoder conformance testing procedure
==========================================

The VC-2 encoder conformance testing procedure is described below. In summary,
the raw video test sequences generated in the
:ref:`guide-generating-test-cases` step will be encoded using the candidate
encoder. The resulting bitstream will then be checked using the
:ref:`vc2-bitstream-validator` and encoded pictures compared with the originals
for similarity.

.. note::

    Whilst it is possible to carry out the encoder testing procedure manually,
    we recommend producing a script to automate most of the steps required for
    the particular encoder being tested. You must still take care to manually
    inspect and compare all decoded pictures, however.


Encoding the reference bitstreams
---------------------------------

For each codec feature set provided, a set of raw videos are produced. These
are located in directories matching the pattern ``<codec feature set
name>/encoder/<test-case-name>/``. The specific test cases generated will vary
depending on the codec features specified.

Each test case must be encoded independently by the encoder under test and the
encoded bitstreams stored on disk. The encoder must not crash or produce any
warnings when encoding these test sequences.


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

If the bitstream is valid, the following message will be produced:

.. code-block:: text

    No errors found in bitstream. Verify decoded pictures to confirm conformance.

Otherwise, if a conformance error is found, processing will stop and a detailed
error message will be produced explaining the problem.

Once a bitstream has been validated and decoded using
:ref:`vc2-bitstream-validator`, the :ref:`vc2-picture-compare` command is used
to compare the output against the original pictures. The script must be
provided with two raw picture filenames, or two directory names containing raw
pictures.  One should contain the original images, and the other its encoded
then decoded counterpart. The similarity of the images will be reported. For
example::

    $ vc2-picture-compare real_pictures/ real_pictures_decoded/
    Comparing real_pictures/picture_0.raw and real_pictures_decoded/picture_0.raw
      Pictures are different:
        Y: Different: PSNR = 55.6 dB, 1426363 pixels (68.8%) differ
        C1: Different: PSNR = 57.7 dB, 662607 pixels (63.9%) differ
        C2: Different: PSNR = 56.8 dB, 703531 pixels (67.9%) differ
    Comparing real_pictures/picture_1.raw and real_pictures_decoded/picture_1.raw
      Pictures are different:
        Y: Different: PSNR = 55.6 dB, 1426363 pixels (68.8%) differ
        C1: Different: PSNR = 57.7 dB, 662607 pixels (63.9%) differ
        C2: Different: PSNR = 56.8 dB, 703531 pixels (67.9%) differ
    Comparing real_pictures/picture_2.raw and real_pictures_decoded/picture_2.raw
      Pictures are different:
        Y: Different: PSNR = 55.6 dB, 1426363 pixels (68.8%) differ
        C1: Different: PSNR = 57.7 dB, 662607 pixels (63.9%) differ
        C2: Different: PSNR = 56.8 dB, 703531 pixels (67.9%) differ
    Summary: 0 identical, 3 different

.. note::

    When provided with two directories to compare the
    :ref:`vc2-picture-compare` tool will ignore all but the numercial part of
    the filenames when matching pictures together. Differing names or uses (and
    non-uses) of leading zeros are ignored. For example, it would compare two
    files named ``expected/picture_12.raw`` and ``actual/image_0012.raw``.

For a test case to pass:

* The encoder must not raise an error condition during encoding.
* The :ref:`vc2-bitstream-validator` must not find any errors in the bit stream.
* For lossless encoders, :ref:`vc2-picture-compare` tool must report ``Pictures are
  identical``, with no warnings, for every picture in the reference decoding.
* For lossy encoders, :ref:`vc2-picture-compare` tool might report a difference
  and the quoted PSNR figure should be checked to ensure it is appropriate for
  the intended application of the codec.
* Input and output pictures must be visually compared and should be
  sufficiently similar as to be suitable for the intended application of the
  codec.
* No additional pictures must have been decoded.

.. tip::

    When viewing pictures using the ``ffplay`` commands suggested by
    :ref:`vc2-picture-explain` you might sometimes find it helpful to use a
    very low frame rate or playback the sequence in a loop.
    
    To reduce the frame rate such that each frame is shown for 5 seconds,
    replace the value after ``-framerate`` with ``1/5``.
    
    To loop the sequence indefinately add ``-loop 0`` to the command.

For an encoder to pass the conformance test, all test cases, for all supported
codec feature sets must pass. If any tests fail, this indicates that the
encoder is non-conformant to the VC-2 specification.

The section below outlines the purpose of each test case and gives advice on
what that case failing might indicate.

.. _encoder-test-cases:

Encoder test cases
------------------

The purpose of each test case (or group of test cases), along with advice on
debugging failing tests is provided below.

..
    The following directive automatically extracts the test case documentation
    from the test case Registry objects in ``vc2_conformance.test_cases``.  See
    the ``docs/source/_ext/test_case_documentation.py`` script for the
    definition of the auto-documentation extraction routine below.

.. test-case-documentation:: encoder


Testing additional bitstreams' conformance
------------------------------------------

The :ref:`vc2-bitstream-validator` tool may also be used to check the
conformance of other bitstreams produced by an encoder. For example, you might
optionally encode your own (short) test sequences and use this tool to validate
the bitstream. You should follow the procedure described earlier to do this.
You can also use the :ref:`vc2-picture-compare` utility to compare the decoded
output produced by :ref:`vc2-bitstream-validator` against your original test
sequence.
