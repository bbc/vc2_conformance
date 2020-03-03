import pytest

import numpy as np

from vc2_conformance.test_cases import ENCODER_TEST_CASE_GENERATOR_REGISTRY

from vc2_conformance.file_format import compute_dimensions_and_depths

from vc2_data_tables import (
    PictureCodingModes,
)

from sample_codec_features import MINIMAL_CODEC_FEATURES


@pytest.mark.parametrize(
    "test_case",
    ENCODER_TEST_CASE_GENERATOR_REGISTRY.generate_test_cases(
        MINIMAL_CODEC_FEATURES,
    ),
)
def test_all_encoder_test_cases(test_case):
    component_dimensions_and_depths = compute_dimensions_and_depths(
        test_case.value.video_parameters,
        test_case.value.picture_coding_mode,
    )
    
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
