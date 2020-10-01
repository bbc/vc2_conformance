"""
Tests which verify that codecs correctly process streams formed of multiple
concatenated sequences (10.3).
"""

from copy import deepcopy

from vc2_conformance.bitstream import Stream

from vc2_conformance.test_cases import decoder_test_case_generator

from vc2_conformance.picture_generators import mid_gray

from vc2_conformance.encoder import make_sequence


@decoder_test_case_generator
def concatenated_sequences(codec_features):
    """
    **Tests that streams containing multiple concatenated sequences can be
    decoded.**

    A stream consisting of the concatenation of two sequences (10.3) with one
    frame each, the first picture is given picture number zero in both
    sequences.
    """
    sequence = make_sequence(
        codec_features,
        mid_gray(
            codec_features["video_parameters"],
            codec_features["picture_coding_mode"],
        ),
    )

    return Stream(sequences=[sequence, deepcopy(sequence)])
