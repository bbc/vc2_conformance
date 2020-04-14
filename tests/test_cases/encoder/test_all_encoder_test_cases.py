import pytest

import os

import sys

import json

import numpy as np

from vc2_conformance.codec_features import CodecFeatures

from vc2_conformance.test_cases import ENCODER_TEST_CASE_GENERATOR_REGISTRY

from vc2_conformance.file_format import compute_dimensions_and_depths

from vc2_data_tables import PictureCodingModes

# Add test root directory to path for sample_codec_features test utility module
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..",))

from sample_codec_features import MINIMAL_CODEC_FEATURES
from smaller_real_pictures import alternative_real_pictures


# NB: Test case generators run during test collection so we must replace the
# pictures with smaller ones (for performance reasons) during tests
with alternative_real_pictures():
    ALL_TEST_CASES = [
        # ALl tests run for frame and field containing pictures
        (
            codec_features,
            list(
                ENCODER_TEST_CASE_GENERATOR_REGISTRY.generate_test_cases(
                    codec_features,
                )
            ),
        )
        for codec_features in [
            CodecFeatures(
                MINIMAL_CODEC_FEATURES, picture_coding_mode=picture_coding_mode,
            )
            for picture_coding_mode in PictureCodingModes
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
