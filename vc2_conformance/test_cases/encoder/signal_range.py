"""
Test pictures designed to produce extreme signal levels in an encoder.
"""

import logging

from vc2_conformance.test_cases import (
    encoder_test_case_generator,
    TestCase,
    EncoderTestSequence,
)

from vc2_conformance.picture_generators import (
    mid_gray,
    repeat_pictures,
)

from vc2_conformance.test_cases.bit_widths_common import (
    get_test_pictures,
    MissingStaticAnalysisError,
)


@encoder_test_case_generator
def signal_range(codec_features):
    """
    **Tests that an encoder has sufficient numerical dynamic range.**

    These test cases contain test patterns designed to produce extreme signals
    within encoders. During these test cases, no integer clamping or overflows
    must occur.

    A test case is produced for each picture component:

    ``signal_range[Y]``
        Luma component test patterns.

    ``signal_range[C1]``
        Color difference 1 component test patterns.

    ``signal_range[C2]``
        Color difference 2 component test patterns.

    Though the test patterns produce near worst case signal levels, they are
    not guaranteed to produce the largest values possible.

    .. note::

        For informational purposes, an example of a set of test patterns are shown below:

        .. image:: /_static/user_guide/signal_range_encoder.png

    An informative metadata file is provided along side each test case which
    gives, for each picture in the bitstream, the parts of a encoder which are
    being tested by the test patterns. See
    :py:class:`vc2_bit_widths.helpers.TestPoint` for details.
    """
    try:
        (
            analysis_luma_pictures,
            synthesis_luma_pictures,
            analysis_color_diff_pictures,
            synthesis_color_diff_pictures,
        ) = get_test_pictures(codec_features)
    except MissingStaticAnalysisError:
        logging.warning(
            (
                "No static analysis available for the wavelet "
                "used by codec '%s'. Signal range test cases cannot "
                "be generated."
            ),
            codec_features["name"],
        )
        return

    for component, analysis_test_pictures in [
        ("Y", analysis_luma_pictures),
        ("C1", analysis_color_diff_pictures),
        ("C2", analysis_color_diff_pictures),
    ]:
        # Generate an initially empty set of mid-gray pictures
        one_gray_frame = list(
            mid_gray(
                codec_features["video_parameters"],
                codec_features["picture_coding_mode"],
            )
        )
        pictures = list(
            repeat_pictures(
                one_gray_frame,
                (
                    (len(analysis_test_pictures) + len(one_gray_frame) - 1)
                    // len(one_gray_frame)
                ),
            )
        )

        # Fill-in the test patterns
        for test_picture, picture in zip(analysis_test_pictures, pictures):
            picture[component] = test_picture.picture.tolist()

        # Extract the testpoints in JSON-serialisable form
        metadata = [
            [tp._asdict() for tp in p.test_points] for p in analysis_test_pictures
        ]

        out = EncoderTestSequence(
            pictures=pictures,
            video_parameters=codec_features["video_parameters"],
            picture_coding_mode=codec_features["picture_coding_mode"],
        )

        yield TestCase(out, component, metadata=metadata)
