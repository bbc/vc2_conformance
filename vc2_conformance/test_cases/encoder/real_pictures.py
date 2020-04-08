"""
Real picture based test sequences.
"""

from vc2_conformance.test_cases import (
    encoder_test_case_generator,
)

from vc2_conformance.test_cases.encoder.common import (
    picture_generator_to_test_case,
)

from vc2_conformance import picture_generators


@encoder_test_case_generator
def real_pictures(codec_features):
    """
    This test sequence contains a series of still images to check that an
    encoder makes sensible choices when presented with 'typical' scenes.
    """
    return picture_generator_to_test_case(
        picture_generators.real_pictures,
        codec_features,
    )
