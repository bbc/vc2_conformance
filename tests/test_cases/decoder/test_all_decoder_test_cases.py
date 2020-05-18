import pytest

import json

from io import BytesIO

from vc2_data_tables import Profiles, Levels, PictureCodingModes

from vc2_conformance.bitstream import Stream, autofill_and_serialise_stream

from vc2_conformance.test_cases import DECODER_TEST_CASE_GENERATOR_REGISTRY

from vc2_conformance.codec_features import CodecFeatures

from vc2_conformance.video_parameters import VideoParameters

from sample_codec_features import MINIMAL_CODEC_FEATURES
from smaller_real_pictures import alternative_real_pictures
from alternative_level_constraints import alternative_level_1

from vc2_conformance.state import State

from vc2_conformance.decoder import (
    init_io,
    parse_stream,
)


# NB: Test case generators run during test collection
with alternative_level_1():
    with alternative_real_pictures():
        ALL_TEST_CASES = [
            (
                codec_features,
                list(
                    DECODER_TEST_CASE_GENERATOR_REGISTRY.generate_test_cases(
                        codec_features,
                    )
                ),
            )
            for codec_features in [
                # High quality
                CodecFeatures(MINIMAL_CODEC_FEATURES, profile=Profiles.high_quality),
                # Low delay
                CodecFeatures(MINIMAL_CODEC_FEATURES, profile=Profiles.low_delay),
                # Lossless coding
                CodecFeatures(
                    MINIMAL_CODEC_FEATURES,
                    profile=Profiles.high_quality,
                    lossless=True,
                    picture_bytes=None,
                ),
                # Fragmented pictures
                CodecFeatures(
                    MINIMAL_CODEC_FEATURES,
                    profile=Profiles.high_quality,
                    fragment_slice_count=2,
                ),
                # Pictures are fields (above are all frames)
                CodecFeatures(
                    MINIMAL_CODEC_FEATURES,
                    picture_coding_mode=PictureCodingModes.pictures_are_fields,
                ),
                # Custom quantisation matrix
                CodecFeatures(
                    MINIMAL_CODEC_FEATURES,
                    dwt_depth=1,
                    dwt_depth_ho=2,
                    quantization_matrix={
                        0: {"L": 1},
                        1: {"H": 2},
                        2: {"H": 3},
                        3: {"LH": 4, "HL": 5, "HH": 6},
                    },
                ),
                # Level constraints apply (NB: level 1 is overridden for this
                # test with an alternative definition matching
                # MINIMAL_CODEC_FEATURES, with some arbitrary encoding
                # requirements)
                CodecFeatures(MINIMAL_CODEC_FEATURES, level=Levels(1),),
                # Very high, asymmetric bit depths.
                #
                # Here 'very high' means 32 bits and 48 bits (for luma and color
                # difference). In practice no real codec is likely to use more than
                # 16 bits since any video format requiring greater dynamic range is
                # likely to need to turn to floating point anyway.
                CodecFeatures(
                    MINIMAL_CODEC_FEATURES,
                    video_parameters=VideoParameters(
                        MINIMAL_CODEC_FEATURES["video_parameters"],
                        luma_offset=0,
                        luma_excursion=(1 << 32) - 1,
                        color_diff_offset=(1 << 48) // 2,
                        color_diff_excursion=(1 << 48) - 1,
                    ),
                ),
            ]
        ]


def test_names_unique():
    for codec_features, test_cases in ALL_TEST_CASES:
        names = [tc.name for tc in test_cases]
        print("\n".join(sorted(names)))
        assert len(set(names)) == len(names)


@pytest.mark.parametrize(
    "codec_features,test_case",
    [
        (codec_features, test_case)
        for codec_features, test_cases in ALL_TEST_CASES
        for test_case in test_cases
    ],
)
def test_all_decoder_test_cases(codec_features, test_case):
    # Every test case for every basic video mode must produce a valid bitstream
    # containing pictures with the correct format. Any JSON metadata must also
    # be seriallisable.

    # Must return a Stream
    assert isinstance(test_case.value, Stream)

    # Mustn't crash!
    json.dumps(test_case.metadata)

    # Serialise
    f = BytesIO()
    autofill_and_serialise_stream(f, test_case.value)
    f.seek(0)

    # Deserialise/validate
    def output_picture_callback(picture, video_parameters):
        assert video_parameters == codec_features["video_parameters"]

    state = State(_output_picture_callback=output_picture_callback,)

    with alternative_level_1():
        init_io(state, f)
        parse_stream(state)
