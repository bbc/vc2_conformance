"""
Faster :py:mod:`sympy` functions
================================

This module contains implementations of functions natively provided by
:py:mod:`sympy`, but which are extremely slow for the kinds of expressions used
in this software.

.. autofunction:: subs

.. autofunction:: coeffs

"""

__all__ = ["subs"]

from sympy import sympify, Add, Mul, Rational, Symbol


def subs(expression, mapping):
    """
    Substitute symbols for new values in a :py:mod:`sympy` expression.
    
    Equivalent to (but faster than)::
        
        >>> expression.subs(mapping)
    
    Sympy's :py:meth:`~sympy.core.basic.Basic.subs` method is incredibly
    flexible but extremely slow when operating on very large expressions or
    when used to perform a very large number of simple subsititutions.
    This implementation implements a tiny subset of this method but does so
    extremely fast.
    
    Parameters
    ==========
    expression : :py:mod:`sympy` expression
        An expression consising only of :py:mod:`sympy` ``Add``, ``Mul``,
        ``Rational`` and ``Symbol`` values.
    mapping : {before: after, ...}
        A dictionary of replacements to make. Before values should be sympy
        Symbols.
    """
    expression = sympify(expression)
    
    if isinstance(expression, (Add, Mul)):
        return expression.func(*(
            subs(arg, mapping)
            for arg in expression.args
        ))
    else:
        if not isinstance(expression, (Rational, Symbol)):
            raise TypeError("Expression contains unsupported type {}".format(expression.func))
        return mapping.get(expression, expression)


def coeffs(expression):
    """
    Enumerate all coefficients (and their variables) in an expression.
    
    Equivalent to (but faster than)::
    
        >>> {sym: expression.coeff(sym) for sym in expression.free_symbols}
    
    The implementation above is slow due to the ``coeff`` method taking a
    fairly long time on large expressions. This function internally
    re-implements a small subset of the functionality of ``coeff`` in a more
    performant form.
    
    Parameters
    ==========
    expression : Add(Mul(Rational, Symbol), Mul(Rational, Symbol), ..., Rational)
    
    Returns
    =======
    coeffs : {Symbol: Rational, ...}
    """
    expression = sympify(expression)
    
    out = {}
    
    if not isinstance(expression, (Add, Mul, Rational, Symbol)):
        raise TypeError("Expression contains unsupported type {}".format(expression.func))
    
    if isinstance(expression, Add):
        args = expression.args
    else:
        args = [expression]
    
    for arg in args:
        if not isinstance(arg, (Mul, Rational, Symbol)):
            raise TypeError("Expression contains unsupported type {}".format(arg.func))
        if isinstance(arg, Mul):
            if len(arg.args) != 2:
                raise TypeError("Mul has more than two arguments.")
            if isinstance(arg.args[0], Symbol):
                sym = arg.args[0]
                val = arg.args[1]
            else:
                sym = arg.args[1]
                val = arg.args[0]
            if not isinstance(sym, (Symbol)):
                raise TypeError("Expression contains unsupported type {}".format(sym.func))
            if not isinstance(val, (Rational)):
                raise TypeError("Expression contains unsupported type {}".format(sym.func))
        elif isinstance(arg, Symbol):
            sym = arg
            val = 1
        else:
            continue
        out[sym] = val
    
    return out
