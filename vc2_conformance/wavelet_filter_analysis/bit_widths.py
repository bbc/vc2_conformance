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

Since the wavelet transform may be implemented using FIR filters, the above
approach could be used to find input signals which maximise any desired
intermediate or output value. Unfortunately because VC-2 uses integer
arithmetic, the filter is not strictly linear due to rounding during divisions.
Since there is a potential for rounding errors to compound and accumulate, it
is conceivable that larger values might be encountered than predicted by a
simple FIR filter analysis.

Since an under-estimate of bit width requirements could produce catastrophic
numerical errors, an alternative analysis is required which accounts for the
non-linearities in integer arithmetic.


Theorem Provers
```````````````

Theorem provers (such as Z3_) may be used to compute optimal bit widths for
arbitrary calculations under integer arithmetic (see, for example, `"Bit-Width
Allocation for Hardware Accelerators for Scientific Computing Using SAT-Modulo
Theory", Kinsman and Nicolici (2007)
<https://ieeexplore.ieee.org/abstract/document/5419231>`_).

.. _Z3: https://github.com/Z3Prover/z3/

Unfortunately, computing the minimum bit width required for an arbitrary piece
of arithmetic is NP-complete in the general case. This means that beyond a
certain problem size, finding the true minimum bit width of an expression
becomes intractable, even for sophisticated theorem proving software.

Regrettably, the arithmetic expressions for the VC-2 wavelet filters are too
large to succumb to this approach. As a consequence, we must fall back on
alternative techniques which cannot guarantee the smallest possible bit width,
while still ensuring a sufficient number of bits are available.


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


Interval arithmetic
```````````````````

A similar, but more refined approach, is to track the largest and smallest
values achievable at each point in the computation and, for each operation,
assume the worst case combinations of its operands to determine the new largest
and smallest values. This approach is known as `interval arithmetic
<https://en.wikipedia.org/wiki/Interval_arithmetic>`_.

This approach, while an improvement, still produces gross over estimates. These
result from the fact that values which 'cancel out' are not accounted for (e.g.
in the expression :math:`(a + b) - a` the result only needs to be the size of
:math:`b`, but interval arithmetic approach will over-estimate, assuming three
independent variables). This type of cancellation is commonplace in VC-2's
filters (where the same pixel values will be used by multiple filters) and so
this approach will still produce unacceptable over-estimates in practice.


Affine arithmetic
`````````````````

Affine arithmetic is a further refinement of interval arithmetic which is able
to track dependent values in an expression. For example, unlike interval
arithmetic, given the expression :math:`(a + b) - a`, affine arithmetic is able
to correctly deduce the resulting bitwidth is that of the variable :math:`b`.

See the :py:mod:`~vc2_conformance.wavelet_filter_analysis.affine_arithmetic`
module documentation for a primer on affine arithmetic.

Affine arithmetic is able to exactly track the value ranges (and thus required
bit widths) of affine operations (e.g. addition, subtraction, multiplication by
a constant). In the case of non-affine operations, such as truncating division
(as implicitly implemented by VC-2's right-shift operations), affine arithmetic
makes a conservative (over-) estimate of the value bounds when rounding occurs.
Fortunately, in well-designed filters, rounding errors are much smaller in
magnitude than signal values and consequently this over-estimation of the error
bounds is likely to be very small.


Symbolic Filter Expressions
---------------------------

An symbolic (algebraic) expression describing the filters used by VC-2 will be
required when finding extreme signals and bit width requirements. The
:py:mod:`~vc2_conformance.wavelet_filter_analysis.infinite_arrays` module
provides the pieces needed to produce such an expression using affine
arithmetic (see the
:py:mod:`~vc2_conformance.wavelet_filter_analysis.infinite_arrays` and
:py:mod:`~vc2_conformance.wavelet_filter_analysis.affine_arithmetic`
documentation for details). The following functions assemble these to implement
VC-2's analysis and synthesis filters on :py:class:`~InfiniteArray`\ s.

.. autofunction:: analysis_transform

.. autofunction:: synthesis_transform

Using the above functions, symbolic representations of arbitrary VC-2 filter
configurations may be obtained as illustrated in the (synthesis) example
below::

    >>> from vc2_conformance.wavelet_filter_analysis.infinite_arrays import SymbolArray
    >>> from vc2_conformance.wavelet_filter_analysis.bit_widths import synthesis_transform
    >>> from vc2_data_tables import WaveletFilters, LIFTING_FILTERS
    
    >>> # In this example we'll demonstrate a 1-level 2D wavelet transform
    >>> # using a LeGall wavelet horizontally and Haar wavelet vertically.
    >>> h_filter_params = LIFTING_FILTERS[WaveletFilters.le_gall_5_3]
    >>> v_filter_params = LIFTING_FILTERS[WaveletFilters.haar_with_shift]
    >>> dwt_depth = 1
    >>> dwt_depth_ho = 0
    
    >>> # Create a series of infinite 2D arrays of symbols representing #
    >>> transform coefficients (inputs) for our transform
    >>> coeff_arrays = {
    ...     0: {"LL": SymbolArray(2, ("coeff", 0, "L"))},
    ...     1: {
    ...         "LH": SymbolArray(2, ("coeff", 1, "LH")),
    ...         "HL": SymbolArray(2, ("coeff", 1, "HL")),
    ...         "HH": SymbolArray(2, ("coeff", 1, "HH")),
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
    >>> print(picture[0, 0])
    (1/2)*(('coeff', 0, 'L'), 0, 0) + (-1/4)*(('coeff', 1, 'LH'), 0, 0) + (-1/4)*Error(id=9) + (-1/8)*(('coeff', 1, 'HL'), -1, 0) + (1/16)*(('coeff', 1, 'HH'), -1, 0) + (1/16)*Error(id=6) + (-1/8)*(('coeff', 1, 'HL'), 0, 0) + (1/16)*(('coeff', 1, 'HH'), 0, 0) + (1/16)*Error(id=7) + (-1/4)*Error(id=8) + (1/2)*Error(id=10)



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

    >>> from vc2_conformance.wavelet_filter_analysis.bit_widths import non_error_coeffs
    >>> for sym, coeff in non_error_coeffs(picture[0, 0]).items():
    ...     print("{}: {}".format(sym, coeff))
    (('coeff', 0, 'L'), 0, 0): 1/2
    (('coeff', 1, 'LH'), 0, 0): -1/4
    (('coeff', 1, 'HL'), -1, 0): -1/8
    (('coeff', 1, 'HH'), -1, 0): 1/16
    (('coeff', 1, 'HL'), 0, 0): -1/8
    (('coeff', 1, 'HH'), 0, 0): 1/16


Finding every equivalent FIR filter
-----------------------------------

In general, different output pixels are the result of different filtering
processes. For example::

    >>> print(picture[0, 0])
    (1/2)*(('coeff', 0, 'L'), 0, 0) + (-1/4)*(('coeff', 1, 'LH'), 0, 0) + (-1/4)*Error(id=9) + (-1/8)*(('coeff', 1, 'HL'), -1, 0) + (1/16)*(('coeff', 1, 'HH'), -1, 0) + (1/16)*Error(id=6) + (-1/8)*(('coeff', 1, 'HL'), 0, 0) + (1/16)*(('coeff', 1, 'HH'), 0, 0) + (1/16)*Error(id=7) + (-1/4)*Error(id=8) + (1/2)*Error(id=10)
    
    >>> print(picture[1, 0])
    (3/8)*(('coeff', 1, 'HL'), 0, 0) + (-3/16)*(('coeff', 1, 'HH'), 0, 0) + (-3/16)*Error(id=7) + (1/4)*(('coeff', 0, 'L'), 0, 0) + (-1/8)*(('coeff', 1, 'LH'), 0, 0) + (-1/8)*Error(id=9) + (-1/16)*(('coeff', 1, 'HL'), -1, 0) + (1/32)*(('coeff', 1, 'HH'), -1, 0) + (1/32)*Error(id=6) + (-1/8)*Error(id=8) + (1/4)*(('coeff', 0, 'L'), 1, 0) + (-1/8)*(('coeff', 1, 'LH'), 1, 0) + (-1/8)*Error(id=13) + (-1/16)*(('coeff', 1, 'HL'), 1, 0) + (1/32)*(('coeff', 1, 'HH'), 1, 0) + (1/32)*Error(id=11) + (-1/8)*Error(id=12) + (1/4)*Error(id=14) + (1/2)*Error(id=15)

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

    >>> print(picture[0, 0])
    (1/2)*(('coeff', 0, 'L'), 0, 0) + (-1/4)*(('coeff', 1, 'LH'), 0, 0) + (-1/4)*Error(id=9) + (-1/8)*(('coeff', 1, 'HL'), -1, 0) + (1/16)*(('coeff', 1, 'HH'), -1, 0) + (1/16)*Error(id=6) + (-1/8)*(('coeff', 1, 'HL'), 0, 0) + (1/16)*(('coeff', 1, 'HH'), 0, 0) + (1/16)*Error(id=7) + (-1/4)*Error(id=8) + (1/2)*Error(id=10)
    >>> print(picture[2, 2])
    (1/2)*(('coeff', 0, 'L'), 1, 1) + (-1/4)*(('coeff', 1, 'LH'), 1, 1) + (-1/4)*Error(id=19) + (-1/8)*(('coeff', 1, 'HL'), 0, 1) + (1/16)*(('coeff', 1, 'HH'), 0, 1) + (1/16)*Error(id=16) + (-1/8)*(('coeff', 1, 'HL'), 1, 1) + (1/16)*(('coeff', 1, 'HH'), 1, 1) + (1/16)*Error(id=17) + (-1/4)*Error(id=18) + (1/2)*Error(id=20)
    >>> print(picture[4, 6])
    (1/2)*(('coeff', 0, 'L'), 2, 3) + (-1/4)*(('coeff', 1, 'LH'), 2, 3) + (-1/4)*Error(id=24) + (-1/8)*(('coeff', 1, 'HL'), 1, 3) + (1/16)*(('coeff', 1, 'HH'), 1, 3) + (1/16)*Error(id=21) + (-1/8)*(('coeff', 1, 'HL'), 2, 3) + (1/16)*(('coeff', 1, 'HH'), 2, 3) + (1/16)*Error(id=22) + (-1/4)*Error(id=23) + (1/2)*Error(id=25)

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
    {(('coeff', 0, 'L'), 0, 0): 511, (('coeff', 1, 'LH'), 0, 0): -512, (('coeff', 1, 'HL'), -1, 0): -512, (('coeff', 1, 'HH'), -1, 0): 511, (('coeff', 1, 'HL'), 0, 0): -512, (('coeff', 1, 'HH'), 0, 0): 511}
    
    >>> min_coeffs = minimise_filter_output(coeffs, -512, 511)
    >>> min_coeffs
    {(('coeff', 0, 'L'), 0, 0): -512, (('coeff', 1, 'LH'), 0, 0): 511, (('coeff', 1, 'HL'), -1, 0): 511, (('coeff', 1, 'HH'), -1, 0): -512, (('coeff', 1, 'HL'), 0, 0): 511, (('coeff', 1, 'HH'), 0, 0): -512}

By substituting these worst-case inputs into the pixel's algebraic expression,
and assuming the worst-case values for the error terms (using
:py:func:`affine_arithmetic.upper_bound` and
:py:func:`affine_arithmetic.lower_bound`) we obtain the minimum and maximum
possible output value for this filter::

    >>> import vc2_conformance.wavelet_filter_analysis.affine_arithmetic as aa
    
    >>> greatest_possible_value = aa.upper_bound(pixel_expr.subs(max_coeffs))
    >>> print(greatest_possible_value)
    1153/2
    >>> least_possible_value = aa.lower_bound(pixel_expr.subs(min_coeffs))
    >>> print(least_possible_value)
    -4613/8

The above steps are automated by the following functions:

.. autofunction:: synthesis_filter_expression_bounds

.. autofunction:: analysis_filter_expression_bounds

In addition, the following functions take a :py:class:`InfiniteArray` and find
the overall upper and lower bounds of every filter phase in that array.

.. autofunction:: synthesis_filter_bounds

.. autofunction:: analysis_filter_bounds

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
    >>> from vc2_data_tables import WaveletFilters, LIFTING_FILTERS
    
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
    (('coeff', 0, 'L'), 0, 0) = 511
    (('coeff', 1, 'H'), -1, 0) = -512
    (('coeff', 1, 'H'), 0, 0) = -512
    (('coeff', 2, 'LH'), 0, -1) = -512
    (('coeff', 2, 'LH'), 0, 0) = -512
    (('coeff', 2, 'HL'), -1, 0) = -512
    (('coeff', 2, 'HH'), -1, -1) = 511
    (('coeff', 2, 'HH'), -1, 0) = 511
    (('coeff', 2, 'HL'), 0, 0) = -512
    (('coeff', 2, 'HH'), 0, -1) = 511
    (('coeff', 2, 'HH'), 0, 0) = 511

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
    (('coeff', 0, 'L'), 1, 1) = 511
    (('coeff', 1, 'H'), 0, 1) = -512
    (('coeff', 1, 'H'), 1, 1) = -512
    (('coeff', 2, 'LH'), 2, 0) = -512
    (('coeff', 2, 'LH'), 2, 1) = -512
    (('coeff', 2, 'HL'), 1, 1) = -512
    (('coeff', 2, 'HH'), 1, 0) = 511
    (('coeff', 2, 'HH'), 1, 1) = 511
    (('coeff', 2, 'HL'), 2, 1) = -512
    (('coeff', 2, 'HH'), 2, 0) = 511
    (('coeff', 2, 'HH'), 2, 1) = 511

The above procedure is implemented in the following functions which automate
the process of finding indices of filters with no negative input coordinates:

.. autofunction:: find_negative_input_free_synthesis_index

.. autofunction:: find_negative_input_free_analysis_index


Accounting for Quantisation
---------------------------

The quantisation and dequantisation steps in the encoder and decoder
(respectively) may round transform values up or down and, consequently, these
rounding errors must also be taken into account when computing bit width
requirements.


Quantifying quantisation errors
```````````````````````````````

Below we will derive an expression indicating the worst-case rounding error a
VC-2's quantiser can produce.

Conceptually VC-2 uses a 'dead-zone' quantiser to quantise transform
coefficients. The specification informatively notes (13.1.1) that quantisation
may be implemented as follows:

.. math::

    \text{quantize}(x) = \left\{\begin{array}{ll}
        \left\lfloor\frac{x}{qf}\right\rfloor & \text{if}~x \ge 0 \\
        -\left\lfloor\frac{-x}{qf}\right\rfloor & \text{if}~x < 0 \\
    \end{array}\right

Where :math:`qf` is the chosen quantisation factor.

During dequantisation, the ``inverse_quant`` function (13.3.1) approximates the
reversal of this process producing dequantised values approximately in the
middle of the ranges of inputs which might have produced a given quantised
value.

The figure below illustrates the mapping performed during quantisation:

.. image:: /_static/bit_widths/deadzone_quantisation.svg
    :alt: Illustration of dead-zone quantiser.

The range of input values which are quantised to 0 is known as the 'dead-zone'
and is notably twice the width of the regions which quantise to any other
value. As a consequence, the worst-case quantisation errors arise from inputs
at the left and right extremes of the dead-zone.

Considering only positive inputs momentarily, the worst-case quantisation error
occurs when the input is set to the largest value, :math:`x_{\textrm{max}}`,
which satisifies:

.. math::

    \left\lfloor \frac{x_{\textrm{max}}}{qf} \right\rfloor = 0

Or equivalently, expressed as an inequality:

.. math::

    \frac{x_{\textrm{max}}}{qf} < 1

The maximum value satisfying this inequality may be derrived by introducing an
infintecimal offset, :math:`\iota`, to the RHS:

.. math::

    \frac{x_{\textrm{max}}}{qf} &< 1 \\
    \frac{x_{\textrm{max}}}{qf} &\le 1 - \iota \\
    \frac{x_{\textrm{max}}}{qf} &= 1 - \iota \\
    x_{\textrm{max}} &= qf - \iota \\

Since all values in VC-2 are integers, the largest integer value of
:math:`x_{\textrm{max}}` is therefore:

.. math::

    x_{\textrm{max integer}} = \left\lfloor qf - \iota \right\rfloor

Since :math:`x_{\textrm{max integer}}` is the largest value the VC-2 quantiser
will round to zero, :math:`x_{\textrm{max integer}}` is the largest
quantisation error in positive part of the dead-zone and therefore the largest
possible quantisation error for any positive value.

By an analagous process (or the symmetry of the quantiser), the largest
negative value quantised to zero (and therefore the negative value with the
largest quantisation error) may be found to be :math:`-x_{\textrm{max
integer}}`.

The following function may be used to compute :math:`x_{\textrm{max integer}}`
for any VC-2 quantisation index.

.. autofunction:: worst_case_quantisation_error


Bounding quantisation factors
`````````````````````````````

As the quantisation factor increases, the worst-case quantisation error
magnitude also increases. We must therefore determine the largest quantisation
factor which might be applied by an encoder. We will assume that the largest
quantisation factor which an encoder might choose is the smallest factor which
would quantise all transform values to zero.

The function below may be used to determine the quantisation index
corresponding with the smallest quantisation factor sufficient to quantise a
given value to zero.

.. autofunction:: maximum_useful_quantisation_index

"""

__all__ = [
    "analysis_transform",
    "synthesis_transform",
    "make_coeff_arrays",
    "non_error_coeffs",
    "maximise_filter_output",
    "minimise_filter_output",
    "synthesis_filter_expression_bounds",
    "analysis_filter_expression_bounds",
    "synthesis_filter_bounds",
    "analysis_filter_bounds",
    "minimum_signed_int_width",
    "find_negative_input_free_synthesis_index",
    "find_negative_input_free_analysis_index",
    "worst_case_quantisation_error",
    "maximum_useful_quantisation_index",
]

import math

from collections import defaultdict

from vc2_conformance.decoder.transform_data_syntax import quant_factor

from vc2_conformance.wavelet_filter_analysis.linexp import LinExp

import vc2_conformance.wavelet_filter_analysis.affine_arithmetic as aa

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
    h_filter_params, v_filter_params : :py:class:`vc2_data_tables.LiftingFilterParameters`
        Horizontal and vertical filter parameters (e.g. from
        :py:data:`vc2_data_tables.LIFTING_FILTERS`.
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
    h_filter_params, v_filter_params : :py:class:`vc2_data_tables.LiftingFilterParameters`
        Horizontal and vertical filter parameters (e.g. from
        :py:data:`vc2_data_tables.LIFTING_FILTERS`.
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
        
        The symbols will have the naming convention ``((prefix, level, orient),
        x, y)``
        where:
        
        * prefix is given by the 'prefix' argument
        * level is an integer giving the level number
        * orient is the transform orientation (one of L, H, LL, LH, HL or HH).
        * x and y are the coordinate of the coefficient within that subband.
    """
    coeff_arrays = {}
    
    if dwt_depth_ho > 0:
        coeff_arrays[0] = {"L": SymbolArray(2, (prefix, 0, "L"))}
        for level in range(1, dwt_depth_ho + 1):
            coeff_arrays[level] = {"H": SymbolArray(2, (prefix, level, "H"))}
    else:
        coeff_arrays[0] = {"LL": SymbolArray(2, (prefix, 0, "LL"))}
    
    for level in range(dwt_depth_ho + 1, dwt_depth + dwt_depth_ho + 1):
        coeff_arrays[level] = {
            "LH": SymbolArray(2, (prefix, level, "LH")),
            "HL": SymbolArray(2, (prefix, level, "HL")),
            "HH": SymbolArray(2, (prefix, level, "HH")),
        }
    
    return coeff_arrays


def non_error_coeffs(expression):
    """
    Extract the coefficients for each non-error and non-constant term in an
    expression.
    
    Parameters
    ==========
    expression : :py:class:`LinExp` expression
        An expression. Constants as well as error terms involving variables
        created by
        :py:func:`~vc2_conformance.wavelet_filter_analysis.symbolic_error_terms.new_error_term`
        will be ignored.
    
    Returns
    =======
    coeffs : {variable: coefficient, ...}
    """
    return {
        sym: value
        for sym, value in LinExp(expression)
        if not isinstance(sym, aa.Error) and sym is not None
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


def analysis_filter_expression_bounds(expression, picture_value_range):
    """
    Return the bounds for an expression describing a particular anlaysis
    filter, assuming worst-case error term values.
    
    Parameters
    ==========
    expression : :py:class:`LinExp` expression
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
    
    lower_bound = aa.lower_bound(expression.subs(min_coeffs))
    upper_bound = aa.upper_bound(expression.subs(max_coeffs))
    
    return (lower_bound, upper_bound)


def synthesis_filter_expression_bounds(expression, coeff_value_ranges):
    """
    Return the bounds for an expression describing a particular synthesis
    filter, assuming worst-case error term values.
    
    Parameters
    ==========
    expression : :py:class:`LinExp` expression
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
        (_, level, orient), _, _ = symbol
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
    
    lower_bound = aa.lower_bound(expression.subs(min_coeffs))
    upper_bound = aa.upper_bound(expression.subs(max_coeffs))
    
    return (lower_bound, upper_bound)


def analysis_filter_bounds(coeff_array, picture_value_range):
    """
    Return the overall value bounds across all filter phases of a particular
    anlaysis filter output subband or intermediate value, assuming worst-case
    error term values.
    
    Parameters
    ==========
    coeff_array : :py:class:`InfiniteArray`
    picture_value_range : (min, max)
        The lower and upper bounds for the values of the non-error symbols in
        the expression.
    
    Returns
    =======
    (lower_bound, upper_bound)
    """
    w, h = coeff_array.period
    lower_bounds, upper_bounds = zip(*(
        analysis_filter_expression_bounds(coeff_array[x, y], picture_value_range)
        for x in range(w)
        for y in range(h)
    ))
    return min(lower_bounds), max(upper_bounds)


def synthesis_filter_bounds(picture_array, coeff_value_ranges):
    """
    Return the overall value bounds across all filter phases of a synthesis
    filter output or invermediate value, assuming worst-case error term values.
    
    Parameters
    ==========
    picture_array : :py:class:`InfiniteArray`
    coeff_value_ranges : {(level, orient): (min, max), ...}
        For each input coefficient band, the maximum values for values in that
        band.
    Returns
    =======
    (lower_bound, upper_bound)
    """
    w, h = picture_array.period
    lower_bounds, upper_bounds = zip(*(
        synthesis_filter_expression_bounds(picture_array[x, y], coeff_value_ranges)
        for x in range(w)
        for y in range(h)
    ))
    return (min(lower_bounds), max(upper_bounds))


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
        (_, level, orient), coeff_x, coeff_y = coeff_symbol
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
        _, picture_x, picture_y = picture_symbol
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


def worst_case_quantisation_error(quantisation_index):
    """
    Compute the worst-case quantisation error which may be introduced by VC-2's
    quantisation scheme as defined in (13.3).
    
    Parameters
    ==========
    index : int
        The VC-2 quantisation index used.
    
    Returns
    =======
    error_magnitude : int
        The worst case quantisation error magnitude. Worst-case quantisation
        errors may be plus or minus this value.
    """
    # The worst-case quantisation error occurs when quantising the values:
    #
    #     +-floor(qf - iota)
    #
    # See the derrivation in documentation at the top of this module for
    # details.
    #
    # In VC-2, the quantisation factor is computed from the quantisation index
    # by the `quant_factor` pseudocode function (13.3.2). The value returned is
    # given as a fixed-point number with two fractional bits. That is, 4*qf is
    # returned, not qf. Consequently, the expression above may be rewritten as:
    #
    #     +-floor(quant_factor(quantisation_index)/4.0 - iota)
    #
    # This computation is implemented in truncating integer arithmetic by
    # adding an extra fractional bit to the quatisation factor and replacing
    # iota with the new smallest fixed point value possible.
    return ((quant_factor(quantisation_index) << 1) - 1) // 8


def maximum_useful_quantisation_index(value):
    """
    Compute the smallest quantisation index which quantizes the supplied value
    to zero. This is considered to be the largest useful quantisation index
    with respect to this value.
    """
    # NB: Since quantisation indices correspond to exponentially growing
    # quantisation factors, the runtime of this loop is only logarithmic with
    # respect to the magnitude of the value.
    quantisation_index = 0
    while (4*abs(value)) // quant_factor(quantisation_index) != 0:
        quantisation_index += 1
    return quantisation_index
