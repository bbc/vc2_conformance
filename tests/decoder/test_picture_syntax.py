import pytest

from decoder_test_utils import serialise_to_bytes, bytes_to_state

from vc2_conformance._constraint_table import ValueSet

from vc2_conformance.state import State

from vc2_conformance import bitstream
from vc2_conformance import decoder

import vc2_data_tables as tables


def test_picture_header_picture_numbering_sanity_check():
    # Only a sanity check as assert_picture_number_incremented_as_expected
    # (which performs these checks) is tested fully elsewhere
    ph1 = serialise_to_bytes(bitstream.PictureHeader(picture_number=1000))
    ph2 = serialise_to_bytes(bitstream.PictureHeader(picture_number=1001))
    ph3 = serialise_to_bytes(bitstream.PictureHeader(picture_number=1003))
    
    state = bytes_to_state(ph1 + ph2 + ph3)
    state["_picture_coding_mode"] = tables.PictureCodingModes.pictures_are_frames
    state["_num_pictures_in_sequence"] = 0
    
    decoder.picture_header(state)
    decoder.picture_header(state)
    with pytest.raises(decoder.NonConsecutivePictureNumbers) as exc_info:
        decoder.picture_header(state)
    assert exc_info.value.last_picture_number_offset == (len(ph1) + len(ph2), 7)
    assert exc_info.value.picture_number_offset == (len(ph1) + len(ph2) + len(ph3), 7)
    assert exc_info.value.last_picture_number == 1001
    assert exc_info.value.picture_number == 1003


minimal_transform_parameters_state = {
    "major_version": 3,
    "parse_code": tables.ParseCodes.high_quality_picture,
    "luma_width": 1920,
    "luma_height": 1080,
    "color_diff_width": 960,
    "color_diff_height": 540,
}

def test_transform_parameters_wavelet_index_must_be_valid():
    state = minimal_transform_parameters_state.copy()
    state.update(bytes_to_state(serialise_to_bytes(
        bitstream.TransformParameters(
            wavelet_index=tables.WaveletFilters.haar_no_shift,
        ),
        state,
    )))
    decoder.transform_parameters(state)
    
    state = minimal_transform_parameters_state.copy()
    state.update(bytes_to_state(serialise_to_bytes(
        bitstream.TransformParameters(
            wavelet_index=9999,
        ),
        state,
    )))
    with pytest.raises(decoder.BadWaveletIndex) as exc_info:
        decoder.transform_parameters(state)
    assert exc_info.value.wavelet_index == 9999


def test_extended_transform_parameters_wavelet_index_ho_must_be_valid():
    state = bytes_to_state(serialise_to_bytes(
        bitstream.ExtendedTransformParameters(
            asym_transform_index_flag=True,
            wavelet_index_ho=tables.WaveletFilters.haar_no_shift,
        ),
    ))
    decoder.extended_transform_parameters(state)
    
    state = bytes_to_state(serialise_to_bytes(
        bitstream.ExtendedTransformParameters(
            asym_transform_index_flag=True,
            wavelet_index_ho=9999,
        ),
    ))
    with pytest.raises(decoder.BadHOWaveletIndex) as exc_info:
        decoder.extended_transform_parameters(state)
    assert exc_info.value.wavelet_index_ho == 9999


minimal_slice_parameters_state = {
    "major_version": 3,
    "parse_code": tables.ParseCodes.high_quality_picture,
    "luma_width": 1920,
    "luma_height": 1080,
    "color_diff_width": 960,
    "color_diff_height": 540,
    "dwt_depth": 0,
    "dwt_depth_ho": 0,
}

class TestSliceParameters(object):
    
    @pytest.mark.parametrize("slices_x,slices_y,exp_fail", [
        (1, 1, False),
        (0, 1, True),
        (1, 0, True),
        (0, 0, True),
    ])
    def test_number_of_slices_must_be_nonzero(self, slices_x, slices_y, exp_fail):
        state = minimal_slice_parameters_state.copy()
        state.update(bytes_to_state(serialise_to_bytes(
            bitstream.SliceParameters(
                slices_x=slices_x,
                slices_y=slices_y,
            ),
            state,
        )))
        if exp_fail:
            with pytest.raises(decoder.ZeroSlicesInCodedPicture) as exc_info:
                decoder.slice_parameters(state)
            assert exc_info.value.slices_x == slices_x
            assert exc_info.value.slices_y == slices_y
        else:
            decoder.slice_parameters(state)
    
    def test_zero_slice_bytes_denominator(self):
        state = minimal_slice_parameters_state.copy()
        state["parse_code"] = tables.ParseCodes.low_delay_picture
        state.update(bytes_to_state(serialise_to_bytes(
            bitstream.SliceParameters(
                slice_bytes_numerator=1,
                slice_bytes_denominator=0,
            ),
            state,
        )))
        with pytest.raises(decoder.SliceBytesHasZeroDenominator) as exc_info:
            decoder.slice_parameters(state)
        assert exc_info.value.slice_bytes_numerator == 1
    
    @pytest.mark.parametrize("numer,denom,exp_fail", [
        (1, 1, False),
        (9, 9, False),
        (10, 9, False),
        (0, 1, True),
        (0, 9, True),
        (8, 9, True),
    ])
    def test_slice_bytes_less_than_one(self, numer, denom, exp_fail):
        state = minimal_slice_parameters_state.copy()
        state["parse_code"] = tables.ParseCodes.low_delay_picture
        state.update(bytes_to_state(serialise_to_bytes(
            bitstream.SliceParameters(
                slice_bytes_numerator=numer,
                slice_bytes_denominator=denom,
            ),
            state,
        )))
        if exp_fail:
            with pytest.raises(decoder.SliceBytesIsLessThanOne) as exc_info:
                decoder.slice_parameters(state)
            assert exc_info.value.slice_bytes_numerator == numer
            assert exc_info.value.slice_bytes_denominator == denom
        else:
            decoder.slice_parameters(state)
    
    def test_zero_slice_size_scaler(self):
        state = minimal_slice_parameters_state.copy()
        state.update(bytes_to_state(serialise_to_bytes(
            bitstream.SliceParameters(
                slice_prefix_bytes=0,
                slice_size_scaler=0,
            ),
            state,
        )))
        with pytest.raises(decoder.SliceSizeScalerIsZero) as exc_info:
            decoder.slice_parameters(state)

    @pytest.mark.parametrize("slices_x,slices_y,state_override,exp_same_dimensions", [
        (1, 1, {}, True),
        (192, 108, {}, True),
        # Up to limit
        (960, 540, {}, True),
        # Too small for colour diff
        (1920, 1, {}, False),
        (1, 1080, {}, False),
        # Not a multiple of either
        (111, 1, {}, False),
        (1, 111, {}, False),
        # Too small for either
        (3840, 1, {}, False),
        (1, 2160, {}, False),
        # With increased transform depths
        (1, 1, {"dwt_depth":1, "dwt_depth_ho": 1}, True),
        # Up to limit
        (240, 270, {"dwt_depth":1, "dwt_depth_ho": 1}, True),
        # Past new limit should fail
        (192, 1, {"dwt_depth":1, "dwt_depth_ho": 1}, False),
        (1, 108, {"dwt_depth":1, "dwt_depth_ho": 1}, False),
    ])
    def test_slices_have_same_dimensions(self, slices_x, slices_y, state_override, exp_same_dimensions):
        state = minimal_slice_parameters_state.copy()
        state.update(state_override)
        state.update(bytes_to_state(serialise_to_bytes(
            bitstream.SliceParameters(
                slices_x=slices_x,
                slices_y=slices_y,
            ),
            state,
        )))
        decoder.slice_parameters(state)
        assert state["_level_constrained_values"]["slices_have_same_dimensions"] is exp_same_dimensions

class TestQuantisationMatrix(object):

    def test_disallows_unsupported_combinations(self):
        state = {
            "wavelet_index": tables.WaveletFilters.haar_no_shift,
            "wavelet_index_ho": tables.WaveletFilters.haar_no_shift,
            "dwt_depth": 1,
            "dwt_depth_ho": 1,
        }
        state.update(bytes_to_state(serialise_to_bytes(
            bitstream.QuantMatrix(
                custom_quant_matrix=False,
            ),
            state.copy(),
        )))
        decoder.quant_matrix(state)
        
        state = {
            "wavelet_index": tables.WaveletFilters.haar_no_shift,
            "wavelet_index_ho": tables.WaveletFilters.haar_with_shift,
            "dwt_depth": 999,
            "dwt_depth_ho": 9999,
        }
        state.update(bytes_to_state(serialise_to_bytes(
            bitstream.QuantMatrix(
                custom_quant_matrix=False,
            ),
            state.copy(),
        )))
        with pytest.raises(decoder.NoQuantisationMatrixAvailable) as exc_info:
            decoder.quant_matrix(state)
        assert exc_info.value.wavelet_index == tables.WaveletFilters.haar_no_shift
        assert exc_info.value.wavelet_index_ho == tables.WaveletFilters.haar_with_shift
        assert exc_info.value.dwt_depth == 999
        assert exc_info.value.dwt_depth_ho == 9999
    
    @pytest.mark.parametrize("dwt_depth,dwt_depth_ho,matrix,exp_fail_value", [
        # No transform
        (0, 0, [0], None),
        (0, 0, [127], None),
        (0, 0, [128], 128),
        # Horizontal only Transform
        (0, 1, [0, 0], None),
        (0, 1, [127, 127], None),
        (0, 1, [128, 0], 128),
        (0, 1, [0, 128], 128),
        # 2D transform
        (1, 0, [0, 0, 0, 0], None),
        (1, 0, [127, 127, 127, 127], None),
        (1, 0, [128, 0, 0, 0], 128),
        (1, 0, [0, 128, 0, 0], 128),
        (1, 0, [0, 0, 128, 0], 128),
        (1, 0, [0, 0, 0, 128], 128),
    ])
    def test_value_ranges_restricted(self, dwt_depth, dwt_depth_ho, matrix, exp_fail_value):
        state = {
            "wavelet_index": tables.WaveletFilters.haar_no_shift,
            "wavelet_index_ho": tables.WaveletFilters.haar_no_shift,
            "dwt_depth": dwt_depth,
            "dwt_depth_ho": dwt_depth_ho,
            "_level_constrained_values": {
                "level": tables.Levels.sub_sd,
            },
        }
        state.update(bytes_to_state(serialise_to_bytes(
            bitstream.QuantMatrix(
                custom_quant_matrix=True,
                quant_matrix=matrix,
            ),
            state.copy(),
        )))
        if exp_fail_value is not None:
            with pytest.raises(decoder.QuantisationMatrixValueNotAllowedInLevel) as exc_info:
                decoder.quant_matrix(state)
            assert exc_info.value.value == exp_fail_value
            assert exc_info.value.allowed_values == ValueSet((0, 127))
            assert exc_info.value.level_constrained_values == {
                "level": tables.Levels.sub_sd,
                "custom_quant_matrix": True,
            }
        else:
            decoder.quant_matrix(state)


@pytest.mark.parametrize("parse_code,extra_slice_parameters,extra_constrained_values", [
    (
        tables.ParseCodes.high_quality_picture,
        {
            "slice_prefix_bytes": 10,
            "slice_size_scaler": 20,
        },
        {
            "slice_prefix_bytes": 10,
            "slice_size_scaler": 20,
        },
    ),
    (
        tables.ParseCodes.low_delay_picture,
        {
            "slice_bytes_numerator": 2,
            "slice_bytes_denominator": 1,
        },
        {
            "slice_bytes_numerator": 2,
            "slice_bytes_denominator": 1,
        },
    ),
])
def test_transform_parameters_et_al_level_constraints(parse_code, extra_slice_parameters, extra_constrained_values):
    # Checks level constraints for:
    #
    # * transform_parameters
    #   * extended_transform_parameters
    #   * slice_parameters
    #   * quant_matrix
    #
    # Simply check that all constrainted level values get asserted. We check
    # this by making sure assert_level_constraint has added the relevant values
    # to # state["_level_constrained_values"].
    state = minimal_transform_parameters_state.copy()
    state["parse_code"] = parse_code
    state.update(bytes_to_state(serialise_to_bytes(
        bitstream.TransformParameters(
            wavelet_index=tables.WaveletFilters.haar_no_shift,
            dwt_depth=1,
            extended_transform_parameters=bitstream.ExtendedTransformParameters(
                asym_transform_index_flag=True,
                wavelet_index_ho=tables.WaveletFilters.le_gall_5_3,
                asym_transform_flag=True,
                dwt_depth_ho=2,
            ),
            slice_parameters=bitstream.SliceParameters(
                slices_x=1,
                slices_y=2,
                **extra_slice_parameters
            ),
            quant_matrix=bitstream.QuantMatrix(
                custom_quant_matrix=False,
            ),
        ),
        state,
    )))
    decoder.transform_parameters(state)
    expected_constrained_values = {
        "wavelet_index": tables.WaveletFilters.haar_no_shift,
        "dwt_depth": 1,
        "asym_transform_index_flag": True,
        "wavelet_index_ho": tables.WaveletFilters.le_gall_5_3,
        "asym_transform_flag": True,
        "dwt_depth_ho": 2,
        "slices_x": 1,
        "slices_y": 2,
        "slices_have_same_dimensions": True,
        "custom_quant_matrix": False,
    }
    expected_constrained_values.update(extra_constrained_values)
    assert state["_level_constrained_values"] == expected_constrained_values


@pytest.mark.parametrize("parse_code", [
    tables.ParseCodes.low_delay_picture,
    tables.ParseCodes.high_quality_picture,
])
def test_whole_picture(parse_code):
    # A sanity check which runs picture decoding for whole pictures and makes
    # sure nothing crashes
    
    # Serialise a sample stream
    sh = bitstream.SequenceHeader(
        video_parameters=bitstream.SourceParameters(
            frame_size=bitstream.FrameSize(
                # Don't waste time on full-sized frames
                custom_dimensions_flag=True,
                frame_width=4,
                frame_height=4,
            ),
            clean_area=bitstream.CleanArea(
                custom_clean_area_flag=True,
                clean_width=4,
                clean_height=4,
            ),
        ),
    )
    serialisation_state = State()
    sh_bytes = serialise_to_bytes(sh, serialisation_state)
    serialisation_state["parse_code"] = parse_code
    pic_bytes = serialise_to_bytes(bitstream.PictureParse(), serialisation_state)
    
    # Check it is parsed without failiures
    state = bytes_to_state(sh_bytes + pic_bytes)
    state["_num_pictures_in_sequence"] = 0
    decoder.sequence_header(state)
    state["parse_code"] = parse_code
    decoder.picture_parse(state)
