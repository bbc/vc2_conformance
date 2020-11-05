.. _guide-decoder-testing:

VC-2 decoder conformance testing procedure
==========================================

The VC-2 decoder conformance testing procedure is described below. In summary,
each of the bitstreams generated in the previous step
(:ref:`guide-generating-test-cases`), we will be decoded using the candidate
decoder and the resulting raw video compared with a reference decoding.


Decoding the reference bitstreams
---------------------------------

For each codec feature set provided, a set of bitstreams which test different
decoder behaviours are produced. These are located in files whose names match
the pattern ``<codec feature set name>/decoder/<test-case-name>.vc2``. The
specific test cases generated will vary depending on the codec features
specified.

Each bitstream must be decoded independently by the decoder under test. The
decoded pictures must then be stored as raw video as described in the
:ref:`guide-file-format` section.


Checking the decoded pictures
-----------------------------

Each bitstream has an associated reference decoding in the ``<codec feature set
name>/decoder/<test-case-name>_expected/`` directory. The output of the decoder
under test must be identical to the reference decoding.

The :ref:`vc2-picture-compare` tool is provided for comparing decoder outputs
with the reference decodings. It takes as argument either the names of two raw
picture files, or the names of two directories containing numbered raw picture
files.  Differences between pictures are then reported.

For example::

    $ vc2-picture-compare expected/ actual/
    Comparing expected/picture_0.raw and actual/picture_0.raw
      Pictures are identical
    Comparing expected/picture_1.raw and actual/picture_1.raw
      Pictures are identical
    Comparing expected/picture_2.raw and actual/picture_2.raw
      Pictures are identical
    Summary: 3 identical, 0 different

For a test case to pass:

* The :ref:`vc2-picture-compare` tool must report ``Pictures are identical``, with
  no warnings, for every picture in the reference decoding.
* No additional pictures must have been decoded by the decoder under test.
* The decoder under test must not have crashed or indicated an error condition
  while decoding the bitstream.

For a decoder to pass the conformance test, all test cases, for all supported
codec feature sets must pass. If any tests fail, this indicates that the
decoder is non-conformant to the VC-2 specification.

The section below outlines the purpose of each test case and gives advice on
what that case failing may indicate. Alternatively, once all decoder tests have
passed, we can continue onto :ref:`guide-encoder-testing`.


.. _decoder-test-cases:

Decoder Test Cases
------------------

The purpose of each test case (or group of test cases), along with advice on
debugging failing tests is provided below. In all test cases, the bitstream
provided is a valid bitstream permitted by the spec.

..
    The following directive automatically extracts the test case documentation
    from the test case Registry objects in ``vc2_conformance.test_cases``.  See
    the ``docs/source/_ext/test_case_documentation.py`` script for the
    definition of the auto-documentation extraction routine below.

.. test-case-documentation:: decoder
