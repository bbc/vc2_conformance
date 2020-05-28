import pytest

import json

import numpy as np

from vc2_conformance.codec_features import CodecFeatures

from vc2_conformance.pseudocode.video_parameters import VideoParameters

from vc2_conformance.test_cases import ENCODER_TEST_CASE_GENERATOR_REGISTRY

from vc2_conformance.dimensions_and_depths import compute_dimensions_and_depths

from vc2_data_tables import PictureCodingModes

from sample_codec_features import MINIMAL_CODEC_FEATURES
from smaller_real_pictures import alternative_real_pictures


# NB: Test case generators run during test collection so we must replace the
# pictures with smaller ones (for performance reasons) during tests
with alternative_real_pictures():
    ALL_TEST_CASES = [
        (
            codec_features,
            list(
                ENCODER_TEST_CASE_GENERATOR_REGISTRY.generate_test_cases(
                    codec_features,
                )
            ),
        )
        for codec_features in [
            # Both picture coding modes
            CodecFeatures(
                MINIMAL_CODEC_FEATURES,
                picture_coding_mode=PictureCodingModes.pictures_are_frames,
            ),
            CodecFeatures(
                MINIMAL_CODEC_FEATURES,
                picture_coding_mode=PictureCodingModes.pictures_are_fields,
            ),
            # Test with very high, asymmetric bit depths.
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
        assert len(set(names)) == len(names)


@pytest.mark.parametrize(
    "codec_features,test_case",
    [
        (codec_features, test_case)
        for codec_features, test_cases in ALL_TEST_CASES
        for test_case in test_cases
    ],
)
def test_all_encoder_test_cases(codec_features, test_case):
    component_dimensions_and_depths = compute_dimensions_and_depths(
        test_case.value.video_parameters, test_case.value.picture_coding_mode,
    )

    # Metadata should be serialisable (mustn't crash)
    json.dumps(test_case.metadata)

    last_pic_num = None
    for picture in test_case.value.pictures:
        # Picture components must have the correct dimensions
        for component, dd in component_dimensions_and_depths.items():
            a = np.array(picture[component])
            assert a.shape == (dd.height, dd.width)

        # Picture numbers must be sequential
        if last_pic_num is not None:
            assert picture["pic_num"] == last_pic_num + 1
        last_pic_num = picture["pic_num"]

    # Must have a non-zero, whole number of pictures
    assert len(test_case.value.pictures) >= 1
    if test_case.value.picture_coding_mode == PictureCodingModes.pictures_are_fields:
        assert len(test_case.value.pictures) % 2 == 0
