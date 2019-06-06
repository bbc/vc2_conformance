import pytest

from decoder_test_utils import seriallise_to_bytes, bytes_to_state

from vc2_conformance._constraint_table import ValueSet

from vc2_conformance import bitstream
from vc2_conformance import tables
from vc2_conformance import decoder


def picture_header_to_bytes(**kwargs):
    """
    Seriallise a PictureHeader block, returning a bytes object.
    """
    return seriallise_to_bytes(
        bitstream.PictureHeader(**kwargs),
        bitstream.picture_header,
    )

class TestPictureHeader(object):

    def test_picture_numbers_must_be_consecutive(self):
        ph1 = picture_header_to_bytes(picture_number=1000)
        ph2 = picture_header_to_bytes(picture_number=1001)
        ph3 = picture_header_to_bytes(picture_number=1003)
        
        state = bytes_to_state(ph1 + ph2 + ph3)
        state["_picture_coding_mode"] = tables.PictureCodingModes.pictures_are_frames
        state["_num_pictures_in_sequence"] = 0
        
        decoder.picture_header(state)
        decoder.picture_header(state)
        with pytest.raises(decoder.NonConsecutivePictureNumbers) as exc_info:
            decoder.picture_header(state)
        assert exc_info.value.last_picture_header_offset == (len(ph1), 7)
        assert exc_info.value.picture_header_offset == (len(ph1) + len(ph2), 7)
        assert exc_info.value.last_picture_number == 1001
        assert exc_info.value.picture_number == 1003
    
    def test_picture_numbers_wrap_around_correctly(self):
        ph1 = picture_header_to_bytes(picture_number=(2**32)-1)
        ph2 = picture_header_to_bytes(picture_number=0)
        state = bytes_to_state(ph1 + ph2)
        state["_picture_coding_mode"] = tables.PictureCodingModes.pictures_are_frames
        state["_num_pictures_in_sequence"] = 0
        
        decoder.picture_header(state)
        decoder.picture_header(state)

    def test_picture_numbers_dont_wrap_around_correctly(self):
        ph1 = picture_header_to_bytes(picture_number=(2**32)-1)
        ph2 = picture_header_to_bytes(picture_number=1)
        state = bytes_to_state(ph1 + ph2)
        state["_picture_coding_mode"] = tables.PictureCodingModes.pictures_are_frames
        state["_num_pictures_in_sequence"] = 0
        
        decoder.picture_header(state)
        with pytest.raises(decoder.NonConsecutivePictureNumbers) as exc_info:
            decoder.picture_header(state)
        assert exc_info.value.last_picture_header_offset == (0, 7)
        assert exc_info.value.picture_header_offset == (len(ph1), 7)
        assert exc_info.value.last_picture_number == (2**32)-1
        assert exc_info.value.picture_number == 1
    
    @pytest.mark.parametrize("picture_coding_mode,picture_number,exp_fail", [
        (tables.PictureCodingModes.pictures_are_frames, 0, False),
        (tables.PictureCodingModes.pictures_are_frames, 1, False),
        (tables.PictureCodingModes.pictures_are_frames, 2, False),
        (tables.PictureCodingModes.pictures_are_frames, 3, False),
        (tables.PictureCodingModes.pictures_are_frames, 4, False),
        (tables.PictureCodingModes.pictures_are_fields, 0, False),
        (tables.PictureCodingModes.pictures_are_fields, 1, True),
        (tables.PictureCodingModes.pictures_are_fields, 2, False),
        (tables.PictureCodingModes.pictures_are_fields, 3, True),
        (tables.PictureCodingModes.pictures_are_fields, 4, False),
    ])
    def test_early_fields_must_have_even_numbers(self, picture_coding_mode, picture_number, exp_fail):
        ph = picture_header_to_bytes(picture_number=picture_number)
        state = bytes_to_state(ph)
        state["_picture_coding_mode"] = picture_coding_mode
        state["_num_pictures_in_sequence"] = 100
        
        if exp_fail:
            with pytest.raises(decoder.EarliestFieldHasOddPictureNumber) as exc_info:
                decoder.picture_header(state)
            assert exc_info.value.picture_number == picture_number
        else:
            decoder.picture_header(state)
            
            # Also check that the pictures in sequence count is incremented
            assert state["_num_pictures_in_sequence"] == 101


def transform_parameters_to_bytes(state, **kwargs):
    """
    Seriallise a transform_parameters block, returning a bytes object.
    """
    return seriallise_to_bytes(
        bitstream.TransformParameters(
            **kwargs
        ),
        lambda serdes, _: bitstream.transform_parameters(serdes, state),
    )

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
    state.update(bytes_to_state(transform_parameters_to_bytes(
        state,
        wavelet_index=tables.WaveletFilters.haar_no_shift,
        slice_parameters=bitstream.SliceParameters(
            slices_x=1,
            slices_y=1,
            slice_prefix_bytes=0,
            slice_size_scaler=1,
        ),
    )))
    decoder.transform_parameters(state)
    
    state = minimal_transform_parameters_state.copy()
    state.update(bytes_to_state(transform_parameters_to_bytes(
        state,
        wavelet_index=9999,
        slice_parameters=bitstream.SliceParameters(
            slices_x=1,
            slices_y=1,
            slice_prefix_bytes=0,
            slice_size_scaler=1,
        ),
    )))
    with pytest.raises(decoder.BadWaveletIndex) as exc_info:
        decoder.transform_parameters(state)
    assert exc_info.value.wavelet_index == 9999


def test_extended_transform_parameters_wavelet_index_ho_must_be_valid():
    state = bytes_to_state(seriallise_to_bytes(
        bitstream.ExtendedTransformParameters(
            asym_transform_index_flag=True,
            wavelet_index_ho=tables.WaveletFilters.haar_no_shift,
        ),
        bitstream.extended_transform_parameters,
    ))
    decoder.extended_transform_parameters(state)
    
    state = bytes_to_state(seriallise_to_bytes(
        bitstream.ExtendedTransformParameters(
            asym_transform_index_flag=True,
            wavelet_index_ho=9999,
        ),
        bitstream.extended_transform_parameters,
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
        state.update(bytes_to_state(seriallise_to_bytes(
            bitstream.SliceParameters(
                slices_x=slices_x,
                slices_y=slices_y,
                slice_prefix_bytes=0,
                slice_size_scaler=1,
            ),
            lambda serdes, _: bitstream.slice_parameters(serdes, state),
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
        state.update(bytes_to_state(seriallise_to_bytes(
            bitstream.SliceParameters(
                slices_x=1,
                slices_y=1,
                slice_bytes_numerator=1,
                slice_bytes_denominator=0,
            ),
            lambda serdes, _: bitstream.slice_parameters(serdes, state),
        )))
        with pytest.raises(decoder.SliceBytesHasZeroDenominator) as exc_info:
            decoder.slice_parameters(state)
        assert exc_info.value.slice_bytes_numerator == 1
    
    def test_zero_slice_size_scaler(self):
        state = minimal_slice_parameters_state.copy()
        state.update(bytes_to_state(seriallise_to_bytes(
            bitstream.SliceParameters(
                slices_x=1,
                slices_y=1,
                slice_prefix_bytes=0,
                slice_size_scaler=0,
            ),
            lambda serdes, _: bitstream.slice_parameters(serdes, state),
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
        state.update(bytes_to_state(seriallise_to_bytes(
            bitstream.SliceParameters(
                slices_x=slices_x,
                slices_y=slices_y,
                slice_prefix_bytes=0,
                slice_size_scaler=1,
            ),
            lambda serdes, _: bitstream.slice_parameters(serdes, state),
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
        state.update(bytes_to_state(seriallise_to_bytes(
            bitstream.QuantMatrix(
                custom_quant_matrix=False,
            ),
            lambda serdes, _: bitstream.quant_matrix(serdes, state),
        )))
        decoder.quant_matrix(state)
        
        state = {
            "wavelet_index": tables.WaveletFilters.haar_no_shift,
            "wavelet_index_ho": tables.WaveletFilters.haar_with_shift,
            "dwt_depth": 999,
            "dwt_depth_ho": 9999,
        }
        state.update(bytes_to_state(seriallise_to_bytes(
            bitstream.QuantMatrix(
                custom_quant_matrix=False,
            ),
            lambda serdes, _: bitstream.quant_matrix(serdes, state),
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
                "level": tables.Levels.sub_hd,
            },
        }
        state.update(bytes_to_state(seriallise_to_bytes(
            bitstream.QuantMatrix(
                custom_quant_matrix=True,
                quant_matrix=matrix,
            ),
            lambda serdes, _: bitstream.quant_matrix(serdes, state),
        )))
        if exp_fail_value is not None:
            with pytest.raises(decoder.QuantisationMatrixValueNotAllowedInLevel) as exc_info:
                decoder.quant_matrix(state)
            assert exc_info.value.value == exp_fail_value
            assert exc_info.value.allowed_values == ValueSet((0, 127))
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
            "slice_bytes_numerator": 1,
            "slice_bytes_denominator": 2,
        },
        {
            "slice_bytes_numerator": 1,
            "slice_bytes_denominator": 2,
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
    state.update(bytes_to_state(transform_parameters_to_bytes(
        state,
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
