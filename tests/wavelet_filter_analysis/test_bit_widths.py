import pytest

import operator

import sympy

from vc2_conformance import tables

from vc2_conformance.wavelet_filter_analysis.quantisation_matrices import (
    convert_between_synthesis_and_analysis,
)

from vc2_conformance.wavelet_filter_analysis.bit_widths import (
    new_analysis_input,
    new_synthesis_input,
    new_error_term,
    SymbolicValue,
    extract_variables,
    total_error_magnitude,
    analysis_input_coefficients,
    synthesis_input_coefficients,
    get_filter_input_sample_indices,
    get_representative_synthesis_sample_indices,
    get_representative_analysis_sample_indices,
)

le_gall_synthesis = tables.LIFTING_FILTERS[tables.WaveletFilters.le_gall_5_3]
le_gall_analysis = convert_between_synthesis_and_analysis(
    tables.LIFTING_FILTERS[tables.WaveletFilters.le_gall_5_3]
)

haar_synthesis = tables.LIFTING_FILTERS[tables.WaveletFilters.haar_with_shift]
haar_analysis = convert_between_synthesis_and_analysis(
    tables.LIFTING_FILTERS[tables.WaveletFilters.haar_with_shift]
)

fidelity_synthesis = tables.LIFTING_FILTERS[tables.WaveletFilters.fidelity]
fidelity_analysis = convert_between_synthesis_and_analysis(
    tables.LIFTING_FILTERS[tables.WaveletFilters.fidelity]
)



def test_new_analysis_input():
    a00 = new_analysis_input(0, 0)
    a01 = new_analysis_input(0, 1)
    a10 = new_analysis_input(1, 0)
    
    # Should not be equal to different-indexed values
    assert a00 != a01
    assert a00 != a10
    
    assert a01 != a00
    assert a01 != a10
    
    assert a10 != a00
    assert a10 != a01
    
    # Should be equal to new instances of the same symbol
    assert a00 == new_analysis_input(0, 0)
    
    assert a10.name == "a_1_0"


def test_new_analysis_input():
    s0 = new_synthesis_input(0, "LL", 1, 2)
    s1 = new_synthesis_input(1, "HH", 3, 4)
    
    # Should not equal different indexed values
    assert s0 != s1
    
    # Should be equal to new instances of the same symbol
    assert s0 == new_synthesis_input(0, "LL", 1, 2)
    
    assert s0.name == "s_0_LL_1_2"


def test_new_error_term():
    e1 = new_error_term()
    e2 = new_error_term()
    
    assert e1 - e2 != 0
    assert e1.name.startswith("e_")
    assert e2.name.startswith("e_")


class TestSymbolicValue(object):
    
    # A trivial subclass to be used in these tests
    class SubSV(SymbolicValue):
        pass
    
    def test_as_symbolic_value(self):
        # Cast non-SVs to SVs (using the current subclass)
        v = self.SubSV.as_symbolic_value(123)
        assert isinstance(v, self.SubSV)
        assert v.value == 123
        
        # Keep existing SVs without re-wrapping
        v2 = self.SubSV.as_symbolic_value(v)
        assert v2 is v
    
    @pytest.mark.parametrize("v1,v2", [
        # Both are SVs
        (SubSV(10), SubSV(20)),
        # One is an SV
        (SubSV(10), 20),
        (10, SubSV(20)),
    ])
    def test_apply(self, v1, v2):
        
        v3 = self.SubSV.apply(v1, v2, lambda a, b: a + b)
        assert isinstance(v3, self.SubSV)
        assert v3.value == 30
    
    @pytest.mark.parametrize("op", [
        operator.add,
        operator.sub,
        operator.mul,
    ])
    def test_non_shift_operators(self, op):
        v1 = self.SubSV(10)
        v2 = self.SubSV(20)
        
        v3 = op(v1, v2)
        assert isinstance(v3, self.SubSV)
        assert v3.value == op(10, 20)
        
        v3 = op(v1, 20)
        assert isinstance(v3, self.SubSV)
        assert v3.value == op(10, 20)
        
        v3 = op(10, v2)
        assert isinstance(v3, self.SubSV)
        assert v3.value == op(10, 20)
    
    def test_left_shift(self):
        # NB: Shift not natively supported on floats, but emulated here
        v1 = self.SubSV(2.5)
        v2 = self.SubSV(3)
        
        v3 = v1 << v2
        assert isinstance(v3, self.SubSV)
        assert v3.value == 20
        
        v3 = 2.5 << v2
        assert isinstance(v3, self.SubSV)
        assert v3.value == 20
        
        v3 = v1 << 3
        assert isinstance(v3, self.SubSV)
        assert v3.value == 20
    
    def test_right_shift(self):
        # NB: Shift not natively supported on floats, but emulated here
        v1 = self.SubSV(10.0)
        v2 = self.SubSV(3)
        
        v3 = v1 >> v2
        assert isinstance(v3, self.SubSV)
        assert (v3.value - 10.0/8).name.startswith("e_")
        
        v3 = 10.0 >> v2
        assert isinstance(v3, self.SubSV)
        assert (v3.value - 10.0/8).name.startswith("e_")
        
        v3 = v1 >> 3
        assert isinstance(v3, self.SubSV)
        assert (v3.value - 10.0/8).name.startswith("e_")
    
    def test_repr(self):
        v = self.SubSV("Value")
        assert repr(v) == "SubSV('Value')"
    
    def test_str(self):
        v = self.SubSV("Value")
        assert str(v) == "Value"


@pytest.mark.parametrize("expr,expected", [
    # Empty
    (0, {}),
    # Constant only
    (123, {1: 123}),
    (-123, {1: -123}),
    (sympy.Rational(1, 2), {1: sympy.Rational(1, 2)}),
    # Single symbol
    (sympy.abc.a, {sympy.abc.a: 1}),
    (-sympy.abc.a, {sympy.abc.a: -1}),
    (123*sympy.abc.a, {sympy.abc.a: 123}),
    (-123*sympy.abc.a, {sympy.abc.a: -123}),
    (sympy.Rational(1, 2)*sympy.abc.a, {sympy.abc.a: sympy.Rational(1, 2)}),
    (sympy.Rational(-1, 2)*sympy.abc.a, {sympy.abc.a: sympy.Rational(-1, 2)}),
    # Multiple symbols and constants
    (
        sympy.abc.a + sympy.abc.b,
        {sympy.abc.a: 1, sympy.abc.b: 1},
    ),
    (
        123*sympy.abc.a + sympy.Rational(1, 2)*sympy.abc.b + 321,
        {
            sympy.abc.a: 123,
            sympy.abc.b: sympy.Rational(1, 2),
            1: 321,
        },
    ),
])
def test_extract_variables(expr, expected):
    assert extract_variables(expr) == expected

def test_extract_variables_non_linear_combination():
    with pytest.raises(ValueError):
        extract_variables(sympy.abc.a*sympy.abc.b)


@pytest.mark.parametrize("expr,expected", [
    # No error terms
    (0, 0),
    (123, 0),
    (sympy.abc.a + 123, 0),
    # With error term
    (new_error_term(), 1),
    (123*new_error_term(), 123),
    (-123*new_error_term(), 123),
    # With several error terms
    (10*new_error_term() - 20*new_error_term(), 30),
])
def test_total_error_magnitude(expr, expected):
    assert total_error_magnitude(expr) == expected


def test_analysis_input_coefficients():
    assert analysis_input_coefficients(
        10*new_analysis_input(1, 2) +
        -20*new_analysis_input(3, 4) +
        30
    ) == {
        (1, 2): 10,
        (3, 4): -20,
    }


def test_synthesis_input_coefficients():
    assert synthesis_input_coefficients(
        10*new_synthesis_input(0, "LL", 1, 2) +
        -20*new_synthesis_input(3, "HH", 4, 5) +
        30
    ) == {
        (0, "LL", 1, 2): 10,
        (3, "HH", 4, 5): -20,
    }


# The following have been worked out 'by hand' from the figures in the
# documentation for the bit-width calculation scheme.
@pytest.mark.parametrize("output_index,filter_params,depth,synthesis,exp_input_indices", [
    # Synthesis
    # Depth 0
    (
        0,
        le_gall_synthesis, 0, True,
        [0],
    ),
    # Depth 1
    (
        0,
        le_gall_synthesis, 1, True,
        [-1, 0, 1],
    ),
    (
        1,
        le_gall_synthesis, 1, True,
        [-1, 0, 1, 2, 3],
    ),
    # Depth 2
    (
        0,
        le_gall_synthesis, 2, True,
        [-2, -1, 0, 1, 2],
    ),
    (
        1,
        le_gall_synthesis, 2, True,
        [-2, -1, 0, 1, 2, 3, 4, 6],
    ),
    (
        2,
        le_gall_synthesis, 2, True,
        [-2, 0, 1, 2, 3, 4, 6],
    ),
    (
        3,
        le_gall_synthesis, 2, True,
        [-2, 0, 1, 2, 3, 4, 5, 6],
    ),
    # Analysis
    # Depth 0
    (
        0,
        le_gall_analysis, 0, False,
        [0],
    ),
    # Depth 1
    (
        0,
        le_gall_analysis, 1, False,
        [-2, -1, 0, 1, 2],
    ),
    (
        1,
        le_gall_analysis, 1, False,
        [0, 1, 2],
    ),
    # Depth 2
    (
        0,
        le_gall_analysis, 2, False,
        list(range(-6, 6+1)),
    ),
    (
        1,
        le_gall_analysis, 2, False,
        [0, 1, 2],
    ),
    (
        2,
        le_gall_analysis, 2, False,
        list(range(-2, 6+1)),
    ),
    (
        3,
        le_gall_analysis, 2, False,
        [2, 3, 4],
    ),
    # Check a filter with an asymmetric set of taps
    (
        0,
        haar_synthesis, 2, True,
        [0, 1, 2],
    ),
    (
        1,
        haar_synthesis, 2, True,
        [0, 1, 2],
    ),
    (
        2,
        haar_synthesis, 2, True,
        [0, 2, 3],
    ),
    (
        3,
        haar_synthesis, 2, True,
        [0, 2, 3],
    ),
    (
        0,
        haar_analysis, 2, False,
        [0, 1, 2, 3],
    ),
    (
        1,
        haar_analysis, 2, False,
        [0, 1],
    ),
    (
        2,
        haar_analysis, 2, False,
        [0, 1, 2, 3],
    ),
    (
        3,
        haar_analysis, 2, False,
        [2, 3],
    ),
    # Check a filter whose length > 2
    (
        0,
        fidelity_synthesis, 1, True,
        [-14, -12, -10, -8, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14],
    ),
    (
        1,
        fidelity_synthesis, 1, True,
        [-6, -4, -2, 0, 1, 2, 4, 6, 8],
    ),
    (
        0,
        fidelity_analysis, 1, False,
        [-7, -5, -3, -1, 0, 1, 3, 5, 7],
    ),
    (
        1,
        fidelity_analysis, 1, False,
        [-13, -11, -9, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 13, 15],
    ),
])
def test_get_filter_input_sample_indices(output_index, filter_params, depth, synthesis, exp_input_indices):
    assert get_filter_input_sample_indices(output_index, filter_params, depth, synthesis) == exp_input_indices
    
    # Pattern should repeat every 2**depth steps
    assert get_filter_input_sample_indices(output_index + 2**depth, filter_params, depth, synthesis) == [
        index + 2**depth
        for index in exp_input_indices
    ]


# Hand-worked examples
@pytest.mark.parametrize("filter_params,depth,width,indices", [
    # Haar is an odd-ball in that no extra padding should be required
    (haar_synthesis, 2, 4, [0, 1, 2, 3]),
    # A relatively deep 'real world' filter
    (le_gall_synthesis, 3, 21, [8, 9, 10, 11, 12, 13, 14, 15]),
])
def test_get_representative_synthesis_sample_indices(filter_params, depth, width, indices):
    minimum_width, output_sample_indices = get_representative_synthesis_sample_indices(
        filter_params, depth,
    )
    assert minimum_width == width
    assert output_sample_indices == indices


# Hand-worked examples
@pytest.mark.parametrize("filter_params,depth,width,indices", [
    # Haar is an odd-ball in that no extra padding should be required
    (haar_synthesis, 2, 4, [
        (0, "L", 0),  # 0//4
        (1, "H", 0),  # (2-2)//4
        (2, "H", 0),  # (1-1)//2
    ]),
    # A relatively deep 'real world' filter
    (le_gall_analysis, 3, 31, [
        (0, "L", 2),  # 16//8
        (1, "H", 1),  # (12-4)//8
        (2, "H", 1),  # (6-2)//4
        (3, "H", 0),  # (1-1)//2
    ]),
])
def test_get_representative_analysis_sample_indices(filter_params, depth, width, indices):
    minimum_width, output_sample_indices = get_representative_analysis_sample_indices(
        filter_params,
        depth,
    )
    assert minimum_width == width
    assert output_sample_indices == indices
