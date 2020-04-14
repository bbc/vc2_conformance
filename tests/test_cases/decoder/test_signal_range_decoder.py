import pytest

import os

import sys

import logging

import numpy as np

from copy import deepcopy

from io import BytesIO

from vc2_data_tables import (
    Profiles,
    PictureCodingModes,
    ColorDifferenceSamplingFormats,
)

from vc2_conformance.state import State

from vc2_conformance.bitstream import autofill_and_serialise_sequence

from vc2_conformance.decoder import (
    init_io,
    parse_sequence,
)

from vc2_conformance.test_cases.decoder.signal_range import signal_range

# Add test root directory to path for sample_codec_features test utility module
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..",))

from sample_codec_features import MINIMAL_CODEC_FEATURES


def encode_and_decode(sequence):
    f = BytesIO()
    autofill_and_serialise_sequence(f, sequence)
    f.seek(0)

    pictures = []
    state = State(_output_picture_callback=lambda p, vp: pictures.append(p))
    init_io(state, f)
    parse_sequence(state)

    return pictures


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

    @pytest.mark.parametrize(
        "profile,lossless",
        [
            (Profiles.high_quality, False),
            (Profiles.high_quality, True),
            (Profiles.low_delay, False),
        ],
    )
    @pytest.mark.parametrize("picture_coding_mode", PictureCodingModes)
    @pytest.mark.parametrize(
        "color_diff_format_index",
        [
            ColorDifferenceSamplingFormats.color_4_4_4,
            ColorDifferenceSamplingFormats.color_4_2_0,
        ],
    )
    def test_works_as_intended(
        self,
        codec_features,
        profile,
        lossless,
        picture_coding_mode,
        color_diff_format_index,
    ):
        codec_features["profile"] = profile
        if lossless:
            codec_features["lossless"] = True
            codec_features["picture_bytes"] = None
        else:
            # Allow *plenty* of space to ensure correct QIs can be used
            codec_features["lossless"] = False
            codec_features["picture_bytes"] = (8 * 4) * 3 * 2

        # Check works when force an even number of pictures
        codec_features["picture_coding_mode"] = picture_coding_mode

        # Odd, and differing color depth
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

        # Check works when luma/color diff are different sizes
        vp["color_diff_format_index"] = color_diff_format_index

        test_cases = list(signal_range(codec_features))

        # Should provide test cases for all components
        assert set(tc.subcase_name for tc in test_cases) == set(["Y", "C1", "C2",])

        # Without going to great lengths we can only really verify that the
        # test patterns designed to produce min/max responses in the output
        # produce (clamped) maximal or minimal outputs...
        for test_case in test_cases:
            pictures = encode_and_decode(test_case.value)
            component = test_case.subcase_name
            picture_bit_width = component_bit_widths[component]

            # Should have enough pictures for all of the test case pictures
            # expected (may possibly be one longer)
            assert (
                len(test_case.metadata) <= len(pictures) <= len(test_case.metadata) + 1
            )

            for picture, test_points in zip(pictures, test_case.metadata):
                for test_point in test_points:
                    if test_point["level"] == 1 and test_point["array_name"] in (
                        "Input",
                        "Output",
                    ):
                        x = test_point["tx"]
                        y = test_point["ty"]
                        maximise = test_point["maximise"]

                        if maximise:
                            assert (
                                picture[component][y][x] == (1 << picture_bit_width) - 1
                            )
                        else:
                            assert picture[component][y][x] == 0

    def test_warnings(self, codec_features, caplog):
        # Make it necessary to quantize more than the test patterns otherwise
        # would by providing far too little space (here we don't provide any
        # bits for transform coefficients so the QI must be set to zero out all
        # values)
        codec_features["profile"] = Profiles.high_quality
        codec_features["picture_bytes"] = (
            codec_features["slices_x"] * codec_features["slices_y"] * 4
        )

        # Check that warnings are printed
        caplog.set_level(logging.WARNING)
        test_cases = list(signal_range(codec_features))
        assert "WARNING" in caplog.text
        assert "qindex" in caplog.text

        # Should have provided test cases for all components
        assert set(tc.subcase_name for tc in test_cases) == set(["Y", "C1", "C2",])
