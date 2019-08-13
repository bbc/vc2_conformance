import pytest

from vc2_conformance import tables

from vc2_conformance.wavelet_filter_analysis.quantisation_matrices import (
    convert_between_synthesis_and_analysis,
)

from vc2_conformance.wavelet_filter_analysis.symbolic_error_terms import (
    strip_error_terms,
    worst_case_error_bounds,
)

from vc2_conformance.wavelet_filter_analysis.infinite_arrays import (
    SymbolArray,
)

from vc2_conformance.wavelet_filter_analysis.bit_widths import (
    idwt,
    dwt,
)

class TestVC2FilterImplementations(object):

    @pytest.mark.parametrize("wavelet_index,wavelet_index_ho,dwt_depth,dwt_depth_ho,exp_error", [
        # Check that when no shifting occurs, no constant error exists
        # (since all other rounding errors should cancel out due to lifting)
        (
            tables.WaveletFilters.haar_no_shift,
            tables.WaveletFilters.haar_no_shift,
            1,
            2,
            False,
        ),
        # Check:
        # * Asymmetric transforms
        # * Differing horizontal and vertical transform depths
        # * Bit shift is taken from the correct filter
        # * Remaining error terms which are normally cancelled during
        #   bit-shifts are within the predicted bounds
        (
            tables.WaveletFilters.haar_no_shift,  # Vertical only
            tables.WaveletFilters.le_gall_5_3,  # Horizontal only
            1,
            2,
            True,
        ),
    ])
    def test_idwt_inverts_dwt(self, wavelet_index, wavelet_index_ho, dwt_depth, dwt_depth_ho, exp_error):
        # Test that the analysis and synthesis filters invert each-other as a
        # check of consistency (and, indirectly, the correctness of the DWT
        # implementation)
        
        h_sf = tables.LIFTING_FILTERS[wavelet_index_ho]
        v_sf = tables.LIFTING_FILTERS[wavelet_index]
        
        h_af = convert_between_synthesis_and_analysis(h_sf)
        v_af = convert_between_synthesis_and_analysis(v_sf)
        
        input_picture = SymbolArray(2, "p")
        
        transform_coeffs = dwt(h_af, v_af, dwt_depth, dwt_depth_ho, input_picture)
        output_picture = idwt(h_sf, v_sf, dwt_depth, dwt_depth_ho, transform_coeffs)
        
        rounding_errors = strip_error_terms(output_picture[0, 0]) - input_picture[0, 0]
        
        if exp_error:
            # Once error and the decoded pixel have been removed, all we should be left
            # with is a small constant. This constant term comes from the bit shift
            # between transform levels where an offset is introduced which would
            # normally be truncated away but remains in the symbolic arithmetic,
            assert rounding_errors.free_symbols == set()
            
            # The 'rounding error' due to the lack of truncation in symbolic arithmetic
            # will be bounded by the error terms in the final result. Since in this
            # instance we know the only source of error is the added fractional value,
            # only positive error terms are relevant.
            upper_bound = worst_case_error_bounds(output_picture[0, 0] - input_picture[0, 0])[1]
            
            assert 0 <= rounding_errors <= upper_bound
        else:
            assert rounding_errors == 0
