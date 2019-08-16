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


Symbolic Filter Expressions
---------------------------

This focus of this module is implementing the two steps involved in performing
real-valued filter analysis with error tracking: finding worst-case values and
estimating worst-case rounding errors.

For both tasks, an algebraic expression describing the filters used by VC-2 is
required. The
:py:mod:`~vc2_conformance.wavelet_filter_analysis.infinite_arrays` module
provides the pieces needed to produce such an expression (see the
:py:mod:`~vc2_conformance.wavelet_filter_analysis.infinite_arrays`
documentation for details). The following functions assemble these to implement
VC-2's synthesis and analysis filters on :py:class:`~InfiniteArray`\ s.

.. autofunction:: idwt

.. autofunction:: dwt

Using the above functions, symbolic representations of arbitrary VC-2 filter
configurations may be obtained as illustrated in the (synthesis) example
below::

    >>> from vc2_conformance.wavelet_filter_analysis.infinite_arrays import SymbolArray
    >>> from vc2_conformance.wavelet_filter_analysis.bit_widths import idwt
    >>> from vc2_conformance.tables import WaveletFilters, LIFTING_FILTERS
    
    >>> # In this example we'll demonstrate a 1-level 2D wavelet transform
    >>> # using a LeGall wavelet horizontally and Haar wavelet vertically.
    >>> h_filter_params = LIFTING_FILTERS[WaveletFilters.le_gall_5_3]
    >>> v_filter_params = LIFTING_FILTERS[WaveletFilters.haar_with_shift]
    >>> dwt_depth = 1
    >>> dwt_depth_ho = 0
    
    >>> # Create a series of infinite 2D arrays of sympy Symbols representing
    >>> # transform coefficients (inputs) for our transform
    >>> coeff_arrays = {
    ...     0: {"LL": SymbolArray(2, "coeff_0_L")},
    ...     1: {
    ...         "LH": SymbolArray(2, "coeff_1_LH"),
    ...         "HL": SymbolArray(2, "coeff_1_HL"),
    ...         "HH": SymbolArray(2, "coeff_1_HH"),
    ...     },
    ... }
    
    >>> # Apply the filter
    >>> picture = idwt(h_filter_params, v_filter_params, dwt_depth, dwt_depth_ho, coeff_arrays)
    
    >>> # An algebraic expression for the filter which produced output pixel
    >>> # (0, 0) is found thus:
    >>> picture[0, 0]
    coeff_0_L_0_0/2 + coeff_1_HH_-1_0/16 + coeff_1_HH_0_0/16 - coeff_1_HL_-1_0/8 - coeff_1_HL_0_0/8 - coeff_1_LH_0_0/4 - e_1/8 - e_2/8 + e_3/2 + e_4/2 - e_5 + 1/8

.. note::

    The :py:func:`make_coeff_arrays` utility function can be used to
    automatically create a nested dictionary of coefficients like the one
    defined by hand above.
    
    .. autofunction:: make_coeff_arrays

From an algebraic expression such as the example above, the equivalent FIR
filter coefficients may be easily read-off. The following function is provided
which implements this process (while omitting error terms)::

.. autofunction:: extract_coeffs

For example, the coefficients for a particular pixel may be printed like so::

    >>> for sym, coeff in extract_coeffs(picture[0, 0]).items():
    ...     print("{}: {}".format(sym, coeff))
    coeff_0_L_0_0: 1/2
    coeff_1_HH_-1_0: 1/16
    coeff_1_HH_0_0: 1/16
    coeff_1_HL_-1_0: -1/8
    coeff_1_HL_0_0: -1/8
    coeff_1_LH_0_0: -1/4


Finding every equivalent FIR filter
-----------------------------------

In general, different output pixels are the result of different filtering
processes. For example::

    >>> picture[0, 0]
    coeff_0_L_0_0/2 + coeff_1_HH_-1_0/16 + coeff_1_HH_0_0/16 - coeff_1_HL_-1_0/8 - coeff_1_HL_0_0/8 - coeff_1_LH_0_0/4 - e_1/8 - e_2/8 + e_3/2 + e_4/2 - e_5 + 1/8
    
    >>> picture[1, 0]
    coeff_0_L_0_0/4 + coeff_0_L_1_0/4 + coeff_1_HH_-1_0/32 - 3*coeff_1_HH_0_0/16 + coeff_1_HH_1_0/32 - coeff_1_HL_-1_0/16 + 3*coeff_1_HL_0_0/8 - coeff_1_HL_1_0/16 - coeff_1_LH_0_0/8 - coeff_1_LH_1_0/8 - e_1/16 - e_10 + 3*e_2/8 + e_3/4 + e_4/4 - e_6/16 + e_7/4 + e_8/4 - e_9/2 + 1/8

The figure below illustrates the series of lifting filters which imlement a
2-level LeGall synthesis transform on a simple one dimensional (interleaved)
input.

.. image:: /_static/bit_widths/filter_phases.svg
    :alt: Lifting filtering illustrated for a 2-level one dimensional LeGall filter.

In each diagram, the filters involved in producing a particular output value
are highlighted in red. As the particular combination of paths through the
filters varies at each output; the equivalent FIR filters implemented differ
too.

Since there are only a finite number of paths through the lifting filters, the
filters used to produce output pixels are repeated periodically, i.e. a
polyphase filter is implemented.

This effect is illustrated below for various pixels which have the same filter
phase:

    >>> picture[0, 0]
    coeff_0_L_0_0/2 + coeff_1_HH_-1_0/16 + coeff_1_HH_0_0/16 - coeff_1_HL_-1_0/8 - coeff_1_HL_0_0/8 - coeff_1_LH_0_0/4 - e_1/8 - e_2/8 + e_3/2 + e_4/2 - e_5 + 1/8
    >>> picture[2, 2]
    coeff_0_L_1_1/2 + coeff_1_HH_0_1/16 + coeff_1_HH_1_1/16 - coeff_1_HL_0_1/8 - coeff_1_HL_1_1/8 - coeff_1_LH_1_1/4 - e_17/8 - e_26/8 + e_27/2 + e_28/2 - e_29 + 1/8
    >>> picture[4, 6]
    coeff_0_L_2_3/2 + coeff_1_HH_1_3/16 + coeff_1_HH_2_3/16 - coeff_1_HL_1_3/8 - coeff_1_HL_2_3/8 - coeff_1_LH_2_3/4 - e_30/8 - e_31/8 + e_32/2 + e_33/2 - e_34 + 1/8

The :py:class:`~infinite_arrays.InfiniteArray` class provides the
:py:attr:`~infinite_arrays.InfiniteArray.period` proprty giving the period with
which filters repeat::

    >>> picture.period
    (2, 2)

A representative set of filters may be obtained by iterating over every pixel
within a single period (i.e. every phase of the polyphase filter).

    >>> representative_pixels = {
    ...     (x, y): picture[x, y]
    ...     for x in range(picture.period[0])
    ...     for y in range(picture.period[1])
    ... }

.. note::
    
    A single-level wavelet transform (both synthesis and analysis) will always
    produce an output with a period of two in the filtered dimension. (See the
    detailed explanation in implementation of :py:attr:`LiftedArray.period`).
    As a consequence, a single-level 2D transform will have a period of (2, 2)
    and therefore a total of four filter phases.
    
    During a multi-level synthesis transform, the number of phases (i.e. the
    period) combines multiplicitatively in each level. For example, a two-level
    2D transform will have a period of (4, 4), i.e. 16 phases and a three-level
    2D transform will have a period of (8, 8) with 64 phases. More generally,
    the number of phases for a multi-level 2D transform is given by
    :math:`(2^{\textrm{level}-1})^2`.
    
    During multi-level analysis transforms, however, subsampling results in
    fewer filter phases being added than during synthesis. This is illustrated
    in the figure below:
    
    .. image:: /_static/bit_widths/analysis_filter_phase_growth.svg
        :alt: Illustration showing the period of transform outputs before and after subsampling.
    
    When the transform output (with four phases) is subsampled, each of the
    subsampled outputs contains only one of the filter phases. Consequently,
    the input to the next transform level only has a single filter phase,
    rather than four as in the synthesis case.
    
    As shown in this example, after a two level analysis transform there are
    only 7 filter phases (rather than 16, as for the equivalent synthesis
    transform).
    
    Generically, the number of phases in a multi-level 2D analysis transform is
    :math:`3\times\textrm{level} + 1`, i.e. one for each resulting transform
    subband.


Finding extreme output values
-----------------------------

Using the above techniques we can now obtain the equivalent FIR filter
coefficients for an arbitrary VC-2 analysis or synthesis filter. From these
coefficients, finding inputs which maximise or minimise the output of a
particular filter is straightforward. For example, to produce the largest
possible result, variables with positive coefficients should be set to the
largest legal input value while variables with negative coefficients should be
assigned the smallest legal value.

The following functions follow this procedure to produce variable assignments
which elicit either the highest or lowest possible outputs:

.. autofunction:: maximise_filter_output

.. autofunction:: minimise_filter_output

For example, to find the signals which maximise and minimise the value of a
particular pixel given a hypothetical 10-bit input to our running example::

    >>> from vc2_conformance.wavelet_filter_analysis.bit_widths import (
    ...     extract_coeffs,
    ...     maximise_filter_output,
    ...     minimise_filter_output,
    ... )
    
    >>> pixel_expr = picture[0, 0]
    >>> coeffs = extract_coeffs(pixel_expr)
    
    >>> max_coeffs = maximise_filter_output(coeffs, -512, 511)
    >>> max_coeffs
    {coeff_1_HH_0_0: 511, coeff_1_HL_0_0: -512, coeff_1_HH_-1_0: 511, coeff_0_L_0_0: 511, coeff_1_HL_-1_0: -512, coeff_1_LH_0_0: -512}
    
    >>> min_coeffs = minimise_filter_output(coeffs, -512, 511)
    >>> min_coeffs
    {coeff_1_HH_0_0: -512, coeff_1_HL_0_0: 511, coeff_1_HH_-1_0: -512, coeff_0_L_0_0: -512, coeff_1_HL_-1_0: 511, coeff_1_LH_0_0: 511}

By substituting these worst-case inputs into the pixel's algebraic expression,
and assuming the worst-case values for the error terms (using
:py:func:`upper_error_bound` and :py:func:`lower_error_bound`) we obtain the
minimum and maximum possible output value for this filter::

    >>> from vc2_conformance.wavelet_filter_analysis.symbolic_error_terms import (
    ...     upper_error_bound,
    ...     lower_error_bound,
    ... )
    
    >>> greatest_possible_value = upper_error_bound(pixel_expr.subs(max_coeffs))
    >>> greatest_possible_value
    1153/2
    >>> least_possible_value = lower_error_bound(pixel_expr.subs(min_coeffs))
    >>> least_possible_value
    -4613/8

From this we can determine the number of bits necessary to store any value
which might be computed for this pixel (or other pixels with the same filter
phase). The following function is provided for this purpose:

.. autofunction:: minimum_signed_int_width

Therefore minimum number of bits for this output pixel in our example is::

    >>> max(
    ...     minimum_signed_int_width(greatest_possible_value),
    ...     minimum_signed_int_width(least_possible_value),
    ... )
    11

Finding extreme intermediate values
-----------------------------------

The technique above may be used to find extreme filter output values (and bit
widths) however intermediate bit widths are also of interest.


"""

__all__ = [
    "idwt",
    "dwt",
    "make_coeff_arrays",
    "extract_coeffs",
    "maximise_filter_output",
    "minimise_filter_output",
    "minimum_signed_int_width",
]

import math

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
    Perform a multi-level VC-2 (analysis) Discrete Wavelet Transform (DWT) on
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


def make_coeff_arrays(dwt_depth, dwt_depth_ho, prefix="coeff"):
    r"""
    Create a set of :py:class:`InfiniteArray`\ s representing transform
    coefficient values, as expected by :py:func:`idwt`.
    
    Returns
    =======
    coeff_arrays : {level: {orientation: :py:class:`InfiniteArray`, ...}, ...}
        The transform coefficient values. These dictionaries are indexed the
        same way as 'coeff_data' in the idwt pseudocode function in (15.4.1) in
        the VC-2 specification.
        
        The symbols will have the naming convention ``prefix_level_orient_x_y``
        where:
        
        * prefix is given by the 'prefix' argument
        * level is an integer giving the level number
        * orient is the transform orientation (one of L, H, LL, LH, HL or HH).
        * x and y are the coordinate of the coefficient within that subband.
    """
    coeff_arrays = {}
    
    if dwt_depth_ho > 0:
        coeff_arrays[0] = {"L": SymbolArray(2, "{}_0_L".format(prefix))}
        for level in range(1, dwt_depth_ho + 1):
            coeff_arrays[level] = {"H": SymbolArray(2, "{}_{}_H".format(
                prefix,
                level,
            ))}
    else:
        coeff_arrays[0] = {"LL": SymbolArray(2, "{}_0_LL".format(prefix))}
    
    for level in range(dwt_depth_ho + 1, dwt_depth + dwt_depth_ho + 1):
        coeff_arrays[level] = {
            "LH": SymbolArray(2, "{}_{}_LH".format(prefix, level)),
            "HL": SymbolArray(2, "{}_{}_HL".format(prefix, level)),
            "HH": SymbolArray(2, "{}_{}_HH".format(prefix, level)),
        }
    
    return coeff_arrays


def extract_coeffs(expression):
    """
    Extract the coefficients for each non-error and non-constant term in an
    expression.
    
    Parameters
    ==========
    expression : :py:mod`sympy` expression
        An expression containing a simple sum of variables multiplied by
        coefficients. Error terms involving variables created by
        :py:func:`~vc2_conformance.wavelet_filter_analysis.symbolic_error_terms.new_error_term`
        will be ignored.
    
    Returns
    =======
    coeffs : {variable: coefficient, ...}
    """
    coeffs = {}
    
    for sym in expression.free_symbols:
        if not sym.name.startswith("e_"):
            coeffs[sym] = expression.coeff(sym)
    
    return coeffs


def maximise_filter_output(coeffs, minimum_input, maximum_input):
    """
    Given a set of FIR filter coefficients (e.g. from
    :py:func:`extract_coeffs`) return the variable assignments which will
    maximise the output value for that filter.
    
    Parameters
    ==========
    coeffs : {variable: coefficient, ...}
    minimum_input, maximum_input
        The minimum and maximum values which may be assigned to any variable.
    
    Returns
    =======
    values : {variable: value, ...}
    """
    return {
        sym: (
            maximum_input
            if coeff > 0 else
            minimum_input
        )
        for sym, coeff in coeffs.items()
    }


def minimise_filter_output(coeffs, minimum_input, maximum_input):
    """
    Given a set of FIR filter coefficients (e.g. from
    :py:func:`extract_coeffs`) return the variable assignments which will
    minimise the output value for that filter.
    
    Parameters
    ==========
    coeffs : {variable: coefficient, ...}
    minimum_input, maximum_input
        The minimum and maximum values which may be assigned to any variable.
    
    Returns
    =======
    values : {variable: value, ...}
    """
    return {
        sym: (
            minimum_input
            if coeff > 0 else
            maximum_input
        )
        for sym, coeff in coeffs.items()
    }


def minimum_signed_int_width(number):
    """
    Return the minimum number of bits necessary to represent the supplied
    signed number as an integer (assuming the number is first rounded to an
    integer, rounding away from zero).
    """
    # Special case (don't even need a sign bit)
    if number == 0:
        return 0
    
    # Round to integer away from zero
    number = float(number)
    number = int(math.ceil(number) if number > 0 else math.floor(number))
    
    # If negative, make positive accounting for the increased magnitude range
    # for negative two's-compliment numbers.
    if number < 0:
        number = -number - 1
    
    # Return number of bits including sign bit
    return number.bit_length() + 1
