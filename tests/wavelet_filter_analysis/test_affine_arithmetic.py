import pytest

from vc2_conformance.wavelet_filter_analysis.linexp import LinExp

import vc2_conformance.wavelet_filter_analysis.affine_arithmetic as aa


def test_new_error_term():
    e1 = aa.new_error_symbol()
    e2 = aa.new_error_symbol()
    
    assert e1 - e2 != 0
    assert str(e1).startswith("Error(")
    assert str(e2).startswith("Error(")


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
    (LinExp("a") + 5 + 3*aa.new_error_symbol(), LinExp("a") + 2, LinExp("a") + 8),
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
        r = aa.div(LinExp("a"), 2)
        assert aa.lower_bound(r) == (LinExp("a")/2) - 1
        assert aa.upper_bound(r) == LinExp("a")/2
    
    def test_returns_different_error_terms_for_different_inputs(self):
        r1 = aa.div(1, 2)
        r2 = aa.div(2, 2)
        r3 = aa.div(1, 3)
        assert set(r1.symbols()) != set(r2.symbols())
        assert set(r2.symbols()) != set(r3.symbols())
        assert set(r3.symbols()) != set(r1.symbols())
    
    def test_returns_same_error_terms_for_same_inputs(self):
        r1 = aa.div(LinExp("a") + LinExp("b") + 3, 2)
        r2 = aa.div(LinExp("a") + LinExp("b") + 3, 2)
        assert r1 == r2
