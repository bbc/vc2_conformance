"""
Test pictures designed to produce extreme signal levels in an encoder.
"""

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
)


@encoder_test_case_generator
def signal_range(codec_features):
    """
    This test is designed to produce extreme signal levels within an encoder's
    processing chain. Implementations should ensure that no integer clamping or
    overflow operations occur while encoding these pictures.
    
    The metadata provided with each test case gives, for each picture, the test
    points checked by that picture. See
    :py:class:`vc2_bit_widths.helpers.TestPoint` for details.
    """
    (
        analysis_luma_pictures,
        synthesis_luma_pictures,
        analysis_color_diff_pictures,
        synthesis_color_diff_pictures,
    ) = get_test_pictures(codec_features)
    
    for component, analysis_test_pictures in [
        ("Y", analysis_luma_pictures),
        ("C1", analysis_color_diff_pictures),
        ("C2", analysis_color_diff_pictures),
    ]:
        # Generate an initially empty set of mid-grey pictures
        one_gray_frame = list(mid_gray(
            codec_features["video_parameters"],
            codec_features["picture_coding_mode"],
        ))
        pictures = list(repeat_pictures(
            one_gray_frame,
            (
                (len(analysis_test_pictures) + len(one_gray_frame) - 1)
                // len(one_gray_frame)
            ),
        ))
        
        # Fill-in the test patterns
        for test_picture, picture in zip(analysis_test_pictures, pictures):
            picture[component] = test_picture.picture.tolist()
        
        # Extract the testpoints in JSON-serialisable form
        metadata = [
            [tp._asdict() for tp in p.test_points]
            for p in analysis_test_pictures
        ]
        
        out = EncoderTestSequence(
            pictures=pictures,
            video_parameters=codec_features["video_parameters"],
            picture_coding_mode=codec_features["picture_coding_mode"],
        )
        
        yield TestCase(out, component, metadata=metadata)
