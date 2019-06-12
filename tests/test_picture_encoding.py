import pytest

from copy import deepcopy

from vc2_conformance import tables

from vc2_conformance.arrays import new_array, width, height

from vc2_conformance.picture_decoding import (
    picture_decode,
    oned_synthesis,
    h_synthesis,
    vh_synthesis,
    idwt,
    offset_picture,
)

from vc2_conformance.picture_encoding import (
    picture_encode,
    oned_analysis,
    h_analysis,
    vh_analysis,
    dwt,
    dwt_pad_addition,
    remove_offset_picture,
)


def test_picture_encode_and_picture_decode_are_inverses():
    original_picture = {
        "Y": [
            [1, 2, 3],
            [101, 102, 103],
        ],
        "C1": [
            [4, 5],
        ],
        "C2": [
            [6, 7],
        ],
        "pic_num": 123,
    }
    state = {
        "luma_width": 3,
        "luma_height": 2,
        "color_diff_width": 2,
        "color_diff_height": 1,
        
        "luma_depth": 7,
        "color_diff_depth": 3,
        
        "wavelet_index": tables.WaveletFilters.haar_with_shift,
        "wavelet_index_ho": tables.WaveletFilters.haar_with_shift,
        "dwt_depth": 1,
        "dwt_depth_ho": 1,
        
        "picture_number": 123,
    }
    
    # Should encode into the 'state' variable
    picture_encode(state, deepcopy(original_picture))
    assert "current_picture" not in state
    assert "y_transform" in state
    assert "c1_transform" in state
    assert "c2_transform" in state
    
    # Should decode back out again
    decoded_picture = picture_decode(state)
    assert state["current_picture"] is decoded_picture
    assert decoded_picture == original_picture


################################################################################
# Wavelet transform
################################################################################

@pytest.mark.parametrize("filter_index", tables.WaveletFilters)
def test_oned_analysis_and_oned_synthesis_are_inverses(filter_index):
    A_orig = list(range(128))
    
    A = A_orig[:]
    oned_analysis(A, filter_index)
    assert A != A_orig
    
    oned_synthesis(A, filter_index)
    assert A == A_orig


@pytest.fixture
def two_d_array():
    """A 2D array of numbers for test purposes."""
    a = new_array(32, 16)
    for y in range(height(a)):
        for x in range(width(a)):
            a[y][x] = (y * 100) + x
    return a


@pytest.mark.parametrize("filter_index", tables.WaveletFilters)
def test_h_analysis_and_h_synthesis_are_inverses(filter_index, two_d_array):
    state = {
        "wavelet_index": filter_index,
        "wavelet_index_ho": filter_index,
    }
    
    L_data, H_data = h_analysis(state, deepcopy(two_d_array))
    data = h_synthesis(state, L_data, H_data)
    assert data == two_d_array


@pytest.mark.parametrize("filter_index", tables.WaveletFilters)
def test_vh_analysis_and_vh_synthesis_are_inverses(filter_index, two_d_array):
    state = {
        "wavelet_index": filter_index,
        "wavelet_index_ho": filter_index,
    }
    
    LL_data, HL_data, LH_data, HH_data = vh_analysis(state, deepcopy(two_d_array))
    data = vh_synthesis(state, LL_data, HL_data, LH_data, HH_data)
    assert data == two_d_array


@pytest.mark.parametrize("filter_index", tables.WaveletFilters)
@pytest.mark.parametrize("dwt_depth,dwt_depth_ho", [
    # No transform
    (0, 0),
    # 2D only
    (1, 0),
    (2, 0),
    # Horizontal only
    (0, 1),
    (0, 2),
    # Mixture
    (1, 1),
    (1, 2),
    (2, 1),
    (2, 2),
])
def test_dwt_and_idwt_are_inverses(filter_index, two_d_array, dwt_depth, dwt_depth_ho):
    state = {
        "wavelet_index": filter_index,
        "wavelet_index_ho": filter_index,
        "dwt_depth": dwt_depth,
        "dwt_depth_ho": dwt_depth_ho,
    }
    
    coeff_data = dwt(state, deepcopy(two_d_array))
    data = idwt(state, coeff_data)
    assert data == two_d_array

################################################################################
# Padding
################################################################################

def test_dwt_pad_addition():
    state = {
        "luma_width": 5,
        "luma_height": 3,
        "color_diff_width": 2,
        "color_diff_height": 3,
        
        "dwt_depth": 1,
        "dwt_depth_ho": 1,
    }
    
    # Should be expanded from 2x3 to a multiple of 4x2 = 4x4
    luma_pic = [
        [1, 2, 3, 4, 5],
        [11, 12, 13, 14, 15],
        [21, 22, 23, 24, 25],
    ]
    dwt_pad_addition(state, luma_pic, "Y")
    assert luma_pic == [
        [1, 2, 3, 4, 5, 5, 5, 5],
        [11, 12, 13, 14, 15, 15, 15, 15],
        [21, 22, 23, 24, 25, 25, 25, 25],
        [21, 22, 23, 24, 25, 25, 25, 25],
    ]
    
    # Should be expanded from 5x3 to a multiple of 4x2 = 8x4
    color_diff_pic = [
        [1, 2],
        [11, 12],
        [21, 22],
    ]
    dwt_pad_addition(state, color_diff_pic, "C1")
    assert color_diff_pic == [
        [1, 2, 2, 2],
        [11, 12, 12, 12],
        [21, 22, 22, 22],
        [21, 22, 22, 22],
    ]

################################################################################
# Offsetting
################################################################################

def test_offset_invertability():
    picture = {
        "Y": new_array(16, 8, 123),
        "C1": new_array(8, 4, 456),
        "C2": new_array(8, 4, 789),
    }
    state = {
        "luma_depth": 8,
        "color_diff_depth": 10,
    }
    
    remove_offset_picture(state, picture)
    assert picture["Y"][0][0] == 123 - 128
    assert picture["C1"][0][0] == 456 - 512
    assert picture["C2"][0][0] == 789 - 512
    
    offset_picture(state, picture)
    assert picture["Y"][0][0] == 123
    assert picture["C1"][0][0] == 456
    assert picture["C2"][0][0] == 789
