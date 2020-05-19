import pytest

import numpy as np

import os

from io import BytesIO

from copy import deepcopy

from vc2_data_tables import (
    WaveletFilters,
    QUANTISATION_MATRICES,
    Levels,
    Profiles,
    ColorDifferenceSamplingFormats,
    SourceSamplingModes,
    PictureCodingModes,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    ParseCodes,
)

from sample_codec_features import MINIMAL_CODEC_FEATURES

from vc2_conformance.arrays import width, height

from vc2_conformance.state import State

from vc2_conformance.codec_features import CodecFeatures

from vc2_conformance.video_parameters import VideoParameters

from vc2_conformance.bitstream import (
    BitstreamWriter,
    Serialiser,
    vc2_default_values,
    transform_data,
    quant_matrix,
    QuantMatrix,
    HQSlice,
    hq_slice,
    LDSlice,
    ExtendedTransformParameters,
    DataUnit,
    ParseInfo,
    Sequence,
    Stream,
    autofill_and_serialise_stream,
)

from vc2_conformance.decoder.transform_data_syntax import dc_prediction

from vc2_conformance import decoder

from vc2_conformance import file_format

from vc2_conformance.encoder.sequence_header import make_sequence_header_data_unit

from vc2_conformance.constraint_table import ValueSet

from vc2_conformance.level_constraints import LEVEL_CONSTRAINTS

from vc2_conformance.encoder.exceptions import (
    MissingQuantizationMatrixError,
    IncompatibleLevelAndExtendedTransformParametersError,
    AsymmetricTransformPreVersion3Error,
    PictureBytesSpecifiedForLosslessModeError,
    InsufficientLDPictureBytesError,
    InsufficientHQPictureBytesError,
    LosslessUnsupportedByLowDelayError,
)

from vc2_conformance.encoder.pictures import (
    get_quantization_marix,
    serialize_quantization_matrix,
    apply_dc_prediction,
    calculate_coeffs_bits,
    calculate_hq_length_field,
    quantize_to_fit,
    quantize_coeffs,
    SliceCoeffs,
    ComponentCoeffs,
    transform_and_slice_picture,
    make_hq_slice,
    make_ld_slice,
    make_transform_data_hq_lossless,
    get_safe_lossy_hq_slice_size_scaler,
    make_transform_data_hq_lossy,
    interleave,
    make_transform_data_ld_lossy,
    make_quant_matrix,
    decide_flag,
    make_extended_transform_parameters,
    make_picture_parse_data_unit,
    make_fragment_parse_data_units,
    make_picture_data_units,
)


@pytest.fixture(scope="module")
def lovell():
    """
    A simple 64x64, 8 bit, 4:2:2 sampled test picture, cropped out of a real
    photograph.

    This fixture is a tuple (picture, video_parameters, picture_coding_mode) as
    returned by :py:func:`vc2_conformance.file_format.read`.
    """
    return file_format.read(
        os.path.join(os.path.dirname(__file__), "..", "test_images", "lovell.raw",)
    )


class TestGetQuantMatrix(object):
    def test_default_quantisation_matrix(self):
        codec_features = MINIMAL_CODEC_FEATURES.copy()
        codec_features["wavelet_index"] = WaveletFilters.haar_no_shift
        codec_features["wavelet_index_ho"] = WaveletFilters.le_gall_5_3
        codec_features["dwt_depth"] = 2
        codec_features["dwt_depth_ho"] = 0
        codec_features["quantization_matrix"] = None

        assert (
            get_quantization_marix(codec_features)
            == QUANTISATION_MATRICES[
                (WaveletFilters.haar_no_shift, WaveletFilters.le_gall_5_3, 2, 0,)
            ]
        )

    def test_fail_on_default_unknown_transform(self):
        codec_features = MINIMAL_CODEC_FEATURES.copy()
        codec_features["wavelet_index"] = WaveletFilters.fidelity
        codec_features["wavelet_index_ho"] = WaveletFilters.haar_with_shift
        codec_features["dwt_depth"] = 99
        codec_features["dwt_depth_ho"] = 100
        codec_features["quantization_matrix"] = None

        with pytest.raises(MissingQuantizationMatrixError):
            get_quantization_marix(codec_features)

    def test_custom_quantisation_matrix(self):
        codec_features = MINIMAL_CODEC_FEATURES.copy()
        codec_features["wavelet_index"] = WaveletFilters.le_gall_5_3
        codec_features["wavelet_index_ho"] = WaveletFilters.haar_no_shift
        codec_features["dwt_depth"] = 0
        codec_features["dwt_depth_ho"] = 1

        codec_features["quantization_matrix"] = {
            0: {"L": 0},
            1: {"H": 1},
        }

        assert get_quantization_marix(codec_features) == {
            0: {"L": 0},
            1: {"H": 1},
        }


@pytest.mark.parametrize(
    "dwt_depth,dwt_depth_ho,quantization_matrix",
    [
        (0, 0, {0: {"LL": 10}}),
        (0, 2, {0: {"L": 1}, 1: {"H": 2}, 2: {"H": 3}}),
        (
            2,
            0,
            {
                0: {"LL": 1},
                1: {"HL": 2, "LH": 3, "HH": 4},
                2: {"HL": 5, "LH": 6, "HH": 7},
            },
        ),
        (1, 1, {0: {"L": 1}, 1: {"H": 2}, 2: {"HL": 3, "LH": 4, "HH": 5}}),
    ],
)
def test_serialize_quantization_matrix(
    dwt_depth, dwt_depth_ho, quantization_matrix,
):
    # Check that the function serialises the quantization matrix values in the
    # same order the pseudocode (in this case as implemented in the Serialiser)
    state = State(dwt_depth=dwt_depth, dwt_depth_ho=dwt_depth_ho,)
    context = QuantMatrix(
        custom_quant_matrix=True,
        quant_matrix=serialize_quantization_matrix(quantization_matrix),
    )
    with Serialiser(BitstreamWriter(BytesIO()), context) as ser:
        quant_matrix(ser, state)

    assert state["quant_matrix"] == quantization_matrix


def test_apply_dc_prediction():
    # Simply test that apply_dc_prediction is inverted by dc_prediction on a
    # noise picture...
    rand = np.random.RandomState(0)

    orig = rand.randint(0, 255, (5, 10)).tolist()

    band = deepcopy(orig)

    apply_dc_prediction(band)
    assert band != orig

    dc_prediction(band)
    assert band == orig


@pytest.mark.parametrize(
    "coeffs,exp",
    [
        # Empty case
        ([], 0),
        # Should correctly calculate signed exp-golomb sizes
        ([1], 4),
        ([3], 6),
        # Should support signed values
        ([-1], 4),
        # Should support several values concatenated
        ([1, 3], 4 + 6),
        # Internal zeros should cost space
        ([0, 1, 3], 1 + 4 + 6),
        # Trailing zeros should be ignored
        ([1, 0, 3, 0], 4 + 1 + 6 + 0),
        ([1, 0, 3, 0, 0, 0], 4 + 1 + 6 + 0 + 0 + 0),
        # Fully trailing zeros case should work
        ([0, 0, 0], 0),
    ],
)
def test_calculate_coeffs_bits(coeffs, exp):
    assert calculate_coeffs_bits(coeffs) == exp


@pytest.mark.parametrize(
    "coeffs,slice_size_scaler,exp",
    [
        # Empty case
        ([], 1, 0),
        ([], 2, 0),
        ([0, 0, 0], 1, 0),
        ([0, 0, 0], 2, 0),
        # Should round to whole number of bytes
        ([1], 1, 1),  # 4 bits
        ([3], 1, 1),  # 6 bits
        ([7], 1, 1),  # 8 bits
        ([16], 1, 2),  # 10 bits
        # Size scaler should round-up
        ([7] * 1, 3, 1),  # 1 byte
        ([7] * 2, 3, 1),  # 2 bytes
        ([7] * 3, 3, 1),  # 3 bytes
        ([7] * 4, 3, 2),  # 4 bytes
    ],
)
def test_calculate_hq_length_field(coeffs, slice_size_scaler, exp):
    assert calculate_hq_length_field(coeffs, slice_size_scaler) == exp


@pytest.mark.parametrize(
    "quant_index,coeff_values,quant_matrix_values,exp",
    [
        (0, [], [], []),
        # Don't quantize
        (0, [1, 2, 3, 4], [0, 0, 0, 0], [1, 2, 3, 4]),
        # Divide by two (qi=4)
        (4, [1, 2, 3, 4], [0, 0, 0, 0], [0, 1, 1, 2]),
        # With quant matrix values
        (8, [8, 8, 8], [0, 4, 8], [2, 4, 8]),
    ],
)
def test_quantize_coeffs(quant_index, coeff_values, quant_matrix_values, exp):
    assert quantize_coeffs(quant_index, coeff_values, quant_matrix_values) == exp


class TestQuantizeToFit(object):
    @pytest.fixture
    def random_coeff_sets(self):
        rand = np.random.RandomState(0)
        return [
            ComponentCoeffs(
                rand.randint(0, 1023, length).tolist(),
                rand.randint(0, 8, length).tolist(),
            )
            for length in [50, 100]
        ]

    def test_quantized_values_as_expected(self, random_coeff_sets):
        # Check that the returned values are actually quantized using the
        # specified quantization index
        qindex, quantized_coeff_sets = quantize_to_fit(100, random_coeff_sets)
        assert qindex != 0
        assert len(random_coeff_sets) == len(quantized_coeff_sets)
        for coeffs, quantized_coeffs in zip(random_coeff_sets, quantized_coeff_sets):
            assert quantized_coeffs == quantize_coeffs(
                qindex, coeffs.coeff_values, coeffs.quant_matrix_values,
            )

    @pytest.mark.parametrize("align_bits", [1, 8, 16])
    def test_quantized_values_fit_target_size(self, random_coeff_sets, align_bits):
        target_bits = 1024
        qindex, quantized_coeff_sets = quantize_to_fit(
            target_bits, random_coeff_sets, align_bits,
        )

        # Compute length, accounting for the fact that when align_bits is used,
        # the length of each set of coeffs must be rounded up to a whole
        # multiple of align_bits.
        lengths = [
            ((calculate_coeffs_bits(coeffs) + align_bits - 1) // align_bits)
            * align_bits
            for coeffs in quantized_coeff_sets
        ]
        total_bits = sum(lengths)

        assert total_bits <= target_bits
        assert total_bits != 0

    def test_lengths_measured_separately(self):
        # In this example, if the two sets of coeffs were treated as a single
        # sequence, the quantizer would be required to fit within the limit.
        # However, because they're separate, the trailing zeros are coded for
        # free and so in this case no quantization is required.
        assert quantize_to_fit(
            8,
            [
                ComponentCoeffs([1] + [0] * 7, [0] * 8),
                ComponentCoeffs([1] + [0] * 7, [0] * 8),
            ],
        ) == (0, [[1] + [0] * 7, [1] + [0] * 7])

    def test_minimum_qindex(self):
        assert quantize_to_fit(
            100, [ComponentCoeffs([8, 8, 8], [0, 0, 0])], minimum_qindex=4,
        ) == (4, [[4, 4, 4]])


class TestTransformAndSlicePicture(object):

    # NB: These tests are essentially sanity checks. The later integration test
    # of make_picture_parse serves to more comprehensively check the
    # correctness of transform_and_slice_picture by checking it is inverted by
    # the VC-2 pseudocode decoder.

    @pytest.fixture
    def codec_features(self):
        # A 1D Haar (no shift) transform on a 12x4 4:2:2 8 bit image, HQ
        # profile, with 3x2 picture slices
        return CodecFeatures(
            name="basic",
            level=Levels.unconstrained,
            profile=Profiles.high_quality,
            major_version=3,
            minor_version=0,
            picture_coding_mode=PictureCodingModes.pictures_are_frames,
            video_parameters=VideoParameters(
                frame_width=12,
                frame_height=4,
                color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
                source_sampling=SourceSamplingModes.progressive,
                top_field_first=True,
                frame_rate_numer=1,
                frame_rate_denom=1,
                pixel_aspect_ratio_numer=1,
                pixel_aspect_ratio_denom=1,
                clean_width=12,
                clean_height=4,
                left_offset=0,
                top_offset=0,
                luma_offset=0,
                luma_excursion=255,
                color_diff_offset=128,
                color_diff_excursion=255,
                color_primaries_index=PresetColorPrimaries.hdtv,
                color_matrix_index=PresetColorMatrices.hdtv,
                transfer_function_index=PresetTransferFunctions.tv_gamma,
            ),
            wavelet_index=WaveletFilters.haar_no_shift,
            wavelet_index_ho=WaveletFilters.haar_no_shift,
            dwt_depth=0,
            dwt_depth_ho=1,
            slices_x=3,
            slices_y=2,
            fragment_slice_count=0,
            lossless=False,
            picture_bytes=24,
            quantization_matrix={0: {"L": 123}, 1: {"H": 321}},
        )

    @pytest.fixture
    def picture(self):
        # The picture below actually corresponds to the following when values
        # are offset to lie around 0:
        #
        #     Y = [[ 0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11],
        #          [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
        #          [24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35],
        #          [36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]]
        #
        #    C1 = [[ 0,  1,  2,  3,  4,  5],
        #          [ 6,  7,  8,  9, 10, 11],
        #          [12, 13, 14, 15, 16, 17],
        #          [18, 19, 20, 21, 22, 23]]
        #
        #    C2 = [[ -0,  -1,  -2,  -3,  -4,  -5],
        #          [ -6,  -7,  -8,  -9, -10, -11],
        #          [-12, -13, -14, -15, -16, -17],
        #          [-18, -19, -20, -21, -22, -23]]

        return {
            "Y": [  # Ascending numbers starting from 128
                [128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139],
                [140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151],
                [152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163],
                [164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175],
            ],
            "C1": [  # Ascending numbers starting from 128
                [128, 129, 130, 131, 132, 133],
                [134, 135, 136, 137, 138, 139],
                [140, 141, 142, 143, 144, 145],
                [146, 147, 148, 149, 150, 151],
            ],
            "C2": [  # Descending numbers startin from 128
                [128, 127, 126, 125, 124, 123],
                [122, 121, 120, 119, 118, 117],
                [116, 115, 114, 113, 112, 111],
                [110, 109, 108, 107, 106, 105],
            ],
            "pic_num": 123,
        }

    def test_basic(self, codec_features, picture):
        # This test checks that we get the same result as a hand-evaluated Haar
        # transform.
        transform_coeffs = transform_and_slice_picture(codec_features, picture)

        # Check slice sizes are as expected
        assert width(transform_coeffs) == 3
        assert height(transform_coeffs) == 2

        for sy in range(2):
            for sx in range(3):
                assert len(transform_coeffs[sy][sx].Y.coeff_values) == (12 // 3) * (
                    4 // 2
                )
                assert len(transform_coeffs[sy][sx].C1.coeff_values) == (6 // 3) * (
                    4 // 2
                )
                assert len(transform_coeffs[sy][sx].C2.coeff_values) == (6 // 3) * (
                    4 // 2
                )

        # Check transform values are as expected in a couple of example slices
        # as a sanity check

        # Slice 0 0
        assert transform_coeffs[0][0].Y.coeff_values == [
            # Level 0, Subband L
            1,
            3,
            13,
            15,
            # Level 0, Subband H
            1,
            1,
            1,
            1,
        ]
        assert transform_coeffs[0][0].C1.coeff_values == [
            # Level 0, Subband L
            1,
            7,
            # Level 0, Subband H
            1,
            1,
        ]
        assert transform_coeffs[0][0].C2.coeff_values == [
            # Level 0, Subband L
            0,
            -6,
            # Level 0, Subband H
            -1,
            -1,
        ]

        # Slice 2 1
        assert transform_coeffs[1][2].Y.coeff_values == [
            # Level 0, Subband L
            33,
            35,
            45,
            47,
            # Level 0, Subband H
            1,
            1,
            1,
            1,
        ]
        assert transform_coeffs[1][2].C1.coeff_values == [
            # Level 0, Subband L
            17,
            23,
            # Level 0, Subband H
            1,
            1,
        ]
        assert transform_coeffs[1][2].C2.coeff_values == [
            # Level 0, Subband L
            -16,
            -22,
            # Level 0, Subband H
            -1,
            -1,
        ]

        # Check quantisation matrix values are right throughout
        for sy in range(2):
            for sx in range(3):
                assert transform_coeffs[sy][sx].Y.quant_matrix_values == (
                    # Level 0, Suband L
                    ([123] * 4)
                    +
                    # Level 0, Suband H
                    ([321] * 4)
                )
                assert transform_coeffs[sy][sx].C1.quant_matrix_values == (
                    # Level 0, Suband L
                    ([123] * 2)
                    +
                    # Level 0, Suband H
                    ([321] * 2)
                )
                assert transform_coeffs[sy][sx].C2.quant_matrix_values == (
                    # Level 0, Suband L
                    ([123] * 2)
                    +
                    # Level 0, Suband H
                    ([321] * 2)
                )

    def test_dc_prediction(self, codec_features, picture):
        codec_features["profile"] = Profiles.low_delay
        transform_coeffs = transform_and_slice_picture(codec_features, picture)

        # As a santiy check, check the top-left slice does as a hand-calculated
        # result predicts...
        assert transform_coeffs[0][0].Y.coeff_values == [
            # Level 0, Subband L
            # Before DC prediction
            #   1, 3,
            #   13, 15,
            1,
            3 - 1,
            13 - 1,
            15 - 6,
            # Level 0, Subband H
            1,
            1,
            1,
            1,
        ]
        assert transform_coeffs[0][0].C1.coeff_values == [
            # Level 0, Subband L
            # Before DC prediction
            #   1,
            #   7,
            1,
            7 - 1,
            # Level 0, Subband H
            1,
            1,
        ]
        assert transform_coeffs[0][0].C2.coeff_values == [
            # Level 0, Subband L
            # Before DC Prediction
            #   0,
            #   -6,
            0,
            -6 - 0,
            # Level 0, Subband H
            -1,
            -1,
        ]


class TestMakeHQSlice(object):
    def test_unspecified_total_length(self):
        assert make_hq_slice(
            [1, 1, 1, 1, 1, 1, 1, 1],  # 4 bytes
            [1, 1, 1, 1],  # 2 bytes
            [1, 1, 1, 1],  # 2 bytes
            total_length=None,
            qindex=123,
            slice_size_scaler=1,
        ) == HQSlice(
            qindex=123,
            slice_y_length=4,
            slice_c1_length=2,
            slice_c2_length=2,
            y_transform=[1, 1, 1, 1, 1, 1, 1, 1],
            c1_transform=[1, 1, 1, 1],
            c2_transform=[1, 1, 1, 1],
        )

    def test_unspecified_total_length_with_scaler(self):
        assert make_hq_slice(
            [1, 1, 1, 1, 1, 1, 1, 1],  # 4 bytes
            [1, 1, 1, 1],  # 2 bytes
            [1, 1, 1, 1],  # 2 bytes
            total_length=None,
            qindex=123,
            slice_size_scaler=3,
        ) == HQSlice(
            qindex=123,
            slice_y_length=2,
            slice_c1_length=1,
            slice_c2_length=1,
            y_transform=[1, 1, 1, 1, 1, 1, 1, 1],
            c1_transform=[1, 1, 1, 1],
            c2_transform=[1, 1, 1, 1],
        )

    def test_specified_total_length(self):
        assert make_hq_slice(
            [1, 1, 1, 1, 1, 1, 1, 1],  # 4 bytes
            [1, 1, 1, 1],  # 2 bytes
            [1, 1, 1, 1],  # 2 bytes
            total_length=100,
            qindex=123,
            slice_size_scaler=1,
        ) == HQSlice(
            qindex=123,
            slice_y_length=4,
            slice_c1_length=2,
            slice_c2_length=100 - 4 - 2,
            y_transform=[1, 1, 1, 1, 1, 1, 1, 1],
            c1_transform=[1, 1, 1, 1],
            c2_transform=[1, 1, 1, 1],
        )

    def test_specified_total_length_with_scaler(self):
        assert make_hq_slice(
            [1, 1, 1, 1, 1, 1, 1, 1],  # 4 bytes
            [1, 1, 1, 1],  # 2 bytes
            [1, 1, 1, 1],  # 2 bytes
            total_length=100,
            qindex=123,
            slice_size_scaler=3,
        ) == HQSlice(
            qindex=123,
            slice_y_length=2,
            slice_c1_length=1,
            slice_c2_length=100 - 2 - 1,
            y_transform=[1, 1, 1, 1, 1, 1, 1, 1],
            c1_transform=[1, 1, 1, 1],
            c2_transform=[1, 1, 1, 1],
        )

    @pytest.mark.parametrize("slice_size_scaler", [1, 3])
    def test_seriallised_size_matches_request(self, slice_size_scaler):
        context = make_hq_slice(
            [1, 1, 1, 1, 1, 1, 1, 1],  # 4 bytes
            [1, 1, 1, 1],  # 2 bytes
            [1, 1, 1, 1],  # 2 bytes
            total_length=100,
            qindex=123,
            slice_size_scaler=slice_size_scaler,
        )

        f = BytesIO()
        state = State(
            luma_width=8,
            luma_height=1,
            color_diff_width=4,
            color_diff_height=1,
            slices_x=1,
            slices_y=1,
            slice_prefix_bytes=0,
            slice_size_scaler=slice_size_scaler,
            dwt_depth=0,
            dwt_depth_ho=0,
        )
        with Serialiser(BitstreamWriter(f), context, vc2_default_values) as ser:
            hq_slice(ser, state, 0, 0)

        assert len(f.getvalue()) == 4 + 100 * slice_size_scaler


def test_make_ld_slice():
    assert make_ld_slice(
        [1, 1, 1, 1], [1, 1, 1, 1, 1, 1, 1, 1], qindex=123,  # 2 bytes  # 4 bytes
    ) == LDSlice(
        qindex=123,
        slice_y_length=16,
        y_transform=[1, 1, 1, 1],
        c_transform=[1, 1, 1, 1, 1, 1, 1, 1],
    )


class TestMakeTransformDataHQLossless(object):
    def test_all_zeros(self):
        # Special case should still produce slice_size_scaler of 1
        slice_size_scaler, transform_data = make_transform_data_hq_lossless(
            [
                [
                    SliceCoeffs(
                        ComponentCoeffs([0], [0]),
                        ComponentCoeffs([0], [0]),
                        ComponentCoeffs([0], [0]),
                    ),
                ]
            ]
        )
        assert slice_size_scaler == 1

        assert len(transform_data["hq_slices"]) == 1
        assert transform_data["hq_slices"][0]["slice_y_length"] == 0
        assert transform_data["hq_slices"][0]["slice_c1_length"] == 0
        assert transform_data["hq_slices"][0]["slice_c2_length"] == 0

    def test_no_slice_size_scaler_required(self):
        # Here all slices components are below 255 bytes long, but some are
        # above 255 per slice.
        slice_size_scaler, transform_data = make_transform_data_hq_lossless(
            [
                [
                    SliceCoeffs(  # 1 byte slice components
                        ComponentCoeffs([7], [0]),
                        ComponentCoeffs([7], [0]),
                        ComponentCoeffs([7], [0]),
                    ),
                    SliceCoeffs(  # 255 byte slice components
                        ComponentCoeffs([7] * 255, [0] * 255),
                        ComponentCoeffs([7] * 255, [0] * 255),
                        ComponentCoeffs([7] * 255, [0] * 255),
                    ),
                ]
            ]
        )
        assert slice_size_scaler == 1

        assert len(transform_data["hq_slices"]) == 2

        assert transform_data["hq_slices"][0]["slice_y_length"] == 1
        assert transform_data["hq_slices"][0]["slice_c1_length"] == 1
        assert transform_data["hq_slices"][0]["slice_c2_length"] == 1

        assert transform_data["hq_slices"][1]["slice_y_length"] == 255
        assert transform_data["hq_slices"][1]["slice_c1_length"] == 255
        assert transform_data["hq_slices"][1]["slice_c2_length"] == 255

    def test_minimum_slice_size_scaler(self):
        # 3 byte slice components
        slice_size_scaler, transform_data = make_transform_data_hq_lossless(
            [
                [
                    SliceCoeffs(
                        ComponentCoeffs([7] * 3, [0] * 3),
                        ComponentCoeffs([7] * 3, [0] * 3),
                        ComponentCoeffs([7] * 3, [0] * 3),
                    ),
                    SliceCoeffs(
                        ComponentCoeffs([7] * 3, [0] * 3),
                        ComponentCoeffs([7] * 3, [0] * 3),
                        ComponentCoeffs([7] * 3, [0] * 3),
                    ),
                ]
            ],
            minimum_slice_size_scaler=2,
        )
        assert slice_size_scaler == 2

        assert len(transform_data["hq_slices"]) == 2

        assert transform_data["hq_slices"][0]["slice_y_length"] == 2
        assert transform_data["hq_slices"][0]["slice_c1_length"] == 2
        assert transform_data["hq_slices"][0]["slice_c2_length"] == 2

        assert transform_data["hq_slices"][1]["slice_y_length"] == 2
        assert transform_data["hq_slices"][1]["slice_c1_length"] == 2
        assert transform_data["hq_slices"][1]["slice_c2_length"] == 2

    def test_slice_size_scaler_required(self):
        slice_size_scaler, transform_data = make_transform_data_hq_lossless(
            [
                [
                    SliceCoeffs(  # 1 byte slice components
                        ComponentCoeffs([7], [0]),
                        ComponentCoeffs([7], [0]),
                        ComponentCoeffs([7], [0]),
                    ),
                    SliceCoeffs(  # 255 byte slice components
                        ComponentCoeffs([7] * 255, [0] * 255),
                        ComponentCoeffs([7] * 255, [0] * 255),
                        ComponentCoeffs([7] * 255, [0] * 255),
                    ),
                    SliceCoeffs(  # 700 byte slice components
                        ComponentCoeffs([7] * 700, [0] * 255),
                        ComponentCoeffs([7] * 700, [0] * 255),
                        ComponentCoeffs([7] * 700, [0] * 255),
                    ),
                ]
            ]
        )
        assert slice_size_scaler == 3

        assert len(transform_data["hq_slices"]) == 3

        assert transform_data["hq_slices"][0]["slice_y_length"] == 1
        assert transform_data["hq_slices"][0]["slice_c1_length"] == 1
        assert transform_data["hq_slices"][0]["slice_c2_length"] == 1

        assert transform_data["hq_slices"][1]["slice_y_length"] == 85
        assert transform_data["hq_slices"][1]["slice_c1_length"] == 85
        assert transform_data["hq_slices"][1]["slice_c2_length"] == 85

        assert transform_data["hq_slices"][2]["slice_y_length"] == 234
        assert transform_data["hq_slices"][2]["slice_c1_length"] == 234
        assert transform_data["hq_slices"][2]["slice_c2_length"] == 234


@pytest.mark.parametrize(
    "picture_bytes,exp_slice_size_scaler",
    [
        # Special case: 4 bytes per slice (the minimum possible)
        (3 * 2 * 4, 1),
        # No need for a slice size scaler (<259 bytes per slice)
        (3 * 2 * 100, 1),
        # Maximum slice size before we might need a slice size scaler
        (3 * 2 * (255 + 4), 1),
        # Just over the line
        ((3 * 2 * (255 + 4)) + 1, 2),
        # Just short of next threshold
        ((3 * 2 * (255 + 255 + 4)), 2),
        # Just over next threshold
        ((3 * 2 * (255 + 255 + 4)) + 1, 3),
    ],
)
def test_get_safe_lossy_hq_slice_size_scaler(picture_bytes, exp_slice_size_scaler):
    assert (
        get_safe_lossy_hq_slice_size_scaler(picture_bytes, 3 * 2)
        == exp_slice_size_scaler
    )


@pytest.mark.parametrize(
    "picture_bytes,minimum_slice_size_scaler,exp_slice_size_scaler",
    [
        # In this example we're using 3x2 picture slices
        # 100 bytes per slice; easily fits
        (3 * 2 * 100, 1, 1),
        # Exactly 259 bytes per slice; *just* fits
        (3 * 2 * 259, 1, 1),
        # *Just* over 259 bytes per slice; requires a scaler
        (3 * 2 * 259 + 1, 1, 2),
        (3 * 2 * 259 + 2, 1, 2),
        (3 * 2 * 259 + 3, 1, 2),
        (3 * 2 * 259 + 4, 1, 2),
        # 100 bytes per slice; but force a larger slice size scaler
        (3 * 2 * 100, 3, 3),
    ],
)
def test_make_transform_data_hq_lossy(
    picture_bytes, minimum_slice_size_scaler, exp_slice_size_scaler
):
    # Using 3x2 slices. We need to have enough data per slice that we stil need
    # the quantizer to fit into 255-4 bytes.
    #
    # 6x9 pixels per slice, with 4:4:4 color at 8 bits per sample should be enough:
    #   6*9 = 54 pixels per slice
    #   3*54 = 162 values per slice
    #   16*162 = 2592 bits per 16-bit values
    #   2*2592 = 5184 bits (approx) as exp golomb values
    #          = 648 bytes
    rand = np.random.RandomState(0)
    sw = 6
    sh = 9
    slices_x = 3
    slices_y = 2
    slice_size_scaler, context = make_transform_data_hq_lossy(
        picture_bytes,
        [
            [
                SliceCoeffs(
                    ComponentCoeffs(
                        rand.randint(-(1 << 15), (1 << 15) - 1, sw * sh).tolist(),
                        [0] * sw * sh,
                    ),
                    ComponentCoeffs(
                        rand.randint(-(1 << 15), (1 << 15) - 1, sw * sh).tolist(),
                        [0] * sw * sh,
                    ),
                    ComponentCoeffs(
                        rand.randint(-(1 << 15), (1 << 15) - 1, sw * sh).tolist(),
                        [0] * sw * sh,
                    ),
                )
                for sx in range(slices_x)
            ]
            for sy in range(slices_y)
        ],
        minimum_slice_size_scaler=minimum_slice_size_scaler,
    )
    assert slice_size_scaler == exp_slice_size_scaler

    # Check that quantization has been applied to all slices
    assert all(hq_slice["qindex"] > 0 for hq_slice in context["hq_slices"])

    # Check that the seriallized length is as expected

    f = BytesIO()
    state = State(
        parse_code=ParseCodes.high_quality_picture,
        slices_x=slices_x,
        slices_y=slices_y,
        luma_width=slices_x * sw,
        luma_height=slices_y * sh,
        color_diff_width=slices_x * sw,
        color_diff_height=slices_y * sh,
        dwt_depth=0,
        dwt_depth_ho=0,
        slice_prefix_bytes=0,
        slice_size_scaler=slice_size_scaler,
    )
    with Serialiser(BitstreamWriter(f), context, vc2_default_values) as ser:
        transform_data(ser, state)
    serialized_length = len(f.getvalue())

    coeff_bytes = picture_bytes - (slices_x * slices_y * 4)
    if coeff_bytes % slice_size_scaler == 0:
        # If the space assigned to coefficient bytes is a multiple of the
        # slice_size_scaler then we should able to *exactly* match the
        # requested picture_bytes
        assert serialized_length == picture_bytes
    else:
        # Otherwise, should be within slice_size_scaler bytes of the requested
        # size
        assert abs(serialized_length - picture_bytes) < slice_size_scaler


def test_interleave():
    assert interleave([], []) == []
    assert interleave([1, 2, 3], [4, 5, 6]) == [1, 4, 2, 5, 3, 6]


class TestMakeTransformDataLDLossy(object):
    def test_interleaved_color(self):
        transform_data = make_transform_data_ld_lossy(
            999,
            [
                [
                    SliceCoeffs(
                        ComponentCoeffs([1, 2, 3, 4], [0, 0, 0, 0]),
                        ComponentCoeffs([1, 2], [0, 0]),
                        ComponentCoeffs([3, 4], [0, 0]),
                    ),
                ]
            ],
        )

        assert transform_data["ld_slices"][0]["qindex"] == 0
        assert transform_data["ld_slices"][0]["y_transform"] == [1, 2, 3, 4]
        assert transform_data["ld_slices"][0]["c_transform"] == [1, 3, 2, 4]

    @pytest.mark.parametrize(
        "picture_bytes",
        [
            # A range of sizes which will require different slice_y_length sizes
            3 * 2 * 32,
            3 * 2 * 100,
            3 * 2 * 255,
            # Sizes which will result in different slices being different lengths
            3 * 2 * 32 + 1,
            3 * 2 * 32 + 2,
            3 * 2 * 32 + 3,
        ],
    )
    def test_size_is_correct(self, picture_bytes):
        # Using 3x2 slices. We need to have enough data per slice that we stil
        # need the quantizer to fit everything into 255 - ~2 bytes.
        #
        # 6x9 pixels per slice, with 4:4:4 color at 8 bits per sample should be enough:
        #   6*9 = 54 pixels per slice
        #   3*54 = 162 values per slice
        #   16*162 = 2592 bits per 16-bit values
        #   2*2592 = 5184 bits (approx) as exp golomb values
        #          = 648 bytes
        rand = np.random.RandomState(0)
        sw = 6
        sh = 9
        slices_x = 3
        slices_y = 2
        context = make_transform_data_ld_lossy(
            picture_bytes,
            [
                [
                    SliceCoeffs(
                        ComponentCoeffs(
                            rand.randint(-(1 << 15), (1 << 15) - 1, sw * sh).tolist(),
                            [0] * sw * sh,
                        ),
                        ComponentCoeffs(
                            rand.randint(-(1 << 15), (1 << 15) - 1, sw * sh).tolist(),
                            [0] * sw * sh,
                        ),
                        ComponentCoeffs(
                            rand.randint(-(1 << 15), (1 << 15) - 1, sw * sh).tolist(),
                            [0] * sw * sh,
                        ),
                    )
                    for sx in range(slices_x)
                ]
                for sy in range(slices_y)
            ],
        )

        # Check that quantization has been applied to all slices
        assert all(ld_slice["qindex"] > 0 for ld_slice in context["ld_slices"])

        # Check that the seriallized length is as expected
        f = BytesIO()
        state = State(
            parse_code=ParseCodes.low_delay_picture,
            slices_x=slices_x,
            slices_y=slices_y,
            luma_width=slices_x * sw,
            luma_height=slices_y * sh,
            color_diff_width=slices_x * sw,
            color_diff_height=slices_y * sh,
            dwt_depth=0,
            dwt_depth_ho=0,
            slice_bytes_numerator=picture_bytes,
            slice_bytes_denominator=slices_x * slices_y,
        )
        with Serialiser(BitstreamWriter(f), context, vc2_default_values) as ser:
            transform_data(ser, state)
        serialized_length = len(f.getvalue())

        assert serialized_length == picture_bytes


class TestMakeQuantMatrix(object):
    def test_default(self):
        assert make_quant_matrix(
            CodecFeatures(quantization_matrix=None,)
        ) == QuantMatrix(custom_quant_matrix=False,)

    def test_custom(self):
        assert make_quant_matrix(
            CodecFeatures(
                dwt_depth=0,
                dwt_depth_ho=1,
                quantization_matrix={0: {"L": 10}, 1: {"H": 20}},
            )
        ) == QuantMatrix(custom_quant_matrix=True, quant_matrix=[10, 20],)


class TestMakeDecideFlag(object):
    @pytest.yield_fixture
    def level_constraints(self):
        # Override allow temporary modifications to the level constraints
        original_constraints = deepcopy(LEVEL_CONSTRAINTS)

        try:
            yield LEVEL_CONSTRAINTS
        finally:
            LEVEL_CONSTRAINTS.clear()
            LEVEL_CONSTRAINTS.extend(original_constraints)

    @pytest.mark.parametrize("required,expected", [(True, True), (False, False)])
    def test_unconstrained(self, required, expected):
        assert (
            decide_flag(MINIMAL_CODEC_FEATURES, "asym_transform_index_flag", required,)
            is expected
        )

    @pytest.mark.parametrize("required", [True, False])
    def test_constrained_true(self, level_constraints, required):
        assert level_constraints[0]["level"] == ValueSet(0)
        level_constraints[0]["asym_transform_index_flag"] = ValueSet(True)
        assert (
            decide_flag(MINIMAL_CODEC_FEATURES, "asym_transform_index_flag", required,)
            is True
        )

    def test_constrained_false_not_required(self, level_constraints):
        assert level_constraints[0]["level"] == ValueSet(0)
        level_constraints[0]["asym_transform_index_flag"] = ValueSet(False)
        assert (
            decide_flag(MINIMAL_CODEC_FEATURES, "asym_transform_index_flag", False,)
            is False
        )

    def test_constrained_false_but_required(self, level_constraints):
        assert level_constraints[0]["level"] == ValueSet(0)
        level_constraints[0]["asym_transform_index_flag"] = ValueSet(False)
        with pytest.raises(IncompatibleLevelAndExtendedTransformParametersError):
            decide_flag(
                MINIMAL_CODEC_FEATURES, "asym_transform_index_flag", True,
            )


class TestMakeExtendedTransformParameters(object):
    @pytest.yield_fixture
    def level_constraints(self):
        # Override allow temporary modifications to the level constraints
        original_constraints = deepcopy(LEVEL_CONSTRAINTS)

        try:
            yield LEVEL_CONSTRAINTS
        finally:
            LEVEL_CONSTRAINTS.clear()
            LEVEL_CONSTRAINTS.extend(original_constraints)

    def test_symmetric(self):
        assert make_extended_transform_parameters(
            CodecFeatures(
                MINIMAL_CODEC_FEATURES,
                wavelet_index=WaveletFilters.haar_with_shift,
                wavelet_index_ho=WaveletFilters.haar_with_shift,
                dwt_depth=2,
                dwt_depth_ho=0,
            )
        ) == ExtendedTransformParameters(
            asym_transform_index_flag=False, asym_transform_flag=False,
        )

    def test_forced_flags(self, level_constraints):
        # Use the level to force the asym transform flags to be specified for a
        # symmetric transform
        assert level_constraints[0]["level"] == ValueSet(0)
        level_constraints[0]["asym_transform_index_flag"] = ValueSet(True)
        level_constraints[0]["asym_transform_flag"] = ValueSet(True)

        assert make_extended_transform_parameters(
            CodecFeatures(
                MINIMAL_CODEC_FEATURES,
                wavelet_index=WaveletFilters.haar_with_shift,
                wavelet_index_ho=WaveletFilters.haar_with_shift,
                dwt_depth=2,
                dwt_depth_ho=0,
            )
        ) == ExtendedTransformParameters(
            asym_transform_index_flag=True,
            wavelet_index_ho=WaveletFilters.haar_with_shift,
            asym_transform_flag=True,
            dwt_depth_ho=0,
        )

    def test_asymmetric_transform_index(self):
        assert make_extended_transform_parameters(
            CodecFeatures(
                MINIMAL_CODEC_FEATURES,
                wavelet_index=WaveletFilters.le_gall_5_3,
                wavelet_index_ho=WaveletFilters.haar_no_shift,
                dwt_depth=2,
                dwt_depth_ho=0,
            )
        ) == ExtendedTransformParameters(
            asym_transform_index_flag=True,
            wavelet_index_ho=WaveletFilters.haar_no_shift,
            asym_transform_flag=False,
        )

    def test_asymmetric_transform(self):
        assert make_extended_transform_parameters(
            CodecFeatures(
                MINIMAL_CODEC_FEATURES,
                wavelet_index=WaveletFilters.haar_with_shift,
                wavelet_index_ho=WaveletFilters.haar_with_shift,
                dwt_depth=2,
                dwt_depth_ho=1,
            )
        ) == ExtendedTransformParameters(
            asym_transform_index_flag=False, asym_transform_flag=True, dwt_depth_ho=1,
        )


def serialize_and_decode(sequence):
    """
    Serialise a provided :py:class:`Sequence` and then decode them with the
    conformance checking decoder. Return all decoded pictures.
    """
    # Serialise
    f = BytesIO()
    autofill_and_serialise_stream(f, Stream(sequences=[sequence]))

    # Setup callback to capture decoded pictures
    decoded_pictures = []

    def output_picture_callback(picture, video_parameters):
        decoded_pictures.append(picture)

    # Feed to conformance checking decoder
    f.seek(0)
    state = State(_output_picture_callback=output_picture_callback)
    decoder.init_io(state, f)
    decoder.parse_stream(state)

    return decoded_pictures


class TestMakePictureParseDataUnit(object):
    # These tests serve as integration tests of most of the rest of the module
    # to ensure that the encoder does actually match up to the pseudocode
    # defined decoder.

    @pytest.fixture
    def codec_features(self):
        # NB: By default this produces uneaven slice sizes
        return CodecFeatures(
            name="basic",
            level=Levels.unconstrained,
            profile=Profiles.high_quality,
            major_version=3,
            minor_version=0,
            picture_coding_mode=PictureCodingModes.pictures_are_frames,
            video_parameters=VideoParameters(
                frame_width=64,
                frame_height=32,
                color_diff_format_index=ColorDifferenceSamplingFormats.color_4_2_2,
                source_sampling=SourceSamplingModes.progressive,
                top_field_first=True,
                frame_rate_numer=1,
                frame_rate_denom=1,
                pixel_aspect_ratio_numer=1,
                pixel_aspect_ratio_denom=1,
                clean_width=64,
                clean_height=32,
                left_offset=0,
                top_offset=0,
                luma_offset=0,
                luma_excursion=255,
                color_diff_offset=128,
                color_diff_excursion=255,
                color_primaries_index=PresetColorPrimaries.hdtv,
                color_matrix_index=PresetColorMatrices.hdtv,
                transfer_function_index=PresetTransferFunctions.tv_gamma,
            ),
            wavelet_index=WaveletFilters.le_gall_5_3,
            wavelet_index_ho=WaveletFilters.le_gall_5_3,
            dwt_depth=2,
            dwt_depth_ho=0,
            slices_x=5,
            slices_y=7,
            fragment_slice_count=0,
            lossless=False,
            picture_bytes=500,
            quantization_matrix=None,
        )

    @pytest.fixture
    def noise_picture(self, codec_features):
        # A noise plate...
        rand = np.random.RandomState(0)

        y_shape = (
            codec_features["video_parameters"]["frame_height"],
            codec_features["video_parameters"]["frame_width"],
        )
        c_shape = (
            codec_features["video_parameters"]["frame_height"],
            codec_features["video_parameters"]["frame_width"] // 2,
        )

        return {
            "Y": rand.randint(0, 255, y_shape).tolist(),
            "C1": rand.randint(0, 255, c_shape).tolist(),
            "C2": rand.randint(0, 255, c_shape).tolist(),
            "pic_num": 100,
        }

    @pytest.fixture
    def natural_picture(self, codec_features, lovell):
        picture, video_parameters, picture_coding_mode = lovell
        codec_features["video_parameters"] = video_parameters
        codec_features["picture_coding_mode"] = picture_coding_mode
        return picture

    @pytest.mark.parametrize(
        "major_version,wavelet_index,wavelet_index_ho,dwt_depth,dwt_depth_ho",
        [
            # Version 2 (no extended_transform_parameters)
            (2, WaveletFilters.le_gall_5_3, WaveletFilters.le_gall_5_3, 2, 0,),
            # Version 3 (has extended_transform_parameters)
            (3, WaveletFilters.le_gall_5_3, WaveletFilters.le_gall_5_3, 2, 0,),
            # Version 3 + asymmetric transform
            (3, WaveletFilters.haar_no_shift, WaveletFilters.le_gall_5_3, 2, 1,),
        ],
    )
    def test_lossless(
        self,
        codec_features,
        noise_picture,
        major_version,
        wavelet_index,
        wavelet_index_ho,
        dwt_depth,
        dwt_depth_ho,
    ):
        # Test that lossless mode truly is lossless. It is also used to check
        # features such as asymmetric transforms work as expected.
        #
        # This test should be a
        # fairly reliable indicator of whether anything has been done wrong in
        # terms of slicing, transforming, quantizing and serialising the
        # stream.
        codec_features["lossless"] = True
        codec_features["picture_bytes"] = None

        codec_features["major_version"] = major_version
        codec_features["wavelet_index"] = wavelet_index
        codec_features["wavelet_index_ho"] = wavelet_index_ho
        codec_features["dwt_depth"] = dwt_depth
        codec_features["dwt_depth_ho"] = dwt_depth_ho

        decoded_pictures = serialize_and_decode(
            Sequence(
                data_units=[
                    make_sequence_header_data_unit(codec_features),
                    make_picture_parse_data_unit(codec_features, noise_picture),
                    DataUnit(
                        parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)
                    ),
                ]
            )
        )

        assert decoded_pictures == [noise_picture]

    @pytest.mark.parametrize("profile", Profiles)
    def test_lossy(self, codec_features, natural_picture, profile):
        codec_features["profile"] = profile

        # Chose an approx 4:1 compression scheme
        codec_features["lossless"] = False
        codec_features["picture_bytes"] = (
            codec_features["video_parameters"]["frame_width"]
            * codec_features["video_parameters"]["frame_height"]
            * 2
        ) // 4

        # Compress
        decoded_pictures = serialize_and_decode(
            Sequence(
                data_units=[
                    make_sequence_header_data_unit(codec_features),
                    make_picture_parse_data_unit(codec_features, natural_picture),
                    DataUnit(
                        parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)
                    ),
                ]
            )
        )

        # Check that decoded picture is approximately the same as the original
        assert len(decoded_pictures) == 1
        for component in ["Y", "C1", "C2"]:
            max_f = np.max(natural_picture[component])
            error = np.array(natural_picture[component]) - np.array(
                decoded_pictures[0][component]
            )
            mean_square_error = np.mean(error * error)
            psnr = 20 * (np.log(max_f / np.sqrt(mean_square_error)) / np.log(10))

            # NB: This PSNR would be a fairly low bar for VC-2 in typical
            # applications.  However, for extremely small images (such as the
            # picture used in this example) lower PSNRs are likely. Typical
            # errors should result in PSNRs well below this, however.
            assert psnr > 35.0

    def test_default_pic_num(self, codec_features, natural_picture):
        natural_picture = natural_picture.copy()

        natural_picture["pic_num"] = 123
        data_unit = make_picture_parse_data_unit(codec_features, natural_picture)
        assert data_unit["picture_parse"]["picture_header"]["picture_number"] == 123

        del natural_picture["pic_num"]
        data_unit = make_picture_parse_data_unit(codec_features, natural_picture)
        assert "picture_number" not in data_unit["picture_parse"]["picture_header"]

    def test_lossless_with_picture_bytes_set(self, codec_features, natural_picture):
        codec_features["lossless"] = True
        codec_features["picture_bytes"] = 100
        with pytest.raises(PictureBytesSpecifiedForLosslessModeError):
            make_picture_parse_data_unit(codec_features, natural_picture)

    @pytest.mark.parametrize(
        "profile,exc",
        [
            (Profiles.low_delay, InsufficientLDPictureBytesError),
            (Profiles.high_quality, InsufficientHQPictureBytesError),
        ],
    )
    def test_insufficient_picture_bytes(
        self, codec_features, natural_picture, profile, exc
    ):
        codec_features["profile"] = profile
        codec_features["picture_bytes"] = 1
        with pytest.raises(exc):
            make_picture_parse_data_unit(codec_features, natural_picture)

    @pytest.mark.parametrize(
        "wavelet_index,dwt_depth_ho",
        [(WaveletFilters.haar_no_shift, 0), (WaveletFilters.le_gall_5_3, 1)],
    )
    def test_asymmetric_version_2(
        self, codec_features, natural_picture, wavelet_index, dwt_depth_ho,
    ):
        codec_features["major_version"] = 2
        codec_features["wavelet_index"] = wavelet_index
        codec_features["dwt_depth_ho"] = dwt_depth_ho
        with pytest.raises(AsymmetricTransformPreVersion3Error):
            make_picture_parse_data_unit(codec_features, natural_picture)

    def test_lossless_low_delay(self, codec_features, natural_picture):
        codec_features["profile"] = Profiles.low_delay
        codec_features["lossless"] = True
        codec_features["picture_bytes"] = None
        with pytest.raises(LosslessUnsupportedByLowDelayError):
            make_picture_parse_data_unit(codec_features, natural_picture)

    @pytest.mark.parametrize("profile", Profiles)
    def test_minimum_qindex(self, codec_features, natural_picture, profile):
        codec_features["profile"] = profile

        # Chose a compression ratio so low that (almost) no quantization would be
        # used ordinarily (here 1:1)
        codec_features["lossless"] = False
        codec_features["picture_bytes"] = (
            codec_features["video_parameters"]["frame_width"]
            * codec_features["video_parameters"]["frame_height"]
            * 2
        )

        minimum_qindex = 20

        # Check all quantization indices are above the threshold
        picture_parse = make_picture_parse_data_unit(
            codec_features, natural_picture, minimum_qindex,
        )["picture_parse"]
        transform_data = picture_parse["wavelet_transform"]["transform_data"]

        if profile == Profiles.high_quality:
            slices = transform_data["hq_slices"]
        elif profile == Profiles.low_delay:
            slices = transform_data["ld_slices"]

        assert all(slice["qindex"] == minimum_qindex for slice in slices)


class TestMakeFragmentParseDataUnits(object):
    # NB: Since the fragment generation process is based on the picture
    # generation process, all we're interested in here is that we get identical
    # pictures out of the decoder to non-fragment based encodings.

    @pytest.fixture
    def codec_features(self):
        # NB: By default this produces uneaven slice sizes
        return CodecFeatures(
            name="basic",
            level=Levels.unconstrained,
            profile=Profiles.high_quality,
            major_version=3,
            minor_version=0,
            # picture_coding_mode: set by ``natural_picture`` fixture
            # video_parameters: set by ``natural_picture`` fixture
            wavelet_index=WaveletFilters.le_gall_5_3,
            wavelet_index_ho=WaveletFilters.le_gall_5_3,
            dwt_depth=2,
            dwt_depth_ho=0,
            slices_x=5,
            slices_y=7,
            fragment_slice_count=3,
            lossless=False,
            picture_bytes=2000,
            quantization_matrix=None,
        )

    @pytest.fixture
    def natural_picture(self, codec_features, lovell):
        # A small section cropped out of a real picture
        picture, video_parameters, picture_coding_mode = lovell
        codec_features["video_parameters"] = video_parameters
        codec_features["picture_coding_mode"] = picture_coding_mode
        return picture

    @pytest.mark.parametrize(
        "fragment_slice_count",
        [
            # Notable case: one slice per fragment
            1,
            # Typical case 1: Several slices per fragment, several fragments per
            # picture. All fragments have the same number of slices.
            5,
            # Typical case 2: Final fragment will have fewer fragments than the rest.
            6,
            # 'Weird' case: Whole picture in one fragment (+ a header fragment)
            999999,
        ],
    )
    def test_fragment_slice_count(
        self, codec_features, natural_picture, fragment_slice_count
    ):
        # Generate a fragment based encoding
        codec_features["fragment_slice_count"] = fragment_slice_count
        fragment_data_units = make_fragment_parse_data_units(
            codec_features, natural_picture
        )
        decoded_pictures = serialize_and_decode(
            Sequence(
                data_units=(
                    [make_sequence_header_data_unit(codec_features)]
                    + fragment_data_units
                    + [
                        DataUnit(
                            parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)
                        )
                    ]
                )
            )
        )

        # Check that the expected number of fragments were created
        num_slices = codec_features["slices_x"] * codec_features["slices_y"]
        expected_fragments = (
            # Header fragment
            1
            +
            # Picture slice fragments
            ((num_slices + fragment_slice_count - 1) // fragment_slice_count)
        )
        assert expected_fragments == len(fragment_data_units)

        # Also generate a non-fragment based version as a model answer and
        # check that the picture is identical
        codec_features["fragment_slice_count"] = 0
        expected_decoded_pictures = serialize_and_decode(
            Sequence(
                data_units=[
                    make_sequence_header_data_unit(codec_features),
                    make_picture_parse_data_unit(codec_features, natural_picture),
                    DataUnit(
                        parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)
                    ),
                ]
            )
        )
        assert decoded_pictures == expected_decoded_pictures

    @pytest.mark.parametrize("profile", Profiles)
    def test_both_profiles(self, codec_features, natural_picture, profile):
        codec_features["profile"] = profile

        # Generate a fragment based encoding
        decoded_pictures = serialize_and_decode(
            Sequence(
                data_units=(
                    [make_sequence_header_data_unit(codec_features)]
                    + make_fragment_parse_data_units(codec_features, natural_picture)
                    + [
                        DataUnit(
                            parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)
                        )
                    ]
                )
            )
        )

        # Also generate a non-fragment based version as a model answer and
        # check that the picture is identical
        codec_features["fragment_slice_count"] = 0
        expected_decoded_pictures = serialize_and_decode(
            Sequence(
                data_units=[
                    make_sequence_header_data_unit(codec_features),
                    make_picture_parse_data_unit(codec_features, natural_picture),
                    DataUnit(
                        parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)
                    ),
                ]
            )
        )
        assert decoded_pictures == expected_decoded_pictures

    def test_default_pic_num(self, codec_features, natural_picture):
        natural_picture = natural_picture.copy()

        natural_picture["pic_num"] = 123
        data_units = make_fragment_parse_data_units(codec_features, natural_picture)
        for data_unit in data_units:
            assert (
                data_unit["fragment_parse"]["fragment_header"]["picture_number"] == 123
            )

        del natural_picture["pic_num"]
        data_units = make_fragment_parse_data_units(codec_features, natural_picture)
        for data_unit in data_units:
            assert (
                "picture_number" not in data_unit["fragment_parse"]["fragment_header"]
            )

    def test_minimum_qindex(self, codec_features, natural_picture):
        # Chose a data rate high enough that very little quantisation would
        # ordinarily be used (here 1:1)
        codec_features["picture_bytes"] = (
            codec_features["video_parameters"]["frame_width"]
            * codec_features["video_parameters"]["frame_height"]
            * 2
        )

        minimum_qindex = 20

        # Generate a fragment based encoding
        fragment_data_units = make_fragment_parse_data_units(
            codec_features, natural_picture, minimum_qindex,
        )

        # Check all quantization indices are above the threshold
        for fragment_data_unit in fragment_data_units[1:]:
            fragment_data = fragment_data_unit["fragment_parse"]["fragment_data"]
            slices = fragment_data["hq_slices"]

            assert all(slice["qindex"] == minimum_qindex for slice in slices)


@pytest.mark.parametrize(
    "fragment_slice_count,exp_data_units", [(0, 1), (9999, 2), (9999, 2)]
)
def test_make_picture_data_units(fragment_slice_count, exp_data_units, lovell):
    picture, video_parameters, picture_coding_mode = lovell
    codec_features = CodecFeatures(
        name="basic",
        level=Levels.unconstrained,
        profile=Profiles.high_quality,
        major_version=3,
        minor_version=0,
        picture_coding_mode=picture_coding_mode,
        video_parameters=video_parameters,
        wavelet_index=WaveletFilters.le_gall_5_3,
        wavelet_index_ho=WaveletFilters.le_gall_5_3,
        dwt_depth=2,
        dwt_depth_ho=0,
        slices_x=5,
        slices_y=7,
        fragment_slice_count=fragment_slice_count,
        lossless=False,
        # A data rate high enough that very little quantisation would
        # ordinarily be used (here 1:1)
        picture_bytes=(
            video_parameters["frame_width"] * video_parameters["frame_height"] * 2
        ),
        quantization_matrix=None,
    )

    minimum_qindex = 20

    data_units = make_picture_data_units(codec_features, picture, minimum_qindex,)

    assert len(data_units) == exp_data_units
