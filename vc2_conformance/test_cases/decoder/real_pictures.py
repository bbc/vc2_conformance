"""
Real picture based test sequences.
"""

from vc2_conformance.encoder import make_sequence

from vc2_conformance import picture_generators

from vc2_conformance.test_cases import decoder_test_case_generator


@decoder_test_case_generator
def real_pictures(codec_features):
    """
    A series of real still images.

    Provided to give implementers some quick feedback on the correctness of
    their codec.
    """
    return make_sequence(
        codec_features,
        picture_generators.real_pictures(
            codec_features["video_parameters"], codec_features["picture_coding_mode"],
        ),
    )
