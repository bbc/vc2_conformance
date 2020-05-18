.. _guide-limitations:

Conformance test limtations
===========================

The conformance testing procedures outlined in the previous sections are unable
to guarantee the overall conformance of an implementation -- only their
conformance with respect to particular bitstreams or pictures. Furthermore, not
every possible combination of features are verified, though care has been taken
to do so where it is likely to find issues.

There are also a small number of VC-2 features which are only tested to a
limited extent by the generated test cases. Some of these are listed below.

**Longer sequences**
    The conformance test cases all consist of relatively short test sequences.
    Since VC-2 is an intra-frame only codec, codecs should only maintain
    limited state between pictures and so be insensitive to sequence length and
    so this limitation of the test suite should be immaterial.

**Mixing fragmented and non-fragmented picture data units**
    The VC-2 standard does not prohibit the use of fragmented and
    non-fragmented pictures within the same sequence. No test cases are
    generated to test this esoteric case, however, since this it is unlikely to
    be used in practice.

**Concatenated sequences**
    All test cases consist of a single VC-2 sequence. Streams consisting of
    several sequences (10.3) are not tested. This is due to each stream being
    considered a separately decodable entity with no state shared between them.

**Auxiliary data-units**
    Auxiliary data units (10.4.4) are not tested. This is because the contents
    of such units are not defined by the VC-2 standard and so in the event that
    a particular codec supported some form of auxiliary data stream, its format
    would not be known to the conformance software.

**Variable slice sizes**
    In all non-lossless mode test cases, high quality picture slices are sized
    to (approximately) the same number of bytes each. Although in principle
    other modes of operation are possible (e.g. buffer-based byte allocation),
    these are not the intended mode of operation for VC-2 and would be too
    numerous to comprehensively test.

**Changing wavelet transform mid sequence**
    All test cases use the same wavelet transform and slice parameters for
    every picture in the sequence. Though the VC-2 specification permits these
    parameters to change mid-sequence, though this is not the intended mode of
    operation for VC-2. The range of potential behaviours to test would also be
    numerous and so this scenario is not tested.

**Degenerate formats**
    The test case generator may not be able to generate test cases for all
    degenerate video formats. For example, picture component bit depths of
    greater than 32 bits or absurd transform depths are not supported.
