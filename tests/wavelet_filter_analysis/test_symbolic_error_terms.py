import pytest

import sympy

from vc2_conformance.wavelet_filter_analysis.symbolic_error_terms import (
    new_error_term,
    strip_error_terms,
    worst_case_error_bounds,
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
