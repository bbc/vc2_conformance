import pytest

from fractions import Fraction

from vc2_conformance import tables

from vc2_conformance.decoder.transform_data_syntax import (
    quant_factor,
    inverse_quant,
)

from vc2_conformance.wavelet_filter_analysis.linexp import LinExp

from vc2_conformance.wavelet_filter_analysis.quantisation_matrices import (
    convert_between_synthesis_and_analysis,
)

import vc2_conformance.wavelet_filter_analysis.affine_arithmetic as aa

from vc2_conformance.wavelet_filter_analysis.infinite_arrays import (
    SymbolArray,
)

from vc2_conformance.wavelet_filter_analysis.bit_widths import (
    analysis_transform,
    synthesis_transform,
    make_coeff_arrays,
    non_error_coeffs,
    maximise_filter_output,
    minimise_filter_output,
    synthesis_filter_expression_bounds,
    analysis_filter_expression_bounds,
    minimum_signed_int_width,
    find_negative_input_free_synthesis_index,
    find_negative_input_free_analysis_index,
    worst_case_quantisation_error,
    maximum_useful_quantisation_index,
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
        
        # In this example, no quantisation is applied between the two
        # filters. As a consequence the rounding errors in the analysis and
        # synthesis filters exactly cancel out. As such the input and output
        # picture values should be identical.
        #
        # The bit shift between transform levels used by some filters
        # unfortunately exposes a limitation of the affine arithmetic approach.
        # Specifically, we know that the values fed to the inter-level bit
        # shift are always a multiple of two and so no rounding takes place.
        # The affine arithmetic, however, has no way to know this and so error
        # terms are introduced, one per transform level, ammounting to an
        # small over-estimate of the error bounds. We check that this is the
        # case.
        rounding_errors = output_picture[0, 0] - input_picture[0, 0]
        if exp_error:
            assert len(set(rounding_errors.symbols())) == dwt_depth + dwt_depth_ho
            assert -1 < aa.upper_bound(rounding_errors) < 1
            assert -1 < aa.lower_bound(rounding_errors) < 1
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
        
        assert coeff_arrays[0]["LL"][10, 20] == LinExp((("foo", 0, "LL"), 10, 20))
        
        assert coeff_arrays[1]["LH"][10, 20] == LinExp((("foo", 1, "LH"), 10, 20))
        assert coeff_arrays[1]["HL"][10, 20] == LinExp((("foo", 1, "HL"), 10, 20))
        assert coeff_arrays[1]["HH"][10, 20] == LinExp((("foo", 1, "HH"), 10, 20))
        
        assert coeff_arrays[2]["LH"][10, 20] == LinExp((("foo", 2, "LH"), 10, 20))
        assert coeff_arrays[2]["HL"][10, 20] == LinExp((("foo", 2, "HL"), 10, 20))
        assert coeff_arrays[2]["HH"][10, 20] == LinExp((("foo", 2, "HH"), 10, 20))
    
    def test_2d_and_1d(self):
        coeff_arrays = make_coeff_arrays(1, 2, "foo")
        
        assert set(coeff_arrays) == set([0, 1, 2, 3])
        
        assert set(coeff_arrays[0]) == set(["L"])
        assert set(coeff_arrays[1]) == set(["H"])
        assert set(coeff_arrays[2]) == set(["H"])
        assert set(coeff_arrays[3]) == set(["LH", "HL", "HH"])
        
        assert coeff_arrays[0]["L"][10, 20] == LinExp((("foo", 0, "L"), 10, 20))
        assert coeff_arrays[1]["H"][10, 20] == LinExp((("foo", 1, "H"), 10, 20))
        assert coeff_arrays[2]["H"][10, 20] == LinExp((("foo", 2, "H"), 10, 20))
        
        assert coeff_arrays[3]["LH"][10, 20] == LinExp((("foo", 3, "LH"), 10, 20))
        assert coeff_arrays[3]["HL"][10, 20] == LinExp((("foo", 3, "HL"), 10, 20))
        assert coeff_arrays[3]["HH"][10, 20] == LinExp((("foo", 3, "HH"), 10, 20))


def test_extract_coeffs():
    expr = (
        # Constant term
        1234 +
        # Error terms
        1 * aa.new_error_symbol() +
        2 * aa.new_error_symbol() +
        3 * aa.new_error_symbol() +
        # Non-error/constant terms
        Fraction(1, 2) * LinExp("a") +
        Fraction(1, -3) * LinExp("b") +
        4 * LinExp("c") +
        -5 * LinExp("d")
    )
    
    assert non_error_coeffs(expr) == {
        "a": Fraction(1, 2),
        "b": Fraction(1, -3),
        "c": 4,
        "d": -5,
    }


def test_maximise_filter_output():
    coeffs = {
        LinExp("a"): Fraction(1, 2),
        LinExp("b"): Fraction(-1, 2),
        LinExp("c"): 1,
        LinExp("d"): -1,
    }
    
    assert maximise_filter_output(coeffs, -10, 100) == {
        LinExp("a"): 100,
        LinExp("b"): -10,
        LinExp("c"): 100,
        LinExp("d"): -10,
    }


def test_minimise_filter_output():
    coeffs = {
        LinExp("a"): Fraction(1, 2),
        LinExp("b"): Fraction(-1, 2),
        LinExp("c"): 1,
        LinExp("d"): -1,
    }
    
    assert minimise_filter_output(coeffs, -10, 100) == {
        LinExp("a"): -10,
        LinExp("b"): 100,
        LinExp("c"): -10,
        LinExp("d"): 100,
    }


def test_analysis_filter_expression_bounds():
    p = SymbolArray(2, "p")
    expression = (
        30*p[0, 0] +
        -10*p[1, 0] +
        1*aa.new_error_symbol()
        -3*aa.new_error_symbol()
    )
    
    assert analysis_filter_expression_bounds(expression, (-1, 1000)) == (
        -30 - 10000 - 1 - 3,
        30000 + 10 + 1 + 3,
    )


def test_synthesis_filter_expression_bounds():
    coeff_arrays = make_coeff_arrays(0, 1)
    expression = (
        30*coeff_arrays[0]["L"][0, 0] +
        -10*coeff_arrays[1]["H"][0, 0] +
        1*aa.new_error_symbol()
        -3*aa.new_error_symbol()
    )
    
    coeff_value_ranges = {
        (0, "L"): (-1, 100),
        (1, "H"): (-10, 1000),
    }
    
    assert synthesis_filter_expression_bounds(expression, coeff_value_ranges) == (
        -30 - 10000 - 1 - 3,
        3000 + 100 + 1 + 3,
    )


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
    # Fractions are rounded away from zero
    (Fraction(30, 10), 3),
    (Fraction(31, 10), 4),
    (Fraction(-40, 10), 3),
    (Fraction(-41, 10), 4),
])
def test_minimum_signed_int_width(number, exp_bits):
    assert minimum_signed_int_width(number) == exp_bits


def test_find_negative_input_free_synthesis_index():
    # A non-Haar filter (which will always use some out-of-bounds coordinates
    # for the (0, 0) output)
    synthesis_filter = tables.LIFTING_FILTERS[tables.WaveletFilters.le_gall_5_3]
    
    # Asymmetric
    dwt_depth = 1
    dwt_depth_ho = 1
    
    coeff_arrays = make_coeff_arrays(dwt_depth, dwt_depth_ho)
    picture, intermediate_values = synthesis_transform(
        synthesis_filter,
        synthesis_filter,
        dwt_depth,
        dwt_depth_ho,
        coeff_arrays,
    )
    
    # The same filter as (0, 0), but at a wildly too-high coordinate
    x = 40
    y = 20
    
    x2, y2 = find_negative_input_free_synthesis_index(coeff_arrays, picture, x, y)
    
    # Make sure solution has no negative terms
    for _, cx, cy in non_error_coeffs(picture[x2, y2]):
        assert cx >= 0
        assert cy >= 0
    
    # Make sure no smaller coordinates are available
    for x3, y3 in [
        (x2 - picture.period[0], y2),
        (x2, y2 - picture.period[1]),
        (x2 - picture.period[0], y2 - picture.period[1]),
    ]:
        assert any(
            cx < 0 or cy < 0
            for _, cx, cy in non_error_coeffs(picture[x3, y3])
        )


def test_find_negative_input_free_analysis_index():
    # A non-Haar filter (which will always use some out-of-bounds coordinates
    # for the (0, 0) output)
    analysis_filter = convert_between_synthesis_and_analysis(
        tables.LIFTING_FILTERS[tables.WaveletFilters.le_gall_5_3]
    )
    
    # Asymmetric
    dwt_depth = 1
    dwt_depth_ho = 1
    
    picture = SymbolArray(2)
    coeff_arrays, intermediate_values = analysis_transform(
        analysis_filter,
        analysis_filter,
        dwt_depth,
        dwt_depth_ho,
        picture,
    )
    
    # Pick an intermediate value prior to final subsampling which ensures that
    # the period is not (1, 1) in the test
    coeff_array = intermediate_values[(2, "H''")]
    
    # The same filter as (0, 0), but at a wildly too-high coordinate
    x = 10
    y = 20
    
    x2, y2 = find_negative_input_free_analysis_index(picture, coeff_array, x, y)
    
    # Make sure solution has no negative terms
    for _, cx, cy in non_error_coeffs(coeff_array[x2, y2]):
        assert cx >= 0
        assert cy >= 0
    
    # Make sure no smaller coordinates are available
    for x3, y3 in [
        (x2 - coeff_array.period[0], y2),
        (x2, y2 - coeff_array.period[1]),
        (x2 - coeff_array.period[0], y2 - coeff_array.period[1]),
    ]:
        assert any(
            cx < 0 or cy < 0
            for _, cx, cy in non_error_coeffs(coeff_array[x3, y3])
        )



@pytest.mark.parametrize("quantisation_index", [
    # Indices with special case offsets
    0,
    1,
    # Remaining phases of multiples of four
    2,
    3,
    4,
    5,
    # Some larger indices (with all phases of multiples of four)
    20,
    21,
    22,
    23,
])
def test_worst_case_quantisation_error(quantisation_index):
    # Empirically determine the worst-case quantisation error and check it
    # matches the value found
    qf4 = quant_factor(quantisation_index)
    quantisation_errors = []
    for x in range(-1000, 1001):
        if x >= 0:
            quantised_x = (4*x) // qf4
        else:
            quantised_x = -((4*-x) // qf4)
        dequantised_x = inverse_quant(quantised_x, quantisation_index)
        quantisation_errors.append(dequantised_x - x)
    
    max_positive_error = max(quantisation_errors)
    max_negative_error = min(quantisation_errors)
    
    error_magnitude = worst_case_quantisation_error(quantisation_index)
    assert max_positive_error == error_magnitude
    assert max_negative_error == -error_magnitude

@pytest.mark.parametrize("value", [
    # The first ten quantisation factors
    1, 2, 3, 4, 5, 6, 8, 9, 11, 13,
    # Some non-quantisation-factor values
    14, 15,
    # A very large value to ensure runtime is actually logarithmic
    999999999999,
])
def test_maximum_useful_quantisation_index(value):
    # Empirically check that any lower quantisation index produces a non-zero
    # result
    index = maximum_useful_quantisation_index(value)
    
    def quantize(value, index):
        if value >= 0:
            return (4*value) // quant_factor(index)
        else:
            return -((4*-value) // quant_factor(index))
    
    assert quantize(value, index) == 0
    assert quantize(value, index-1) != 0
