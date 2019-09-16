r"""
Affine Airthmetic
=================

This module provides utilities for performing Affine Arithmetic (AA) with the
:py:mod:`linexp` library.

Affine Arithmetic Primer
------------------------

Suppose we have two variables, :math:`a` and :math:`b`, with some known range
of values.  Using affine arithmetic we can answer questions of the form 'what
is the range of :math:`\textrm{round}(a + 2*b)`?'.

Affine arithmetic form
``````````````````````

In affine arithmetic, variables with a known range are substituted with
expressions of the form :math:`\alpha e + \beta` where :math:`\alpha` and
:math:`\beta` are constants and :math:`e` is defined as being a value in the
range :math:`[-1, +1]`.

Affine operations
`````````````````
For any affine operation (e.g. addition, subtraction, multiplication by a
constant), this operation may be performed as usual, producing a result in
affine arithmetic form.

For example, say we have a variable :math:`a` in the range :math:`[100, 110]`.
This is defined in affine arithmetic as :math:`a = 5 e_1 + 105` where
:math:`e_1` is any value in the range :math:`[-1, +1]`. By evaluating this
expression using the (obvious) values of :math:`e_1` which minimise and
maximise the result we can get back the range of the expression.

As an exmple of an affine operation consider :math:`3a` (multiplication by a
constant). The resulting affine expression is :math:`15 e_1 + 315`. From this
we can easily determine that the range of :math:`3a` is :math:`[300, 330]` when
:math:`e_1` is set to :math:`-1` and :math:`+1` respectively.

Lets define another variable, :math:`b`, in the range :math:`[-10, 30]`. In
affine arithmetic this is represented as :math:`b = 20 e_2 + 10`, where
:math:`e_2` is in the range :math:`[-1, +1]`. (Note that :math:`a` and
:math:`b` are assigned their own :math:`e_n` variables.)

If we consider :math:`a - b` (another affine operation) we get :math:`5 e_1 -
20 e_2 + 95`. The minima of this expression is found when :math:`e_1 = -1` and
:math:`e_2 = +1` while the maxima is found when :math:`e_1 = +1` and :math:`e_2
= -1` giving the range :math:`[70, 120]`.

Dependent variables
```````````````````

A key feature of Affine Arithmetic (as compared to, for example, Interval
Arithmetic) is that it takes into account the inter-dependence of variables.
For example, the expression :math:`a - a` evaluates to :math:`0` and therefore
the range :math:`[0, 0]`, as expected.

Non-affine operations
`````````````````````

Affine Arithmetic may be defined for some non-affine operations such as
rounding. For example, when a value is rounded to the nearest integer, an error is
introduced of up to :math:`\pm 0.5`. Therefore if some affine arithmetic value,
:math:`c`, is rounded to the nearest integer, the result is :math:`c + 0.5
e_3`.

Unfortunately, while non-affine operation definitions, such as the above,
produce safe upper- and lower-bounds, they may be overly-conservative. For
example, if the rounding operation above is repeated, an additional error term
is introduced, even though the resulting range would not change in reality.

In this implementation of Affine Arithmetic, rounding is the only supported
non-affine operations.


API
---

A new affine error symbol (:math:`e_n` in the above examples) may be created
by:

.. autofunction:: new_error_symbol

.. autoclass:: Error

An affine expression representing an error within a specified range may be
created using:

.. autofunction:: error_in_range

The following function implements Python/VC-2 style truncating integer
division.

.. autofunction:: div

The following functions may be used to work out the bounds for a given affine
arithmetic expression.

.. autofunction:: upper_bound

.. autofunction:: lower_bound

"""

from vc2_conformance.wavelet_filter_analysis.linexp import LinExp

from collections import namedtuple

from fractions import Fraction

from vc2_conformance.wavelet_filter_analysis.fast_sympy_functions import (
    subs,
    coeffs,
)

__all__ = [
    "Error",
    "new_error_symbol",
    "error_in_range",
    "div",
    "upper_bound",
    "lower_bound",
]

Error = namedtuple("Error", "id")
"""An error symbol."""

_last_error_term = 0
"""Used by :py:func:`new_error_symbol`. For internal use only."""

def new_error_symbol():
    """
    Create a :py:class:`LinExp` with a unique :py:class:`Error` symbol. This
    term should be considered as having a value in the range :math:`[-1, +1]`.
    """
    global _last_error_term
    _last_error_term += 1
    return LinExp(Error(_last_error_term))


def error_in_range(lower, upper):
    """
    Create an affine arithmetic expression defining an error in the specified
    range (using a new error symbol created by :py:func:`new_error_symbol`).
    """
    mean = Fraction(lower + upper, 2)
    half_range = Fraction(upper - lower, 2)
    
    return (half_range * new_error_symbol()) + mean


# Cache of previous 'div' outputs
#
# {(numerator, denominator): result, ...}
_div_result_cache = {}

def div(numerator, denominator):
    """
    Perform Python/VC-2 style truncating integer division by a constant on an
    affine arithmetic expression.
    
    This function introduces a different error symbol (created with
    :py:func:`new_error_symbol`) for each unique numerator/denominator pairing
    provided. When a numerator/denominator pairing is repeated, the same symbol
    will be used.
    """
    
    global _div_result_cache
    
    if (numerator, denominator) not in _div_result_cache:
        _div_result_cache[(numerator, denominator)] = (
            (LinExp(numerator) / denominator) +
            error_in_range(-1, 0)
        )
    
    return _div_result_cache[(numerator, denominator)]


def upper_bound(expression):
    """
    Calculate the upper-bound of an affine arithmetic expression.
    """
    expression = LinExp(expression)
    
    return expression.subs({
        sym: 1 if value > 0 else -1
        for sym, value in expression
        if isinstance(sym, Error)
    })


def lower_bound(expression):
    """
    Calculate the lower-bound of an affine arithmetic expression.
    """
    expression = LinExp(expression)
    
    return expression.subs({
        sym: 1 if value < 0 else -1
        for sym, value in expression
        if isinstance(sym, Error)
    })
