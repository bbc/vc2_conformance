import pytest

from mock import Mock

import random

import sympy

from vc2_conformance import tables

from vc2_conformance.picture_decoding import SYNTHESIS_LIFTING_FUNCTION_TYPES

from vc2_conformance.wavelet_filter_analysis.quantisation_matrices import (
    convert_between_synthesis_and_analysis,
)

from vc2_conformance.wavelet_filter_analysis.infinite_filters import (
    new_error_term,
    strip_error_terms,
    worst_case_error_bounds,
    InfiniteArray,
    SymbolArray,
    SubsampledArray,
    InterleavedArray,
    LiftedArray,
    RightShiftedArray,
    LeftShiftedArray,
    dwt,
    idwt,
)

def test_new_error_term():
    e1 = new_error_term()
    e2 = new_error_term()
    
    assert e1 - e2 != 0
    assert e1.name.startswith("e_")
    assert e2.name.startswith("e_")


@pytest.mark.parametrize("expr_in,expr_out", [
    # Pure number (not a sympy type)
    (123, 123),
    # Number and (scaled) error terms
    (123 + new_error_term(), 123),
    (123 - new_error_term(), 123),
    (123 + 2*new_error_term(), 123),
    (123 - 3*new_error_term(), 123),
    # Numbers and non-error symbols
    (123 + 2*sympy.abc.a + new_error_term(), 123 + 2*sympy.abc.a),
])
def test_strip_error_terms(expr_in, expr_out):
    assert strip_error_terms(expr_in) == expr_out


@pytest.mark.parametrize("expr_in,lower,upper", [
    # Pure number (not a sympy type)
    (0, 0, 0),
    (123, 123, 123),
    # Single error
    (new_error_term(), 0, 1),
    (-new_error_term(), -1, 0),
    # Scaled error
    (3*new_error_term(), 0, 3),
    (-3*new_error_term(), -3, 0),
    # Several errors
    (3*new_error_term() + 2*new_error_term(), 0, 5),
    (3*new_error_term() - 2*new_error_term(), -2, 3),
    # Errors and other values
    (sympy.abc.a + 5 + 3*new_error_term(), sympy.abc.a + 5, sympy.abc.a + 8),
])
def test_worst_case_error_bounds(expr_in, lower, upper):
    assert worst_case_error_bounds(expr_in) == (lower, upper)


class TestInfiniteArray(object):

    def test_ndim_property(self):
        assert InfiniteArray(123).ndim == 123
    
    class MyArray(InfiniteArray):
        def __init__(self, *args, **kwargs):
            self._last_id = 0
            super(TestInfiniteArray.MyArray, self).__init__(*args, **kwargs)
        
        def get(self, key):
            self._last_id += 1
            return (key, self._last_id)
    
    def test_1d_index(self):
        a = self.MyArray(1)
        assert a[100] == ((100, ), 1)
        assert a[(200, )] == ((200, ), 2)
        assert a[300, ] == ((300, ), 3)
    
    def test_3d_index(self):
        a = self.MyArray(3)
        assert a[1, 2, 3] == ((1, 2, 3), 1)
    
    def test_incorrect_dimensions(self):
        a = self.MyArray(2)
        
        with pytest.raises(TypeError):
            a[1, 2, 3]
        with pytest.raises(TypeError):
            a[1]
    
    def test_caching(self):
        a = self.MyArray(2)
        assert a[10, 20] == ((10, 20), 1)
        assert a[10, 20] == ((10, 20), 1)
        assert a[20, 10] == ((20, 10), 2)
        assert a[10, 20] == ((10, 20), 1)
        assert a[20, 10] == ((20, 10), 2)


def test_symbol_array():
    a = SymbolArray(3, "foo")
    
    foo_0_0_0 = a[0, 0, 0]
    assert foo_0_0_0.name == "foo_0_0_0"
    
    foo_1_2_3 = a[1, 2, 3]
    assert foo_1_2_3.name == "foo_1_2_3"
    
    foo__1__2__3 = a[-1, -2, -3]
    assert foo__1__2__3.name == "foo_-1_-2_-3"


class TestSubsampledArray(object):
    
    @pytest.mark.parametrize("steps,offsets", [
        # Too short
        ((1, 2), (1, 2, 3)),
        ((1, 2, 3), (1, 2)),
        ((1, 2), (1, 2)),
        # Too long
        ((1, 2, 3, 4), (1, 2, 3)),
        ((1, 2, 3), (1, 2, 3, 4)),
        ((1, 2, 3, 4), (1, 2, 3, 4)),
    ])
    def test_bad_arguments(self, steps, offsets):
        a = SymbolArray(3, "v")
        with pytest.raises(TypeError):
            SubsampledArray(a, steps, offsets)
    
    def test_subsampling(self):
        a = SymbolArray(3, "v")
        s = SubsampledArray(a, (1, 2, 3), (0, 10, 20))
        
        assert s[0, 0, 0].name == "v_0_10_20"
        
        assert s[1, 0, 0].name == "v_1_10_20"
        assert s[0, 1, 0].name == "v_0_12_20"
        assert s[0, 0, 1].name == "v_0_10_23"
        
        assert s[2, 2, 2].name == "v_2_14_26"


class TestInterleavedArray(object):
    
    def test_mismatched_array_dimensions(self):
        a = SymbolArray(2, "a")
        b = SymbolArray(3, "b")
        
        with pytest.raises(TypeError):
            InterleavedArray(a, b, 0)
    
    def test_interleave_dimension_out_of_range(self):
        a = SymbolArray(2, "a")
        b = SymbolArray(2, "b")
        
        with pytest.raises(TypeError):
            InterleavedArray(a, b, 2)
    
    def test_interleave(self):
        a = SymbolArray(2, "a")
        b = SymbolArray(2, "b")
        
        # 'Horizontal'
        i = InterleavedArray(a, b, 0)
        assert i[-2, 0].name == "a_-1_0"
        assert i[-1, 0].name == "b_-1_0"
        assert i[0, 0].name == "a_0_0"
        assert i[1, 0].name == "b_0_0"
        assert i[2, 0].name == "a_1_0"
        assert i[3, 0].name == "b_1_0"
        
        assert i[0, 1].name == "a_0_1"
        assert i[1, 1].name == "b_0_1"
        assert i[2, 1].name == "a_1_1"
        assert i[3, 1].name == "b_1_1"
        
        # 'Vertical'
        i = InterleavedArray(a, b, 1)
        assert i[0, -2].name == "a_0_-1"
        assert i[0, -1].name == "b_0_-1"
        assert i[0, 0].name == "a_0_0"
        assert i[0, 1].name == "b_0_0"
        assert i[0, 2].name == "a_0_1"
        assert i[0, 3].name == "b_0_1"
        
        assert i[1, 0].name == "a_1_0"
        assert i[1, 1].name == "b_1_0"
        assert i[1, 2].name == "a_1_1"
        assert i[1, 3].name == "b_1_1"


class TestLiftedArray(object):
    
    @pytest.fixture(params=list(tables.LiftingFilterTypes))
    def stage(self, request):
        """A highly asymmetrical (if contrived) filter stage."""
        return tables.LiftingStage(
            lift_type=request.param,
            S=3,
            L=5,
            D=-3,
            taps=[1000, -2000, 3000, -4000, 5000],
        )
    
    def test_filter_dimension_out_of_range(self, stage):
        a = SymbolArray(2, "a")
        with pytest.raises(TypeError):
            LiftedArray(a, stage, 2)
    
    def test_correctness(self, stage):
        # This test checks that the filter implemented is equivalent to what
        # the VC-2 pseudocode would do
        a = SymbolArray(2, "a")
        l = LiftedArray(a, stage, 0)
        
        # Run the pseudocode against a random input
        rand = random.Random(0)
        input_array = [rand.randint(0, 10000) for _ in range(20)]
        pseudocode_output_array = input_array[:]
        lift = SYNTHESIS_LIFTING_FUNCTION_TYPES[stage.lift_type]
        lift(pseudocode_output_array, stage.L, stage.D, stage.taps, stage.S)
        
        # Check that the symbolic version gets the same answers (modulo
        # rounding errors). Check at output positions which are not affected by
        # rounding errors.
        for index in [10, 11]:
            pseudocode_output = pseudocode_output_array[index]
            
            # Substitute in the random inputs into symbolic answer
            output = l[index, 123].subs({
                sympy.Symbol("a_{}_123".format(i)): value
                for i, value in enumerate(input_array)
            })
            
            lower_bound, upper_bound = worst_case_error_bounds(output)
            
            assert (
                lower_bound <= pseudocode_output <= upper_bound
            )


def test_right_shifted_array():
    a = SymbolArray(3, "foo")
    sa = RightShiftedArray(a, 3)
    
    v = a[1, 2, 3]
    
    sv = sa[1, 2, 3]
    
    sv_no_error = strip_error_terms(sv)
    sv_error = sv - sv_no_error
    
    error_symbol = next(iter(sv_error.free_symbols))
    
    assert sv_no_error == (v + 4) / 8
    assert sv_error == -error_symbol


def test_left_shifted_array():
    a = SymbolArray(3, "foo")
    sa = LeftShiftedArray(a, 3)
    
    v = a[1, 2, 3]
    
    assert sa[1, 2, 3] == v * 8


def test_dwt_and_idwt():
    # Test that the analysis and synthesis filters invert each-other as a check
    # of consistency (if not correctness)
    
    # Specifically chosen so that only the horizontal transform requests a
    # shift.
    h_sf = tables.LIFTING_FILTERS[tables.WaveletFilters.le_gall_5_3]
    v_sf = tables.LIFTING_FILTERS[tables.WaveletFilters.haar_no_shift]
    
    h_af = convert_between_synthesis_and_analysis(h_sf)
    v_af = convert_between_synthesis_and_analysis(v_sf)
    
    dwt_depth = 2
    dwt_depth_ho = 1
    
    input_picture = SymbolArray(2, "p")
    
    transform_coeffs = dwt(h_af, v_af, dwt_depth, dwt_depth_ho, input_picture)
    output_picture = idwt(h_sf, v_sf, dwt_depth, dwt_depth_ho, transform_coeffs)
    
    # Once error and the decoded pixel have been removed, all we should be left
    # with is a small constant. This constant term comes from the bit shift
    # between transform levels where an offset is introduced which would
    # normally be truncated away but remains in the symbolic arithmetic,
    rounding_errors = strip_error_terms(output_picture[0, 0]) - input_picture[0, 0]
    assert rounding_errors.free_symbols == set()
    
    # The 'rounding error' due to the lack of truncation in symbolic arithmetic
    # will be bounded by the error terms in the final result. Since in this
    # instance we know the only source of error is the added fractional value,
    # only positive error terms are relevant.
    upper_bound = worst_case_error_bounds(output_picture[0, 0] - input_picture[0, 0])[1]
    
    assert 0 <= rounding_errors <= upper_bound

