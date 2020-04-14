import pytest

import os
import sys
import copy

import numpy as np

from vc2_data_tables import (
    QUANTISATION_MATRICES,
    WaveletFilters,
    PictureCodingModes,
    ColorDifferenceSamplingFormats,
)

from vc2_bit_widths.bundle import bundle_index

# Add test root directory to path for sample_codec_features test utility module
sys.path.append(os.path.join(os.path.dirname(__file__), "..",))

from sample_codec_features import MINIMAL_CODEC_FEATURES

from vc2_conformance.test_cases.bit_widths_common import (
    get_bundle_filename,
    get_test_pictures,
    MissingStaticAnalysisError,
)


# A VC-2 bit widths bundle file containing optimised test patterns for a
# 2-level 2D Haar-with-Shift transform for 10 bit pictures and default
# quantization matrix.
BUNDLE_WIDTH_OPTIMISED_PATTERNS = os.path.join(
    os.path.dirname(__file__), "bundle_with_optimised_patterns.zip",
)


@pytest.yield_fixture
def custom_environ():
    orig_environ = os.environ.copy()
    os.environ.clear()
    try:
        yield os.environ
    finally:
        os.environ.clear()
        os.environ.update(orig_environ)


class TestGetBundleFileName(object):
    def test_default(self, custom_environ):
        assert os.path.isfile(get_bundle_filename())

    def test_completeness(self):
        # The default bundle file should contain analyses for every transform
        # with a default quantisation matrix; check that here.
        bundle = bundle_index(get_bundle_filename())

        available = set(
            (
                entry["wavelet_index"],
                entry["wavelet_index_ho"],
                entry["dwt_depth"],
                entry["dwt_depth_ho"],
            )
            for entry in bundle["static_filter_analyses"]
        )

        assert set(QUANTISATION_MATRICES) == available

    def test_custom(self, tmpdir, custom_environ):
        custom_filename = str(tmpdir.join("test.zip"))
        custom_environ["VC2_BIT_WIDTHS_BUNDLE"] = custom_filename
        assert get_bundle_filename() == custom_filename


class TestGetTestPictures(object):
    @pytest.fixture
    def codec_features(self):
        # LeGall 1-level 2D transform, 128x32 luma, 64x16 chroma, 8-bit luma,
        # 10-bit chroma
        codec_features = copy.deepcopy(MINIMAL_CODEC_FEATURES)

        codec_features["wavelet_index"] = WaveletFilters.le_gall_5_3
        codec_features["wavelet_index_ho"] = WaveletFilters.le_gall_5_3
        codec_features["dwt_depth"] = 1
        codec_features["dwt_depth_ho"] = 0

        codec_features["picture_coding_mode"] = PictureCodingModes.pictures_are_fields

        video_parameters = codec_features["video_parameters"]
        video_parameters["frame_width"] = 128
        video_parameters["frame_height"] = 64

        video_parameters["luma_offset"] = 10  # Odd choice
        video_parameters["luma_excursion"] = 200  # 8 bits

        video_parameters["color_diff_offset"] = 1000  # Odd choice
        video_parameters["color_diff_excursion"] = 1000  # 10 bits

        video_parameters[
            "color_diff_format_index"
        ] = ColorDifferenceSamplingFormats.color_4_2_0

        return codec_features

    def test_missing_static_analysis(
        self, codec_features,
    ):
        # Check that the built-in bundle is intact and also that we get some
        # pictures out of the correct types/sizes
        codec_features["dwt_depth"] = 99
        with pytest.raises(MissingStaticAnalysisError):
            get_test_pictures(codec_features)

    @pytest.mark.parametrize(
        "quantisation_matrix", [None, {0: {"LL": 0}, 1: {"LH": 0, "HL": 0, "HH": 0},},]
    )
    @pytest.mark.parametrize(
        "bundle_filename_arg",
        [
            # Check the default is intact and contains the content we need
            [],
            [BUNDLE_WIDTH_OPTIMISED_PATTERNS],
        ],
    )
    def test_basic_test_pictures(
        self, codec_features, quantisation_matrix, bundle_filename_arg,
    ):
        # Check that the built-in bundle is intact and also that we get some
        # pictures out of the correct types/sizes
        codec_features["quantization_matrix"] = quantisation_matrix
        (
            analysis_luma_pictures,
            synthesis_luma_pictures,
            analysis_color_diff_pictures,
            synthesis_color_diff_pictures,
        ) = get_test_pictures(codec_features, *bundle_filename_arg)

        assert len(analysis_luma_pictures) >= 1
        assert len(synthesis_luma_pictures) >= 1

        assert len(analysis_color_diff_pictures) >= 1
        assert len(synthesis_color_diff_pictures) >= 1

        for picture in analysis_luma_pictures + synthesis_luma_pictures:
            assert picture.picture.shape == (32, 128)
            assert tuple(np.unique(picture.picture)) == (0, 128, 255)

        for picture in analysis_color_diff_pictures + synthesis_color_diff_pictures:
            assert picture.picture.shape == (16, 64)
            assert tuple(np.unique(picture.picture)) == (0, 512, 1023)

    @pytest.mark.parametrize(
        "quantisation_matrix,exp_same",
        [
            # Use default (for which an optimised version is available)
            (None, False),
            # Use custom (for which no optimised version is available, done as
            # a sanity check for this test
            ({0: {"LL": 0}, 1: {"LH": 0, "HL": 0, "HH": 0}}, True),
        ],
    )
    def test_optimised_patterns(self, codec_features, quantisation_matrix, exp_same):
        codec_features["quantization_matrix"] = quantisation_matrix

        (
            analysis_luma_pictures,
            synthesis_luma_pictures,
            analysis_color_diff_pictures,
            synthesis_color_diff_pictures,
        ) = get_test_pictures(codec_features)

        (
            opt_analysis_luma_pictures,
            opt_synthesis_luma_pictures,
            opt_analysis_color_diff_pictures,
            opt_synthesis_color_diff_pictures,
        ) = get_test_pictures(codec_features, BUNDLE_WIDTH_OPTIMISED_PATTERNS)

        analysis_same = all(
            np.array_equal(picture.picture, opt_picture.picture)
            for picture, opt_picture in zip(
                analysis_luma_pictures + analysis_color_diff_pictures,
                opt_analysis_luma_pictures + opt_analysis_color_diff_pictures,
            )
        )

        synthesis_same = all(
            np.array_equal(picture.picture, opt_picture.picture)
            for picture, opt_picture in zip(
                synthesis_luma_pictures + synthesis_color_diff_pictures,
                opt_synthesis_luma_pictures + opt_synthesis_color_diff_pictures,
            )
        )

        # Analysis should be identical as no optimisation has taken place
        assert analysis_same

        if exp_same:
            assert synthesis_same
        else:
            assert not synthesis_same
