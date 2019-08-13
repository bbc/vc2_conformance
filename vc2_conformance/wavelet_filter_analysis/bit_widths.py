r"""
Wavelet Filter Bit Width Calculation
====================================

Practical implementations of VC-2 use fixed-width (integer) arithmetic. This
(heavily annotated) module implements a procedure for determining the minimum
bit width required for a working implementation. It also includes routines for
generating 'worst-case' test signals which are designed to produce extreme
values during filtering and may be used to test implementations.

Approaches to finding minimum bit widths
----------------------------------------

The number of bits required for a particular implementation depends on both the
supported input/output picture bit widths and the wavelet transforms and depths
used. Unfortunately, the relationship between these parameters and the minimum
bit width is complicated.

In the subsections below, possible approaches are discussed before finally
arriving at the solution used in this module.

Theorem Provers
```````````````

Theorem provers (such as Z3_) are capable of determining the exact bit width
required for arbitrary arithmetic problems. In fact, such systems are now
commonplace in automated software auditing tools where they are able to uncover
subtle buffer overflow type security vulnerabilities 

.. _Z3: https://github.com/Z3Prover/z3/

Computing the minimum bit width required for an arbitrary piece of arithmetic
can be shown to be NP-complete in the general case. This means that beyond a
certain problem size or complexity finding the exact minimum bit width required
becomes intractable. Unfortunately, this point is reached by almost all of the
VC-2 wavelet filters, even for for transform depths of 1.

Though it may be possible to restrict the bit width problem for VC-2 filters
sufficiently that it becomes tractable, the author has been unable to do so in
a sensible amount of time.


Fixed-point arithmetic analysis
```````````````````````````````

A conventional technique for determining bit widths required for a given piece
of fixed-point (or integer) arithmetic is to consider what may be the worst
case outcome of a given operation.

In the most naive case, one might assume that:

* Addition of two numbers with :math:`a` and :math:`b` bits respectively may
  produce a result with :math:`\max(a, b) + 1` bits in the worst case.
* Multiplication of two numbers with :math:`a` and :math:`b` bits respectively may
  produce a result with `a + b` bits in the worst case.

This approach vastly over-estimates the bit width requirements of all but the
smallest sequence of operations. For example, the summation of four 8-bit
numbers can, in the worst case, only produce a 10-bit result however the above
approach may suggest as many as 12 bits are required (depending on the order of
operations).

A similar, but more refined approach is to track the largest and smallest
values achievable at each point in the computation and, for each operation,
assume the worst case combinations of its operands to determine the new largest
and smallest values.

This approach, while an improvement, still produces gross over estimates. These
result from the fact that values which 'cancel out' are not accounted for (e.g.
in the expression :math:`a + b - a` the result only needs to be the size of
:math:`b`, but this approach will over-estimate). This type of cancellation is
commonplace in real world filters and so this approach will still produce
unacceptable over-estimates.


Real-valued filter analysis
```````````````````````````

For Finite Impulse Response (FIR) filters such as the wavelet transform, the
filter coefficients can be used to derive input signals which maximize the
output signal level for a given allowed input value range. These values can
then be used to determine the bit width required by the filter's
implementation.

For example, an FIR filter whose coefficients are :math:`[-1, 2, 3, 2, -1]`
produces the greatest possible output of any signed 8-bit input with the
samples :math:`[-128, 127, 127, 127, -128]` and the lowest possible output for
:math:`[127, -128, -128, -128, 127]`. The resulting outputs, :math:`1145` and
:math:`-1150` respectively both fit into a signed 12 bit integer. As a
consequence we can conclude that 12 bits is sufficient for this filter and
input width.

Because VC-2 uses integer arithmetic with division, the filter is not strictly
linear due to rounding. As a consequence, it is possible that the required bit
width computed for the linear filter may be a slight over or under estimate.
The possibility of under-estimating the required bit width makes this approach
unsuitable for computing bit widths since an under-estimate could result in
catastrophic numerical errors.


Real-valued filter analysis with error tracking
```````````````````````````````````````````````

This final approach, the one used in this module, is a slight extension of the
real-valued filter analysis approach above. Critically, however, it is
guaranteed to yield an answer with at least enough bits, with a very small
possibility of very slightly over-estimating the required bit depth.

As above, worst-case signals are prepared as if for a real-valued filter and
worst-case output (and intermediate) values are calculated.

Next, the filtering process is evaluated algebraically, replacing all division
operations with division plus an error term representing the rounding error,
e.g.:

.. math::
    
    \frac{a}{b} \Rightarrow \frac{a}{b} - e_i

.. note::

    A unique error term, :math:`e_i`, is introduced for every division
    operation, otherwise unrelated error terms may erroneously cancel out.

Once the final filter output's algebraic expression is arrived at, the
magnitudes of all of the error terms' coefficients may be used to determine the
upper and lower bounds on the overall error.

The :py:mod:`~vc2_conformance.wavelet_filter_analysis.symbolic_error_terms`
module provides functions for creating error terms and determining error
bounds.

This approach considers a worst-case where every division produces worst-case
rounding errors and so is guaranteed not to under-estimate the required bit
width. However, it may not be possible for every division to produce a
worst-case rounding error simultaneously so there is potential for
over-estimation of the required bit width.

Fortunately, in well designed filters, rounding errors tend to have
significantly smaller magnitudes than the signal being processed. Consequently
it is quite unlikely that accounting for rounding errors will push the signal
level into a greater number of bits, even if those errors are relatively
generous over-estimates.


Symbolic Evaluation of Pseudocode
---------------------------------

This focus of this module is implementing the two steps involved in performing
real-valued filter analysis with error tracking: finding worst-case values and
estimating worst-case rounding errors.

For both tasks, an algebraic expression describing the filters used by VC-2 is
required. The
:py:mod:`~vc2_conformance.wavelet_filter_analysis.infinite_arrays` module
provides the pieces needed to produce such an expression. The following
functions assemble these to implement VC-2's synthesis and analysis filters on
:py:class:`~InfiniteArray`\ s.

.. autofunction:: idwt

.. autofunction:: dwt

"""

__all__ = [
    "idwt",
    "dwt",
]


from vc2_conformance.wavelet_filter_analysis.infinite_arrays import (
    SymbolArray,
    LiftedArray,
    RightShiftedArray,
    LeftShiftedArray,
    SubsampledArray,
    InterleavedArray,
)


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
    Perform a multi-level VC-2 (analysis) Discrete Wavelet Transform (IDWT) on
    a :py:class:`InfiniteArray` in a manner which is the complement of the
    'idwt' pseudocode function in (15.4.1).
    
    Parameters
    ==========
    h_filter_params, v_filter_params : :py:class:`vc2_conformance.tables.LiftingFilterParameters`
        Horizontal and vertical filter parameters (e.g. from
        :py:data:`vc2_conformance.tables.LIFTING_FILTERS`.
    dwt_depth, dwt_depth_ho: int
        Transform depths for 2D and horizontal-only transforms.
    array : :py:class:`InfiniteArray`
        The picture to be analysed.
    
    Returns
    =======
    coeff_arrays : {level: {orientation: :py:class:`InfiniteArray`, ...}, ...}
        The transform coefficient values. These dictionaries are indexed the
        same way as 'coeff_data' in the idwt pseudocode function in (15.4.1) in
        the VC-2 specification.
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
    Perform a multi-level VC-2 Inverse (synthesis) Discrete Wavelet Transform
    (IDWT) on a :py:class:`InfiniteArray` in a manner equivalent to the 'idwt'
    pseudocode function in (15.4.1).
    
    Parameters
    ==========
    h_filter_params, v_filter_params : :py:class:`vc2_conformance.tables.LiftingFilterParameters`
        Horizontal and vertical filter parameters (e.g. from
        :py:data:`vc2_conformance.tables.LIFTING_FILTERS`.
    dwt_depth, dwt_depth_ho: int
        Transform depths for 2D and horizontal-only transforms.
    coeff_arrays : {level: {orientation: :py:class:`InfiniteArray`, ...}, ...}
        The transform coefficient values to use in the transform. These
        dictionaries are indexed the same way as 'coeff_data' in the idwt
        pseudocode function in (15.4.1) in the VC-2 specification.
    
    Returns
    =======
    picture : :py:class:`InfiniteArray`
        The synthesised picture.
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
