import pytest

from itertools import count

from vc2_data_tables import Levels, WaveletFilters

from vc2_conformance._constraint_table import ValueSet

from vc2_conformance.level_constraints import LEVEL_CONSTRAINTS

from vc2_conformance.codec_features import CodecFeatures

from vc2_conformance.video_parameters import VideoParameters

from vc2_conformance.test_cases.decoder.custom_quantization_matrix import (
    default_quantization_matrix,
    quantization_matrix_from_generator,
    custom_quantization_matrix,
)

from sample_codec_features import MINIMAL_CODEC_FEATURES

from alternative_level_constraints import temporary_level_override


# A set of CodecFeatures with a 2-level symmetric le_gall_5_3 transform and
# custom quant matrix specified
MINIMAL_CODEC_FEATURES_WITH_CUSTOM_QUANT_MATRIX = CodecFeatures(
    MINIMAL_CODEC_FEATURES,
    wavelet_index=WaveletFilters.le_gall_5_3,
    wavelet_index_ho=WaveletFilters.le_gall_5_3,
    dwt_depth=2,
    dwt_depth_ho=0,
    quantization_matrix={
        0: {"LL": 0},
        1: {"HL": 1, "LH": 1, "HH": 1},
        2: {"HL": 1, "LH": 1, "HH": 1},
    },
)


class TestDefaultQuantizationMatrix(object):
    @pytest.mark.parametrize(
        "codec_features",
        [
            # Default quant matrix already in use
            CodecFeatures(
                MINIMAL_CODEC_FEATURES_WITH_CUSTOM_QUANT_MATRIX,
                quantization_matrix=None,
            ),
            # Lossless mode with not enough bits for test pattern
            CodecFeatures(
                MINIMAL_CODEC_FEATURES_WITH_CUSTOM_QUANT_MATRIX,
                video_parameters=VideoParameters(
                    MINIMAL_CODEC_FEATURES_WITH_CUSTOM_QUANT_MATRIX["video_parameters"],
                    luma_excursion=4,
                    color_diff_excursion=4,
                ),
                lossless=True,
                picture_bytes=None,
            ),
            # No default available
            CodecFeatures(
                MINIMAL_CODEC_FEATURES_WITH_CUSTOM_QUANT_MATRIX,
                wavelet_index=WaveletFilters.fidelity,
            ),
        ],
    )
    def test_skipped_cases(self, codec_features):
        assert default_quantization_matrix(codec_features) is None

    @pytest.mark.parametrize("lossless", [False, True])
    def test_uses_default_matrix_instead_of_custom(self, lossless):
        codec_features = CodecFeatures(
            MINIMAL_CODEC_FEATURES_WITH_CUSTOM_QUANT_MATRIX,
            lossless=lossless,
            picture_bytes=(
                None
                if lossless
                else MINIMAL_CODEC_FEATURES_WITH_CUSTOM_QUANT_MATRIX["picture_bytes"]
            ),
        )

        stream = default_quantization_matrix(codec_features)

        custom_quant_matrix_flag_values = set()

        to_visit = list(stream["sequences"][0]["data_units"])
        while to_visit:
            d = to_visit.pop(0)
            if isinstance(d, dict):
                for key, value in d.items():
                    if key == "custom_quant_matrix":
                        custom_quant_matrix_flag_values.add(value)
                    else:
                        to_visit.append(value)

        assert custom_quant_matrix_flag_values == set([False])


@pytest.mark.parametrize(
    "codec_features,generator,exp",
    [
        # Symmetric
        (
            CodecFeatures(dwt_depth=2, dwt_depth_ho=0),
            count(100),
            {
                0: {"LL": 100},
                1: {"HL": 101, "LH": 102, "HH": 103},
                2: {"HL": 104, "LH": 105, "HH": 106},
            },
        ),
        # Asymmetric
        (
            CodecFeatures(dwt_depth=2, dwt_depth_ho=3),
            count(100),
            {
                0: {"L": 100},
                1: {"H": 101},
                2: {"H": 102},
                3: {"H": 103},
                4: {"HL": 104, "LH": 105, "HH": 106},
                5: {"HL": 107, "LH": 108, "HH": 109},
            },
        ),
    ],
)
def test_quantization_matrix_from_generator(codec_features, generator, exp):
    assert quantization_matrix_from_generator(codec_features, generator) == exp


class TestCustomQuantizationMatrix(object):
    @pytest.mark.parametrize(
        "codec_features",
        [
            # Lossless mode with not enough bits for test pattern
            CodecFeatures(
                MINIMAL_CODEC_FEATURES_WITH_CUSTOM_QUANT_MATRIX,
                video_parameters=VideoParameters(
                    MINIMAL_CODEC_FEATURES_WITH_CUSTOM_QUANT_MATRIX["video_parameters"],
                    luma_excursion=4,
                    color_diff_excursion=4,
                ),
                lossless=True,
                picture_bytes=None,
            ),
            # Level prohibits using custom quantisation matrices
            CodecFeatures(
                MINIMAL_CODEC_FEATURES_WITH_CUSTOM_QUANT_MATRIX,
                level=Levels.uhd_over_hd_sdi,
            ),
        ],
    )
    def test_skipped_cases(self, codec_features):
        assert len(list(custom_quantization_matrix(codec_features))) == 0

    @pytest.mark.parametrize("lossless", [False, True])
    @pytest.mark.parametrize(
        "asymmetric,constrain_level_zero,initial_quant_matrix,exp_matrices",
        [
            # By default should produce all three examples
            (
                False,
                False,
                {
                    0: {"LL": 0},
                    1: {"HL": 1, "LH": 1, "HH": 1},
                    2: {"HL": 1, "LH": 1, "HH": 1},
                },
                {
                    "zeros": [0, 0, 0, 0, 0, 0, 0],
                    "arbitrary": [0, 1, 2, 3, 4, 5, 6],
                    "default": [4, 2, 2, 0, 4, 4, 2],
                },
            ),
            # If provided matrix matches a test case, that case should be omitted
            (
                False,
                False,
                {
                    0: {"LL": 0},
                    1: {"HL": 0, "LH": 0, "HH": 0},
                    2: {"HL": 0, "LH": 0, "HH": 0},
                },
                {"arbitrary": [0, 1, 2, 3, 4, 5, 6], "default": [4, 2, 2, 0, 4, 4, 2]},
            ),
            # When no default matrix is available, should omit the default case
            (
                True,
                False,
                {
                    0: {"LL": 0},
                    1: {"HL": 1, "LH": 1, "HH": 1},
                    2: {"HL": 1, "LH": 1, "HH": 1},
                },
                {"zeros": [0, 0, 0, 0, 0, 0, 0], "arbitrary": [0, 1, 2, 3, 4, 5, 6]},
            ),
            # When a level restricts the custom quant index values, this limit should be
            # obeyed
            (
                False,
                True,
                {
                    0: {"LL": 0},
                    1: {"HL": 1, "LH": 1, "HH": 1},
                    2: {"HL": 1, "LH": 1, "HH": 1},
                },
                {"arbitrary": [3, 4, 8, 3, 4, 8, 3]},
            ),
        ],
    )
    def test_generates_custom_quant_matrices(
        self,
        lossless,
        asymmetric,
        constrain_level_zero,
        initial_quant_matrix,
        exp_matrices,
    ):
        codec_features = CodecFeatures(
            MINIMAL_CODEC_FEATURES_WITH_CUSTOM_QUANT_MATRIX,
            wavelet_index_ho=(
                WaveletFilters.le_gall_5_3
                if not asymmetric
                else WaveletFilters.fidelity
            ),
            quantization_matrix=initial_quant_matrix,
            lossless=lossless,
            picture_bytes=(
                None
                if lossless
                else MINIMAL_CODEC_FEATURES_WITH_CUSTOM_QUANT_MATRIX["picture_bytes"]
            ),
        )

        with temporary_level_override():
            if constrain_level_zero:
                # Sanity check
                assert LEVEL_CONSTRAINTS[0]["level"] == ValueSet(0)
                LEVEL_CONSTRAINTS[0]["quant_matrix_values"] = ValueSet(3, 4, 8)

            test_cases = list(custom_quantization_matrix(codec_features))

        matrices = {}

        for test_case in test_cases:
            stream = test_case.value

            to_visit = list(stream["sequences"][0]["data_units"])
            while to_visit:
                d = to_visit.pop(0)
                if isinstance(d, dict):
                    for key, value in d.items():
                        if key == "quant_matrix":
                            assert value["custom_quant_matrix"]
                            matrix = value["quant_matrix"]
                            if test_case.subcase_name in matrices:
                                # All pictures should have same custom
                                # quantization matrix
                                assert matrix == matrices[test_case.subcase_name]
                            else:
                                matrices[test_case.subcase_name] = matrix
                        else:
                            to_visit.append(value)

        assert matrices == exp_matrices
