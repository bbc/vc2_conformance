import pytest

import sympy

from vc2_conformance.wavelet_filter_analysis.fast_sympy_functions import (
    subs,
    coeffs,
)


class TestSubs(object):
    
    @pytest.mark.parametrize("expr,mapping,expected", [
        # No symbols (and not a sympy type!)
        (
            123,
            {},
            123,
        ),
        # Replace in an atom
        (
            sympy.abc.a,
            {sympy.abc.a: 10},
            10,
        ),
        (
            sympy.Rational(10, 2),
            {sympy.abc.a: 10},
            5,
        ),
        # Replace in an addition
        (
            (sympy.abc.a + 1),
            {sympy.abc.a: 10},
            11,
        ),
        # Replace in multiplication
        (
            (sympy.abc.a * sympy.abc.b),
            {sympy.abc.a: 10, sympy.abc.b: 100},
            1000,
        ),
        # Replace in combination
        (
            (2*sympy.abc.a - sympy.Rational(3, 1)*sympy.abc.b + 1),
            {sympy.abc.a: 10, sympy.abc.b: 100},
            20 - 300 + 1,
        ),
    ])
    def test_supported(self, expr, mapping, expected):
        assert subs(expr, mapping) == expected
    
    @pytest.mark.parametrize("expr,mapping", [
        (sympy.abc.a**123, {sympy.abc.a: 10})
    ])
    def test_unsupported(self, expr, mapping):
        with pytest.raises(TypeError):
            subs(expr, mapping)


class TestCoeffs(object):
    
    @pytest.mark.parametrize("expr,expected", [
        # No symbols and not a sympy type
        (123, {}),
        # Bare symbol
        (sympy.abc.a, {sympy.abc.a: 1}),
        # Scaled symbol
        (3*sympy.abc.a, {sympy.abc.a: 3}),
        (-3*sympy.abc.a, {sympy.abc.a: -3}),
        # Sum of bare symbols
        (sympy.abc.a + sympy.abc.b, {sympy.abc.a: 1, sympy.abc.b: 1}),
        # Sum of scaled symbols
        (2*sympy.abc.a - 3*sympy.abc.b, {sympy.abc.a: 2, sympy.abc.b: -3}),
        # Sum with symbols and constant
        (2*sympy.abc.a + 123, {sympy.abc.a: 2}),
    ])
    def test_supported(self, expr, expected):
        assert coeffs(expr) == expected
    
    @pytest.mark.parametrize("expr", [
        # Bare non-supported function
        sympy.abc.a**123,
        # Coeff contains non-supported function
        sympy.abc.a + sympy.abc.b**123,
        # Coeff not a rational+symbol pair
        sympy.abc.a*sympy.abc.b + 3*sympy.abc.d
    ])
    def test_unsupported(self, expr):
        with pytest.raises(TypeError):
            coeffs(expr)
