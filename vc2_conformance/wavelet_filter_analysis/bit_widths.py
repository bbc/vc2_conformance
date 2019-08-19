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
VC-2's analysis and synthesis filters on :py:class:`~InfiniteArray`\ s.

.. autofunction:: analysis_transform

.. autofunction:: synthesis_transform

Using the above functions, symbolic representations of arbitrary VC-2 filter
configurations may be obtained as illustrated in the (synthesis) example
below::

    >>> from vc2_conformance.wavelet_filter_analysis.infinite_arrays import SymbolArray
    >>> from vc2_conformance.wavelet_filter_analysis.bit_widths import synthesis_transform
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
    >>> picture, intermediate_values = synthesis_transform(
    ...     h_filter_params,
    ...     v_filter_params,
    ...     dwt_depth,
    ...     dwt_depth_ho,
    ...     coeff_arrays,
    ... )
    
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

.. autofunction:: non_error_coeffs

For example, the coefficients for a particular pixel may be printed like so::

    >>> from vc2_conformance.wavelet_filter_analysis.bit_widths import non_error_coeffs_coeffs
    >>> for sym, coeff in non_error_coeffs(picture[0, 0]).items():
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
    ...     maximise_filter_output,
    ...     minimise_filter_output,
    ... )
    
    >>> pixel_expr = picture[0, 0]
    >>> coeffs = non_error_coeffs(pixel_expr)
    
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

The above steps are automated by the following functions:

.. autofunction:: synthesis_filter_output_bounds

.. autofunction:: analysis_filter_output_bounds

From the values above we can determine the number of bits necessary to store
any value which might be computed for this pixel (or other pixels with the same
filter phase). The following function is provided for this purpose:

.. autofunction:: minimum_signed_int_width

And is demonstrated here to conclude this example::

    >>> from vc2_conformance.wavelet_filter_analysis.bit_widths import minimum_signed_int_width
    
    >>> max(
    ...     minimum_signed_int_width(greatest_possible_value),
    ...     minimum_signed_int_width(least_possible_value),
    ... )
    11


Generating test signals
-----------------------

Worst-case filter inputs (as found using :py:func:`maximise_filter_output` and
:py:func:`minimise_filter_output`) make useful test signals for real
implementations because they trigger extreme, but legal, values within their
processing chains.

To explain how this is done, we'll work through an example of how we obtain a
usable test signal to maximise the value of a single filter phase's output in a
synthesis transform.

Lets start by defining a 1-level 2D followed by 1-level horizontal-only LeGall
synthesis filter using :py:func:`synthesis_transform` as before::

    >>> from vc2_conformance.wavelet_filter_analysis.infinite_arrays import SymbolArray
    >>> from vc2_conformance.wavelet_filter_analysis.bit_widths import (
    ...     synthesis_transform,
    ...     make_coeff_arrays,
    ... )
    >>> from vc2_conformance.tables import WaveletFilters, LIFTING_FILTERS
    
    >>> # Specify the filters
    >>> synthesis_filter = LIFTING_FILTERS[WaveletFilters.le_gall_5_3]
    >>> dwt_depth = 1
    >>> dwt_depth_ho = 1
    
    >>> # Perform synthesis
    >>> coeff_arrays = make_coeff_arrays(dwt_depth, dwt_depth_ho)
    >>> picture, intermediate_values = synthesis_transform(
    ...     synthesis_filter,
    ...     synthesis_filter,
    ...     dwt_depth,
    ...     dwt_depth_ho,
    ...     coeff_arrays,
    ... )

In this example we'll attempt to produce a test signal which maximises the
filter phase which notionally produces pixel (0, 0). We can start by using
:py:func:`maximise_filter_output` as before::

    >>> from vc2_conformance.wavelet_filter_analysis.bit_widths import (
    ...     non_error_coeffs,
    ...     maximise_filter_output,
    ... )
    
    >>> coeffs = non_error_coeffs(picture[0, 0])
    >>> for sym, value in maximise_filter_output(coeffs, -512, 511).items():
    ...     print("{} = {}".format(sym, value))
    coeff_0_L_0_0 = 511
    coeff_1_H_-1_0 = -512
    coeff_1_H_0_0 = -512
    coeff_2_HH_-1_-1 = 511
    coeff_2_HH_-1_0 = 511
    coeff_2_HH_0_-1 = 511
    coeff_2_HH_0_0 = 511
    coeff_2_HL_-1_0 = -512
    coeff_2_HL_0_0 = -512
    coeff_2_LH_0_-1 = -512
    coeff_2_LH_0_0 = -512


Unfortunately, this result implies that our test signal must include
coefficients at negative coordinates and so we can't use this result as-is to
produce a real test signal.

.. note::

    In VC-2, transform coefficients beyond the boundaries of the inputs are
    substituted for coefficients near the boundary (see remarks about edge
    extension in (15.4.4.2)). As a consequence, the filters operating near the
    edges of the picture may receive some duplicated inputs. Since this reduces
    our freedom to choose worst-case signals (since some inputs are copies) our
    test case should choose pixel values to maximise/minimise where edge
    extension is *not* used.

We must attempt to find an output pixel with the same filter phase as our
example but which doesn't require any input coefficients with negative
coordinates. As we saw earlier, a pixel at an offset of any multiple of the
:py:attr:`~InfiniteArray.period` will have the same filter phase. In this case
the period is::

    >>> picture.period
    (4, 2)

So we could pick (4, 0), (0, 2), (4, 2), (8, 2) (and so on...). To determine
which multiple of the period to pick we can use
:py:meth:`InfiniteArray.relative_step_size_to` to compute the relationship
between indices in the output (i.e. ``picture``) array and relevant input
arrays.

As an example lets consider the ``coeff_2_HH_-1_-1`` term. In this case we're
attempting to use the out-of-bounds coordinate (-1, -1) of the level-2 "HH"
subband. The relationship between indices in this band and the output is found
like so::

    >>> picture.relative_step_size_to(coeff_arrays[2]["HH"])
    (Fraction(1, 2), Fraction(1, 2))

This tells us that to advance the X-index in this array by one, the picture
array's X-index must be advanced by two. Simillarly, to advance one step in Y,
the picture array's index must also be advanced by two. In this case, to avoid
the out-of-bounds X and Y coordinates, we must offset our picture indices by at
least two in both dimensions.  Since we're constrained to offsetting our
coordinate by a multiple of the period, (4, 2), we therefore must pick an
offset of at least (4, 2).

Repeating this process for every coefficient we will eventually find a
coordinate which eliminates all negative input coordinates. In this example,
the answer happens to be (4, 2) for which we obtain the following
negative-coordinate-free coefficients::

    >>> coeffs = non_error_coeffs(picture[4, 2])
    >>> for sym, value in maximise_filter_output(coeffs, -512, 511).items():
    ...     print("{} = {}".format(sym, value))
    coeff_0_L_1_1 = 511
    coeff_1_H_1_1 = -512
    coeff_1_H_0_1 = -512
    coeff_2_HH_2_0 = 511
    coeff_2_HH_1_1 = 511
    coeff_2_HL_2_1 = -512
    coeff_2_HL_1_1 = -512
    coeff_2_LH_2_1 = -512
    coeff_2_LH_2_0 = -512
    coeff_2_HH_1_0 = 511
    coeff_2_HH_2_1 = 511

The above procedure is implemented in the following functions. First, the
following may be used to convert between :py:mod:`sympy` symbols and
coordinates:

.. autofunction:: coeff_symbol_to_indices

.. autofunction:: picture_symbol_to_indices

The following automate the process of finding indices of filters with no
negative input coordinates:

.. autofunction:: find_negative_input_free_synthesis_index

.. autofunction:: find_negative_input_free_analysis_index

"""

__all__ = [
    "analysis_transform",
    "synthesis_transform",
    "make_coeff_arrays",
    "non_error_coeffs",
    "maximise_filter_output",
    "minimise_filter_output",
    "synthesis_filter_output_bounds",
    "analysis_filter_output_bounds",
    "minimum_signed_int_width",
    "coeff_symbol_to_indices",
    "picture_symbol_to_indices",
    "find_negative_input_free_synthesis_index",
    "find_negative_input_free_analysis_index",
]

import math

from collections import defaultdict

from vc2_conformance.wavelet_filter_analysis.fast_sympy_functions import (
    subs,
    coeffs,
)

from vc2_conformance.wavelet_filter_analysis.symbolic_error_terms import (
    lower_error_bound,
    upper_error_bound,
)

from vc2_conformance.wavelet_filter_analysis.infinite_arrays import (
    SymbolArray,
    LiftedArray,
    RightShiftedArray,
    LeftShiftedArray,
    SubsampledArray,
    InterleavedArray,
)


def analysis_transform(h_filter_params, v_filter_params, dwt_depth, dwt_depth_ho, array):
    """
    Perform a multi-level VC-2 (analysis) Discrete Wavelet Transform (DWT) on a
    :py:class:`InfiniteArray` in a manner which is the complement of the 'idwt'
    pseudocode function in (15.4.1).
    
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
        The output transform coefficient values. These nested dictionaries are
        indexed the same way as 'coeff_data' in the idwt pseudocode function in
        (15.4.1) in the VC-2 specification.
    intermediate_values : {(level, array_name): :py:class:`InfiniteArray`, ...}
        All intermediate (and output) values.
        
        The analysis transform consists of a series of transform levels. During
        each level, a series of lifting filter stages, bit shifts and
        sub-samplings take place, illustrated below for the case where both
        horizontal and vertical wavelets have two lifting stages each.
        
        .. image:: /_static/bit_widths/intermediate_analysis_values.svg
            :alt: A single analysis level is shown as a pipeline: bit shift, horizontal lifting stages, horizontal subsampling, vertical lifting stages, vertical subsampling.
        
        Each of these intermediate transform results are added to the
        'intermediate_values' dictionary. The 'level' part of the dictionary
        key is an integer (running from ``dwt_depth_ho + dwt_depth`` for the
        first level to be computed during analysis to ``1``, the final level).
        The 'array_name' part of the key is a string giving a name following
        the naming convention shown in the figure above.
    """
    intermediate_values = {}
    
    input = array
    for level in reversed(range(1, dwt_depth_ho + dwt_depth + 1)):
        intermediate_values[(level, "Input")] = input
        
        # Bit shift
        dc = intermediate_values[(level, "DC")] = LeftShiftedArray(
            input,
            h_filter_params.filter_bit_shift,
        )
        
        # Horizontal lifting stages
        for num, stage in enumerate(h_filter_params.stages):
            name = "DC{}".format("'"*(num + 1))
            dc = intermediate_values[(level, name)] = LiftedArray(dc, stage, 0)
        
        # Horizontal subsample
        l = intermediate_values[(level, "L")] = SubsampledArray(dc, (2, 1), (0, 0))
        h = intermediate_values[(level, "H")] = SubsampledArray(dc, (2, 1), (1, 0))
        
        if level > dwt_depth_ho:
            # Vertical lifting stages
            for num, stage in enumerate(v_filter_params.stages):
                name = "L{}".format("'"*(num + 1))
                l = intermediate_values[(level, name)] = LiftedArray(l, stage, 1)
                name = "H{}".format("'"*(num + 1))
                h = intermediate_values[(level, name)] = LiftedArray(h, stage, 1)
            
            # Vertical subsample
            ll = intermediate_values[(level, "LL")] = SubsampledArray(l, (1, 2), (0, 0))
            lh = intermediate_values[(level, "LH")] = SubsampledArray(l, (1, 2), (0, 1))
            hl = intermediate_values[(level, "HL")] = SubsampledArray(h, (1, 2), (0, 0))
            hh = intermediate_values[(level, "HH")] = SubsampledArray(h, (1, 2), (0, 1))
            
            input = ll
        else:
            input = l
    
    # Separately enumerate just the final output arrays
    coeff_arrays = {}
    for level in range(1, dwt_depth_ho + dwt_depth + 1):
        coeff_arrays[level] = {}
        if level > dwt_depth_ho:
            for orient in ["LH", "HL", "HH"]:
                coeff_arrays[level][orient] = intermediate_values[(level, orient)]
        else:
            coeff_arrays[level]["H"] = intermediate_values[(level, "H")]
    if dwt_depth_ho > 0:
        coeff_arrays[0] = {"L": input}
    else:
        coeff_arrays[0] = {"LL": input}
    
    return coeff_arrays, intermediate_values


def synthesis_transform(h_filter_params, v_filter_params, dwt_depth, dwt_depth_ho, coeff_arrays):
    """
    Perform a multi-level VC-2 (synthesis) Inverse Discrete Wavelet Transform
    (IDWT) on a :py:class:`InfiniteArray` in a manner equivalent
    of the 'idwt' pseudocode function in (15.4.1).
    
    Parameters
    ==========
    h_filter_params, v_filter_params : :py:class:`vc2_conformance.tables.LiftingFilterParameters`
        Horizontal and vertical filter parameters (e.g. from
        :py:data:`vc2_conformance.tables.LIFTING_FILTERS`.
    dwt_depth, dwt_depth_ho: int
        Transform depths for 2D and horizontal-only transforms.
    coeff_arrays : {level: {orientation: :py:class:`InfiniteArray`, ...}, ...}
        The transform coefficient values to be used for synthesis. These nested
        dictionaries are indexed the same way as 'coeff_data' in the idwt
        pseudocode function in (15.4.1) in the VC-2 specification.
    
    Returns
    =======
    array : :py:class:`InfiniteArray`
        The final output value (i.e. decoded picture).
    intermediate_values : {(level, array_name): :py:class:`InfiniteArray`, ...}
        All intermediate (and output) values.
        
        The analysis transform consists of a series of transform levels. During
        each level, a series of lifting filter stages, bit shifts and
        sub-samplings take place, illustrated below for the case where both
        horizontal and vertical wavelets have two lifting stages each.
        
        .. image:: /_static/bit_widths/intermediate_synthesis_values.svg
            :alt: A single analysis level is shown as a pipeline: bit shift, horizontal lifting stages, horizontal subsampling, vertical lifting stages, vertical subsampling.
        
        Each of these intermediate transform results are added to the
        'intermediate_values' dictionary. The 'level' part of the dictionary
        key is an integer (running from ``dwt_depth_ho + dwt_depth`` for the
        first level to be computed during analysis to ``1``, the final level).
        The 'array_name' part of the key is a string giving a name following
        the naming convention shown in the figure above.
    """
    intermediate_values = {}
    
    if dwt_depth_ho > 0:
        output = coeff_arrays[0]["L"]
    else:
        output = coeff_arrays[0]["LL"]
    
    for level in range(1, dwt_depth_ho + dwt_depth + 1):
        if level > dwt_depth_ho:
            ll = intermediate_values[(level, "LL")] = output
            lh = intermediate_values[(level, "LH")] = coeff_arrays[level]["LH"]
            hl = intermediate_values[(level, "HL")] = coeff_arrays[level]["HL"]
            hh = intermediate_values[(level, "HH")] = coeff_arrays[level]["HH"]
            
            # Vertical interleave
            name = "L{}".format("'"*len(v_filter_params.stages))
            l = intermediate_values[(level, name)] = InterleavedArray(ll, lh, 1)
            name = "H{}".format("'"*len(v_filter_params.stages))
            h = intermediate_values[(level, name)] = InterleavedArray(hl, hh, 1)
            
            # Vertical lifting stages
            for num, stage in enumerate(v_filter_params.stages):
                name = "L{}".format("'"*(len(v_filter_params.stages) - num - 1))
                l = intermediate_values[(level, name)] = LiftedArray(l, stage, 1)
                name = "H{}".format("'"*(len(v_filter_params.stages) - num - 1))
                h = intermediate_values[(level, name)] = LiftedArray(h, stage, 1)
        else:
            l = intermediate_values[(level, "L")] = output
            h = intermediate_values[(level, "H")] = coeff_arrays[level]["H"]
        
        # Horizontal interleave
        name = "DC{}".format("'"*len(h_filter_params.stages))
        dc = intermediate_values[(level, name)] = InterleavedArray(l, h, 0)
        
        # Horizontal lifting stages
        for num, stage in enumerate(h_filter_params.stages):
            name = "DC{}".format("'"*(len(h_filter_params.stages) - num - 1))
            dc = intermediate_values[(level, name)] = LiftedArray(dc, stage, 0)
        
        # Bit shift
        output = intermediate_values[(level, "Output")] = RightShiftedArray(
            dc,
            h_filter_params.filter_bit_shift,
        )
    
    return output, intermediate_values


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


def non_error_coeffs(expression):
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
    return {
        sym: value
        for sym, value in coeffs(expression).items()
        if not sym.name.startswith("e_")
    }


def maximise_filter_output(coeffs, minimum_input, maximum_input):
    """
    Given a set of FIR filter coefficients (e.g. from
    :py:func:`non_error_coeffs`) return the variable assignments which will
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
    :py:func:`non_error_coeffs`) return the variable assignments which will
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


def analysis_filter_output_bounds(expression, picture_value_range):
    """
    Return the bounds for an expression describing a particular anlaysis
    filter, assuming worst-case error term values.
    
    Parameters
    ==========
    expression : :py:mod:`sympy` expression
    picture_value_range : (min, max)
        The lower and upper bounds for the values of the non-error symbols in
        the expression.
    
    Returns
    =======
    (lower_bound, upper_bound)
    """
    coeffs = non_error_coeffs(expression)
    
    min_coeffs = minimise_filter_output(coeffs, *picture_value_range)
    max_coeffs = maximise_filter_output(coeffs, *picture_value_range)
    
    lower_bound = lower_error_bound(subs(expression, min_coeffs))
    upper_bound = upper_error_bound(subs(expression, max_coeffs))
    
    return (lower_bound, upper_bound)


def synthesis_filter_output_bounds(expression, coeff_value_ranges):
    """
    Return the bounds for an expression describing a particular synthesis
    filter, assuming worst-case error term values.
    
    Parameters
    ==========
    expression : :py:mod:`sympy` expression
    coeff_value_ranges : {(level, orient): (min, max), ...}
        For each input coefficient band, the maximum values for values in that
        band.
    
    Returns
    =======
    (lower_bound, upper_bound)
    """
    all_coeffs = non_error_coeffs(expression)
    
    # {(level, orient): coeffs, ...}
    coeffs_by_band = defaultdict(dict)
    for symbol, value in all_coeffs.items():
        level, orient, _, _ = coeff_symbol_to_indices(symbol)
        coeffs_by_band[(level, orient)][symbol] = value
    
    min_coeffs = {}
    max_coeffs = {}
    for level_orient, coeffs in coeffs_by_band.items():
        min_coeffs.update(
            minimise_filter_output(coeffs, *coeff_value_ranges[level_orient])
        )
        max_coeffs.update(
            maximise_filter_output(coeffs, *coeff_value_ranges[level_orient])
        )
    
    lower_bound = lower_error_bound(subs(expression, min_coeffs))
    upper_bound = upper_error_bound(subs(expression, max_coeffs))
    
    return (lower_bound, upper_bound)


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


def coeff_symbol_to_indices(symbol):
    """
    Extract the index encoded by a coefficient symbol's name (from, e.g.,
    :py:func:`make_coeff_arrays`).
    
    Given a :py:mod:`sympy` symbol with a name of the form ``coeff_1_HH_-2_3``,
    returns a tuple ``(1, "HH", -2, 3)``.
    """
    level, orient, x, y = symbol.name.split("_")[-4:]
    return (
        int(level),
        orient,
        int(x),
        int(y),
    )

def picture_symbol_to_indices(symbol):
    """
    Extract the index encoded by a symbol's name (e.g. from a
    :py:class:`SymbolArray`).
    
    Given a :py:mod:`sympy` symbol with a name of the form ``pixel_-2_3``,
    returns a tuple ``(-2, 3)``.
    """
    x, y = symbol.name.split("_")[-2:]
    return (int(x), int(y))


def find_negative_input_free_synthesis_index(coeff_arrays, picture, x, y):
    """
    Find a coordinate in 'picture' which implements the same filter as the
    coordinate (x, y) but doesn't require any negative-indexed values in
    coeff_arrays.
    
    Parameters
    ==========
    coeff_arrays : {level: {orient: :py:class:`SymbolArray`, ...}, ...}
        The input coefficients to the synthesis filter. Must be arrays of
        symbols, e.g. as produced by :py:class:`make_coeff_arrays`.
    picture : :py:class:`InfiniteArray`
        The output of the synthesis filter.
    x, y : int
        Coordinates in 'picture'.
    
    Returns
    =======
    (x2, y2)
        A set of coordinates in 'picture' which are the result of the same
        filter phase as (x, y) but whose input coefficients all have
        non-negative coordinates.
    """
    period = picture.period
    x %= period[0]
    y %= period[1]
    
    x2, y2 = x, y
    
    for coeff_symbol in non_error_coeffs(picture[x, y]):
        level, orient, coeff_x, coeff_y = coeff_symbol_to_indices(coeff_symbol)
        coeff_array = coeff_arrays[level][orient]
        relative_step_size = picture.relative_step_size_to(coeff_array)
        
        min_offsets = (
            max(0, int(math.ceil(-idx / rss)))
            for idx, rss in zip((coeff_x, coeff_y), relative_step_size)
        )
        
        # Round up to smallest multiple of period with at least the minimum
        # offset
        offset_x, offset_y = (
            ((mo + p - 1) // p) * p
            for mo, p in zip(min_offsets, period)
        )
        
        x2 = max(x2, x + offset_x)
        y2 = max(y2, y + offset_y)
    
    return (x2, y2)


def find_negative_input_free_analysis_index(picture, coeff_array, x, y):
    """
    Find a coordinate in 'coeff_array' which implements the same filter as the
    coordinate (x, y) but doesn't require any negative-indexed values in
    coeff_arrays.
    
    Parameters
    ==========
    picture : :py:class:`SymbolArray`
        The input to the analysis filter.
    coeff_array : :py:class:`InfiniteArray`
        One of the arrays of output coefficients from the analysis filter.
    x, y : int
        Coordinates in 'coeff_array'.
    
    Returns
    =======
    (x2, y2)
        A set of coordinates in 'coeff_array' which are the result of the same
        filter phase as (x, y) but whose input pixels all have non-negative
        coordinates.
    """
    period = coeff_array.period
    x %= period[0]
    y %= period[1]
    
    x2, y2 = x, y
    
    for picture_symbol in non_error_coeffs(coeff_array[x, y]):
        picture_x, picture_y = picture_symbol_to_indices(picture_symbol)
        relative_step_size = coeff_array.relative_step_size_to(picture)
        
        min_offsets = (
            max(0, int(math.ceil(-idx / rss)))
            for idx, rss in zip((picture_x, picture_y), relative_step_size)
        )
        
        # Round up to smallest multiple of period with at least the minimum
        # offset
        offset_x, offset_y = (
            ((mo + p - 1) // p) * p
            for mo, p in zip(min_offsets, period)
        )
        
        x2 = max(x2, x + offset_x)
        y2 = max(y2, y + offset_y)
    
    return (x2, y2)
