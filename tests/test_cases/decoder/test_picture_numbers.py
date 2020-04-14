import pytest

from copy import deepcopy

from vc2_data_tables import PictureCodingModes

from vc2_conformance.test_cases.decoder.picture_numbers import picture_numbers

from sample_codec_features import MINIMAL_CODEC_FEATURES


@pytest.mark.parametrize(
    "picture_coding_mode,exp_odd_first_picture",
    [
        (PictureCodingModes.pictures_are_fields, False),
        (PictureCodingModes.pictures_are_frames, True),
    ],
)
def test_picture_numbers(picture_coding_mode, exp_odd_first_picture):
    codec_features = deepcopy(MINIMAL_CODEC_FEATURES)
    codec_features["picture_coding_mode"] = picture_coding_mode

    test_cases = {}
    for test_case in picture_numbers(codec_features):
        pic_nums = []
        test_cases[test_case.subcase_name] = pic_nums
        for data_unit in test_case.value["data_units"]:
            if "picture_parse" in data_unit:
                pic_nums.append(
                    data_unit["picture_parse"]["picture_header"]["picture_number"]
                )

    # Check expected cases are present
    #
    # NB: Picture number sequence validity checked by generic test (which
    # passes the sequence through the bitstream validator), just sanity
    # checking here
    assert test_cases["start_at_zero"][0] == 0

    assert test_cases["non_zero_start"][0] != 0
    assert test_cases["non_zero_start"][0] % 2 == 0

    assert test_cases["wrap_around"][0] > test_cases["wrap_around"][-1]

    assert "non_zero_start" in test_cases
    assert "wrap_around" in test_cases

    if exp_odd_first_picture:
        assert test_cases["odd_first_picture"][0] % 2 == 1
    else:
        assert "odd_first_picture" not in test_cases
