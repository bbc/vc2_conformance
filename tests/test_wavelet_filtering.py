import pytest

from copy import deepcopy

from vc2_conformance import tables

from vc2_conformance.arrays import new_array, width, height

from vc2_conformance.wavelet_filtering import (
    oned_synthesis,
    oned_analysis,
    h_synthesis,
    h_analysis,
    vh_synthesis,
    vh_analysis,
    idwt,
    dwt,
)


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
