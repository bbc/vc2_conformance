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

In the subsections below possible approaches are discussed finally arriving at
the solution used in this module.

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
    
    \frac{a}{b} \Rightarrow \frac{a}{b} + e_i

.. note::

    A unique error term, :math:`e_i`, should be introduced for every division
    operation otherwise unrelated error terms might cancel.

Once the final filter output's algebraic expression is arrived at, the
magnitudes of all of the error terms' coefficients should be summed.

For example if the final algebraic expression ends up as :math:`\cdots + 4 e_1
-\frac{3}{2} e_2 + \frac{1}{2} e_3`, the sum of the magnitudes of the error
coefficients would be :math:`6`.

The absolute sum of error coefficients gives an upper bound on the magnitude of
the error introduced by rounding. This value should be added/subtracted to/from
the maximal/minimal values found for the real-valued filter before determining
the required bit width.

This approach considers a worst-case where every division produces a worst-case
rounding error and so is guaranteed not to under-estimate the required bit
width. However, it may not be possible for every division to produce a
worst-case rounding error simultaneously so there is potential for
over-estimation of the required bit width.

Fortunately, in well designed filters, rounding errors have significantly
smaller magnitudes than the signal being processed. Consequently it is quite
unlikely that accounting for rounding errors will push the signal level into a
greater number of bits, even if those errors are generous over-estimates.


Generating algebraic expressions for VC-2 filters
-------------------------------------------------

This focus of this module is implementing the two steps involved in performing
real-valued filter analysis with error tracking: finding worst-case values and
estimating worst-case rounding errors.

For both tasks, an algebraic expression describing the filters used by VC-2 is
required. Rather than directly writing such an expression, the VC-2 pseudocode
functions themselves are used. Using the SymPy_ computer algebra system, the
pseudocode can be fed abstract symbols as input (in place of concrete integer
values) resulting in an algebraic expression for the filter which produced each
output value.

.. _SymPy: https://www.sympy.org/

This approach avoids the need to directly construct an algebraic expression
describing the filters required while also ensuring consistency with the
(normative) pseudocode in the specification.

Determining input sizes and representative outputs
``````````````````````````````````````````````````

The primary challenge of using the VC-2 pseudocode to produce algebraic
expressions for filters is determining the required input dimensions and
representative output values which completely describe the implemented filter.
We'll introduce and explain these challenges more fully, and give their
solution, in the remainder of this section.

In this section we'll consider at the one dimensional case since the minimum
width and height of a 2D picture (and the representative sampling points) can
be determined independently.

We'll also mostly think about filtering occurring *in-place* rather than
*out-of-place* (see figure below).

.. image:: /_static/bit_widths/inplace_filtering.svg
    :alt: Comparison of out-of-place and in-place filtering representations.

Finally, we'll mostly look at the *analysis* wavelet filters used for encoding
since this is easier to follow but, as we'll see later, the results all hold
for synthesis (decoding) too.


Why is there a minimum input size?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

VC-2's wavelet filters are simple FIR filters which map from transform values
to picture values (during decoding) or from picture values to transform values
(during encoding). When computing values near the edges of the output, the FIR
filter may require values beyond the bounds of the input as illustrated below.

.. image:: /_static/bit_widths/filter_repeated_terms.svg
    :alt: VC-2 filter showing how terms are repeated.

VC-2 uses edge extension (see (15.4.4.2) in the VC-2 specification) to fill in
any missing values during filtering. The result is that values near the edges
of the filter's output contain repeated terms, conceptually implementing a
simpler filter than those in the middle of the output.

To get a complete algebraic expression for VC-2's filters, we must ensure that
the input we provide is sufficiently large that there is at least one output
value which contains no repeated terms and is, therefore, representative of the
complete FIR filter. (More on this later.)

Filter offsets and lifting
~~~~~~~~~~~~~~~~~~~~~~~~~~

VC-2 defines its wavelet filters in terms of a series of lifting stages. Each
lifting stage consists of a small FIR filter. These filters have a number of
taps which start from some point to the left of the output position and end at
some point afterwards.

The left- and right-most tap offsets for a lifting stage can be calculated as:

* Left-offset: :math:`f_L = \max(0, 1 - 2D)`
* Right-offset: :math:`f_R = \max(0, 2L + 2D - 3)`

Where :math:`L` is the filter length and :math:`D` is the filter delay as
defined in the VC-2 standard.

These formulae are implemented as:

.. autofunction:: lifting_stage_offsets

As the lifting stages are applied, the filtering operation becomes equivalent
to a successively larger filter, as illustrated below:

.. image:: /_static/bit_widths/lifting_equivalent_filter_width.svg
    :alt: Several lifting stages are equivalent to one larger filter.

The left and right offsets of the effective filter implemented by a series of
lifting stages are simply the sum of the left and right offsets respectively.
This is computed by the following function:

.. autofunction:: combined_lifting_stages_offsets

Because each lifting stage updates either the odd or even numbered samples,
after every lifting stage has been applied, some samples will be the result of
more lifting stages than others as illustrated below:

.. image:: /_static/bit_widths/lifting_and_subsampling.svg
    :alt: Lifting applies more stages to some outputs than others.

As a consequence, odd and even numbered outputs are the result of different
filtering operations. During wavelet analysis (encoding) the two sets of
outputs are conventionally referred to as the low-pass (even) and high-pass
(odd) bands.

For a wavelet with :math:`N` lifting stages in which the final stage updates
the low-pass band (even numbered samples), the effective filter widths of the
two output signals will be:

* Low-pass band

  * Left-offset :math:`s_L = \sum^{N}_{n=1} \max(0, 1 - 2D_n)`
  * Right-offset :math:`s_R = \sum^{N}_{n=1} \max(0, 2L_n + 2D_n - 3)`

* High-pass band

  * Left-offset :math:`d_L = \sum^{N-1}_{n=1} \max(0, 1 - 2D_n)`
  * Right-offset :math:`d_R = \sum^{N-1}_{n=1} \max(0, 2L_n + 2D_n - 3)` 

Where :math:`D_n` and :math:`L_n` are the delay and length (respectively) of
the :math:`n^\textrm{th}` lifting stage.

.. note::
    
    The convention of using the letters :math:`s` and :math:`d` for refering to
    low- and high-pass bands respectively is inherited from the book 'Ripples
    in Mathematics'.

For wavelets whose final lifting stage updates the high-pass band (odd numbered
samples), the expressions for low- and high-pass above should be swapped.

The following function computes the offsets for the low- and high-pass filter
bands of a given VC-2 wavelet.

.. autofunction:: wavelet_filter_offsets


Multi-level filter offsets
~~~~~~~~~~~~~~~~~~~~~~~~~~

During multi-level wavelet filtering, the filtering is recursively applied to
the low-pass filter output. During each level, the effective filter implemented
continues to grow as illustrated in the figure below:

.. image:: /_static/bit_widths/multi_level_filtering.svg
    :alt: Multi-level filtering and equivalent filters.

If we define the filter offsets for the first (zeroth) level as:

* Level 0 low-pass left offset: :math:`s_{L,0} = s_L`
* Level 0 low-pass right offset: :math:`s_{R,0} = s_R`
* Level 0 high-pass left offset: :math:`d_{L,0} = d_L`
* Level 0 high-pass right offset: :math:`d_{R,0} = d_R`

.. warning::
    
    In this module levels are numbered the opposite way to the VC-2 standard
    for reasons of mathematical convenience. Specifically, level 0 is the level
    with the first high-pass band computed during analysis (encoding), level 1
    is the one with the second high-pass band and so on.

In each subsequent level, the filter offsets are the sum of the previous
level's low-pass band and the effective width of the current level's filter.
Since each level operates on a subsampled signal, the filter width effectively
doubles with each level. The resulting offsets are therefore computed as:

* Level :math:`\textrm{level}` low-pass left offset:
  
  .. math::
      
      s_{L,\textrm{level}} =
          s_{L,\textrm{level}-1} + s_L \times 2^{\textrm{level}} =
          s_L (2^{\textrm{level}+1} - 1)

* Level :math:`\textrm{level}` low-pass right offset: 
  
  .. math::
    
      s_{R,\textrm{level}} =
          s_{R,\textrm{level}-1} + s_R \times 2^{\textrm{level}} =
          s_R (2^{\textrm{level}+1} - 1)

* Level :math:`\textrm{level}` high-pass left offset: 
  
  .. math::
    
      d_{L,\textrm{level}} =
          s_{L,\textrm{level}-1} + d_L \times 2^{\textrm{level}} =
          (s_L + d_L)2^{\textrm{level}} - s_L

* Level :math:`\textrm{level}` high-pass right offset: 
  
  .. math::
    
      d_{R,\textrm{level}} =
          s_{R,\textrm{level}-1} + d_R \times 2^{\textrm{level}} =
          (s_R + d_R)2^{\textrm{level}} - s_R


In the previous step we found the filter left and right offsets for values in
each level and band. We can use these offsets to determine which values in a
particular band and level contain repeated terms; as illustrated in the example
below.

.. image:: /_static/bit_widths/subband_filter_repeated_terms.svg
    :alt: Some entries in a subband require values beyond the ends of the input.

This is a relatively straightforward process by visual inspection, but now lets
derive a more formal mathematical method.

During multi-level (in-place) filtering, the samples in each filter band become
interleaved with a particular spacing and alignment within the output as
illustrated in the figure below:

.. image:: /_static/bit_widths/level_interleaving.svg
    :alt: The interleaved results of multi-level filtering.


The pattern describing the alignment of a given band and level in the
interleaved output is easy to spot:

+-----------+------------------------------+--------------------------+----------------------------------+
|           | Spacing                      | Left Gap                 | Right Gap                        |
+===========+==============================+==========================+==================================+
| Low-pass  | :math:`2^{\textrm{level}+1}` | :math:`0`                | :math:`2^{\textrm{level}+1} - 1` |
+-----------+------------------------------+--------------------------+----------------------------------+
| High-pass | :math:`2^{\textrm{level}+1}` | :math:`2^\textrm{level}` | :math:`2^{\textrm{level}} - 1`   |
+-----------+------------------------------+--------------------------+----------------------------------+

The number of samples at the start of given band/level with repeated terms is
then:

.. math::
    
    \textrm{initial samples with repeated terms} =
        \left\lceil
            \frac{
                \textrm{filter left offset}
                +
                \textrm{left gap}
            }{
                \textrm{spacing}
            }
        \right\rceil

The expression for the number of samples at the end of a level/band containing
with repeated terms is analogous.

These formulae are enumerated below, rewritten to use truncating integer
division (as implemented in typical programming environments), rather than the
ceiling operator (:math:`\lceil\cdot\rceil`).

* Level :math:`\textrm{level}` low-pass subsampled left offset 

  .. math::
      s'_{L,\textrm{level}} =
          \left\lfloor
              \frac{
                  s_{L,\textrm{level}} -
                  0 +
                  2^{\textrm{level}+1} - 1
              }{
                  2^{\textrm{level}+1}
              }
          \right\rfloor =
          \left\lfloor
              \frac{
                  (s_L + 1)(2^{\textrm{level}+1} - 1)
              }{
                  2^{\textrm{level}+1}
              }
          \right\rfloor

* Level :math:`\textrm{level}` low-pass subsampled right offset

  .. math::
      s'_{R,\textrm{level}} =
          \left\lfloor
              \frac{
                  s_{R,\textrm{level}} -
                  (2^{\textrm{level}+1} - 1) +
                  2^{\textrm{level}+1} - 1
              }{
                  2^{\textrm{level}+1}
              }
          \right\rfloor =
          \left\lfloor
              \frac{
                  s_R (2^{\textrm{level}+1} - 1)
              }{
                  2^{\textrm{level}+1}
              }
          \right\rfloor

* Level :math:`\textrm{level}` high-pass subsampled left offset

  .. math::
      d'_{L,\textrm{level}} =
          \left\lfloor
              \frac{
                  d_{L,\textrm{level}} -
                  (2^\textrm{level}) +
                  2^{\textrm{level}+1} - 1
              }{
                  2^{\textrm{level}+1}
              }
          \right\rfloor =
          \left\lfloor
              \frac{
                  (s_L + d_L - 1)2^{\textrm{level}} - s_L +
                  2^{\textrm{level}+1} - 1
              }{
                  2^{\textrm{level}+1}
              }
          \right\rfloor

* Level :math:`\textrm{level}` high-pass subsampled right offset

  .. math::
      d'_{R,\textrm{level}} =
          \left\lfloor
              \frac{
                  d_{R,\textrm{level}} -
                  (2^{\textrm{level}} - 1) +
                  2^{\textrm{level}+1} - 1
              }{
                  2^{\textrm{level}+1}
              }
          \right\rfloor =
          \left\lfloor
              \frac{
                  (s_R + d_R - 1)2^{\textrm{level}} - s_R +
                  2^{\textrm{level}+1}
              }{
                  2^{\textrm{level}+1}
              }
          \right\rfloor


The above formulae are computed by the following function:

.. autofunction:: subsampled_offsets_for_level


Minimum input length
~~~~~~~~~~~~~~~~~~~~

The above expressions for the subband left and right offsets can be used to
determine the minimum number of samples in that subband which ensures that at
least one is free from repeated terms.

For example, for the level 2 high-pass band the minimum number of samples in
this band will be :math:`d'_{L,2} + d'_{R,2} + 1`. So long as the band has this
many samples in it, the :math:`{d'_{L,2}}^{\textrm{th}}` sample would be the
first to be free from repeated terms.

For a subband in level :math:`\textrm{level}` to have a :math:`n` samples, the
input signal must be :math:`n * 2^{\textrm{level}+1}` samples long.

Using the above we can find the overall minimum input length which ensures that
every level and band have at least one repeated-term-free sample.


Convenience function
~~~~~~~~~~~~~~~~~~~~

All of the above steps are implemented by the following convenience function:

.. autofunction:: wavelet_filter_minimum_length_and_analysis_offsets


Synthesis filters
~~~~~~~~~~~~~~~~~

The procedure above concentrated on the analysis (encoding) transform. The same
procedures, however, can be used with the synthesis (decoding) transform.

The figure below illustrates the symmetry between the analysis and synthesis
filtering processes.

.. image:: /_static/bit_widths/analysis_vs_synthesis.svg
    :alt: A side-by-side comparison of the analysis and synthesis process

Though the synthesis process runs in reverse, collecting together values from
different levels and bands to produce a single output, it can be seen that
different samples in the output are the results of different filters. For
example, the filtering stages which lead to the synthesised values of outputs
'd' and 'e' are shown below

.. image:: /_static/bit_widths/synthesis_filter_types.svg
    :alt: A side-by-side comparison of synthesis filters for two output samples.

In fact, the pattern of filters responsible for each output sample during
synthesis follow the same interleaving pattern as the output levels and bands
during analysis.

"""

__all__ = [
    "lifting_stage_offsets",
    "combined_lifting_stages_offsets",
    "wavelet_filter_offsets",
    "subsampled_offsets_for_level",
    "wavelet_filter_minimum_length_and_analysis_offsets",
]


def lifting_stage_offsets(stage):
    """
    Compute the left and right tap offsets of a VC-2 lifting stage's FIR
    filter.
    
    Parameters
    ==========
    stage : :py:class:`vc2_conformance.tables.LiftingStage`
    
    Returns
    =======
    left_offset, right_offset : int
    """
    left_offset = max(0, 1 - 2 * stage.D)
    right_offset = max(0, (2 * stage.L) + (2 * stage.D) - 3)
    
    return (left_offset, right_offset)


def combined_lifting_stages_offsets(stages):
    """
    Compute the combined left and right tap offsets of a series of lifting
    stage.
    
    Parameters
    ==========
    stages : [:py:class:`vc2_conformance.tables.LiftingStage`, ...]
    
    Returns
    =======
    left_offset, right_offset : int
    """
    combined_left_offset = 0
    combined_right_offset = 0
    
    for stage in stages:
        left_offset, right_offset = lifting_stage_offsets(stage)
        combined_left_offset += left_offset
        combined_right_offset += right_offset
    
    return (combined_left_offset, combined_right_offset)


def wavelet_filter_offsets(lifting_filter_parameters):
    """
    Find the left and right tap offsets for the low- and high-pass filters
    implemented by the supplied wavelet filter.
    
    Parameters
    ==========
    lifting_filter_parameters : :py:class:`vc2_conformance.tables.LiftingFilterParameters`
    
    Returns
    =======
    s_l, s_r, d_l, d_r : int
        In the following order:
        
        * The low-pass filter left offset (:math:`s_L`)
        * The low-pass filter right offset (:math:`s_R`)
        * The high-pass filter left offset (:math:`d_L`)
        * The high-pass filter right offset (:math:`d_R`)
    """
    final_stage_output = {
        LiftingFilterTypes.even_add_odd: "even",  # Type 1
        LiftingFilterTypes.even_subtract_odd: "even",  # Type 2
        LiftingFilterTypes.odd_add_even: "odd",  # Type 3
        LiftingFilterTypes.odd_subtract_even: "odd",  # Type 4
    }[lifting_filter_parameters.stages[-1].lift_type]
    
    if final_stage_output == "even":
        s_l, s_r = combined_lifting_stages_offsets(lifting_filter_parameters.stages)
        d_l, d_r = combined_lifting_stages_offsets(lifting_filter_parameters.stages[:-1])
    else:
        s_l, s_r = combined_lifting_stages_offsets(lifting_filter_parameters.stages[:-1])
        d_l, d_r = combined_lifting_stages_offsets(lifting_filter_parameters.stages)
    
    return s_l, s_r, d_l, d_r


def subsampled_offsets_for_level(s_l, s_r, d_l, d_r, level):
    r"""
    Given the low-pass and high-pass filter offsets for a (single level)
    wavelet filter as produced by :py:func:`wavelet_filter_offsets`, return the
    low- and high-pass subsampled offsets. That is, the number of samples at
    either end of that subband's signal which contain repeated terms.
    
    Parameters
    ==========
    s_l, s_r, d_l, d_r : int
        In the following order:
        
        * The low-pass filter left offset (:math:`s_L`)
        * The low-pass filter right offset (:math:`s_R`)
        * The high-pass filter left offset (:math:`d_L`)
        * The high-pass filter right offset (:math:`d_R`)
    
    Returns
    =======
    s_sub_l_level, s_sub_r_level, d_sub_l_level, d_sub_r_level : int
        In the following order:
        
        * The low-pass subband filter left offset (:math:`s'_{L,\textrm{level}}`)
        * The low-pass subband filter right offset (:math:`s'_{R,\textrm{level}}`)
        * The high-pass subband filter left offset (:math:`d'_{L,\textrm{level}}`)
        * The high-pass subband filter right offset (:math:`d'_{R,\textrm{level}}`)
    """
    s_sub_l_level = ((s_l + 1)*(2**(level+1) - 1)) // (2**(level+1))
    s_sub_r_level = (s_r*(2**(level+1) - 1)) // (2**(level+1))
    
    d_sub_l_level = ((s_l + d_l - 1)*(2**level) - s_l + 2**(level+1) - 1) // (2**(level+1))
    d_sub_r_level = ((s_r + d_r - 1)*(2**level) - s_r + 2**(level+1)) // (2**(level+1))
    
    return s_sub_l_level, s_sub_r_level, d_sub_l_level, d_sub_r_level


def wavelet_filter_minimum_length_and_analysis_offsets(lifting_filter_parameters, depth):
    """
    Find the minimum input length required for a wavelet filter of the
    specified type and depth to ensure every subband contains at least one
    sample with no repeated terms.
    
    Parameters
    ==========
    lifting_filter_parameters : :py:class:`vc2_conformance.tables.LiftingFilterParameters`
    depth : int
        The filter depth, where '1' is a single wavelet transform.
    
    Returns
    =======
    min_length : int
        The minimum filter input length required to ensure every output band of
        the supplied analysis filter includes one repeated-term-free sample.
    high_pass_subbands_offsets : [(d_sub_l_0, d_sub_r_0), (d_sub_l_1, d_sub_r_1), ...]
        The high-pass subbands' left and right offsets (i.e. number of entries
        at the start and end of each high-pass band with repeated terms). The
        first pair are for level 0 high-pass, the second pair for level 1
        high-pass and so on up to depth-1.
    low_pass_subband_offset : (s_sub_l_level, s_sub_r_level)
        The low-pass subband's left and right offset (i.e. number of entries at
        the start and end of each low-pass band with repeated terms). There is
        only one low-pass band and that is for level depth-1.
    """
    
    s_l, s_r, d_l, d_r = wavelet_filter_offsets(lifting_filter_parameters)
    
    min_length = 1
    
    high_pass_subbands_offsets = []
    s_sub_l_level = 0
    s_sub_r_level = 0
    
    for level in range(depth):
        (
            s_sub_l_level,
            s_sub_r_level,
            d_sub_l_level,
            d_sub_r_level,
        ) = subsampled_offsets_for_level(s_l, s_r, d_l, d_r)
        
        low_pass_band_min_width = s_sub_l_level + s_sub_r_level + 1
        high_pass_band_min_width = d_sub_l_level + d_sub_r_level + 1
        
        min_length = max(
            min_length,
            low_pass_subband_offset * 2**(level + 1),
            high_pass_subband_offset * 2**(level + 1),
        )
        high_pass_subbands_offsets.append((d_sub_l_level, d_sub_r_level))
    
    return (
        min_length,
        high_pass_subbands_offsets,
        (s_sub_l_level, s_sub_r_level),
    )
