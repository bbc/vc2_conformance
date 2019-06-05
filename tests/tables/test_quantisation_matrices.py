import pytest

from vc2_conformance.tables import (
    QUANTISATION_MATRICES,
    WaveletFilters,
)


def test_all_tables_have_valid_wavelets():
    for wavelet_index, wavelet_index_ho, _, _ in QUANTISATION_MATRICES:
        # Check is a known wavelet index
        WaveletFilters(wavelet_index)
        WaveletFilters(wavelet_index_ho)

def test_all_tables_have_correct_levels_and_orientations():
    for (_, _, dwt_depth, dwt_depth_ho), quantisation_matrix in QUANTISATION_MATRICES.items():
        # Should have only as many levels as the depth allows
        levels = sorted(quantisation_matrix.keys())
        assert levels == list(range(dwt_depth + dwt_depth_ho + 1))
        
        # Check the set of orientations is as expected for each level
        level_0 = sorted(quantisation_matrix[0].keys())
        if dwt_depth_ho == 0:
            assert level_0 == ["LL"]
        else:
            assert level_0 == ["L"]
            for ho_level in range(1, dwt_depth_ho + 1):
                assert sorted(quantisation_matrix[ho_level]) == ["H"]
        for level in range(dwt_depth_ho + 1, dwt_depth_ho + dwt_depth + 1):
            assert sorted(quantisation_matrix[level]) == ["HH", "HL", "LH"]
