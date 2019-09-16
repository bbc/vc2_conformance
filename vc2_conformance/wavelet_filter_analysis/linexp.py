r"""
:py:mod:`linexp`: A simple computer algebra system
==================================================

This module implements a simple Computer Algebra System (CAS) which is able to
perform basic algebraic manipulations on linear expressions (linexps).

.. note::

    Compared with the mature and powerful :py:mod:`sympy` CAS, :py:mod:`linexp`
    is extremely limited. However, within its restricted domain,
    :py:mod:`linexp` is significantly more computationally efficient.

Example Usage
-------------

Linear expressions are defined as being of the form:

.. math::
    
    c_1 v_1 + c_2 v_2 + \cdots + c_3

Where :math:`c_n` are constants and :math:`v_n` are free symbols (i.e.
variables). For example, the following represents a linear expression:

.. math::
    
    a + 2b - 3c + 100

Where :math:`a`, :math:`b` and :math:`c` are the free symbols and 1, 2, -3 and
100 are the relevant constants.

The expression above may be constructed using this library as follows::

    >>> from vc2_conformance.wavelet_filter_analysis.linexp import LinExp
    
    >>> # Create expressions containing just the symbols named 'a', 'b' and 'c'.
    >>> a = LinExp("a")
    >>> b = LinExp("b")
    >>> c = LinExp("c")
    
    >>> expr = a + 2*b - 3*c + 100
    >>> str(expr)
    'a + 2*b + -3*c + 100'

The :py:meth:`LinExp.subs` method may then be used to substitute symbols with
numbers::

    >>> result = expr.subs({"a": 1000, "b": 10000, "c": 100000})
    >>> result
    LinExp(-278900)

When a :py:class:`LinExp` contains just a constant value, the constant may be
extracted as a conventional Python number type using :py:attr:`constant`::

    >>> result.is_constant
    True
    >>> result.constant
    -278900

In a similar way, for :py:class:`LinExp` instances consisting of a single
symbol with weight 1, the symbol name may be extracted like so::

    >>> a.is_symbol
    True
    >>> a.symbol
    'a'
    
    >>> # Weighted symbols are considered different
    >>> a3 = a * 3
    >>> a3.is_symbol
    False

Instances of :py:class:`LinExp` support all Python operators when the resulting
expression would be strictly linear. For example::

    >>> expr_times_ten = expr * 10
    >>> str(expr_times_ten)
    '10*a + 20*b + -30*c + 1000'
    
    >>> three = (expr * 3) / expr
    >>> str(three)
    '3'
    
    >>> # Not allowed since the result would not be linear
    >>> expr / a
    TypeError: unsupported operand type(s) for /: 'LinExp' and 'LinExp'

Expressions may use :py:class:`~fractions.Fraction`\ s to represent
coefficients exactly. Accordingly :py:class:`LinExp` implements division using
:py:class:`~fractions.Fraction`::

    >>> expr_over_three = expr / 3
    >>> str(expr_over_three)
    '(1/3)*a + (2/3)*b + -1*c + 100/3'

Internally, linear expressions are represented by a dictionary of the form
``{symbol: coefficient, ...}``. For example::

    >>> repr(expr)
    "LinExp({'a': 1, 'b': 2, 'c': -3, None: 100})"

Note that the constant term is stored in the special entry ``None``.

The :py:class:`LinExp` class provides a number of methods for inspecting the
value within an expression. For example, iterating over a :py:class:`LinExp`
yields the ``(symbol, coefficient)`` pairs::

    >>> list(expr)
    [('a', 1), ('b', 2), ('c', -3), (None, 100)]

Alternatively, just the symbols can be listed::

    >>> list(expr.symbols())
    ['a', 'b', 'c', None]

The coefficients associated with particular symbols can be queried like so::

    >>> expr["b"]
    2
    >>> expr["d"]
    0


API
---

.. autoclass:: LinExp
    :members:

"""

import six

import operator

from numbers import Number, Integral

from functools import total_ordering

from fractions import Fraction

from collections import defaultdict


__all__ = [
    "LinExp",
]


@total_ordering
class LinExp(object):
    r"""
    """
    
    __slots__ = ["_coeffs"]
    
    def __new__(cls, value=0):
        if isinstance(value, cls):
            # Don't bother creating a copy of an existing LinExp
            return value
        else:
            return super(LinExp, cls).__new__(cls)
    
    def __init__(self, value=0):
        r"""
        Create a new linear expression.
    
        A linear expression is defined has having the general form:
        
        .. math::
            
            c_1 v_1 + c_2 v_2 + \cdots + c_3
        
        Where :math:`c_n` are constants and :math:`v_n` are free symbols (i.e.
        variables).
        
        Parameters
        ==========
        value : number or symbol or {symbol or None: coeff, ...} or :py:class:`LinExp`
            The value to be represented by this :py:class:`LinExp`.
            
            If a number, this will be treated as a constant.
            
            If a symbol (any hashable non-number type except None) which will
            be given a coefficient of 1.
            
            .. note::
            
                Symbols are not restricted to strings. Any
                non-:py:class:`numbers.Number` type may be used. For example,
                in standard mathematical the values of a 2D array might be
                written as :math:`a_{1,1}`, :math:`a_{2,1}` and so on...
                Rather than making strings such as ``a_1_1`` which would later
                need to be parsed to extract the array coordinates, a tuples
                such as ``("a", 1, 1)`` could be used directly as symbols. For
                example::
                
                    >>> a_1_1 = LinExp(("a", 1, 1))
                    >>> a_2_1 = LinExp(("a", 2, 1))
                    >>> a_3_1 = LinExp(("a", 3, 1))
                    >>> # ...

            
            If a dictionary, each key should be a symbol (any non-number type)
            or None and each value should be the associated coefficient. The
            key None should be used for the constant term.
            
            If an existing :py:class:`LinExp`, the passed value will be
            returned by the constructor unchanged.
        """
        # If already initialised (i.e. __new__ returned an existing LinExp),
        # don't do anything
        if hasattr(self, "_coeffs"):
            return
        
        if isinstance(value, Number):
            value = {None: value}
        elif not isinstance(value, dict):
            value = {value: 1}
        
        # This is the defining attribute in this class. It is a dictionary
        # formatted as described in the constructor with the additional
        # constrant that zero-weighted terms are dropped.
        self._coeffs = {
            symbol: coeff
            for symbol, coeff in value.items()
            if coeff != 0
        }
        
        # Python's dict type does not support hashing. The following rather
        # crude routine gives a semi-quick-to-compute hash. The hash is
        # precomputed because this routine is outrageously inefficient.
        #self._hash = sum(map(hash, self._coeffs))
    
    def symbols(self):
        """
        Return an iterator over the symbols in this :py:class:`LinExp` where
        the symbol ``None`` represents a constant term.
        """
        return six.iterkeys(self._coeffs)
    
    def __iter__(self):
        """
        Iterate over the (symbol, coefficient) pairs which make up this
        expression. The constant term (if present) is given with symbol set to
        None.
        """
        return six.iteritems(self._coeffs)
    
    def __getitem__(self, symbol):
        """
        Get the coefficient associated with a symbol.
        
        If a symbol not present in the expression is given, zero will be
        returned.
        """
        return self._coeffs.get(symbol, 0)
    
    def __contains__(self, symbol):
        """Check if a symbol has a non-zero coefficient in this expression."""
        return symbol in self._coeffs
    
    @property
    def is_constant(self):
        """
        Property. True iff this :py:class:`LinExp` represents only a constant
        value (including zero) and includes no symbols.
        """
        return (
            len(self._coeffs) == 0 or
            (len(self._coeffs) == 1 and next(iter(self._coeffs)) is None)
        )
    
    @property
    def constant(self):
        """
        If :py:attr:`is_constant` is True, returns the value as a normal
        numerical Python type. Otherwise raises :py:exc:TypeError`
        """
        if self.is_constant:
            return self[None]
        else:
            raise TypeError("LinExp is not a constant.")
    
    def __complex__(self):
        return complex(self.constant)
    
    def __float__(self):
        return float(self.constant)
    
    def __int__(self):
        return int(self.constant)
    
    @property
    def is_symbol(self):
        """
        Property. True iff this :py:class:`LinExp` represents only single
        1-weighted symbols.
        """
        return (
            len(self._coeffs) == 1 and
            next(iter(self._coeffs)) is not None and
            next(six.itervalues(self._coeffs)) == 1
        )
    
    @property
    def symbol(self):
        """
        Property. Iff this :py:class:`LinExp` contains only a single 1-weighted
        symbol (see :py:attr:`is_symbol`) returns that symbol. Otherwise throws
        a :py:exc:`TypeError`.
        """
        if self.is_symbol:
            return next(iter(self._coeffs))
        else:
            raise TypeError("LinExp contains more than a symbol.")
    
    def __bool__(self):
        return bool(self._coeffs)
    
    def __repr__(self):
        if self.is_constant:
            # Constant only
            return "{}({!r})".format(type(self).__name__, self.constant)
        elif len(self._coeffs) == 1 and next(six.itervalues(self._coeffs)) == 1:
            # (Unweighted) Symbol only
            return "{}({!r})".format(type(self).__name__, next(iter(self._coeffs)))
        else:
            return "{}({!r})".format(type(self).__name__, self._coeffs)
    
    def __str__(self):
        if not self._coeffs:
            return "0"
        else:
            # Print the symbols in order (if possible) and always print the
            # constant coefficient last
            symbols = [sym for sym in self.symbols() if sym is not None]
            try:
                symbols = sorted(symbols)
            except TypeError:
                pass
            if None in self._coeffs:
                symbols.append(None)
            
            return " + ".join(
                (
                    str(self[symbol])
                    if symbol is None else
                    str(symbol)
                    if self[symbol] == 1 else
                    "({})*{}".format(self[symbol], symbol)
                    if "/" in str(self[symbol]) else
                    "{}*{}".format(self[symbol], symbol)
                )
                for symbol in symbols
            )
    
    def __hash__(self):
        # This incredibly crude hash is used because Python's dictionaries (the
        # underlying storage for LinExp) are immutable and therefore
        # unhashable.
        #
        # The following hash implementation:
        #
        #     hash(frozenset(self._coeffs.items()))
        #
        # produces results which are fully representative of the contents of
        # this LinExp but is incredibly expensive to compute resulting in
        # significant (order 3x) overall application slow-down in various
        # realistic applications.
        #
        # Instead of the above, a very crude hash is used:
        #
        #     sum(map(hash, self._coeffs))
        #
        # This hash has the following obvious limitations which are not
        # problematic in practice:
        #
        # * **It only hashes the symbols used.** In this application, error
        #   terms are frequantly added (see affine_arithmetic) making the set
        #   of symbols in a given value unique in many case.
        # * **It mixes hashes by summing.** Despite being very poor form for a
        #   hash, performance is perfectly adequate in practice so-far...
        #
        # Aside from performance concerns, special consideration must be made
        # for LinExps containing lone constants and symbols produce the same
        # hash as their raw Python literal equivalents, i.e.:
        #
        #     hash(LinExp(123)) == hash(123)
        #     hash(LinExp("a")) == hash("a")
        #
        if self.is_constant:
            return hash(self.constant)
        else:
            return sum(map(hash, self._coeffs))
    
    def __eq__(self, other):
        try:
            other = LinExp(other)
        except TypeError:
            return False
        
        return self._coeffs == other._coeffs
    
    def __lt__(self, other):
        diff = self - other
        
        # Note that we can only compare values whose free symbols exactly
        # cancel out
        if diff.is_constant:
            return diff.constant < 0
        else:
            return NotImplemented
    
    @classmethod
    def _pairwise_operator(cls, a, b, op):
        try:
            a = cls(a)
            b = cls(b)
        except TypeError:
            return NotImplemented
        
        new_coeffs = a._coeffs.copy()
        for symbol, coeff in b:
            new_coeffs[symbol] = op(new_coeffs.get(symbol, 0), coeff)
        
        return cls(new_coeffs)
    
    def __add__(self, other):
        return self._pairwise_operator(self, other, operator.add)
    def __sub__(self, other):
        return self._pairwise_operator(self, other, operator.sub)
    def __radd__(self, other):
        return self._pairwise_operator(other, self, operator.add)
    def __rsub__(self, other):
        return self._pairwise_operator(other, self, operator.sub)
    
    @classmethod
    def _mul_operator(cls, a, b):
        try:
            a = cls(a)
            b = cls(b)
        except TypeError:
            return NotImplemented
        
        # Only multiplication by a constant is supported (since anything else
        # will result in a polynomial (non-linear) expression).
        if a.is_constant:
            linexp = b
            constant = a.constant
        elif b.is_constant:
            linexp = a
            constant = b.constant
        else:
            return NotImplemented
        
        return cls({
            symbol: coeff * constant
            for symbol, coeff in linexp
        })
    
    def __mul__(self, other):
        return self._mul_operator(self, other)
    def __rmul__(self, other):
        return self._mul_operator(other, self)
    
    @classmethod
    def _div_operator(cls, a, b):
        try:
            a = cls(a)
            b = cls(b)
        except TypeError:
            return NotImplemented
        
        # Division is only supported in the following cases:
        # * Both sides are constants
        # * where RHS = constant
        # * where LHS = constant*RHS (and the result is constant)
        # In all other cases, the result will become non-linear
        if b.is_constant:
            constant = b.constant
            
            # NB: Convert integers into Fraction (rational) numbers so that the
            # reciprocal operation in the next step continues to produce exact
            # results.
            if isinstance(constant, Integral):
                constant = Fraction(constant)
            
            return a * (1 / constant)
        else:
            # Check if the LHS is a multiple of the RHS (special case: or that
            # LHS is zero)
            if a._coeffs and (set(a._coeffs) != set(b._coeffs)):
                return NotImplemented
            
            # NB: Because we know the RHS is not a constant (and therefore not
            # zero) we know there will be at least one symbol and so this loop
            # will run at least once.
            factor = None
            for symbol in b.symbols():
                lcoeff = a[symbol]
                rcoeff = b[symbol]
                
                # Use Fractions (if possible) to ensure exact results
                if isinstance(lcoeff, Integral):
                    lcoeff = Fraction(lcoeff)
                if isinstance(rcoeff, Integral):
                    rcoeff = Fraction(rcoeff)
                
                this_factor = lcoeff/rcoeff
                if factor is not None and this_factor != factor:
                    return NotImplemented
                factor = this_factor
            
            return cls(factor)
    
    # Python 3.x only
    def __truediv__(self, other):
        return self._div_operator(self, other)
    def __rtruediv__(self, other):
        return self._div_operator(other, self)
    
    # Python 2.x only
    def __div__(self, other):
        return self._div_operator(self, other)
    def __rdiv__(self, other):
        return self._div_operator(other, self)
    
    @classmethod
    def _pow_operator(cls, a, b):
        try:
            a = cls(a)
            b = cls(b)
        except TypeError:
            return NotImplemented
        
        # Only supported when both values are constants since anything else
        # would result in a non-linear expression
        if not (a.is_constant and b.is_constant):
            return NotImplemented
        
        return cls(a.constant ** b.constant)
    
    def __pow__(self, other, modulo=None):
        if modulo is not None:
            return NotImplemented
        return self._pow_operator(self, other)
    def __rpow__(self, other):
        return self._pow_operator(other, self)
    
    def __neg__(self):
        return LinExp({
            symbol: -coeff
            for symbol, coeff in self
        })
    
    def __pos__(self):
        return self
    
    def subs(self, substitutions):
        """
        Substitute symbols in this linear expression for new values.
        
        Parameters
        ==========
        substitutions : {symbol: number or symbol or :py:class:`LinExp`, ...}
            Substitutions to carry out. Substitutions will be carried out
            as if performed simultaneously.
        
        Returns
        =======
        linexp : :py:class:`LinExp`
            A new expression once the substitution has been carried out.
        """
        # This implementation is fairly low-level for efficiency reasons as
        # substitutions are an important operation, e.g. in computation of
        # expression values for specific symbol values.
        
        new_coeffs = defaultdict(lambda: 0)
        
        for symbol, coeff in self:
            if symbol not in substitutions:
                # No change (note that a previous symbol may have been
                # substituted for this symbol, hence the need to add here)
                new_coeffs[symbol] += coeff
            elif substitutions[symbol] == 0:
                # Coefficient set to zero
                pass
            elif isinstance(substitutions[symbol], Number):
                # Symbol replaced with number
                new_coeffs[None] += coeff * substitutions[symbol]
            elif isinstance(substitutions[symbol], type(self)):
                # Symbol replaced with linear expression
                for sub_symbol, sub_coeff in substitutions[symbol]:
                    new_coeffs[sub_symbol] += sub_coeff * coeff
            else:
                # Symbol replaced with another symbol
                new_coeffs[substitutions[symbol]] += coeff
        
        return LinExp(new_coeffs)
