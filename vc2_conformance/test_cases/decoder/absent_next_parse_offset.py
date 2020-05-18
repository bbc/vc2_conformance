from vc2_data_tables import ParseCodes

from vc2_conformance.bitstream import Stream

from vc2_conformance.test_cases import decoder_test_case_generator

from vc2_conformance.encoder import make_sequence

from vc2_conformance.picture_generators import (
    mid_gray,
    repeat_pictures,
)


@decoder_test_case_generator
def absent_next_parse_offset(codec_features):
    """
    **Tests handling of missing 'next parse offset' field.**

    The 'next parse offset' field of the ``parse_info`` header (see (10.5.1))
    may be set to zero (i.e. omitted) for pictures. This test case verifies
    that decoders are still able to decode streams with this field absent.
    """
    sequence = make_sequence(
        codec_features,
        repeat_pictures(
            mid_gray(
                codec_features["video_parameters"],
                codec_features["picture_coding_mode"],
            ),
            2,
        ),
    )

    # Prevent the default auto numbering of picture-containing data units
    # during serialisation
    for data_unit in sequence["data_units"]:
        parse_info = data_unit["parse_info"]
        if parse_info["parse_code"] in (
            ParseCodes.low_delay_picture,
            ParseCodes.high_quality_picture,
            ParseCodes.low_delay_picture_fragment,
            ParseCodes.high_quality_picture_fragment,
        ):
            parse_info["next_parse_offset"] = 0

    return Stream(sequences=[sequence])
