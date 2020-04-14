import pytest

import json

from io import BytesIO

from vc2_data_tables import Profiles, PictureCodingModes

from vc2_conformance.bitstream import autofill_and_serialise_sequence

from vc2_conformance.test_cases import DECODER_TEST_CASE_GENERATOR_REGISTRY

from vc2_conformance.codec_features import CodecFeatures

from sample_codec_features import MINIMAL_CODEC_FEATURES
from smaller_real_pictures import alternative_real_pictures

from vc2_conformance.state import State

from vc2_conformance.decoder import (
    init_io,
    parse_sequence,
)


# NB: Test case generators run during test collection
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
            CodecFeatures(MINIMAL_CODEC_FEATURES, profile=Profiles.high_quality,),
            # Low delay
            CodecFeatures(MINIMAL_CODEC_FEATURES, profile=Profiles.low_delay,),
            # Lossless coding
            CodecFeatures(
                MINIMAL_CODEC_FEATURES,
                profile=Profiles.high_quality,
                lossless=True,
                picture_bytes=0,
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
        ]
    ]


def test_names_unique():
    for codec_features, test_cases in ALL_TEST_CASES:
        names = [tc.name for tc in test_cases]
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

    # Mustn't crash!
    json.dumps(test_case.metadata)

    def output_picture_callback(picture, video_parameters):
        assert video_parameters == codec_features["video_parameters"]

    state = State(_output_picture_callback=output_picture_callback,)

    f = BytesIO()
    autofill_and_serialise_sequence(f, test_case.value)

    f.seek(0)
    init_io(state, f)
    parse_sequence(state)
