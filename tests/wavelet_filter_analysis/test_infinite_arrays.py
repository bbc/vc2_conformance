import pytest

import random

from fractions import Fraction

from itertools import combinations_with_replacement, product

import vc2_data_tables as tables

from vc2_conformance.picture_decoding import SYNTHESIS_LIFTING_FUNCTION_TYPES

from vc2_conformance.wavelet_filter_analysis.linexp import LinExp

import vc2_conformance.wavelet_filter_analysis.affine_arithmetic as aa

from vc2_conformance.wavelet_filter_analysis.infinite_arrays import (
    lcm,
    InfiniteArray,
    SymbolArray,
    SubsampledArray,
    InterleavedArray,
    LiftedArray,
    RightShiftedArray,
    LeftShiftedArray,
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
    assert a.relative_step_size_to(a) == (1, 1, 1)
    assert a.relative_step_size_to(SymbolArray(2, "bar")) is None
    
    assert a[0, 0, 0] == LinExp(("foo", 0, 0, 0))
    
    assert a[1, 2, 3] == LinExp(("foo", 1, 2, 3))


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
            # Since error terms will always be different, consider the
            # lower-bound case arbitrarily in order to make a fair comparison.
            aa.lower_bound(a[tuple(c + o for c, o in zip(coord, offset))])
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
                ("a", i, 123): value
                for i, value in enumerate(input_array)
            })
            
            lower_bound = aa.lower_bound(output)
            upper_bound = aa.upper_bound(output)
            
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
    
    def test_relative_step_size_to(self, stage):
        a = SymbolArray(2)
        s = SubsampledArray(a, (2, 3), (0, 0))
        l = LiftedArray(s, stage, 0)
        
        assert l.relative_step_size_to(a) == (2, 3)
        assert l.relative_step_size_to(l) == (1, 1)
        assert l.relative_step_size_to(SymbolArray(2, "nope")) is None


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
        
        assert s[0, 0, 0] == LinExp(("v", 0, 10, 20))
        
        assert s[1, 0, 0] == LinExp(("v", 1, 10, 20))
        assert s[0, 1, 0] == LinExp(("v", 0, 12, 20))
        assert s[0, 0, 1] == LinExp(("v", 0, 10, 23))
        
        assert s[2, 2, 2] == LinExp(("v", 2, 14, 26))
    
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
    
    def test_relative_step_size_to(self):
        a = SymbolArray(3)
        
        s1 = SubsampledArray(a, (1, 2, 3), (4, 5, 6))
        assert s1.relative_step_size_to(a) == (1, 2, 3)
        assert s1.relative_step_size_to(s1) == (1, 1, 1)
        assert s1.relative_step_size_to(SymbolArray(3, "nope")) is None
        
        s2 = SubsampledArray(s1, (11, 22, 33), (4, 5, 6))
        assert s2.relative_step_size_to(a) == (11*1, 22*2, 33*3)
        assert s2.relative_step_size_to(s1) == (11, 22, 33)
        assert s2.relative_step_size_to(s2) == (1, 1, 1)


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
        assert i[-2, 0] == ("a", -1, 0)
        assert i[-1, 0] == ("b", -1, 0)
        assert i[0, 0] == ("a", 0, 0)
        assert i[1, 0] == ("b", 0, 0)
        assert i[2, 0] == ("a", 1, 0)
        assert i[3, 0] == ("b", 1, 0)
        
        assert i[0, 1] == ("a", 0, 1)
        assert i[1, 1] == ("b", 0, 1)
        assert i[2, 1] == ("a", 1, 1)
        assert i[3, 1] == ("b", 1, 1)
        
        # 'Vertical'
        i = InterleavedArray(a, b, 1)
        assert i[0, -2] == ("a", 0, -1)
        assert i[0, -1] == ("b", 0, -1)
        assert i[0, 0] == ("a", 0, 0)
        assert i[0, 1] == ("b", 0, 0)
        assert i[0, 2] == ("a", 0, 1)
        assert i[0, 3] == ("b", 0, 1)
        
        assert i[1, 0] == ("a", 1, 0)
        assert i[1, 1] == ("b", 1, 0)
        assert i[1, 2] == ("a", 1, 1)
        assert i[1, 3] == ("b", 1, 1)
    
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
    
    def test_relative_step_size_to(self):
        a1 = SymbolArray(2, "a1")
        a2 = SymbolArray(2, "a2")
        i1 = InterleavedArray(a1, a2, 0)
        assert i1.relative_step_size_to(a1) == (0.5, 1)
        assert i1.relative_step_size_to(a2) == (0.5, 1)
        assert i1.relative_step_size_to(i1) == (1, 1)
        
        # Other dimensions work
        a3 = SymbolArray(2, "a3")
        a4 = SymbolArray(2, "a4")
        i2 = InterleavedArray(a3, a4, 1)
        assert i2.relative_step_size_to(a3) == (1, 0.5)
        assert i2.relative_step_size_to(a4) == (1, 0.5)
        assert i2.relative_step_size_to(i2) == (1, 1)
        
        # Non-matching arrays work
        assert i2.relative_step_size_to(i1) is None
        
        # Deep nesting
        i3 = InterleavedArray(i1, i2, 0)
        assert i3.relative_step_size_to(a1) == (0.25, 1)
        assert i3.relative_step_size_to(a2) == (0.25, 1)
        assert i3.relative_step_size_to(a3) == (0.5, 0.5)
        assert i3.relative_step_size_to(a4) == (0.5, 0.5)
        assert i3.relative_step_size_to(i1) == (0.5, 1)
        assert i3.relative_step_size_to(i2) == (0.5, 1)
        assert i3.relative_step_size_to(i3) == (1, 1)
        
        # Check partial support when the same values appear on both sides of an
        # interleaving
        i4 = InterleavedArray(i1, a1, 1)
        assert i4.relative_step_size_to(SymbolArray(2, "nope")) is None
        assert i4.relative_step_size_to(i4) == (1, 1)
        assert i4.relative_step_size_to(i1) == (1, 0.5)
        assert i4.relative_step_size_to(a2) == (0.5, 0.5)
        with pytest.raises(ValueError):
            i4.relative_step_size_to(a1)


class TestRightShiftedArray(object):
    
    def test_shifting(self):
        a = SymbolArray(3, "foo")
        sa = RightShiftedArray(a, 3)
        
        v = a[1, 2, 3]
        
        sv = sa[1, 2, 3]
        
        assert aa.lower_bound(sv) == v / 8 - Fraction(1, 2)
        assert aa.upper_bound(sv) == v / 8 + Fraction(1, 2)
    
    def test_period(self):
        a = RepeatingSymbolArray((1, 2, 3))
        sa = RightShiftedArray(a, 3)
        assert sa.period == (1, 2, 3)
        assert period_empirically_correct(sa)
    
    def test_relative_step_size_to(self):
        a = SymbolArray(2)
        s = SubsampledArray(a, (2, 3), (0, 0))
        r = RightShiftedArray(s, 123)
        
        assert r.relative_step_size_to(a) == (2, 3)
        assert r.relative_step_size_to(r) == (1, 1)
        assert r.relative_step_size_to(SymbolArray(2, "nope")) is None


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
    
    def test_relative_step_size_to(self):
        a = SymbolArray(2)
        s = SubsampledArray(a, (2, 3), (0, 0))
        l = LeftShiftedArray(s, 123)
        
        assert l.relative_step_size_to(a) == (2, 3)
        assert l.relative_step_size_to(l) == (1, 1)
        assert l.relative_step_size_to(SymbolArray(2, "nope")) is None
