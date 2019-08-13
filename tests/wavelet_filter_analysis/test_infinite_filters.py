import pytest

from mock import Mock

import random

import sympy

from itertools import combinations_with_replacement, product

from vc2_conformance import tables

from vc2_conformance.picture_decoding import SYNTHESIS_LIFTING_FUNCTION_TYPES

from vc2_conformance.wavelet_filter_analysis.quantisation_matrices import (
    convert_between_synthesis_and_analysis,
)

from vc2_conformance.wavelet_filter_analysis.infinite_filters import (
    lcm,
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


@pytest.mark.parametrize("a,b,exp", [
    # a==b
    (1, 1, 1),  # Ones
    (7, 7, 7),  # Prime
    (10, 10, 10),  # Non-prime
    # a!=b where one or both numbers are prime
    (1, 7, 7),
    (7, 1, 7),
    (3, 7, 21),
    (7, 3, 21),
    # a!=b where one number is prime
    (2, 5, 10),
    (5, 2, 10),
    (10, 5, 10),
    (5, 10, 10),
    # a!=b where both numbers share a common factor
    (10, 15, 30),
    (15, 10, 30),
])
def test_lcm(a, b, exp):
    assert lcm(a, b) == exp


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
    
    assert a.period == (1, 1, 1)
    
    foo_0_0_0 = a[0, 0, 0]
    assert foo_0_0_0.name == "foo_0_0_0"
    
    foo_1_2_3 = a[1, 2, 3]
    assert foo_1_2_3.name == "foo_1_2_3"
    
    foo__1__2__3 = a[-1, -2, -3]
    assert foo__1__2__3.name == "foo_-1_-2_-3"


class RepeatingSymbolArray(SymbolArray):
    """
    A :py:class:`SymbolArray` used in tests which repeats the same symbols with
    a specified period.
    """
    def __init__(self, period, prefix="v"):
        self._period = period
        super(RepeatingSymbolArray, self).__init__(len(self._period), prefix)
    
    def get(self, key):
        key = tuple(
            k % p
            for k, p in zip(key, self.period)
        )
        return super(RepeatingSymbolArray, self).get(key)
    
    @property
    def period(self):
        return self._period


def test_repeating_symbol_array():
    a = RepeatingSymbolArray((3, 2))
    
    assert a.ndim == 2
    assert a.period == (3, 2)
    
    assert len(set(
        a[x, y]
        for x in range(3)
        for y in range(2)
    )) == 3 * 2
    
    for x in range(3):
        for y in range(2):
            assert a[x, y] == a[x+3, y]
            assert a[x, y] == a[x, y+2]
            assert a[x, y] == a[x+3, y+2]


def period_empirically_correct(a):
    """
    Empirically verify the period a particular array claims to have.
    
    Checks that expected repeats are literal repeated values (minus differing
    error terms).
    """
    last_values = None
    # Get the hyper-cube block of values which sample the complete period
    # of the array at various period-multiple offsets
    for offset_steps in combinations_with_replacement([-1, 0, 1, 2], a.ndim):
        offset = tuple(
            step * period
            for step, period in zip(offset_steps, a.period)
        )
        values = [
            strip_error_terms(a[tuple(c + o for c, o in zip(coord, offset))])
            for coord in product(*(range(d) for d in a.period))
        ]
        
        # Every set of values should be identical
        if last_values is not None and values != last_values:
            return False
        
        last_values = values
    
    return True


def test_period_empirically_correct():
    a = RepeatingSymbolArray((2, 3))
    assert period_empirically_correct(a)
    
    a._period = (3, 2)  # Naughty!
    assert not period_empirically_correct(a)


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
    
    @pytest.mark.parametrize("input_period,dim,exp_period", [
        # Examples illustrated in the comments
        ((1, ), 0, (2, )),
        ((2, ), 0, (2, )),
        ((4, ), 0, (4, )),
        ((3, ), 0, (6, )),
        # Multiple-dimensions
        ((1, 2, 3), 0, (2, 2, 3)),
        ((1, 2, 3), 1, (1, 2, 3)),
        ((1, 2, 3), 2, (1, 2, 6)),
    ])
    def test_period(self, input_period, dim, exp_period, stage):
        a = RepeatingSymbolArray(input_period)
        l = LiftedArray(a, stage, dim)
        assert l.period == exp_period
        assert period_empirically_correct(l)


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
    
    @pytest.mark.parametrize("input_period,steps,exp_period", [
        # Examples illustrated in the comments
        ((2, ), (2, ), (1, )),
        ((3, ), (2, ), (3, )),
        # Multiple dimensions
        ((1, 2, 3), (3, 2, 1), (1, 1, 3)),
    ])
    def test_period(self, input_period, steps, exp_period):
        a = RepeatingSymbolArray(input_period)
        s = SubsampledArray(a, steps, (0, )*len(steps))
        assert s.period == exp_period
        assert period_empirically_correct(s)


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
    
    @pytest.mark.parametrize("input_a_period,input_b_period,dim,exp_period", [
        # Examples illustrated in the comments
        ((1, ), (2, ), 0, (4, )),
        ((2, ), (3, ), 0, (12, )),
        ((2, 1), (3, 1), 1, (6, 2)),
    ])
    def test_period(self, input_a_period, input_b_period, dim, exp_period):
        a = RepeatingSymbolArray(input_a_period, "a")
        b = RepeatingSymbolArray(input_b_period, "b")
        i = InterleavedArray(a, b, dim)
        assert i.period == exp_period
        assert period_empirically_correct(i)


class TestRightShiftedArray(object):
    
    def test_shifting(self):
        a = SymbolArray(3, "foo")
        sa = RightShiftedArray(a, 3)
        
        v = a[1, 2, 3]
        
        sv = sa[1, 2, 3]
        
        sv_no_error = strip_error_terms(sv)
        sv_error = sv - sv_no_error
        
        error_symbol = next(iter(sv_error.free_symbols))
        
        assert sv_no_error == (v + 4) / 8
        assert sv_error == -error_symbol
    
    def test_period(self):
        a = RepeatingSymbolArray((1, 2, 3))
        sa = RightShiftedArray(a, 3)
        assert sa.period == (1, 2, 3)
        assert period_empirically_correct(sa)


class TestLeftShiftedArray(object):

    def test_left_shifted_array(self):
        a = SymbolArray(3, "foo")
        sa = LeftShiftedArray(a, 3)
        
        v = a[1, 2, 3]
        
        assert sa[1, 2, 3] == v * 8
    
    def test_period(self):
        a = RepeatingSymbolArray((1, 2, 3))
        sa = LeftShiftedArray(a, 3)
        assert sa.period == (1, 2, 3)
        assert period_empirically_correct(sa)


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

