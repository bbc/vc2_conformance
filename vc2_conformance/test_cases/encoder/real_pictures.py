"""
Real picture based test sequences.
"""

from vc2_conformance.test_cases import encoder_test_case_generator

from vc2_conformance.test_cases.encoder.common import picture_generator_to_test_case

from vc2_conformance import picture_generators


@encoder_test_case_generator
def real_pictures(codec_features):
    """
    **Tests real pictures are encoded sensibly.**

    This test contains a series of three still photographs of natural scenes
    with varying levels of high and low spatial frequency content.

    .. image:: /_static/user_guide/real_pictures.svg

    .. note::

        The source images for this test case are generated from 4256 by 2832
        pixel, 4:4:4, 16 bit, standard dynamic range, RGB color images with the
        ITU-R BT.709 gamut. As such, the pictures may be of reduced technical
        quality compared with the capabilities of the format. The rescaling and
        color conversion algorithms used are also basic in nature, potentially
        further reducing the picture quality.
    """
    return picture_generator_to_test_case(
        picture_generators.real_pictures,
        codec_features,
    )
