import pytest
from mock import Mock

from io import BytesIO
from enum import Enum

from functools import partial

from mock_notification_target import MockNotificationTarget

from vc2_conformance import bitstream
from vc2_conformance import tables

from vc2_conformance.bitstream._integer_io import (
    write_bits,
    write_signed_exp_golomb,
    signed_exp_golomb_length,
)

from vc2_conformance.bitstream.vc2_slices import (
    resize_list,
    subband_dimensions,
    slice_subband_bounds,
    to_coeff_index,
    BaseSliceArray,
    ComponentSubbandView,
    ComponentView,
    component_views_str,
)


def test_resize_list():
    l = [1, 2, 3]
    
    # No change
    resize_list(l, 3)
    assert l == [1, 2, 3]
    
    # Make larger
    resize_list(l, 5)
    assert l == [1, 2, 3, 0, 0]
    
    # Custom constructor
    resize_list(l, 7, lambda: "foo")
    assert l == [1, 2, 3, 0, 0, "foo", "foo"]
    
    # Make smaller
    resize_list(l, 2)
    assert l == [1, 2]


class TestSubbandDimensions(object):

    def test_dc(self):
        assert subband_dimensions(11, 5, dwt_depth=0, dwt_depth_ho=0, level=0) == (11, 5)
    
    def test_ho(self):
        # Horizontal only
        assert subband_dimensions(11, 5, dwt_depth=0, dwt_depth_ho=1, level=1) == (
            12//2,  # Changed to become divisible by two
            5,
        )
        
        assert subband_dimensions(11, 5, dwt_depth=0, dwt_depth_ho=2, level=2) == (
            12//2,  # Changed to become divisible by four
            5,
        )
        
        assert subband_dimensions(11, 5, dwt_depth=0, dwt_depth_ho=3, level=3) == (
            16//2,  # Changed to become divisible by eight
            5,
        )
        
        # Working down the horizontal-only levels
        assert subband_dimensions(11, 5, dwt_depth=0, dwt_depth_ho=3, level=2) == (
            16//4,
            5,
        )
        assert subband_dimensions(11, 5, dwt_depth=0, dwt_depth_ho=3, level=1) == (
            16//8,
            5,
        )
        # DC Again
        assert subband_dimensions(11, 5, dwt_depth=0, dwt_depth_ho=3, level=0) == (
            16//8,
            5,
        )
    
    def test_2d_and_ho(self):
        # Starting from the HO level from above
        assert subband_dimensions(11, 5, dwt_depth=1, dwt_depth_ho=3, level=4) == (
            16//2,  # Changed to become divisible by sixteen
            6//2, # Changed to become divisible by two
        )
        
        assert subband_dimensions(11, 5, dwt_depth=2, dwt_depth_ho=3, level=5) == (
            32//2,  # Changed to become divisible by thirty-two
            8//2, # Changed to become divisible by four
        )
        
        assert subband_dimensions(11, 5, dwt_depth=3, dwt_depth_ho=3, level=6) == (
            64//2,  # Changed to become divisible by sixty-four
            8//2, # Changed to become divisible by eight
        )
        
        # Working down the levels
        assert subband_dimensions(11, 5, dwt_depth=3, dwt_depth_ho=3, level=5) == (
            64//4,
            8//4,
        )
        assert subband_dimensions(11, 5, dwt_depth=3, dwt_depth_ho=3, level=4) == (
            64//8,
            8//8,
        )
        
        # Hit horizontal only
        assert subband_dimensions(11, 5, dwt_depth=3, dwt_depth_ho=3, level=3) == (
            64//16,
            8//8,
        )
        assert subband_dimensions(11, 5, dwt_depth=3, dwt_depth_ho=3, level=2) == (
            64//32,
            8//8,
        )
        assert subband_dimensions(11, 5, dwt_depth=3, dwt_depth_ho=3, level=1) == (
            64//64,
            8//8,
        )
        
        # Hit DC
        assert subband_dimensions(11, 5, dwt_depth=3, dwt_depth_ho=3, level=0) == (
            64//64,
            8//8,
        )


@pytest.mark.parametrize("sx,sy,x1,y1,x2,y2", [
    # Check consecutive and complete in X-axis
    (0, 0,  0, 0,  3, 2),
    (1, 0,  3, 0,  7, 2),
    (2, 0,  7, 0,  11, 2),
    # And then again on the Y-axis
    (0, 1,  0, 2,  3, 5),
    (1, 1,  3, 2,  7, 5),
    (2, 1,  7, 2,  11, 5),
])
def test_slice_subband_bounds(sx, sy, x1, y1, x2, y2):
    assert slice_subband_bounds(
        sx, sy,
        subband_width=11, subband_height=5,
        slices_x=3, slices_y=2,
    ) == (x1, y1, x2, y2)


class TestToCoeffIndex(object):
    
    def test_index_order(self):
        slices_x = 3
        slices_y = 2
        
        # Widths and heights were chosen arbitrarily to achieve
        # * subband_index=0 has subband slices with no entries
        # * subband_index=1 has subband slices with different sizes
        # * subband_index=2 has subband slices with equal sizes (10x10)
        subband_widths = [2, 11, 30]
        subband_heights = [1, 5, 20]
        
        # Iterate over the subband samples in what should be index order
        indices = []
        for sy in range(slices_y + 1):  # NB: Also test we can go beyond slices_y
            for sx in range(slices_x):
                for subband_index, (subband_width, subband_height) in enumerate(
                        zip(subband_widths, subband_heights)):
                    x1, y1, x2, y2 = slice_subband_bounds(
                        sx, sy,
                        subband_width, subband_height,
                        slices_x, slices_y,
                    )
                    subband_slice_width = x2 - x1
                    subband_slice_height = y2 - y1
                    for y in range(subband_slice_height):
                        for x in range(subband_slice_width):
                            indices.append(to_coeff_index(
                                subband_widths,
                                subband_heights,
                                slices_x,
                                slices_y,
                                sx, sy,
                                subband_index,
                                x, y,
                            ))
        
        assert indices == list(range(len(indices)))
    
    @pytest.mark.parametrize("sx,sy,subband_index,x,y", [
        # sx is out of range
        (-2, 0, 0, 0, 0),
        (-1, 0, 0, 0, 0),
        (3, 0, 0, 0, 0),
        (4, 0, 0, 0, 0),
        # subband_index is out of range
        (0, 0, -2, 0, 0),
        (0, 0, -1, 0, 0),
        (0, 0, 3, 0, 0),
        (0, 0, 4, 0, 0),
        # 'x' is out of range (because a zero-sized subband slice)
        (0, 0, 0, -2, 0),
        (0, 0, 0, -1, 0),
        (0, 0, 0, 1, 0),
        (0, 0, 0, 2, 0),
        # 'x' is out of range (because a smaller than usual subband slice)
        (0, 0, 1, -2, 0),
        (0, 0, 1, -1, 0),
        (0, 0, 1, 3, 0),
        (0, 0, 1, 4, 0),
        # 'y' is out of range (because of a zero-sized subband slice)
        (0, 0, 0, 0, -2),
        (0, 0, 0, 0, -1),
        (0, 0, 0, 0, 1),
        (0, 0, 0, 0, 2),
        # 'y' is out of range (because of a smaller than usual subband slice)
        (0, 0, 1, 0, -2),
        (0, 0, 1, 0, -1),
        (0, 0, 1, 0, 2),
        (0, 0, 1, 0, 3),
    ])
    def test_out_of_range_errors(self, sx, sy, subband_index, x, y):
        slices_x = 3
        slices_y = 2
        
        # Chosen carefully such that:
        # * subband_index=0 has subband slices with no entries
        # * subband_index=1 has subband slices with different sizes
        # * subband_index=2 has subband slices with equal sizes (10x10)
        subband_widths = [2, 11, 30]
        subband_heights = [1, 5, 20]
        
        with pytest.raises(IndexError):
            to_coeff_index(
                subband_widths, subband_heights,
                slices_x, slices_y,
                sx, sy,
                subband_index,
                x, y,
            )


class TestBaseSliceArray(object):
    
    @pytest.fixture
    def parse_info(self):
        return bitstream.ParseInfo()
    
    @pytest.fixture
    def sequence_header(self):
        sequence_header = bitstream.SequenceHeader()
        
        # NB: Set to small frame size to save creating a very large array
        # during the test
        sequence_header["video_parameters"]["frame_size"]["custom_dimensions_flag"].value = True
        sequence_header["video_parameters"]["frame_size"]["frame_width"].value = 1
        sequence_header["video_parameters"]["frame_size"]["frame_height"].value = 1
        
        return sequence_header
    
    @pytest.fixture
    def transform_parameters(self, parse_info, sequence_header):
        return bitstream.TransformParameters(parse_info, sequence_header)
    
    def test_auto_slice_count(self, sequence_header, transform_parameters):
        a = BaseSliceArray(sequence_header, transform_parameters)
        
        assert a._start_sx == 0
        assert a._start_sy == 0
        assert a._slice_count == 1
        
        transform_parameters["slice_parameters"]["slices_x"].value = 10
        transform_parameters["slice_parameters"]["slices_y"].value = 20
        
        assert a._start_sx == 0
        assert a._start_sy == 0
        assert a._slice_count == 200
    
    
    def test_metrics(self, sequence_header, transform_parameters):
        start_sx = bitstream.ConstantValue(0)
        start_sy = bitstream.ConstantValue(0)
        slice_count = bitstream.ConstantValue(1)
        
        a = BaseSliceArray(
            sequence_header,
            transform_parameters,
            start_sx,
            start_sy,
            slice_count,
        )
        
        # The following tests simultaneously check the _update_metrics function
        # and that the required notifications have been registered
        
        transform_parameters["slice_parameters"]["slices_x"].value = 4
        transform_parameters["slice_parameters"]["slices_y"].value = 2
        assert a._slices_x == 4
        assert a._slices_y == 2
        
        start_sx.value = 2
        start_sy.value = 1
        assert a._start_sx == 2
        assert a._start_sy == 1
        
        slice_count.value = 30
        assert a._slice_count == 30
        
        sequence_header["parse_parameters"]["major_version"].value = 3
        transform_parameters["dwt_depth"].value = 2
        transform_parameters["extended_transform_parameters"]["asym_transform_flag"].value = True
        transform_parameters["extended_transform_parameters"]["dwt_depth_ho"].value = 1
        assert a._dwt_depth == 2
        assert a._dwt_depth_ho == 1
        
        sequence_header["video_parameters"]["frame_size"]["frame_width"].value = 256
        sequence_header["video_parameters"]["frame_size"]["frame_height"].value = 128
        assert a._luma_width == 256
        assert a._luma_height == 128
        assert a._color_diff_width == 256//2  # 4:2:0
        assert a._color_diff_height == 128//2
        
        assert a._luma_subband_widths == (
            256//8,  # Level 0: L
            256//8,  # Level 1: H
            256//4,  # Level 2: HL
            256//4,  # Level 2: LH
            256//4,  # Level 2: HH
            256//2,  # Level 3: HL
            256//2,  # Level 3: LH
            256//2,  # Level 3: HH
        )
        assert a._luma_subband_heights == (
            128//4,  # Level 0: L
            128//4,  # Level 1: H
            128//4,  # Level 2: HL
            128//4,  # Level 2: LH
            128//4,  # Level 2: HH
            128//2,  # Level 3: HL
            128//2,  # Level 3: LH
            128//2,  # Level 3: HH
        )
        assert a._color_diff_subband_widths == (
            256//2//8,  # Level 0: L
            256//2//8,  # Level 1: H
            256//2//4,  # Level 2: HL
            256//2//4,  # Level 2: LH
            256//2//4,  # Level 2: HH
            256//2//2,  # Level 3: HL
            256//2//2,  # Level 3: LH
            256//2//2,  # Level 3: HH
        )
        assert a._color_diff_subband_heights == (
            128//2//4,  # Level 0: L
            128//2//4,  # Level 1: H
            128//2//4,  # Level 2: HL
            128//2//4,  # Level 2: LH
            128//2//4,  # Level 2: HH
            128//2//2,  # Level 3: HL
            128//2//2,  # Level 3: LH
            128//2//2,  # Level 3: HH
        )
        
        assert a._luma_coeffs_index_offset == to_coeff_index(
            a._luma_subband_widths,
            a._luma_subband_heights,
            a._slices_x,
            a._slices_y,
            2, 1,
        )
        assert a._color_diff_coeffs_index_offset == to_coeff_index(
            a._color_diff_subband_widths,
            a._color_diff_subband_heights,
            a._slices_x,
            a._slices_y,
            2, 1,
        )
        
        start_sx.value = 0
        start_sy.value = 0
        assert a._luma_coeffs_index_offset == 0
        assert a._color_diff_coeffs_index_offset == 0
    
    def test_resize(self, sequence_header, transform_parameters):
        start_sx = bitstream.ConstantValue(2)
        start_sy = bitstream.ConstantValue(1)
        slice_count = bitstream.ConstantValue(10)
        
        a = BaseSliceArray(
            sequence_header,
            transform_parameters,
            start_sx,
            start_sy,
            slice_count,
        )
        
        transform_parameters["slice_parameters"]["slices_x"].value = 8
        transform_parameters["slice_parameters"]["slices_y"].value = 4
        
        sequence_header["video_parameters"]["frame_size"]["frame_width"].value = 256
        sequence_header["video_parameters"]["frame_size"]["frame_height"].value = 128
        
        assert len(a._qindex) == 10
        assert len(a._y_coeffs) == ((256//8) * (128//4)) * 10
        assert len(a._c1_coeffs) == ((256//2//8) * (128//2//4)) * 10
        assert len(a._c2_coeffs) == ((256//2//8) * (128//2//4)) * 10
        
        slice_count.value = 5
        assert len(a._qindex) == 5
        assert len(a._y_coeffs) == ((256//8) * (128//4)) * 5
        assert len(a._c1_coeffs) == ((256//2//8) * (128//2//4)) * 5
        assert len(a._c2_coeffs) == ((256//2//8) * (128//2//4)) * 5
        
        # No change!
        start_sx.value = 3
        start_sy.value = 0
        assert len(a._qindex) == 5
        assert len(a._y_coeffs) == ((256//8) * (128//4)) * 5
        assert len(a._c1_coeffs) == ((256//2//8) * (128//2//4)) * 5
        assert len(a._c2_coeffs) == ((256//2//8) * (128//2//4)) * 5
    
    def test_to_slice_index(self, sequence_header, transform_parameters):
        transform_parameters["slice_parameters"]["slices_x"].value = 4
        transform_parameters["slice_parameters"]["slices_y"].value = 3
        a = BaseSliceArray(sequence_header, transform_parameters, 2, 1, 6)
        
        assert a._to_slice_index(2, 1) == 0
        assert a._to_slice_index(3, 1) == 1
        assert a._to_slice_index(0, 2) == 2
        assert a._to_slice_index(1, 2) == 3
        assert a._to_slice_index(2, 2) == 4
        assert a._to_slice_index(3, 2) == 5
    
    def test_from_slice_index(self, sequence_header, transform_parameters):
        transform_parameters["slice_parameters"]["slices_x"].value = 4
        transform_parameters["slice_parameters"]["slices_y"].value = 3
        a = BaseSliceArray(sequence_header, transform_parameters, 2, 1, 6)
        
        assert a._from_slice_index(0) == (2, 1)
        assert a._from_slice_index(1) == (3, 1)
        assert a._from_slice_index(2) == (0, 2)
        assert a._from_slice_index(3) == (1, 2)
        assert a._from_slice_index(4) == (2, 2)
        assert a._from_slice_index(5) == (3, 2)
    
    def test_to_coeff_index(self, sequence_header, transform_parameters):
        a = BaseSliceArray(sequence_header, transform_parameters, 2, 1, 2)
        sequence_header["video_parameters"]["frame_size"]["frame_width"].value = 128
        sequence_header["video_parameters"]["frame_size"]["frame_height"].value = 64
        
        transform_parameters["slice_parameters"]["slices_x"].value = 4
        transform_parameters["slice_parameters"]["slices_y"].value = 2
        
        # First slice should be first...
        assert a._to_luma_coeff_index(2, 1) == 0
        assert a._to_color_diff_coeff_index(2, 1) == 0
        
        # Slices should be spaced as expected
        assert a._to_luma_coeff_index(3, 1) == (128//4) * (64//2)
        assert a._to_color_diff_coeff_index(3, 1) == (128//2//4) * (64//2//2)
    
    def test_to_num_subband_levels(self, sequence_header, transform_parameters):
        a = BaseSliceArray(sequence_header, transform_parameters)
        
        assert a._num_subband_levels == 1
        
        transform_parameters["dwt_depth"].value = 3
        assert a._num_subband_levels == 1 + 3
        
        transform_parameters["extended_transform_parameters"]["asym_transform_flag"].value = True
        transform_parameters["extended_transform_parameters"]["dwt_depth_ho"].value = 2
        assert a._num_subband_levels == 1 + 2 + 3
    
    def test_to_num_subbands(self, sequence_header, transform_parameters):
        a = BaseSliceArray(sequence_header, transform_parameters)
        
        assert a._num_subbands == 1
        
        transform_parameters["dwt_depth"].value = 3
        assert a._num_subbands == 1 + 3 + 3 + 3
        
        transform_parameters["extended_transform_parameters"]["asym_transform_flag"].value = True
        transform_parameters["extended_transform_parameters"]["dwt_depth_ho"].value = 2
        assert a._num_subbands == 1 + 1 + 1 + 3 + 3 + 3
    
    def test_iter_slice_indices_and_coords(self, sequence_header, transform_parameters):
        a = BaseSliceArray(sequence_header, transform_parameters, 2, 1, 4)
        transform_parameters["slice_parameters"]["slices_x"].value = 4
        transform_parameters["slice_parameters"]["slices_y"].value = 2
        
        assert list(a._iter_slice_indices_and_coords()) == [
            (0, 2, 1),
            (1, 3, 1),
            (2, 0, 2),
            (3, 1, 2),
        ]
    
    def test_slice_num_component_coefficients(self, sequence_header, transform_parameters):
        a = BaseSliceArray(sequence_header, transform_parameters, 2, 1, 2)
        sequence_header["video_parameters"]["frame_size"]["frame_width"].value = 127
        sequence_header["video_parameters"]["frame_size"]["frame_height"].value = 63
        
        transform_parameters["slice_parameters"]["slices_x"].value = 4
        transform_parameters["slice_parameters"]["slices_y"].value = 2
        
        # First slice should be of the smaller size
        luma, color_diff = a._get_slice_num_component_coefficients(0, 0)
        assert luma == (127//4) * (63//2)
        assert color_diff == (127//2//4) * (63//2//2)
        
        # Later slices should have the larger size
        luma, color_diff = a._get_slice_num_component_coefficients(3, 1)
        assert luma == (128//4) * (64//2)
        assert color_diff == (128//2//4) * (64//2//2)


class TestComponentViewsStr(object):
    
    # The following fixtures define structures with the following dimensions
    #
    # 4:2:0 colour sampling -> 128x16 luma, 64x8 color-diff
    # 4x2 slices -> 32x8 luma, 16x4 color-diff dimensions
    # One horizontal only transform level and two 2D transform levels ->
    #   Level 0, L: 4x2 luma, 2x1 color-diff
    #   Level 1, H: 4x2 luma, 2x1 color-diff
    #   Level 2: HL, LH, HH: 8x2 luma, 4x1 color-diff
    #   Level 3: HL, LH, HH: 16x4 luma, 8x2 color-diff
    
    @pytest.fixture
    def parse_info(self):
        parse_info = bitstream.ParseInfo()
        parse_info["parse_code"].value = tables.ParseCodes.high_quality_picture
        return parse_info
    
    @pytest.fixture
    def sequence_header(self):
        sequence_header = bitstream.SequenceHeader()
        
        sequence_header["video_parameters"]["frame_size"]["custom_dimensions_flag"].value = True
        sequence_header["video_parameters"]["frame_size"]["frame_width"].value = 128
        sequence_header["video_parameters"]["frame_size"]["frame_height"].value = 16
        
        return sequence_header
    
    @pytest.fixture
    def transform_parameters(self, parse_info, sequence_header):
        transform_parameters = bitstream.TransformParameters(parse_info, sequence_header)
        transform_parameters["slice_parameters"]["slices_x"].value = 4
        transform_parameters["slice_parameters"]["slices_y"].value = 2
        
        transform_parameters["dwt_depth"].value = 2
        transform_parameters["extended_transform_parameters"]["asym_transform_flag"].value = True
        transform_parameters["extended_transform_parameters"]["dwt_depth_ho"].value = 1
        
        return transform_parameters
    
    @pytest.fixture
    def slice_array(self, sequence_header, transform_parameters):
        return BaseSliceArray(
            sequence_header,
            transform_parameters,
            2, 1,
            2,
        )
    
    def test_with_padding(self, slice_array):
        c1_coeffs = slice_array[0].c1_coeffs
        c2_coeffs = slice_array[0].c2_coeffs
        
        # Pre-populate the color samples with increasing integers
        i = 0
        num_bits = 0
        for subband_index in range(len(c1_coeffs)):
            c1_subband = c1_coeffs[subband_index]
            c2_subband = c2_coeffs[subband_index]
            for value_index in range(len(c1_subband)):
                c1_subband[value_index] = i
                c2_subband[value_index] = i + 1
                num_bits += signed_exp_golomb_length(i)
                num_bits += signed_exp_golomb_length(i+1)
                i += 2
        
        assert component_views_str(
            num_bits + 4,
            0b0101,
            c1_coeffs,
            c2_coeffs,
        ) == (
            "Level 0, L:\n"
            "  (0, 1)  (2, 3)\n"
            "Level 1, H:\n"
            "  (4, 5)  (6, 7)\n"
            "Level 2, HL:\n"
            "  (8, 9)  (10, 11)  (12, 13)  (14, 15)\n"
            "Level 2, LH:\n"
            "  (16, 17)  (18, 19)  (20, 21)  (22, 23)\n"
            "Level 2, HH:\n"
            "  (24, 25)  (26, 27)  (28, 29)  (30, 31)\n"
            "Level 3, HL:\n"
            "  (32, 33)  (34, 35)  (36, 37)  (38, 39)  (40, 41)  (42, 43)  (44, 45)  (46, 47)\n"
            "  (48, 49)  (50, 51)  (52, 53)  (54, 55)  (56, 57)  (58, 59)  (60, 61)  (62, 63)\n"
            "Level 3, LH:\n"
            "  (64, 65)  (66, 67)  (68, 69)  (70, 71)  (72, 73)  (74, 75)  (76, 77)  (78, 79)\n"
            "  (80, 81)  (82, 83)  (84, 85)  (86, 87)  (88, 89)  (90, 91)  (92, 93)  (94, 95)\n"
            "Level 3, HH:\n"
            "    (96, 97)    (98, 99)  (100, 101)  (102, 103)  (104, 105)  (106, 107)  (108, 109)  (110, 111)\n"
            "  (112, 113)  (114, 115)  (116, 117)  (118, 119)  (120, 121)  (122, 123)  (124, 125)  (126, 127)\n"
            "4 unused bits: 0b0101"
        )
    
    def test_with_values_past_end(self, slice_array):
        c1_coeffs = slice_array[0].c1_coeffs
        c2_coeffs = slice_array[0].c2_coeffs
        
        # Pre-populate the color samples with increasing integers
        i = 0
        num_bits = 0
        for subband_index in range(len(c1_coeffs) - 1):
            c1_subband = c1_coeffs[subband_index]
            c2_subband = c2_coeffs[subband_index]
            for value_index in range(len(c1_subband)):
                c1_subband[value_index] = i
                c2_subband[value_index] = i + 1
                num_bits += signed_exp_golomb_length(i)
                num_bits += signed_exp_golomb_length(i+1)
                i += 2
        
        assert component_views_str(
            num_bits + 1,
            0,
            c1_coeffs,
            c2_coeffs,
        ) == (
            "Level 0, L:\n"
            "  (0, 1)  (2, 3)\n"
            "Level 1, H:\n"
            "  (4, 5)  (6, 7)\n"
            "Level 2, HL:\n"
            "  (8, 9)  (10, 11)  (12, 13)  (14, 15)\n"
            "Level 2, LH:\n"
            "  (16, 17)  (18, 19)  (20, 21)  (22, 23)\n"
            "Level 2, HH:\n"
            "  (24, 25)  (26, 27)  (28, 29)  (30, 31)\n"
            "Level 3, HL:\n"
            "  (32, 33)  (34, 35)  (36, 37)  (38, 39)  (40, 41)  (42, 43)  (44, 45)  (46, 47)\n"
            "  (48, 49)  (50, 51)  (52, 53)  (54, 55)  (56, 57)  (58, 59)  (60, 61)  (62, 63)\n"
            "Level 3, LH:\n"
            "  (64, 65)  (66, 67)  (68, 69)  (70, 71)  (72, 73)  (74, 75)  (76, 77)  (78, 79)\n"
            "  (80, 81)  (82, 83)  (84, 85)  (86, 87)  (88, 89)  (90, 91)  (92, 93)  (94, 95)\n"
            "Level 3, HH:\n"
            "   (0, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)\n"
            "  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)  (0*, 0*)"
        )
    
    def test_with_single_coefficient_set(self, slice_array):
        y_coeffs = slice_array[0].y_coeffs
        
        # Pre-populate the color samples with increasing integers
        i = 0
        num_bits = 0
        for subband_index in range(len(y_coeffs) - 1):
            y_subband = y_coeffs[subband_index]
            for value_index in range(len(y_subband)):
                y_subband[value_index] = i
                num_bits += signed_exp_golomb_length(i)
                i += 1
        
        assert component_views_str(
            num_bits + 1,
            0,
            y_coeffs,
        ) == (
            "Level 0, L:\n"
            "  0  1  2  3\n"
            "  4  5  6  7\n"
            "Level 1, H:\n"
            "   8   9  10  11\n"
            "  12  13  14  15\n"
            "Level 2, HL:\n"
            "  16  17  18  19  20  21  22  23\n"
            "  24  25  26  27  28  29  30  31\n"
            "Level 2, LH:\n"
            "  32  33  34  35  36  37  38  39\n"
            "  40  41  42  43  44  45  46  47\n"
            "Level 2, HH:\n"
            "  48  49  50  51  52  53  54  55\n"
            "  56  57  58  59  60  61  62  63\n"
            "Level 3, HL:\n"
            "   64   65   66   67   68   69   70   71   72   73   74   75   76   77   78   79\n"
            "   80   81   82   83   84   85   86   87   88   89   90   91   92   93   94   95\n"
            "   96   97   98   99  100  101  102  103  104  105  106  107  108  109  110  111\n"
            "  112  113  114  115  116  117  118  119  120  121  122  123  124  125  126  127\n"
            "Level 3, LH:\n"
            "  128  129  130  131  132  133  134  135  136  137  138  139  140  141  142  143\n"
            "  144  145  146  147  148  149  150  151  152  153  154  155  156  157  158  159\n"
            "  160  161  162  163  164  165  166  167  168  169  170  171  172  173  174  175\n"
            "  176  177  178  179  180  181  182  183  184  185  186  187  188  189  190  191\n"
            "Level 3, HH:\n"
            "   0  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*\n"
            "  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*\n"
            "  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*\n"
            "  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*  0*"
        )


class TestBaseViews(object):
    
    @pytest.fixture
    def parse_info(self):
        parse_info = bitstream.ParseInfo()
        parse_info["parse_code"].value = tables.ParseCodes.high_quality_picture
        return parse_info
    
    @pytest.fixture
    def sequence_header(self):
        sequence_header = bitstream.SequenceHeader()
        
        sequence_header["video_parameters"]["frame_size"]["custom_dimensions_flag"].value = True
        sequence_header["video_parameters"]["frame_size"]["frame_width"].value = 128
        sequence_header["video_parameters"]["frame_size"]["frame_height"].value = 16
        
        return sequence_header
    
    @pytest.fixture
    def transform_parameters(self, parse_info, sequence_header):
        transform_parameters = bitstream.TransformParameters(parse_info, sequence_header)
        transform_parameters["slice_parameters"]["slices_x"].value = 4
        transform_parameters["slice_parameters"]["slices_y"].value = 2
        
        transform_parameters["dwt_depth"].value = 2
        transform_parameters["extended_transform_parameters"]["asym_transform_flag"].value = True
        transform_parameters["extended_transform_parameters"]["dwt_depth_ho"].value = 1
        
        return transform_parameters
    
    @pytest.fixture
    def slice_array(self, sequence_header, transform_parameters):
        return BaseSliceArray(
            sequence_header,
            transform_parameters,
            2, 1,
            2,
        )
    
    @pytest.fixture
    def notify_target(self, slice_array):
        notify_target = MockNotificationTarget()
        slice_array._notify_on_change(notify_target)
        return notify_target
    
    def test_base_slice_view_identity_properties(self, slice_array):
        # Get via both 1D and 2D coordinates
        print(slice_array[0])
        s0 = slice_array[0]
        s1 = slice_array[3, 1]
        
        assert s0.sx == 2
        assert s0.sy == 1
        assert s0.slice_index == 0
        
        assert s1.sx == 3
        assert s1.sy == 1
        assert s1.slice_index == 1
        
    def test_base_slice_view_qindex(self, slice_array, notify_target):
        slice_array._qindex = [123, 321]
        
        # Read
        assert slice_array[0].qindex == 123
        assert slice_array[1].qindex == 321
        
        # Write
        assert notify_target.notification_count == 0
        slice_array[0].qindex = 1234
        assert notify_target.notification_count == 1
        slice_array[1].qindex = 4321
        assert notify_target.notification_count == 2
        assert slice_array._qindex == [1234, 4321]
    
    def test_component_view_identity_properties(self, slice_array):
        s = slice_array[0]
        
        assert s.y_coeffs.component == "y"
        assert s.c1_coeffs.component == "c1"
        assert s.c2_coeffs.component == "c2"
    
    def test_component_view_identity_getitem(self, slice_array):
        y = slice_array[0].y_coeffs
        
        for n, (level, subband) in enumerate([
                (0, "L"),
                (1, "H"),
                (2, "HL"), (2, "LH"), (2, "HH"),
                (3, "HL"), (3, "LH"), (3, "HH")]):
            assert y[n].subband == (level, subband)
            assert y[n].subband_index == n
            assert y[level, subband].subband_index == n
            assert y[level, subband].subband == (level, subband)
    
    def test_component_view_len(self, slice_array):
        y = slice_array[0].y_coeffs
        assert len(y) == 1 + 1 + (2*3)
    
    def test_component_view_iter(self, slice_array):
        y = slice_array[0].y_coeffs
        assert [sb.subband_index for sb in list(y)] == list(range(len(y)))
    
    def test_component_view_items(self, slice_array):
        y = slice_array[0].y_coeffs
        assert [(sb.subband_index, l, b) for (l, b, sb) in y.items()] == [
            (0, 0, "L"),
            (1, 1, "H"),
            (2, 2, "HL"), (3, 2, "LH"), (4, 2, "HH"),
            (5, 3, "HL"), (6, 3, "LH"), (7, 3, "HH"),
        ]
    
    def test_component_subband_view_geometry(self, slice_array):
        # 4:2:0 colour sampling -> 128x16 luma, 64x8 color-diff
        # 4x2 slices -> 32x8 luma, 16x4 color-diff dimensions
        # 1 horizontal only transform level -> 16x8 luma, 8x4 color-diff DC component dimensions
        # 2 2D transform levels -> 4x2 luma, 2x1 color-diff DC component dimensions
        
        y_dc = slice_array[0].y_coeffs[0]
        assert y_dc.dimensions == (4, 2)
        assert y_dc.bounds == (2*4, 1*2, 3*4, 2*2)
        assert len(y_dc) == 4 * 2
        
        c1_dc = slice_array[0].c1_coeffs[0]
        assert c1_dc.dimensions == (2, 1)
        assert c1_dc.bounds == (2*2, 1*1, 3*2, 2*1)
        assert len(c1_dc) == 2 * 1
        
        c2_dc = slice_array[0].c2_coeffs[0]
        assert c2_dc.dimensions == (2, 1)
        assert c2_dc.bounds == (2*2, 1*1, 3*2, 2*1)
        assert len(c2_dc) == 2 * 1
    
    def test_component_subband_view_get_and_set_iter(self, slice_array, notify_target):
        slice_array._y_coeffs[:] = list(range(len(slice_array._y_coeffs)))
        slice_array._c1_coeffs[:] = list(range(len(slice_array._c1_coeffs)))
        slice_array._c2_coeffs[:] = list(range(len(slice_array._c2_coeffs)))
        
        c1_index = 0
        c2_index = 0
        for component, scale in [("y", 10), ("c1", 100), ("c2", 1000)]:
            index = 0
            for sx, sy in [(2, 1), (3, 1)]:
                slice_view = slice_array[sx, sy]
                
                coeffs = getattr(slice_view, "{}_coeffs".format(component))
                for subband_index in range(1 + 1 + (2*3)):
                    subband_view = coeffs[subband_index]
                    w, h = subband_view.dimensions
                    for y in range(h):
                        for x in range(w):
                            notify_target.reset()
                            assert subband_view[x, y] == index
                            assert subband_view[x + (y*w)] == index
                            assert notify_target.notification_count == 0
                            subband_view[x, y] = index * scale
                            assert notify_target.notification_count == 1
                            assert subband_view[x + (y*w)] == index * scale
                            subband_view[x + (y*w)] = index * -scale
                            assert notify_target.notification_count == 2
                            assert subband_view[x, y] == index * -scale
                            index += 1
                    
                    # Check slices work (can get and can set)
                    notify_target.reset()
                    assert subband_view[:] == [-i for i in range((index-(w*h))*scale, index*scale, scale)]
                    assert notify_target.notification_count == 0
                    subband_view[:] = list(range((index-(w*h))*scale, index*scale, scale))
                    assert notify_target.notification_count == 1
                    
                    # Check iteration
                    assert list(subband_view) == list(range((index-(w*h))*scale, index*scale, scale))
                    assert list(subband_view.items()) == [
                        (x, y, ((index-(w*h)) + x + (y*w))*scale)
                        for y in range(h)
                        for x in range(w)
                    ]
        
        # Check mutations were applied correctly/completely
        assert slice_array._y_coeffs == [
            i * 10 for i in range(len(slice_array._y_coeffs))
        ]
        assert slice_array._c1_coeffs == [
            i * 100 for i in range(len(slice_array._c1_coeffs))
        ]
        assert slice_array._c2_coeffs == [
            i * 1000 for i in range(len(slice_array._c2_coeffs))
        ]
    
    def test_component_subband_view_len(self, slice_array):
        s = slice_array[0].y_coeffs[0]
        w, h = s.dimensions
        assert len(s) == w * h
    
    def test_component_subband_normalise_key(self, slice_array):
        subband_view = slice_array[0].y_coeffs[1]
        
        start_index = len(slice_array[0].y_coeffs[0])
        
        # Simple numerical indices
        assert subband_view._normalise_key(0) == start_index
        assert subband_view._normalise_key(1) == start_index + 1
        
        # 2D indices
        w, h = subband_view.dimensions
        assert subband_view._normalise_key((0, 0)) == start_index
        assert subband_view._normalise_key((1, 0)) == start_index + 1
        assert subband_view._normalise_key((0, 1)) == start_index + w
        assert subband_view._normalise_key((1, 1)) == start_index + w + 1
        
        # Slice simple
        assert subband_view._normalise_key(slice(2, 5)) == slice(
            start_index+2,
            start_index+5,
            None,
        )
        
        # Slice open-ended
        assert subband_view._normalise_key(slice(None, 5)) == slice(
            start_index,
            start_index+5,
            None,
        )
        assert subband_view._normalise_key(slice(None, 5, -1)) == slice(
            start_index+(w*h)-1,
            start_index+5,
            -1,
        )
        assert subband_view._normalise_key(slice(2, None)) == slice(
            start_index+2,
            start_index+(w*h),
            None,
        )
        assert subband_view._normalise_key(slice(2, None, -1)) == slice(
            start_index+2,
            start_index-1,
            -1,
        )
        
        # Slice negative endpoints
        assert subband_view._normalise_key(slice(-5, -2)) == slice(
            start_index+(w*h)-5,
            start_index+(w*h)-2,
            None,
        )
        
        # Steps
        assert subband_view._normalise_key(slice(2, 5, 2)) == slice(
            start_index+2,
            start_index+5,
            2,
        )
        
        # Out-of-range endpoints are truncated
        assert subband_view._normalise_key(slice(-w*h*2, w*h*2)) == slice(
            start_index,
            start_index+(w*h),
            None,
        )
        assert subband_view._normalise_key(slice(w*h*2, -w*h*2, -1)) == slice(
            start_index+(w*h)-1,
            start_index-1,
            -1,
        )

class TestLDSliceArray(object):
    
    @pytest.fixture
    def parse_info(self):
        parse_info = bitstream.ParseInfo()
        parse_info["parse_code"].value = tables.ParseCodes.low_delay_picture
        return parse_info
    
    @pytest.fixture
    def sequence_header(self):
        sequence_header = bitstream.SequenceHeader()
        
        sequence_header["video_parameters"]["frame_size"]["custom_dimensions_flag"].value = True
        sequence_header["video_parameters"]["frame_size"]["frame_width"].value = 16
        sequence_header["video_parameters"]["frame_size"]["frame_height"].value = 8
        
        return sequence_header
    
    @pytest.fixture
    def transform_parameters(self, parse_info, sequence_header):
        transform_parameters = bitstream.TransformParameters(parse_info, sequence_header)
        transform_parameters["slice_parameters"]["slices_x"].value = 4
        transform_parameters["slice_parameters"]["slices_y"].value = 2
        transform_parameters["slice_parameters"]["slice_bytes_numerator"].value = 127
        transform_parameters["slice_parameters"]["slice_bytes_denominator"].value = 2
        return transform_parameters
    
    @pytest.fixture
    def example_bitstream(self):
        """
        A sample low-delay bitstream containing two slices as follows:
        
        * Slice size: 127/2 bytes, so:
          * Slice 0 will be 63 bytes (504 bits)
          * Slice 1 will be 64 bytes (512 bits)
        * Data dimensions (no transform)
          * 4 x 4 luma data per slice
          * 2 x 2 color-diff data per slice
        * qindex = 10 for slice 0, 11 for slice 1
        * slice_y_length is chosen such that in slice 0 the luma data will not
          fit in the allocated space and in slice 1, the color diff data will
          not fit. This field is 9 bits long in both slices. Accounting for the
          qindex and slice_y_length field, 488 bits remain for data in slice 0
          and 496 remain in slice 1.
          * In slice 0: slice_y_length = 5 (leaving 483 for color diff)
          * In slice 1: slice_y_length = 487 (leaving 9 for color diff)
        * Luma data
          * Slice 0: '1' in first sample, '0' in rest
          * Slice 1: '1' in all samples
        * Color diff data
          * Slice 0: '2' in c1, and '-2' in c2 for all samples
          * Slice 1: '2' in c1, and '-2' in c2 for first samples, '0' in rest
        * Padding data in bounded blocks will be set to a binary string
          0b1000....0001 which fills the remaining space. Specifically:
          * Slice 0: Luma: No padding, Color-diff: 483-(2*2*4*2)=451 bits of padding
          * Slice 1: Luma: 487-(4*4*4)=423 bits of padding, Color-diff: No padding
        """
        out = b""
        
        # Slice 0 qindex and slice_y_length
        # 0d_____10________5
        # 0b0001010000000101
        # 0x___1___4___0___5
        out += b"\x14\x05"
        
        # Slice 0 luma and color-diff samples
        #    Luma          Color Diff                  Padding
        #     |                |                          |
        #    ,--, ,---------------------------,           |
        #    1  0 2  -2   2  -2   2  -2   2  -2           |
        #    |  | |   |   |   |   |   |   |   |           |
        #   ,--,|,--,,--,,--,,--,,--,,--,,--,,--,,------------------,
        # 0b00101011001110110011101100111011001111000000 ... 00000001
        # 0x___2___B___3___B___3___B___3___B___3___C___0 ... ___0___1
        out += b"\x2B\x3B\x3B\x3B\x3C" + (b"\x00"*55) + b"\x01"
        
        # Slice 1 qindex and slice_y_length
        # 0d_____11______487
        # 0b0001011111100111
        # 0x___1___7___E___7
        out += b"\x17\xE7"
        
        # Slice 1 luma and color-diff samples
        #       Luma             Padding      Color Diff
        #         |                 |             |
        #    ,----------,           |          ,-----,
        #    1   1  ... 1           |          2  -2 0
        #    |   |  +13 |           |          |   | |
        #   ,--,,--,   ,--,,----------------,,--,,--,|
        # 0b00100010...001010000000...0000001011001111
        # 0x___2___2...___2___8___0...___0___2___C___F
        out += (b"\x22"*8) + b"\x80" + (b"\x00"*51) + b"\x02\xCF"
        
        # Sanity check
        assert len(out) == 127
        
        return out
    
    def test_read(self, sequence_header, transform_parameters, example_bitstream):
        a = bitstream.LDSliceArray(sequence_header, transform_parameters, 0, 0, 2)
        # Read the data back in and check it is correct
        r = bitstream.BitstreamReader(BytesIO(example_bitstream))
        a.read(r)
        
        assert a.offset == (0, 7)
        assert a.bits_past_eof == 0
        
        # Check data is as expected
        assert a._qindex == [10, 11]
        assert a._slice_y_length == [5, 487]
        
        assert a._y_coeffs == [1] + ([0]*15) + ([1]*16)
        assert a._c1_coeffs == ([2]*4) + [2] + ([0]*3)
        assert a._c2_coeffs == ([-2]*4) + [-2] + ([0]*3)
        
        assert a._y_block_padding == [
            0,
            1<<(423-1) | 1,
        ]
        
        assert a._c_block_padding == [
            1<<(451-1) | 1,
            0,
        ]
    
    def test_write(self, sequence_header, transform_parameters, example_bitstream):
        # Start with the reference bitstream
        a = bitstream.LDSliceArray(sequence_header, transform_parameters, 0, 0, 2)
        r = bitstream.BitstreamReader(BytesIO(example_bitstream))
        a.read(r)
        
        # Write this and check it is produced bit-for-bit identically
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        a.write(w)
        assert a.offset == (0, 7)
        assert a.bits_past_eof == 0
        assert w.tell() == r.tell()
        assert f.getvalue() == example_bitstream
    
    def test_length(self, sequence_header, transform_parameters, example_bitstream):
        a = bitstream.LDSliceArray(sequence_header, transform_parameters, 0, 0, 2)
        r = bitstream.BitstreamReader(BytesIO(example_bitstream))
        a.read(r)
        assert a.length == len(example_bitstream) * 8
    
    def test_invalid_slice_y_length(self, sequence_header, transform_parameters):
        # Ensure that whatever the slice_y_length, the output slice sizes
        # always remain the same
        for sx, expected_size in [(0, 63), (1, 64)]:
            a1 = bitstream.LDSliceArray(sequence_header, transform_parameters, sx, 0, 1)
            # NB: (1<<9)-1 is int-max for the slice_y_length field
            a1._slice_y_length[0] = (1<<9) - 1
            
            # Writing should generate right sized bitstream (despite
            # longer-than-the-slice slice_y_length)
            f = BytesIO()
            w = bitstream.BitstreamWriter(f)
            a1.write(w)
            assert w.tell() == (expected_size, 7)
            
            # Reading should read-back the longer-than-the-slice
            # slice_y_length value while still reading the correct data
            # back.
            a2 = bitstream.LDSliceArray(sequence_header, transform_parameters, sx, 0, 1)
            r = bitstream.BitstreamReader(BytesIO(f.getvalue()))
            a2.read(r)
            assert r.tell() == (expected_size, 7)
            assert a1._qindex == a2._qindex
            assert a1._slice_y_length == a2._slice_y_length
    
    def test_ld_slice_view_accessors(self, sequence_header, transform_parameters):
        notify = MockNotificationTarget()
        a = bitstream.LDSliceArray(sequence_header, transform_parameters, 0, 0, 2)
        a._notify_on_change(notify)
        
        a._slice_y_length = [10, 20]
        a._y_block_padding = [100, 200]
        a._c_block_padding = [1000, 2000]
        
        assert a[0].slice_y_length == 10
        assert a[1].slice_y_length == 20
        assert notify.notification_count == 0
        a[0].slice_y_length = 1
        assert notify.notification_count == 1
        a[1].slice_y_length = 2
        assert notify.notification_count == 2
        assert a._slice_y_length == [1, 2]
        
        assert a[0].y_block_padding == 100
        assert a[1].y_block_padding == 200
        assert notify.notification_count == 2
        a[0].y_block_padding = 10
        assert notify.notification_count == 3
        a[1].y_block_padding = 20
        assert notify.notification_count == 4
        assert a._y_block_padding == [10, 20]
        
        assert a[0].c_block_padding == 1000
        assert a[1].c_block_padding == 2000
        assert notify.notification_count == 4
        a[0].c_block_padding = 100
        assert notify.notification_count == 5
        a[1].c_block_padding = 200
        assert notify.notification_count == 6
        assert a._c_block_padding == [100, 200]
    
    def test_ld_slice_view_lengths(self, sequence_header, transform_parameters):
        a = bitstream.LDSliceArray(sequence_header, transform_parameters, 0, 0, 2)
        
        assert a[0].length == 63*8
        assert a[1].length == 64*8
        
        assert a[0].header_length == 7 + 9
        assert a[1].header_length == 7 + 9
        
        a[0].slice_y_length = 0
        a[1].slice_y_length = 0
        assert a[0].true_slice_y_length == 0
        assert a[1].true_slice_y_length == 0
        assert a[0].slice_c_length == 63*8 - (7 + 9)
        assert a[1].slice_c_length == 64*8 - (7 + 9)
        
        a[0].slice_y_length = 123
        a[1].slice_y_length = 321
        assert a[0].true_slice_y_length == 123
        assert a[1].true_slice_y_length == 321
        assert a[0].slice_c_length == 63*8 - (7 + 9) - 123
        assert a[1].slice_c_length == 64*8 - (7 + 9) - 321
        
        # Clamp to maximum size
        a[0].slice_y_length = 100000
        a[1].slice_y_length = 100000
        assert a[0].true_slice_y_length == 63*8 - (7 + 9)
        assert a[1].true_slice_y_length == 64*8 - (7 + 9)
        assert a[0].slice_c_length == 0
        assert a[1].slice_c_length == 0
    
    def test_ld_slice_view_str(self, sequence_header, transform_parameters, example_bitstream):
        a = bitstream.LDSliceArray(sequence_header, transform_parameters, 0, 0, 2)
        r = bitstream.BitstreamReader(BytesIO(example_bitstream))
        a.read(r)
        
        assert str(a[1]) == (
            "ld_slice(sx=1, sy=0):\n"
            "  qindex: 11\n"
            "  slice_y_length: 487\n"
            "  y_coeffs:\n"
            "    Level 0, DC:\n"
            "      1  1  1  1\n"
            "      1  1  1  1\n"
            "      1  1  1  1\n"
            "      1  1  1  1\n"
            "    423 unused bits: 0b10000...00001\n"
            "  c1_coeffs & c2_coeffs:\n"
            "    Level 0, DC:\n"
            "       (2, -2)   (0, 0*)\n"
            "      (0*, 0*)  (0*, 0*)"
        )


class TestHQSliceArray(object):
    
    @pytest.fixture
    def parse_info(self):
        parse_info = bitstream.ParseInfo()
        parse_info["parse_code"].value = tables.ParseCodes.high_quality_picture
        return parse_info
    
    @pytest.fixture
    def sequence_header(self):
        sequence_header = bitstream.SequenceHeader()
        
        sequence_header["video_parameters"]["frame_size"]["custom_dimensions_flag"].value = True
        sequence_header["video_parameters"]["frame_size"]["frame_width"].value = 16
        sequence_header["video_parameters"]["frame_size"]["frame_height"].value = 8
        
        return sequence_header
    
    @pytest.fixture
    def transform_parameters(self, parse_info, sequence_header):
        transform_parameters = bitstream.TransformParameters(parse_info, sequence_header)
        transform_parameters["slice_parameters"]["slices_x"].value = 4
        transform_parameters["slice_parameters"]["slices_y"].value = 2
        transform_parameters["slice_parameters"]["slice_prefix_bytes"].value = 2
        transform_parameters["slice_parameters"]["slice_size_scaler"].value = 3
        return transform_parameters
    
    @pytest.fixture
    def example_bitstream(self):
        """
        A sample high-quality bitstream containing two slices as follows:
        
        * Slice prefixes: 2 bytes long
          * Slice 0 will have prefix bytes 0xDE 0xAD
          * Slice 1 will have prefix bytes 0xBE 0xEF
        * Data dimensions (no transform)
          * 4 x 4 luma data per slice
          * 2 x 2 color-diff data per slice
        * qindex = 10 for slice 0, 11 for slice 1
        * transform coefficients:
          * slice 0: all coefficients set to 1, 7 and -7 for Y, C1 and C2 (respectively)
          * slice 1: all coefficients set to 0 for all components
        * length: Set to be the samllest size large enough to fit the
          coefficients
          * slice 0: 
            * Y: Coeffs = 4*16bits = 8 bytes. Length field = 3. Length = 3*3=9 Bytes
            * C1: Coeffs = 8*4bits = 4 bytes. Length field = 2. Length = 2*3=6 Bytes
            * C2: Coeffs = 8*4bits = 4 bytes. Length field = 2. Length = 2*3=6 Bytes
          * slice 1: length field = 0
        * padding a binary string 0b100...001 filling any remaining space
          * slice 0:
            * Y: 0x81 (8 bits)
            * C1: 0x8001 (16 bits)
            * C2: 0x8001 (16 bits)
        """
        out = b""
        
        # Slice 0 prefix bytes
        out += b"\xDE\xAD"
        
        # Slice 0 qindex
        out += b"\x0A"
        
        # Slice 0 slice_y_length
        out += b"\x03"
        
        # Slice 0 y_coeffs
        #     1   1 ...  1  Padding
        #     |   | +13  |    |
        #   ,--,,--,...,--,,------,
        # 0b00100010   001010000001
        # 0x___2___2...___2___8___1
        out += (b"\x22"*8) + b"\x81"
        
        # Slice 0 slice_c1_length
        out += b"\x02"
        
        # Slice 0 c1_coeffs
        #      7       7       7       7        Padding
        #      |       |       |       |           |
        #   ,------,,------,,------,,------,,--------------,
        # 0b000000100000001000000010000000101000000000000001
        # 0x___0___2___0___2___0___2___0___2___8___0___0___1
        out += (b"\x02"*4) + b"\x80\x01"
        
        # Slice 0 slice_c2_length
        out += b"\x02"
        
        # Slice 0 c2_coeffs
        #     -7      -7      -7      -7        Padding
        #      |       |       |       |           |
        #   ,------,,------,,------,,------,,--------------,
        # 0b000000110000001100000011000000111000000000000001
        # 0x___0___3___0___3___0___3___0___3___8___0___0___1
        out += (b"\x03"*4) + b"\x80\x01"
        
        # Slice 1 prefix bytes
        out += b"\xBE\xEF"
        
        # Slice 1 qindex
        out += b"\x0B"
        
        # Slice 1 slice_*_length
        out += b"\x00\x00\x00"
        
        return out
    
    def test_read(self, sequence_header, transform_parameters, example_bitstream):
        a = bitstream.HQSliceArray(sequence_header, transform_parameters, 0, 0, 2)
        # Read the data back in and check it is correct
        r = bitstream.BitstreamReader(BytesIO(example_bitstream))
        a.read(r)
        
        assert a.offset == (0, 7)
        assert a.bits_past_eof == 0
        
        # Check data is as expected
        assert a._prefix_bytes == [b"\xDE\xAD", b"\xBE\xEF"]
        assert a._qindex == [10, 11]
        assert a._slice_y_length == [3, 0]
        assert a._slice_c1_length == [2, 0]
        assert a._slice_c2_length == [2, 0]
        
        assert a._y_coeffs == ([1]*16) + ([0]*16)
        assert a._c1_coeffs == ([7]*4) + ([0]*4)
        assert a._c2_coeffs == ([-7]*4) + ([0]*4)
        
        assert a._y_block_padding == [0x81, 0]
        assert a._c1_block_padding == [0x8001, 0]
        assert a._c2_block_padding == [0x8001, 0]
    
    def test_write(self, sequence_header, transform_parameters, example_bitstream):
        # Start with the reference bitstream
        a = bitstream.HQSliceArray(sequence_header, transform_parameters, 0, 0, 2)
        r = bitstream.BitstreamReader(BytesIO(example_bitstream))
        a.read(r)
        
        # Write this and check it is produced bit-for-bit identically
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        a.write(w)
        assert a.offset == (0, 7)
        assert a.bits_past_eof == 0
        assert w.tell() == r.tell()
        assert f.getvalue() == example_bitstream
    
    def test_length(self, sequence_header, transform_parameters, example_bitstream):
        a = bitstream.HQSliceArray(sequence_header, transform_parameters, 0, 0, 2)
        r = bitstream.BitstreamReader(BytesIO(example_bitstream))
        a.read(r)
        assert a.length == len(example_bitstream) * 8
    
    def test_hq_slice_view(self, sequence_header, transform_parameters):
        notify = MockNotificationTarget()
        a = bitstream.HQSliceArray(sequence_header, transform_parameters, 0, 0, 2)
        a._notify_on_change(notify)
        
        
        a._prefix_bytes = [b"\xAA", b"\xBB"]
        a._slice_y_length = [10, 20]
        a._slice_c1_length = [100, 200]
        a._slice_c2_length = [1000, 2000]
        a._y_block_padding = [10000, 20000]
        a._c1_block_padding = [100000, 200000]
        a._c2_block_padding = [1000000, 2000000]
        
        assert a[0].prefix_bytes == b"\xAA"
        assert a[1].prefix_bytes == b"\xBB"
        assert notify.notification_count == 0
        a[0].prefix_bytes = b"\xA0"
        assert notify.notification_count == 1
        a[1].prefix_bytes = b"\xB0"
        assert notify.notification_count == 2
        assert a._prefix_bytes == [b"\xA0", b"\xB0"]
        
        assert a[0].slice_y_length == 10
        assert a[1].slice_y_length == 20
        assert notify.notification_count == 2
        a[0].slice_y_length = 1
        assert notify.notification_count == 3
        a[1].slice_y_length = 2
        assert notify.notification_count == 4
        assert a._slice_y_length == [1, 2]
        
        assert a[0].slice_c1_length == 100
        assert a[1].slice_c1_length == 200
        assert notify.notification_count == 4
        a[0].slice_c1_length = 10
        assert notify.notification_count == 5
        a[1].slice_c1_length = 20
        assert notify.notification_count == 6
        assert a._slice_c1_length == [10, 20]
        
        assert a[0].slice_c2_length == 1000
        assert a[1].slice_c2_length == 2000
        assert notify.notification_count == 6
        a[0].slice_c2_length = 100
        assert notify.notification_count == 7
        a[1].slice_c2_length = 200
        assert notify.notification_count == 8
        assert a._slice_c2_length == [100, 200]
        
        assert a[0].y_block_padding == 10000
        assert a[1].y_block_padding == 20000
        assert notify.notification_count == 8
        a[0].y_block_padding = 1000
        assert notify.notification_count == 9
        a[1].y_block_padding = 2000
        assert notify.notification_count == 10
        assert a._y_block_padding == [1000, 2000]
        
        assert a[0].c1_block_padding == 100000
        assert a[1].c1_block_padding == 200000
        assert notify.notification_count == 10
        a[0].c1_block_padding = 10000
        assert notify.notification_count == 11
        a[1].c1_block_padding = 20000
        assert notify.notification_count == 12
        assert a._c1_block_padding == [10000, 20000]
        
        assert a[0].c2_block_padding == 1000000
        assert a[1].c2_block_padding == 2000000
        assert notify.notification_count == 12
        a[0].c2_block_padding = 100000
        assert notify.notification_count == 13
        a[1].c2_block_padding = 200000
        assert notify.notification_count == 14
        assert a._c2_block_padding == [100000, 200000]
    
    def test_hq_slice_view_str(self, sequence_header, transform_parameters, example_bitstream):
        a = bitstream.HQSliceArray(sequence_header, transform_parameters, 0, 0, 2)
        r = bitstream.BitstreamReader(BytesIO(example_bitstream))
        a.read(r)
        
        assert str(a[0]) == (
            "hq_slice(sx=0, sy=0):\n"
            "  prefix_bytes: 0xDE 0xAD\n"
            "  qindex: 10\n"
            "  slice_y_length: 3\n"
            "  y_coeffs:\n"
            "    Level 0, DC:\n"
            "      1  1  1  1\n"
            "      1  1  1  1\n"
            "      1  1  1  1\n"
            "      1  1  1  1\n"
            "    8 unused bits: 0b10000001\n"
            "  slice_c1_length: 2\n"
            "  c1_coeffs:\n"
            "    Level 0, DC:\n"
            "      7  7\n"
            "      7  7\n"
            "    16 unused bits: 0b1000000000000001\n"
            "  slice_c2_length: 2\n"
            "  c2_coeffs:\n"
            "    Level 0, DC:\n"
            "      -7  -7\n"
            "      -7  -7\n"
            "    16 unused bits: 0b1000000000000001"
        )
        
        # Remove prefix bytes
        transform_parameters["slice_parameters"]["slice_prefix_bytes"].value = 0
        
        assert str(a[0]) == (
            "hq_slice(sx=0, sy=0):\n"
            "  qindex: 10\n"
            "  slice_y_length: 3\n"
            "  y_coeffs:\n"
            "    Level 0, DC:\n"
            "      1  1  1  1\n"
            "      1  1  1  1\n"
            "      1  1  1  1\n"
            "      1  1  1  1\n"
            "    8 unused bits: 0b10000001\n"
            "  slice_c1_length: 2\n"
            "  c1_coeffs:\n"
            "    Level 0, DC:\n"
            "      7  7\n"
            "      7  7\n"
            "    16 unused bits: 0b1000000000000001\n"
            "  slice_c2_length: 2\n"
            "  c2_coeffs:\n"
            "    Level 0, DC:\n"
            "      -7  -7\n"
            "      -7  -7\n"
            "    16 unused bits: 0b1000000000000001"
        )
