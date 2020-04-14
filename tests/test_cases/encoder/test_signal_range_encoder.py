import pytest

import os

import sys

from copy import deepcopy

import numpy as np

import logging

from vc2_data_tables import (
    WaveletFilters,
    PictureCodingModes,
    ColorDifferenceSamplingFormats,
)

from vc2_conformance.state import State

from vc2_conformance.picture_encoding import picture_encode

from vc2_conformance.video_parameters import set_coding_parameters

from vc2_conformance.test_cases.encoder.signal_range import signal_range

# Add test root directory to path for sample_codec_features test utility module
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..",))

from sample_codec_features import MINIMAL_CODEC_FEATURES


class TestSignalRange(object):
    @pytest.fixture
    def codec_features(self):
        return deepcopy(MINIMAL_CODEC_FEATURES)

    def test_unsupported_codec(self, caplog, codec_features):
        codec_features["dwt_depth"] = 99

        caplog.set_level(logging.WARNING)
        assert len(list(signal_range(codec_features))) == 0
        assert "WARNING" in caplog.text
        assert "No static analysis available" in caplog.text

    @pytest.mark.parametrize("picture_coding_mode", PictureCodingModes)
    @pytest.mark.parametrize(
        "color_diff_format_index",
        [
            ColorDifferenceSamplingFormats.color_4_4_4,
            ColorDifferenceSamplingFormats.color_4_2_0,
        ],
    )
    def test_works_as_intended(
        self, codec_features, picture_coding_mode, color_diff_format_index,
    ):
        # A simple transform
        codec_features["wavelet_index"] = WaveletFilters.le_gall_5_3
        codec_features["wavelet_index_ho"] = WaveletFilters.le_gall_5_3
        codec_features["dwt_depth"] = 1
        codec_features["dwt_depth_ho"] = 0

        # Check works when force an even number of pictures
        codec_features["picture_coding_mode"] = picture_coding_mode

        # Odd bit depths/offsets (Luma 8 bit, color diff, 10 bit)
        vp = codec_features["video_parameters"]
        vp["luma_offset"] = 42
        vp["luma_excursion"] = 255
        vp["color_diff_offset"] = 900
        vp["color_diff_excursion"] = 1000
        component_bit_widths = {
            "Y": 8,
            "C1": 10,
            "C2": 10,
        }

        # Make frame large enough to ensure some blank areas
        vp["frame_width"] = 48
        vp["frame_height"] = 32

        # Check works when luma/color diff are different sizes
        vp["color_diff_format_index"] = color_diff_format_index

        test_cases = list(signal_range(codec_features))

        # Should provide test cases for all components
        assert set(tc.subcase_name for tc in test_cases) == set(["Y", "C1", "C2",])

        # Without going to great lengths we can only really verify that the
        # test patterns designed to produce encoded values of the correct
        # polarity
        for test_case in test_cases:
            pictures = test_case.value.pictures
            component = test_case.subcase_name
            picture_bit_width = component_bit_widths[component]

            # Should have enough pictures for all of the test case pictures
            # expected (may possibly be one longer)
            assert (
                len(test_case.metadata) <= len(pictures) <= len(test_case.metadata) + 1
            )

            for picture, test_points in zip(pictures, test_case.metadata):
                # Test pattern pictures should be saturated
                assert tuple(np.unique(picture[component])) == (
                    0,
                    1 << (picture_bit_width - 1),
                    (1 << picture_bit_width) - 1,
                )

                # Encode test pattern and get the coefficients for just the
                # required component
                state = State(
                    wavelet_index=codec_features["wavelet_index"],
                    wavelet_index_ho=codec_features["wavelet_index_ho"],
                    dwt_depth=codec_features["dwt_depth"],
                    dwt_depth_ho=codec_features["dwt_depth_ho"],
                )
                set_coding_parameters(
                    state,
                    codec_features["video_parameters"],
                    codec_features["picture_coding_mode"],
                )
                picture_encode(state, deepcopy(picture))
                encoded = state["{}_transform".format(component.lower())]

                # Check polarity w.r.t. test patterns
                checked = False
                for test_point in test_points:
                    if test_point["level"] == 1 and test_point["array_name"] in (
                        "L''",
                        "H''",
                    ):
                        checked = True

                        x = test_point["tx"]
                        y = test_point["ty"]

                        level = 1
                        if test_point["array_name"] == "L''":
                            if y % 2 == 0:
                                orient = "LL"
                                level -= 1
                            else:
                                orient = "LH"
                        else:
                            if y % 2 == 0:
                                orient = "HL"
                            else:
                                orient = "HH"
                        y //= 2

                        maximise = test_point["maximise"]

                        value = encoded[level][orient][y][x]

                        if maximise:
                            assert value > 0
                        else:
                            assert value < 0

                assert checked
