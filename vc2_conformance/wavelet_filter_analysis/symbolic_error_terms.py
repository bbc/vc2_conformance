"""
Symbolic error terms
====================

Utilities for creating and measuring (usually rounding) errors symbolically in
:py:mod:`sympy` arithmetic.

One approach to algebraically modelling the behaviour of truncating integer
division (and similar operations) is to introduce error terms. For example, the
truncating integer division operation ``a // b``, may be symbolically
represented as :math:`a // b = a / b - e_1` where :math:`e_1` is some error in
the range :math:`[0, 1)`.

This module provides a set of simple utility functions for creating and
analysing properties of :py:mod:`sympy` expressions with error terms as in the
above.

Error symbols are created using:

.. autofunction:: new_error_term

.. warning::

    Take care to create new (unique) error symbols for each and every division
    operation since the error produced by two different operations is not
    necessarily related and so must be accounted for separately.

Error symbols in a given expression may be stripped out using:

.. autofunction:: strip_error_terms

The following functions may be used to work out the worst-case error bounds for
a given expression. The lower-bound is defined to be the case when all
negatively-weighted error terms are 1 and all positively weighted errors are 0.
Conversely the upper-bound is given when all positively-weighted error terms
are set to 1 and the negatively-weighted terms are 0.

.. autofunction:: upper_error_bound

.. autofunction:: lower_error_bound

"""

from sympy import Symbol, sympify

__all__ = [
    "new_error_term",
    "strip_error_terms",
    "upper_error_bound",
    "lower_error_bound",
]


_last_error_term = 0
"""Used by :py:func:`new_error_term`. For internal use only."""

def new_error_term():
    """
    Create a new, and unique, :py:mod:`sympy` symbol with a name of the form
    'e_123'.
    """
    global _last_error_term
    _last_error_term += 1
    return Symbol("e_{}".format(_last_error_term))


def strip_error_terms(expression):
    """
    Strip all error terms (created by :py:func:`new_error_term`) from an
    expression.
    """
    expression = sympify(expression)
    
    return expression.subs({
        sym: 0
        for sym in expression.free_symbols
        if sym.name.startswith("e_")
    })


def upper_error_bound(expression):
    """
    Calculate the upper-bound for the total value of the error terms in the
    provided expression.
    """
    expression = sympify(expression)
    
    return expression.subs({
        sym: 1 if expression.coeff(sym) > 0 else 0
        for sym in expression.free_symbols
        if sym.name.startswith("e_")
    })


def lower_error_bound(expression):
    """
    Calculate the lower-bound for the total value of the error terms in the
    provided expression.
    """
    expression = sympify(expression)
    
    return expression.subs({
        sym: 1 if expression.coeff(sym) < 0 else 0
        for sym in expression.free_symbols
        if sym.name.startswith("e_")
    })
