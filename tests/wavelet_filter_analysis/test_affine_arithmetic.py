import pytest

import sympy.abc

import vc2_conformance.wavelet_filter_analysis.affine_arithmetic as aa


def test_new_error_term():
    e1 = aa.new_error_symbol()
    e2 = aa.new_error_symbol()
    
    assert e1 - e2 != 0
    assert e1.name.startswith("e_")
    assert e2.name.startswith("e_")


@pytest.mark.parametrize("expr_in,lower,upper", [
    # Pure number (not a sympy type)
    (0, 0, 0),
    (123, 123, 123),
    # Single error
    (aa.new_error_symbol(), -1, 1),
    (-aa.new_error_symbol(), -1, 1),
    # Scaled error
    (3*aa.new_error_symbol(), -3, 3),
    # Several errors
    (3*aa.new_error_symbol() + 2*aa.new_error_symbol(), -5, 5),
    (3*aa.new_error_symbol() + 2*aa.new_error_symbol() + 5, 0, 10),
    # Errors and other values
    (sympy.abc.a + 5 + 3*aa.new_error_symbol(), sympy.abc.a + 2, sympy.abc.a + 8),
])
def test_bounds(expr_in, lower, upper):
    assert aa.lower_bound(expr_in) == lower
    assert aa.upper_bound(expr_in) == upper


def test_error_in_range():
    a = aa.error_in_range(-10, 123)
    assert aa.lower_bound(a) == -10
    assert aa.upper_bound(a) == 123


class TestDiv(object):
    
    def test_basic_division_works(self):
        r = aa.div(sympy.abc.a, 2)
        assert aa.lower_bound(r) == (sympy.abc.a/2) - 1
        assert aa.upper_bound(r) == sympy.abc.a/2
    
    def test_returns_different_error_terms_for_different_inputs(self):
        r1 = aa.div(1, 2)
        r2 = aa.div(2, 2)
        r3 = aa.div(1, 3)
        assert r1.free_symbols != r2.free_symbols
        assert r2.free_symbols != r3.free_symbols
        assert r1.free_symbols != r3.free_symbols
    
    def test_returns_same_error_terms_for_same_inputs(self):
        r1 = aa.div(sympy.abc.a + sympy.abc.b + 3, 2)
        r2 = aa.div(sympy.abc.a + sympy.abc.b + 3, 2)
        assert r1 == r2
