r"""
Infinite Arrays
===============

Infinite array types which may be used to construct algebraic descriptions of
wavelet filters on infinite inputs.

:py:class:`InfiniteArray` types
-------------------------------

The implementation assumes all inputs (and therefore outputs) to every
operation are infinite 2D arrays. As a consequence, no edge-extension or
padding is performed and so no artefacts from these processes appear in the
results. This is useful when analysing the general behaviour of a filter since
there is no need to determine which outputs are free from edge artefacts.

The underlying type used in this module is the :py:class:`InfiniteArray`. An
:py:class:`InfiniteArray` is an :math:`n`-dimensional array which may be
indexed using the usual Python syntax (e.g. an element in a 2D array might be
accessed as ``a[1, -2]``).

Entries in an :py:class:`InfiniteArray` are computed on demand (infinite memory
not required!) and the actual values depend entirely on the implementation of
the :py:class:`InfiniteArray` subclass.

.. autoclass:: InfiniteArray
    :members:

Typically, the starting point to any filtering operation will be one or more
:py:class:`SymbolArray`\ s.

.. autoclass:: SymbolArray

A single, one-dimensional lifting filter stage may be applied to the values in
a :py:class:`InfiniteArray` using:

.. autoclass:: LiftedArray

Values may be subjected to a bit-shift operation using:

.. autoclass:: LeftShiftedArray

.. autoclass:: RightShiftedArray

Arrays may be subsampled or interleaved, producing new
:py:class:`InfiniteArray`\ s, using:

.. autoclass:: SubsampledArray

.. autoclass:: InterleavedArray


Array period
------------

While :py:class:`InfiniteArray`\ s have an infinite number of elements,
these elements are typically very similar.

Consider the following example:

    >>> from vc2_conformance.tables import LIFTING_FILTERS, WaveletFilters
    >>> from vc2_conformance.wavelet_filter_analysis.infinite_arrays import (
    ...     SymbolArray,
    ...     LiftedArray,
    ... )
    
    >>> v = SymbolArray(2)
    >>> stage = LIFTING_FILTERS[WaveletFilters.haar_no_shift].stages[0]
    >>> out = LiftedArray(v, stage, 0)
    
    >>> out[0, 0]
    e_1 + v_0_0 - v_1_0/2 - 1/2
    >>> out[1, 0]
    v_1_0
    >>> out[2, 0]
    e_2 + v_2_0 - v_3_0/2 - 1/2
    >>> out[3, 0]
    v_3_0

In this example, after a lifting stage all odd-numbered values consist of a
single symbol and all even numbered values follow the same algebraic pattern
(i.e. ``e_? + v_?_0 - v_?_0/2 - 1/2``).

An array's *period* is the period with which the algebraic structures in the
array repeat. The array in the example has a period of (2, 1) because the
pattern of values repeats every two elements horizontally and on every element
vertically. The period of a given :py:class:`InfiniteArray` can be obtained
from its :py:attr:`~InfiniteArray.period` property. For example::

    >>> out.period
    (2, 1)
    
    >>> # NB: SymbolArrays always have a period of 1 in every dimension
    >>> v.period
    (1, 1)


Relative step sizes
-------------------

When a :py:class:`SubsampledArray` or :py:class:`InterleavedArray` is used, the
step size between neighbouring indices in the resulting array changes. For
exaple, consider the following::

    >>> from vc2_conformance.wavelet_filter_analysis.infinite_arrays import (
    ...     SymbolArray,
    ...     SubsampledArray,
    ...     InterleavedArray,
    ... )
    
    >>> v = SymbolArray(2)
    >>> ss = SubsampledArray(v, (2, 3), (0, 0))
    
    >>> ss[0, 0]
    v_0_0
    >>> ss[1, 0]
    v_2_0
    >>> ss[2, 0]
    v_4_0
    >>> ss[0, 1]
    v_0_3
    >>> ss[0, 2]
    v_0_6

Here the step size of the array ``ss`` is twice (horizontally) and thrice
(vertically) that of the array ``a``.

Conversely::

    >>> v1 = SymbolArray(2, "v1")
    >>> v2 = SymbolArray(2, "v2")
    >>> il = InterleavedArray(v1, v2, 0)
    
    >>> il[0, 0]
    v1_0_0
    >>> il[2, 0]
    v1_1_0
    >>> il[4, 0]
    v1_2_0
    >>> il[0, 1]
    v1_0_1
    >>> il[0, 2]
    v1_0_2

This time, the step size of ``il`` is half, horizontally, that of ``v1`` (or
``v2``) but the same vertically.

The step size relationships between pairings of arrays may be looked up using
the :py:meth:`InfiniteArray.relative_step_size_to` method. For example::

    >>> ss.relative_step_size_to(v)
    (Fraction(2, 1), Fraction(3, 1))
    >>> il.relative_step_size_to(v1)
    (Fraction(1, 2), Fraction(1, 1))


Periodic Caching
----------------

When a large chain of :py:class:`InfiniteArray`\ s have been chained together,
computing the value of an element can become expensive. The
:py:class:`PeriodicCachingArray` array implements a smart caching behaviour for
arrays whose contents follow a regular pattern.

.. autoclass:: PeriodicCachingArray

"""

import re

from fractions import Fraction

from vc2_conformance.wavelet_filter_analysis.linexp import LinExp

from vc2_conformance.tables import LiftingFilterTypes

from vc2_conformance._py2x_compat import gcd

import vc2_conformance.wavelet_filter_analysis.affine_arithmetic as aa


__all__ = [
    "InfiniteArray",
    "SymbolArray",
    "LiftedArray",
    "RightShiftedArray",
    "LeftShiftedArray",
    "SubsampledArray",
    "InterleavedArray",
    "PeriodicCachingArray",
]


def lcm(a, b):
    """
    Compute the Lowest Common Multiple (LCM) of two integers.
    """
    return abs(a*b) // gcd(a, b)


class InfiniteArray(object):
    """
    An abstract base class describing an immutable infinite N-dimensional array
    of symbolic values.
    
    Subclasses should implement :py:meth:`get` to return the value at a given
    position in an array.
    
    Instances of this type may be indexed like an N-dimensional array. 
    """
    
    def __init__(self, ndim):
        self._ndim = ndim
        self._cache = {}
    
    def __getitem__(self, keys):
        if not isinstance(keys, tuple):
            keys = (keys, )
        
        if len(keys) != self._ndim:
            raise TypeError("{dims}D ValueArray requires {dims}D coordinates".format(
                dims=self._ndim,
            ))
        
        if keys in self._cache:
            return self._cache[keys]
        else:
            value = self.get(keys)
            self._cache[keys] = value
            return value
    
    def get(self, keys):
        """
        Called by :py:meth:`__getitem__` with a tuple of array indices.
        
        The array of keys is guaranteed to be a tuple with :py:data:`ndim`
        entries.
        
        Values returned by this method will be memoized (cached) by
        :py:meth:`__getitem__`. Consequently, this method will only be called
        the first time a particular array index is requested. Subsequent
        accesses will return the cached value.
        """
        raise NotImplementedError()
    
    @property
    def ndim(self):
        """The number of dimensions in the array."""
        return self._ndim
    
    
    @property
    def period(self):
        """
        Return the period of this array.
        
        An array's period is the interval at which the algebraic form of
        elements in the array are similar (see
        :mod:`vc2_conformance.wavelet_filter_analysis.infinite_arrays`).
        
        Returns
        =======
        period : (int, ...)
            The period of the array in each dimension.
        """
        raise NotImplementedError()
    
    def relative_step_size_to(self, other):
        r"""
        For a step along a dimension in this array, compute the equivalent step
        size in the provided array.
        
        Parameters
        ==========
        other : :py:class:`InfiniteArray`
            An array to compare the step size with. Must have been used (maybe
            indirectly) to define this array.
        
        Returns
        =======
        relative_step_size : (:py:class:`fractions.Fraction`, ...) or None
            The relative step sizes for each dimension, or None if the provided
            array was not used in the computation of this array.
        """
        raise NotImplementedError()


class SymbolArray(InfiniteArray):
    
    def __init__(self, ndim, prefix="v"):
        r"""
        An infinite array of :py:class:`LinExp` symbols.
        
        Symbols will be identified by tuples like ``(prefix, n)`` for a one
        dimensional array, ``(prefix, n, n)`` for a two-dimensional array,
        ``(prefix, n, n, n)`` for a three-dimensional array and so-on.
        
        Example usage::
    
            >>> a = SymbolArray(3, "foo")
            >>> a[1, 2, 3]
            LinExp(('foo', 1, 2, 3))
            >>> a[100, -5, 0]
            LinExp(('foo', 100, -5, 0))
        
        Parameters
        ==========
        ndim : int
            The number of dimensions in the array.
        prefix : object
            A prefix to be used as the first element of every symbol tuple.
        """
        self._prefix = prefix
        super(SymbolArray, self).__init__(ndim)
    
    def get(self, keys):
        return LinExp((self._prefix, ) + keys)
    
    @property
    def prefix(self):
        """The prefix used for all symbol names in this array."""
        return self._prefix
    
    @property
    def period(self):
        return (1, ) * self.ndim
    
    def relative_step_size_to(self, other):
        if other is self:
            return (Fraction(1), ) * self.ndim
        else:
            return None


class LiftedArray(InfiniteArray):
    
    def __init__(self, input_array, stage, filter_dimension):
        """
        Apply a one-dimensional lifting filter step to an array, as described
        in the VC-2 specification (15.4.4).
        
        In this implementation, affine arithmetic (rather than truncating
        integer arithmetic) is used. Consequently, rounding errors which would
        be present in an integer implementation are represented by the
        insertion of error terms (see
        :py:mod:`~vc2_conformance.wavelet_filter_analysis.affine_arithmetic`).
        
        Parameters
        ==========
        input_array : :py:class:`InfiniteArray`
            The input array whose entries will be filtered by the specified
            lifting stage.
        stage : :py:class:`vc2_conformance.tables.LiftingStage`
            A description of the lifting stage.
        interleave_dimension: int
            The dimension along which the filter will act.
        """
        if filter_dimension >= input_array.ndim:
            raise TypeError("filter dimension out of range")
        
        self._input_array = input_array
        self._stage = stage
        self._filter_dimension = filter_dimension
        
        super(LiftedArray, self).__init__(self._input_array.ndim)
    
    # For each lifting stage type, does this update the odd or even numbered
    # samples?
    LIFT_UPDATES_EVEN = {
        LiftingFilterTypes.even_add_odd: True,
        LiftingFilterTypes.even_subtract_odd: True,
        LiftingFilterTypes.odd_add_even: False,
        LiftingFilterTypes.odd_subtract_even: False,
    }
    
    # For each lifting stage type, does this add or subtract the sum of the
    # weighted filter taps to the sample being updated?
    LIFT_ADDS = {
        LiftingFilterTypes.even_add_odd: True,
        LiftingFilterTypes.even_subtract_odd: False,
        LiftingFilterTypes.odd_add_even: True,
        LiftingFilterTypes.odd_subtract_even: False,
    }
    
    def get(self, keys):
        key = keys[self._filter_dimension]
        
        is_even = (key & 1) == 0
        
        if is_even != LiftedArray.LIFT_UPDATES_EVEN[self._stage.lift_type]:
            # This lifting stage doesn't update this sample index; pass through
            # existing value.
            return self._input_array[keys]
        else:
            # This sample is updated by the lifting stage, work out the filter
            # coefficients.
            tap_indices = [
                key + (i*2) - 1
                for i in range(
                    self._stage.D,
                    self._stage.L + self._stage.D,
                )
            ]
            
            taps = [
                self._input_array[tuple(
                    key if i != self._filter_dimension else tap_index
                    for i, key in enumerate(keys)
                )]
                for tap_index in tap_indices
            ]
            
            total = sum(
                tap * weight
                for tap, weight in zip(taps, self._stage.taps)
            )
            
            if self._stage.S > 0:
                total += 1 << (self._stage.S - 1)
            
            # Right-shift replaced with division and error term to enable it to
            # work with LinExp
            total = aa.div(total, 1 << self._stage.S)
            
            if LiftedArray.LIFT_ADDS[self._stage.lift_type]:
                return self._input_array[keys] + total
            else:
                return self._input_array[keys] - total
    
    @property
    def period(self):
        # A lifting filter applies the same filtering operation to all odd and
        # all even entries in an array.
        #
        # For an input with period 1 or 2, this results in an output with
        # period 2 (since all odd samples will be the result of one filtering
        # operation and all even samples another).
        #
        #           Input (period=1)              Input (period=2)
        #      +---+---+---+---+---+---+     +---+---+---+---+---+---+
        #      | a | a | a | a | a | a |     | a | b | a | b | a | b |
        #      +---+---+---+---+---+---+     +---+---+---+---+---+---+
        #                  |                             |
        #                  |                             |
        #                  V                             V
        #      +---+---+---+---+---+---+     +---+---+---+---+---+---+
        #      | Ea| Oa| Ea| Oa| Ea| Oa|     | Ea| Ob| Ea| Ob| Ea| Ob|
        #      +---+---+---+---+---+---+     +---+---+---+---+---+---+
        #          Output (period=2)             Output (period=2)
        #
        #                              +---+
        #                       Key:   | Ea|
        #                              +---+
        #                               /  \
        #                              /    \
        #             'E' = Even filter      'a' = Aligned with input 'a'
        #             'O' = Odd filter       'b' = Aligned with input 'b'
        #                                    ...
        # For inputs with an *even* period greater than 2, the resulting output
        # will have the same period as the input:
        #
        #             Input (period=4)
        #     +---+---+---+---+---+---+---+---+
        #     | a | b | c | d | a | b | c | d |
        #     +---+---+---+---+---+---+---+---+
        #                     |
        #                     |
        #                     V
        #     +---+---+---+---+---+---+---+---+
        #     | Ea| Ob| Ec| Od| Ea| Ob| Ec| Od|
        #     +---+---+---+---+---+---+---+---+
        #             Output (period=4)
        #
        # Finally, for inputs with an *odd* period greater than 2, the
        # resulting output will have a period of *double* the input as the
        # filters drift in and out of phase with the repeating input:
        #
        #                     Input (period=3)
        #     +---+---+---+---+---+---+---+---+---+---+---+---+
        #     | a | b | c | a | b | c | a | b | c | a | b | c |
        #     +---+---+---+---+---+---+---+---+---+---+---+---+
        #                             |
        #                             |
        #                             V
        #     +---+---+---+---+---+---+---+---+---+---+---+---+
        #     | Ea| Ob| Ec| Oa| Eb| Oc| Ea| Ob| Ec| Oa| Eb| Oc|
        #     +---+---+---+---+---+---+---+---+---+---+---+---+
        #                     Output (period=6)
        
        return tuple(
            lcm(2, p) if dim == self._filter_dimension else p
            for dim, p in enumerate(self._input_array.period)
        )
    
    def relative_step_size_to(self, other):
        if other is self:
            return (Fraction(1), ) * self.ndim
        else:
            return self._input_array.relative_step_size_to(other)


class RightShiftedArray(InfiniteArray):
    
    def __init__(self, input_array, shift_bits=1):
        r"""
        Apply a right bit shift (implemented as a division) to every value in
        an input array.
        
        The right-shift operation is based on the description in the VC-2
        specification (15.4.3). Specifically, :math:`2^\textrm{shift_bits-1}`
        is added to the input values prior to the right-shift operation (which
        is used to implement rounding behaviour in integer arithmetic).
        
        In this implementation, affine arithmetic (rather than truncating
        integer arithmetic) is used. Consequently, rounding errors which would
        be present in an integer implementation are represented by the
        insertion of error terms (see
        :py:mod:`~vc2_conformance.wavelet_filter_analysis.affine_arithmetic`).
        
        Parameters
        ==========
        input_array : :py:class:`InfiniteArray`
            The array to have its values right-sifted
        shift_bits: int
            Number of bits to shift by
        """
        self._input_array = input_array
        self._shift_bits = shift_bits
        
        super(RightShiftedArray, self).__init__(self._input_array.ndim)
    
    def get(self, keys):
        if self._shift_bits == 0:
            return self._input_array[keys]
        else:
            value = self._input_array[keys]
            value += 1 << (self._shift_bits - 1)
            value = aa.div(value, 1 << self._shift_bits)
            
            return value
    
    @property
    def period(self):
        return self._input_array.period
    
    def relative_step_size_to(self, other):
        if other is self:
            return (Fraction(1), ) * self.ndim
        else:
            return self._input_array.relative_step_size_to(other)


class LeftShiftedArray(InfiniteArray):
    
    def __init__(self, input_array, shift_bits=1):
        """
        Apply a left bit shift (implemented as a multiplication) to every value
        in an input array.
        
        Parameters
        ==========
        input_array : :py:class:`InfiniteArray`
            The array to have its values left-shifted.
        shift_bits: int
            Number of bits to shift by.
        """
        self._input_array = input_array
        self._shift_bits = shift_bits
        
        super(LeftShiftedArray, self).__init__(self._input_array.ndim)
    
    def get(self, keys):
        return self._input_array[keys] * (1 << self._shift_bits)
    
    @property
    def period(self):
        return self._input_array.period
    
    def relative_step_size_to(self, other):
        if other is self:
            return (Fraction(1), ) * self.ndim
        else:
            return self._input_array.relative_step_size_to(other)


class SubsampledArray(InfiniteArray):
    
    def __init__(self, input_array, steps, offsets):
        """
        A subsampled view of another :py:class:`InfiniteArray`.
        
        Parameters
        ==========
        input_array : :py:class:`InfiniteArray`
            The array to be subsampled.
        steps, offsets: (int, ...)
            Tuples giving the step size and start offset for each dimension.
            
            When this array is indexed, the index into the input array is
            computed as::
            
                input_array_index[n] = (index[n] * step[n]) + offset[n]
        """
        if len(steps) != len(offsets):
            raise TypeError("steps and offsets do not match in length")
        if input_array.ndim != len(steps):
            raise TypeError("length of steps and offsets do not match input dimensions")
        
        self._input_array = input_array
        self._steps = steps
        self._offsets = offsets
        
        super(SubsampledArray, self).__init__(self._input_array.ndim)
    
    def get(self, keys):
        return self._input_array[tuple(
            (key*step) + offset
            for key, step, offset in zip(keys, self._steps, self._offsets)
        )]
    
    @property
    def period(self):
        # In cases where the input period is divisible by the step size,
        # the output period will be the former divided by the latter:
        #
        #           Input (period=2)
        #      +---+---+---+---+---+---+
        #      | a | b | a | b | a | b |
        #      +---+---+---+---+---+---+
        #        .       . |     .
        #        .       . |     .       step=2, offset=0
        #        .       . V     .
        #      +-------+-------+-------+
        #      | a     | a     | a     |
        #      +-------+-------+-------+
        #          Output (period=1)
        #
        # However, if the input period is not evenly divisible by the step
        # interval, the resulting output period will be greater due to the
        # changing phase relationship of the subsampling and input period.
        #
        #                      Input (period=3)
        #      +---+---+---+---+---+---+---+---+---+---+---+---+
        #      | a | b | c | a | b | c | a | b | c | a | b | c |
        #      +---+---+---+---+---+---+---+---+---+---+---+---+
        #        .       .       .     | .       .       .
        #        .       .       .     | .       .       .       step=2, offset=0
        #        .       .       .     V .       .       .
        #      +-------+-------+-------+-------+-------+-------+
        #      | a     | c     | b     | a     | c     | b     |
        #      +-------+-------+-------+-------+-------+-------+
        #                     Output (period=3)
        #
        # Expressed mathematically, the actual period is found as the LCM of
        # the input period and step size, divided by the step size.
        return tuple(
            lcm(p, step)//step
            for p, step in zip(self._input_array.period, self._steps)
        )
    
    def relative_step_size_to(self, other):
        if other is self:
            return (Fraction(1), ) * self.ndim
        
        relative_step_size = self._input_array.relative_step_size_to(other)
        if relative_step_size is None:
            return None
        
        return tuple(
            step_size * prev_relative_step_size
            for step_size, prev_relative_step_size in zip(
                self._steps,
                relative_step_size,
            )
        )


class InterleavedArray(InfiniteArray):
    
    def __init__(self, array_even, array_odd, interleave_dimension):
        r"""
        An array view which interleaves two :py:class:`InfiniteArray`\ s
        together into a single array.
        
        Parameters
        ==========
        array_even, array_odd : :py:class:`InfiniteArray`
            The two arrays to be interleaved. 'array_even' will be used for
            even-indexed values in the specified dimension and 'array_odd' for
            odd.
        interleave_dimension: int
            The dimension along which the two arrays will be interleaved.
        """
        if array_even.ndim != array_odd.ndim:
            raise TypeError("arrays do not have same number of dimensions")
        if interleave_dimension >= array_even.ndim:
            raise TypeError("interleaving dimension out of range")
        
        self._array_even = array_even
        self._array_odd = array_odd
        self._interleave_dimension = interleave_dimension
        
        super(InterleavedArray, self).__init__(self._array_even.ndim)
    
    def get(self, keys):
        is_even = (keys[self._interleave_dimension] & 1) == 0
        
        downscaled_keys = tuple(
            key if i != self._interleave_dimension else key//2
            for i, key in enumerate(keys)
        )
        
        if is_even:
            return self._array_even[downscaled_keys]
        else:
            return self._array_odd[downscaled_keys]
    
    @property
    def period(self):
        # When a pair of arrays are interleaved the resulting period in the
        # interleaved dimension will be double the LCM of their respective
        # periods. This is because, the respective phases of the two inputs may
        # drift with respect to eachother. For example:
        #
        #      +-------+-------+-------+-------+
        #      | a     | a     | a     | a     | Input (period=1)
        #      +-------+-------+-------+-------+
        #      +-.-----+-.-----+-.-----+-.-----+
        #      | .   A | .   B | .   A | .   B | Input (period=2)
        #      +-.-----+-.-----+-.-----+-.-----+
        #        .   .   .   . | .   .   .   .
        #        .   .   .   . | .   .   .   .
        #        .   .   .   . V .   .   .   .
        #      +---+---+---+---+---+---+---+---+
        #      | a | A | a | B | a | A | a | B | Output (period=4)
        #      +---+---+---+---+---+---+---+---+
        #
        # Example 2:
        #
        #      +-------+-------+-------+-------+-------+-------+
        #      | a     | b     | a     | b     | a     | b     | Input (period=2)
        #      +-------+-------+-------+-------+-------+-------+
        #      +-.-----+-.-----+-.-----+-.-----+-.-----+-.-----+
        #      | .   A | .   B | .   C | .   A | .   B | .   C | Input (period=3)
        #      +-.-----+-.-----+-.-----+-.-----+-.-----+-.-----+
        #        .   .   .   .   .   . | .   .   .   .   .   .
        #        .   .   .   .   .   . | .   .   .   .   .   .
        #        .   .   .   .   .   . V .   .   .   .   .   .
        #      +---+---+---+---+---+---+---+---+---+---+---+---+
        #      | a | A | b | B | a | C | b | A | a | B | b | C | Output (period=12)
        #      +---+---+---+---+---+---+---+---+---+---+---+---+
        #
        # In the dimension not being interleaved, the period will simply be the
        # LCM of the two inputs in that dimension as the phases of the
        # interleaved values drift with respect to eachother. In the
        # illustraton below, interleaving occurs on dimension 1:
        #
        #      +---+---+---+---+---+---+---+---+---+---+---+---+
        #      | a | b | a | b | a | b | a | b | a | b | a | b | Input (period=(2, xxx))
        #      +---+---+---+---+---+---+---+---+---+---+---+---+
        #      +---+---+---+---+---+---+---+---+---+---+---+---+
        #      | A | B | C | A | B | C | A | B | C | A | B | C | Input (period=(3, xxx))
        #      +---+---+---+---+---+---+---+---+---+---+---+---+
        #                              |
        #                              |
        #                              V
        #      +---+---+---+---+---+---+---+---+---+---+---+---+
        #      | a | b | a | b | a | b | a | b | a | b | a | b |
        #      +---+---+---+---+---+---+---+---+---+---+---+---+ Output (period=(6, xxx))
        #      | A | B | C | A | B | C | A | B | C | A | B | C |
        #      +---+---+---+---+---+---+---+---+---+---+---+---+
        return tuple(
            lcm(pa, pb) * (2 if dim == self._interleave_dimension else 1)
            for dim, (pa, pb) in enumerate(zip(
                self._array_even.period,
                self._array_odd.period,
            ))
        )
    
    def relative_step_size_to(self, other):
        if other is self:
            return (Fraction(1), ) * self.ndim
        
        even_step_size = self._array_even.relative_step_size_to(other)
        odd_step_size = self._array_odd.relative_step_size_to(other)
        
        if even_step_size is None and odd_step_size is None:
            return None
        
        if even_step_size is not None and not odd_step_size is None:
            raise ValueError(
                "Cannot find relative step size of {} in {} "
                "as it is interleaved with itself.".format(other, self)
            )
        
        if even_step_size is not None:
            relative_step_size = even_step_size
        else:
            relative_step_size = odd_step_size
        
        return tuple(
            s/2 if d == self._interleave_dimension else s
            for d, s in enumerate(relative_step_size)
        )
