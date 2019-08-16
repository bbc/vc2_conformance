import pytest

import sympy

from vc2_conformance import tables

from vc2_conformance.wavelet_filter_analysis.quantisation_matrices import (
    convert_between_synthesis_and_analysis,
)

from vc2_conformance.wavelet_filter_analysis.symbolic_error_terms import (
    new_error_term,
    strip_error_terms,
    upper_error_bound,
)

from vc2_conformance.wavelet_filter_analysis.infinite_arrays import (
    SymbolArray,
)

from vc2_conformance.wavelet_filter_analysis.bit_widths import (
    analysis_transform,
    synthesis_transform,
    make_coeff_arrays,
    extract_coeffs,
    maximise_filter_output,
    minimise_filter_output,
    minimum_signed_int_width,
)

class TestAnalysisAndSynthesisTransforms(object):

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
    def test_filters_invert_eachother(self, wavelet_index, wavelet_index_ho, dwt_depth, dwt_depth_ho, exp_error):
        # Test that the analysis and synthesis filters invert each-other as a
        # check of consistency (and, indirectly, the correctness of the
        # analysis implementation)
        
        h_sf = tables.LIFTING_FILTERS[wavelet_index_ho]
        v_sf = tables.LIFTING_FILTERS[wavelet_index]
        
        h_af = convert_between_synthesis_and_analysis(h_sf)
        v_af = convert_between_synthesis_and_analysis(v_sf)
        
        input_picture = SymbolArray(2, "p")
        
        transform_coeffs, _ = analysis_transform(
            h_af,
            v_af,
            dwt_depth,
            dwt_depth_ho,
            input_picture,
        )
        output_picture, _ = synthesis_transform(
            h_sf,
            v_sf,
            dwt_depth,
            dwt_depth_ho,
            transform_coeffs,
        )
        
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
            upper_bound = upper_error_bound(output_picture[0, 0] - input_picture[0, 0])
            
            assert 0 <= rounding_errors <= upper_bound
        else:
            assert rounding_errors == 0
    
    @pytest.mark.parametrize("dwt_depth,dwt_depth_ho", [
        (0, 0),
        (1, 0),
        (2, 0),
        (0, 1),
        (0, 2),
        (1, 1),
        (2, 2),
    ])
    def test_analysis_intermediate_steps_as_expected(self, dwt_depth, dwt_depth_ho):
        filter_params = convert_between_synthesis_and_analysis(
            tables.LIFTING_FILTERS[tables.WaveletFilters.haar_with_shift]
        )
        
        input_picture = SymbolArray(2, "p")
        
        _, intermediate_values = analysis_transform(
            filter_params,
            filter_params,
            dwt_depth,
            dwt_depth_ho,
            input_picture,
        )
        
        # 2D stages have all expected values
        for level in range(dwt_depth_ho + 1, dwt_depth + dwt_depth_ho + 1):
            names = set(n for l, n in intermediate_values if l == level)
            assert names == set([
                "Input",
                "DC",
                "DC'",
                "DC''",
                "L",
                "L'",
                "L''",
                "H",
                "H'",
                "H''",
                "LL",
                "LH",
                "HL",
                "HH",
            ])
        
        # HO stages have all expected values
        for level in range(1, dwt_depth_ho + 1):
            names = set(n for l, n in intermediate_values if l == level)
            assert names == set([
                "Input",
                "DC",
                "DC'",
                "DC''",
                "L",
                "H",
            ])
    
    @pytest.mark.parametrize("dwt_depth,dwt_depth_ho", [
        (0, 0),
        (1, 0),
        (2, 0),
        (0, 1),
        (0, 2),
        (1, 1),
        (2, 2),
    ])
    def test_synthesis_intermediate_steps_as_expected(self, dwt_depth, dwt_depth_ho):
        filter_params = tables.LIFTING_FILTERS[tables.WaveletFilters.haar_with_shift]
        
        transform_coeffs = make_coeff_arrays(dwt_depth, dwt_depth_ho)
        
        _, intermediate_values = synthesis_transform(
            filter_params,
            filter_params,
            dwt_depth,
            dwt_depth_ho,
            transform_coeffs,
        )
        
        # 2D stages have all expected values
        for level in range(dwt_depth_ho + 1, dwt_depth + dwt_depth_ho + 1):
            names = set(n for l, n in intermediate_values if l == level)
            assert names == set([
                "LL",
                "LH",
                "HL",
                "HH",
                "L''",
                "L'",
                "L",
                "H''",
                "H'",
                "H",
                "DC''",
                "DC'",
                "DC",
                "Output",
            ])
        
        # HO stages have all expected values
        for level in range(1, dwt_depth_ho + 1):
            names = set(n for l, n in intermediate_values if l == level)
            assert names == set([
                "L",
                "H",
                "DC''",
                "DC'",
                "DC",
                "Output",
            ])


class TestMakeCoeffArrays(object):
    
    def test_2d_only(self):
        coeff_arrays = make_coeff_arrays(2, 0, "foo")
        
        assert set(coeff_arrays) == set([0, 1, 2])
        
        assert set(coeff_arrays[0]) == set(["LL"])
        assert set(coeff_arrays[1]) == set(["LH", "HL", "HH"])
        assert set(coeff_arrays[2]) == set(["LH", "HL", "HH"])
        
        assert coeff_arrays[0]["LL"][10, 20].name == "foo_0_LL_10_20"
        
        assert coeff_arrays[1]["LH"][10, 20].name == "foo_1_LH_10_20"
        assert coeff_arrays[1]["HL"][10, 20].name == "foo_1_HL_10_20"
        assert coeff_arrays[1]["HH"][10, 20].name == "foo_1_HH_10_20"
        
        assert coeff_arrays[2]["LH"][10, 20].name == "foo_2_LH_10_20"
        assert coeff_arrays[2]["HL"][10, 20].name == "foo_2_HL_10_20"
        assert coeff_arrays[2]["HH"][10, 20].name == "foo_2_HH_10_20"
    
    def test_2d_and_1d(self):
        coeff_arrays = make_coeff_arrays(1, 2, "foo")
        
        assert set(coeff_arrays) == set([0, 1, 2, 3])
        
        assert set(coeff_arrays[0]) == set(["L"])
        assert set(coeff_arrays[1]) == set(["H"])
        assert set(coeff_arrays[2]) == set(["H"])
        assert set(coeff_arrays[3]) == set(["LH", "HL", "HH"])
        
        assert coeff_arrays[0]["L"][10, 20].name == "foo_0_L_10_20"
        assert coeff_arrays[1]["H"][10, 20].name == "foo_1_H_10_20"
        assert coeff_arrays[2]["H"][10, 20].name == "foo_2_H_10_20"
        
        assert coeff_arrays[3]["LH"][10, 20].name == "foo_3_LH_10_20"
        assert coeff_arrays[3]["HL"][10, 20].name == "foo_3_HL_10_20"
        assert coeff_arrays[3]["HH"][10, 20].name == "foo_3_HH_10_20"


def test_extract_coeffs():
    expr = (
        # Constant term
        1234 +
        # Error terms
        1 * new_error_term() +
        2 * new_error_term() +
        3 * new_error_term() +
        # Non-error/constant terms
        sympy.Rational(1, 2) * sympy.abc.a +
        sympy.Rational(1, -3) * sympy.abc.b +
        4 * sympy.abc.c +
        -5 * sympy.abc.d
    )
    
    assert extract_coeffs(expr) == {
        sympy.abc.a: sympy.Rational(1, 2),
        sympy.abc.b: sympy.Rational(1, -3),
        sympy.abc.c: 4,
        sympy.abc.d: -5,
    }


def test_maximise_filter_output():
    coeffs = {
        sympy.abc.a: sympy.Rational(1, 2),
        sympy.abc.b: sympy.Rational(-1, 2),
        sympy.abc.c: 1,
        sympy.abc.d: -1,
    }
    
    assert maximise_filter_output(coeffs, -10, 100) == {
        sympy.abc.a: 100,
        sympy.abc.b: -10,
        sympy.abc.c: 100,
        sympy.abc.d: -10,
    }


def test_minimise_filter_output():
    coeffs = {
        sympy.abc.a: sympy.Rational(1, 2),
        sympy.abc.b: sympy.Rational(-1, 2),
        sympy.abc.c: 1,
        sympy.abc.d: -1,
    }
    
    assert minimise_filter_output(coeffs, -10, 100) == {
        sympy.abc.a: -10,
        sympy.abc.b: 100,
        sympy.abc.c: -10,
        sympy.abc.d: 100,
    }


@pytest.mark.parametrize("number,exp_bits", [
    # Zero
    (0, 0),
    # Positive integers
    (1, 2),
    (2, 3), (3, 3),
    (4, 4), (5, 4), (6, 4), (7, 4),
    (8, 5), (9, 5), (10, 5), (11, 5), (12, 5), (13, 5), (14, 5), (15, 5),
    (16, 6),
    # Negative integers
    (-1, 1),
    (-2, 2),
    (-3, 3), (-4, 3),
    (-5, 4), (-6, 4), (-7, 4), (-8, 4),
    (-9, 5), (-10, 5), (-11, 5), (-12, 5), (-13, 5), (-14, 5), (-15, 5), (-16, 5),
    (-17, 6),
    # Floats are rounded away from zero
    (3.0, 3),
    (3.1, 4),
    (-4.0, 3),
    (-4.1, 4),
    # Sympy values are rounded away from zero
    (sympy.Rational(30, 10), 3),
    (sympy.Rational(31, 10), 4),
    (sympy.Rational(-40, 10), 3),
    (sympy.Rational(-41, 10), 4),
])
def test_minimum_signed_int_width(number, exp_bits):
    assert minimum_signed_int_width(number) == exp_bits
