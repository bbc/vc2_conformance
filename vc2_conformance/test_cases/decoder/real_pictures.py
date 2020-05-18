"""
Real picture based test sequences.
"""

from vc2_conformance.bitstream import Stream

from vc2_conformance.encoder import make_sequence

from vc2_conformance import picture_generators

from vc2_conformance.test_cases import decoder_test_case_generator


@decoder_test_case_generator
def real_pictures(codec_features):
    """
    **Tests real pictures are decoded correctly.**

    A series of three still photographs.

    .. image:: /_static/user_guide/real_pictures.svg

    .. note::

        The images encoded in this sequence are generated from 4256 by 2832
        pixel, 4:4:4, 16 bit, standard dynamic range, RGB color images with the
        ITU-R BT.709 gamut. As such, the decoded pictures may be of reduced
        technical quality compared with the capabilities of the format. The
        rescaling, color conversion and encoding algorithms used are also basic
        in nature, potentially further reducing the picture quality.
    """
    return Stream(
        sequences=[
            make_sequence(
                codec_features,
                picture_generators.real_pictures(
                    codec_features["video_parameters"],
                    codec_features["picture_coding_mode"],
                ),
            )
        ]
    )
