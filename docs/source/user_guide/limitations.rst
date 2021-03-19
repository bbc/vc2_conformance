.. _guide-limitations:

Conformance test limtations
===========================

The conformance testing procedures outlined in the previous sections are unable
to guarantee the overall conformance of an implementation -- only their
conformance with respect to particular bitstreams or pictures. Furthermore, not
every possible combination of features are verified, though care has been taken
to include any combinations likely to uncover issues.

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
    generated to test this esoteric case, however, since this is unlikely to be
    used in practice.

**Quantisation in lossless formats**
    Lossless formats can use quantization where transform coefficients happen
    to be multiples of the quantisation factor. Because quantisation can, in the
    general case, result in larger intermediate signals within a decoder, it is
    not appropriate to use lossily encoded test signals to test a lossless
    decoder's support for quantisation. As a result, a special test case is
    provided for lossless decoders which uses quantisation but ensures safe
    signal ranges.

**Auxiliary data-units**
    Auxiliary data units (10.4.4) are not included in any tests. This is
    because the contents of such units are not defined by the VC-2 standard and
    so in the event that a particular codec supported some form of auxiliary
    data stream, its format would not be known to the conformance software.
    Likewise, the contents of any auxiliary data units produced by an encoder
    under test will be ignored by this software.

**Variable slice sizes**
    In all non-lossless mode test cases, high quality picture slices are sized
    to (approximately) the same number of bytes each. Although in principle
    other modes of operation are possible (e.g. buffer-based byte allocation),
    these are not the intended mode of operation for VC-2 and would be too
    numerous to comprehensively test.

**Changing wavelet transform mid sequence**
    All test cases use the same wavelet transform and slice parameters for
    every picture in the sequence. Though the VC-2 specification permits these
    parameters to change mid-sequence, this is not the intended mode of
    operation for VC-2. Because of this, and the number of test cases which
    would be required, this scenario is not tested.

**Degenerate formats**
    The test case generator cannot generate test cases for all degenerate video
    formats. For example, picture component bit depths of greater than 32 bits
    or absurd transform depths are not supported.


**Differences from specification**
    The SMPTE ST 2042-1:2017 specification contains a small number of minor
    errors. In these cases, this software assumes the intention of the
    specification.
