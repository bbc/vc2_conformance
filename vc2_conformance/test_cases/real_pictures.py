"""
Real picture based test sequences.
"""

from vc2_conformance.test_cases import encoder_test_case_generator

from vc2_conformance.test_cases.encoder.common import picture_generator_to_test_case

from vc2_conformance import picture_generators


@encoder_test_case_generator
def real_pictures(codec_features):
    """
    This test case is designed to test correct metadata handling in a codec
    implementation while providing a simple sanity check of overall encoder
    behaviour.

    This test sequence consists of a 1 second video sequence as defined by
    :py:class:`vc2_conformance.picture_generators.moving_sprite`. See that
    function's documentation for further details.
    """
    return picture_generator_to_test_case(
        picture_generators.real_pictures, codec_features,
    )
