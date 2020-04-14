"""
Tests which verify that codecs used the necessary number of bits for their
arithmetic.
"""

import logging

from vc2_conformance.file_format import compute_dimensions_and_depths

from vc2_conformance.encoder import make_sequence

from vc2_conformance.picture_generators import (
    mid_gray,
    repeat_pictures,
)

from vc2_conformance.test_cases.bit_widths_common import (
    get_test_pictures,
    MissingStaticAnalysisError,
)

from vc2_conformance.test_cases import (
    TestCase,
    decoder_test_case_generator,
)

from vc2_conformance.test_cases.decoder.pictures import iter_slices_in_sequence


@decoder_test_case_generator
def signal_range(codec_features):
    """
    Verify that a decoder has sufficient numerical range to handle extreme
    input signals.
    
    Decoder implementers should ensure that no integer clamping or overflows
    occur while processing these test pictures.
    
    The metadata provided with each test case gives, for each picture, the test
    points checked by that picture. See
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

    dimensions_and_depths = compute_dimensions_and_depths(
        codec_features["video_parameters"], codec_features["picture_coding_mode"],
    )

    for component, analysis_test_pictures, synthesis_test_pictures in [
        ("Y", analysis_luma_pictures, synthesis_luma_pictures),
        ("C1", analysis_color_diff_pictures, synthesis_color_diff_pictures),
        ("C2", analysis_color_diff_pictures, synthesis_color_diff_pictures),
    ]:
        # For lossless codecs we use the analysis test patterns since no
        # quantisation takes place
        if codec_features["lossless"]:
            test_pictures = analysis_test_pictures
        else:
            test_pictures = synthesis_test_pictures

        # Generate an initially empty set of mid-grey pictures
        one_gray_frame = list(
            mid_gray(
                codec_features["video_parameters"],
                codec_features["picture_coding_mode"],
            )
        )
        pictures = list(
            repeat_pictures(
                one_gray_frame,
                ((len(test_pictures) + len(one_gray_frame) - 1) // len(one_gray_frame)),
            )
        )

        # Fill-in the test patterns
        minimum_qindices = []
        for test_picture, picture in zip(test_pictures, pictures):
            picture[component] = test_picture.picture.tolist()
            if codec_features["lossless"]:
                minimum_qindices.append(0)
            else:
                minimum_qindices.append(test_picture.quantisation_index)
        while len(minimum_qindices) < len(pictures):
            minimum_qindices.append(0)

        # Extract the testpoints in JSON-serialisable form
        metadata = [[tp._asdict() for tp in p.test_points] for p in test_pictures]

        # Encode
        sequence = make_sequence(
            codec_features, pictures, minimum_qindex=minimum_qindices,
        )

        # Check the desired qindex could be used (should only ever fail for
        # absurdly low bitrate configurations).
        num_unexpected_qindices = 0
        expected_qindex = None
        expected_qindex_iter = iter(minimum_qindices)
        for _, sx, sy, slice in iter_slices_in_sequence(codec_features, sequence):
            if sx == 0 and sy == 0:
                expected_qindex = next(expected_qindex_iter, 0)
            if slice["qindex"] != expected_qindex:
                num_unexpected_qindices += 1

        if num_unexpected_qindices > 0:
            logging.warning(
                "Could not assign the required qindex to %d picture slices "
                "for signal range test case. Peak signal levels may be reduced.",
                num_unexpected_qindices,
            )

        yield TestCase(
            sequence, component, metadata=metadata,
        )
