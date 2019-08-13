r"""
Infinite VC-2 Filters
=====================

An implementation of VC-2's wavelet filters based on symbolic arithmetic acting
over an infinite picture.

This module may be used to obtain algebraic expressions describing the complete
arithmetic required to produce any given intermediate or output value during
the encoding or decoding process.

Infinite arrays
---------------

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
not required!) and the actual values held depend entirely on the
:py:class:`InfiniteArray` subclass.

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


Error terms
-----------

Though all arithmetic is carried out as if using (infinite precision) real
numbers, wherever a right shift (truncating integer division) is performed in
the above classes an error term (with a unique name like :math:`e_{123}`) is
added to the result, standing in for the possible rounding error in the range
:math:`[0, 1)`.

Error symbols are created using:

.. autofunction:: new_error_term

The error symbols in a given expression may be stripped out using:

.. autofunction:: strip_error_terms

The following function may be used to work out the worst-case error bounds for
a given expression. The lower-bound is defined as when all negatively-weighted
error terms are 1 and all positively weighted errors are 0.  Conversely the
upper-bound is given when all positively-weighted error terms are set to 1 and
the negatively-weighted terms are 0.

.. autofunction:: worst_case_error_bounds

"""

from sympy import Symbol, sympify

from vc2_conformance.tables import LiftingFilterTypes


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


def worst_case_error_bounds(expression):
    """
    Calculate the worst-case error bounds for the value of the provided
    expression.
    
    Returns
    =======
    lower_bound, upper_bound
    """
    expression = sympify(expression)
    
    lower_bound = expression.subs({
        sym: 1 if expression.coeff(sym) < 0 else 0
        for sym in expression.free_symbols
        if sym.name.startswith("e_")
    })
    
    upper_bound = expression.subs({
        sym: 1 if expression.coeff(sym) > 0 else 0
        for sym in expression.free_symbols
        if sym.name.startswith("e_")
    })
    
    return lower_bound, upper_bound


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


class SymbolArray(InfiniteArray):
    
    def __init__(self, ndim, prefix="v"):
        r"""
        An infinite array of :py:mod:`sympy`
        :py:class:`~sympy.core.symbol.Symbol`\ s.
        
        Symbols names in the array will be of the form ``v_123`` for a one
        dimensional array, ``v_123_321` for a two-dimensional array,
        ``v_1_2_3`` for a three-dimensional array and so-on. The symbol's
        prefix may be changed using the 'prefix' argument to the constructor.
        
        Example usage::
    
            >>> a = SymbolArray(3, "foo")
            >>> a[1, 2, 3]
            foo_1_2_3
            >>> a[100, -5, 0]
            foo_100_-5_0
        
        Parameters
        ==========
        ndim : int
            The number of dimensions in the array.
        prefix : str
            A prefix to be used as the start of every symbol's name.
        """
        self._prefix = prefix
        super(SymbolArray, self).__init__(ndim)
    
    def get(self, keys):
        return Symbol("{}_{}".format(
            self._prefix,
            "_".join(map(str, keys)),
        ))


class LiftedArray(InfiniteArray):
    
    def __init__(self, input_array, stage, filter_dimension):
        """
        Apply a one-dimensional lifting filter step to an array, as described
        in the VC-2 specification (15.4.4).
        
        In this implementation, real arithmetic (rather than truncating integer
        arithmetic) is used. Consequently, rounding errors which would be
        present in an integer implementation are not represented. Instead an
        error term (produced by :py:func:`new_error_term`) is added to the
        result. This error term should be considered as lying in the range
        :math:`[0, 1)`.
        
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
            # work with SymPy
            total /= 1 << self._stage.S
            total -= new_error_term()
            
            if LiftedArray.LIFT_ADDS[self._stage.lift_type]:
                return self._input_array[keys] + total
            else:
                return self._input_array[keys] - total


class RightShiftedArray(InfiniteArray):
    
    def __init__(self, input_array, shift_bits=1):
        r"""
        Apply a right bit shift (implemented as a division) to every value in
        an input array.
        
        The right-shift operation is based on the description in the VC-2
        specification (15.4.3). Specifically, :math:`2^\textrm{shift_bits-1}`
        is added to the input values prior to the right-shift operation (which
        is used to implement rounding behaviour in integer arithmetic).
        
        In this implementation, real arithmetic (rather than truncating integer
        arithmetic) is used. Consequently, rounding errors which would be
        present in an integer implementation are not represented. Instead an
        error term (produced by :py:func:`new_error_term`) is added to the
        result. This error term should be considered as lying in the range
        :math:`[0, 1)`.
        
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
            value /= 1 << self._shift_bits
            value -= new_error_term()
            
            return value


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


def vh_analysis(h_filter_params, v_filter_params, array):
    r"""
    Return a set of four :py:class:`InfiniteArray`\ s resulting from applying a
    single VC-2 wavelet analysis filtering level to the provided input array.
    """
    shifted_array = LeftShiftedArray(array, h_filter_params.filter_bit_shift)
    
    filtered_array = shifted_array
    for stage in h_filter_params.stages:
        filtered_array = LiftedArray(filtered_array, stage, 0)
    for stage in v_filter_params.stages:
        filtered_array = LiftedArray(filtered_array, stage, 1)
    
    ll_array = SubsampledArray(filtered_array, (2, 2), (0, 0))
    hl_array = SubsampledArray(filtered_array, (2, 2), (1, 0))
    lh_array = SubsampledArray(filtered_array, (2, 2), (0, 1))
    hh_array = SubsampledArray(filtered_array, (2, 2), (1, 1))
    
    return ll_array, hl_array, lh_array, hh_array


def h_analysis(h_filter_params, array):
    r"""
    Return a set of two :py:class:`InfiniteArray`\ s resulting from applying a
    single horizontal-only VC-2 wavelet analysis filtering level to the
    provided input array.
    """
    shifted_array = LeftShiftedArray(array, h_filter_params.filter_bit_shift)
    
    filtered_array = shifted_array
    for stage in h_filter_params.stages:
        filtered_array = LiftedArray(filtered_array, stage, 0)
    
    l_array = SubsampledArray(filtered_array, (2, 1), (0, 0))
    h_array = SubsampledArray(filtered_array, (2, 1), (1, 0))
    
    return l_array, h_array


def dwt(h_filter_params, v_filter_params, dwt_depth, dwt_depth_ho, array):
    """
    Perform a multi-level VC-2 wavelet transform on a
    :py:class:`InfiniteArray`.
    """
    coeff_arrays = {}
    
    dc = array
    for n in reversed(range(dwt_depth_ho + 1,
                            dwt_depth_ho + dwt_depth + 1)):
        ll, hl, lh, hh = vh_analysis(h_filter_params, v_filter_params, dc)
        dc = ll
        coeff_arrays[n] = {}
        coeff_arrays[n]["HL"] = hl
        coeff_arrays[n]["LH"] = lh
        coeff_arrays[n]["HH"] = hh
    for n in reversed(range(1, dwt_depth_ho + 1)):
        l, h = h_analysis(h_filter_params, dc)
        dc = l
        coeff_arrays[n] = {}
        coeff_arrays[n]["H"] = h
    
    coeff_arrays[0] = {}
    if dwt_depth_ho == 0:
        coeff_arrays[0]["LL"] = dc
    else:
        coeff_arrays[0]["L"] = dc
    
    return coeff_arrays


def vh_synthesis(h_filter_params, v_filter_params, ll_array, hl_array, lh_array, hh_array):
    r"""
    Return a :py:class:`InfiniteArray` resulting from applying a single VC-2
    wavelet synthesis filtering level to the provided input arrays.
    """
    array = InterleavedArray(
        InterleavedArray(ll_array, hl_array, 0),
        InterleavedArray(lh_array, hh_array, 0),
        1,
    )
    
    filtered_array = array
    for stage in v_filter_params.stages:
        filtered_array = LiftedArray(filtered_array, stage, 1)
    for stage in h_filter_params.stages:
        filtered_array = LiftedArray(filtered_array, stage, 0)
    
    shifted_array = RightShiftedArray(filtered_array, h_filter_params.filter_bit_shift)
    
    return shifted_array


def h_synthesis(h_filter_params, l_array, h_array):
    r"""
    Return a :py:class:`InfiniteArray` resulting from applying a single VC-2
    horizontal-only wavelet synthesis filtering level to the provided input
    arrays.
    """
    array = InterleavedArray(l_array, h_array, 0)
    
    filtered_array = array
    for stage in h_filter_params.stages:
        filtered_array = LiftedArray(filtered_array, stage, 0)
    
    shifted_array = RightShiftedArray(filtered_array, h_filter_params.filter_bit_shift)
    
    return shifted_array


def idwt(h_filter_params, v_filter_params, dwt_depth, dwt_depth_ho, coeff_arrays):
    """
    Perform a multi-level VC-2 wavelet transform on a
    :py:class:`InfiniteArray`.
    """
    if dwt_depth_ho == 0:
        dc = coeff_arrays[0]["LL"]
    else:
        dc = coeff_arrays[0]["L"]
    
    for n in range(1, dwt_depth_ho + 1):
        dc = h_synthesis(h_filter_params, dc, coeff_arrays[n]["H"])
    for n in range(dwt_depth_ho + 1,
                   dwt_depth_ho + dwt_depth + 1):
        dc = vh_synthesis(
            h_filter_params,
            v_filter_params,
            dc,
            coeff_arrays[n]["HL"],
            coeff_arrays[n]["LH"],
            coeff_arrays[n]["HH"],
        )
    
    return dc
