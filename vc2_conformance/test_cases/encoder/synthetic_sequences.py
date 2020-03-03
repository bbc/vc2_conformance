"""
Generic synthetic test sequences.
"""

from vc2_conformance.test_cases import (
    encoder_test_case_generator,
    EncoderTestSequence,
)

from vc2_conformance import picture_generators


def picture_generator_to_test_case(picture_generator, codec_features):
    """
    Internal utility. Takes a function from
    :py:mod:`vc2_conformance.picture_generators` and a set of
    :py:class:`~vc2_conformance.codec_features.CodecFeatures` and
    returns a :py:class:`~vc2_conformance.test_cases.EncoderTestSequence`.
    """
    out = EncoderTestSequence(
        pictures=[],
        video_parameters=codec_features["video_parameters"],
        picture_coding_mode=codec_features["picture_coding_mode"],
    )
    
    for pic_num, (y, c1, c2) in enumerate(picture_generator(
        codec_features["video_parameters"],
        codec_features["picture_coding_mode"],
    )):
        out.pictures.append({
            "Y": y,
            "C1": c1,
            "C2": c2,
            "pic_num": pic_num,
        })
    
    return out


@encoder_test_case_generator
def synthetic_moving_sprite(codec_features):
    """
    This test case is designed to test correct metadata handling in a codec
    implementation while providing a simple sanity check of overall encoder
    behaviour.
    
    This test sequence consists of a 1 second video sequence as defined by
    :py:class:`vc2_conformance.picture_generators.moving_sprite`. See that
    function's documentation for further details.
    """
    return picture_generator_to_test_case(
        picture_generators.moving_sprite,
        codec_features,
    )


@encoder_test_case_generator
def synthetic_linear_ramps(codec_features):
    """
    This test case may be used to check channel ordering and, to a limited
    extent, correctness of colour metadata handling.
    
    This test sequence contains a single frame which contains four horizontal
    color ramps as defined by
    :py:class:`vc2_conformance.picture_generators.linear_ramps`. See that
    function's documentation for further details.
    """
    return picture_generator_to_test_case(
        picture_generators.linear_ramps,
        codec_features,
    )
