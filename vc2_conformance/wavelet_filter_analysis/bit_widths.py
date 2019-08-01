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

    A unique error term, :math:`e_i`, is introduced for every division
    operation, otherwise unrelated error terms may erroneously cancel out.

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


Symbolic Evaluation of Pseudocode
---------------------------------

This focus of this module is implementing the two steps involved in performing
real-valued filter analysis with error tracking: finding worst-case values and
estimating worst-case rounding errors.

For both tasks, an algebraic expression describing the filters used by VC-2 is
required. Rather than directly writing such an expression, the VC-2 pseudocode
functions themselves are used. Using the :py:mod:`sympy` computer algebra
system, the pseudocode can be fed abstract symbols as input (in place of
concrete integer values) resulting in an algebraic expression for the filter
which produced each output value.

This approach avoids the need to directly construct an algebraic expression
describing the filters required while also ensuring consistency with the
(normative) pseudocode in the specification.

The following functions are provided for creating
:py:class:`~sympy.core.symbol.Symbol`\ s for wavelet filter inputs and error
terms.

.. autofunction:: new_analysis_input

.. autofunction:: new_synthesis_input

.. autofunction:: new_error_term

Ideally, plain :py:class:`~sympy.core.symbol.Symbol`\ s would be passed as
inputs to the pseudocode, eventually producing a symbolic output.
Unfortunately :py:mod:`sympy` does not implement the shift operator used by the
VC-2 pseudocode for truncating divisions nor add error terms automatically.
Consequently, the following wrapper class for :py:mod:`sympy` values is
provided.

.. autoclass:: SymbolicValue

Since the wavelet transform is linear, all outputs consist of a weighted sum of
the input values. The following utility function breaks down such sums into a
dictionary giving the weight of each variable.

.. autofunction:: extract_variables

Built upon this function is the following which computes the total (absolute)
magnitude of the error terms in an expression:

.. autofunction:: total_error_magnitude

Finally, a pair of functions is provided to extract the coefficients of the
synthesis/analysis coefficient terms in an expression:

.. autofunction:: analysis_input_coefficients

.. autofunction:: synthesis_input_coefficients


Determining input sizes and representative outputs
--------------------------------------------------

The primary challenge of using the VC-2 pseudocode to produce algebraic
expressions for filters is determining the required input dimensions and a
representative collection of output pixel/sample values which completely
describe the implemented filter banks. We'll introduce and explain these
challenges more fully, and give their solution, in the remainder of this
section.

In this section we'll consider at the one dimensional case since the minimum
width and height of a 2D picture (and the representative sampling points) can
be determined independently.

We'll also mostly think about filtering occurring *in-place* rather than
*out-of-place* (see figure below).

.. image:: /_static/bit_widths/inplace_filtering.svg
    :alt: Comparison of out-of-place and in-place filtering representations.


Why is there a minimum input size?
``````````````````````````````````

VC-2's wavelet filters implement FIR filters which, near the edges of the
picture, may require input samples which don't exist (see figure below):

.. image:: /_static/bit_widths/filter_repeated_terms.svg
    :alt: VC-2 filter showing how terms are repeated.

VC-2 uses edge extension (see (15.4.4.2) in the VC-2 specification) to fill in
any missing values during filtering. The result is that values near the edges
of the filter's output contain repeated terms, conceptually implementing a
simpler filter than those in the middle of the output.

To get a complete algebraic expression for VC-2's filters, we must ensure that
the input we provide is sufficiently large that we can find an output sample in
which no terms have been repeated.

Wavelet filtering with lifting
``````````````````````````````

VC-2 uses multi-level wavelet filters specified in terms of a series of
'lifting' operations in which odd or even samples are updated using simple
filters. The process is illustrated below for a typical 2-level wavelet
transform in which each filter is described as a pair of lifting operations:

.. image:: /_static/bit_widths/analysis_vs_synthesis.svg
    :alt: Wavelet analysis and synthesis implemented using lifting.

The lifting process defines a computationally efficient way of implementing the
overall filtering operations used by VC-2. For example, the diagram below
illustrates how the lifting operations produce one particular output value,
alongside the equivalent classical filter for that value.

.. image:: /_static/bit_widths/lifting_with_equivalent_filter.svg
    :alt: Lifting stages and an equivalent filter which produce a given result.

For a given set of lifting stages and transform depth, the actual filter
implemented varies depending on the output sample chosen as illustrated in the
figure below:

.. image:: /_static/bit_widths/lifting_filter_patterns.svg
    :alt: Analysis and synthesis lifting filter patterns for different outputs.

The following function, given an output sample index, filter depth and set of
lifting stages, computes the input indices used to produce that output value.

.. autofunction:: get_filter_input_sample_indices


Finding minimum input widths and edge-extension free output samples
```````````````````````````````````````````````````````````````````

For a transform with :math:`\textrm{depth}` levels, output samples are produced
by one of :math:`2^{\textrm{depth}}` different filters; repeating every
:math:`2^{\textrm{depth}}` samples. This can be seen by observing that the
pattern of lifting stages (as shown in the figures above) repeats at this
interval.

In principle, by determining the filters for output samples :math:`0` to
:math:`2^{\textrm{depth}} - 1` (inclusive) we obtain a description of every
filter implemented by a given multi-level lifting wavelet transform. In
practice, however, these samples are likely to contain repeated terms due to
edge extension. Instead we must pick an alternative sample, some multiple of
:math:`2^{\textrm{depth}}` samples away which doesn't contain any edge effects.


Synthesis
~~~~~~~~~

Using the :py:func:`get_filter_input_sample_indices` function it is straightforward to
determine if a particular output sample contains any terms beyond the bounds of
the input (and, therefore, will be impacted by edge effects). In fact, if
:math:`l` and :math:`r` are the indices of the left-most and right-most input
samples used to produce output sample :math:`i` (where :math:`i \in [0,
2^{\textrm{depth}} - 1]`) in a :math:`\textrm{depth}`-level transform then
sample :math:`i'` gives the first instance of this filter with no edge effects:

.. math::

    i' = \left\lceil\frac{-l}{2^{\textrm{depth}}}\right\rceil 2^{\textrm{depth}} + i

And :math:`w` the minimum input width required:

.. math::

    w = i' + r - i + 1

Using the above, it is straightforward to compute general minimum input width
and set of representative sample indices for the implemented filter. The
following convenience function is provided for this purpose.

.. autofunction:: get_representative_synthesis_sample_indices

Analysis
~~~~~~~~

While the same approach may be used to find representative analysis filter
taps, there is a slight optimisation which can be applied. In the analysis
filter case, some of the sample points selected using the approach will always
be equivalent.

At the simplest level, the reason for this is that analysis breaks the input
picture into various spatial frequency bands and samples within each band are
always the result of the same filtering step. As such, instead of
:math:`2^{\textrm{depth}}` sample points we therefore only require
:math:`\textrm{depth}+1`.

.. note::

    Another way to look at this effect is to observe that, working backwards
    from output, every lifting stage's inputs always align with the outputs of
    the previous stage resulting in a symmetric trees of filters. Since only
    :math:`\textrm{depth}+1` such symmetric trees can be constructed, only that
    many different filters may be implemented.

In the in-place signal representation, values from each subband are
interleaved. This is illustrated below for a 3-level transform:

.. image:: /_static/bit_widths/level_interleaving.svg
    :alt: Illustration of where subbands are located in the in-place (interleaved) representation.

In general, the sample spacing and first sample in each band are given by:

* Level 0 (Low-pass/DC band):
    * Offset: :math:`0`
    * Spacing: :math:`2^{\textrm{depth}}`
* Level :math:`level` (High-pass bands):
    * Offset: :math:`2^{\textrm{depth} - \textrm{level}}`
    * Spacing: :math:`2^{1 + \textrm{depth} - \textrm{level}}`

Consequently, only the analysis output samples at indices :math:`0` and
:math:`2^{\textrm{depth}-\textrm{level}-1}` for :math:`\textrm{level} \in [0,
2^{\textrm{depth}}-1]`, or their nearest edge-effect free equivalents, need be
chosen.

Since since every sample within a subband is produced by the same filter, and
samples from most subbands are interleaved with a spacing finer than
:math:`2^{\textrm{depth}}` we can do better than the expression for :math:`i'`
above for the synthesis. If :math:`o` and :math:`s` are the offset and spacing
values for the subband containing the output sample at index :math:`i=o`, the
first edge-effect free analysis filter output index will be:

.. math::

    i' = \left\lceil\frac{-l}{s}\right\rceil s + o

As before the minimum input width required will be:

.. math::

    w = i' + r - o + 1

Finally, the following convenience function brings everything together. Rather
than returning in-place output indices, this function returns VC-2 style
out-of-pace (i.e. subband) indices which are likely to be more useful.

.. autofunction:: get_representative_analysis_sample_indices

"""

import operator

from sympy import Symbol, sympify

from vc2_conformance.tables import LiftingFilterTypes

__all__ = [
    "new_error_term",
    "new_analysis_input",
    "new_synthesis_input",
    "SymbolicValue",
    "extract_variables",
    "total_error_magnitude",
    "analysis_input_coefficients",
    "synthesis_input_coefficients",
    "get_filter_input_sample_indices",
    "get_representative_synthesis_sample_indices",
    "get_representative_analysis_sample_indices",
]


def new_analysis_input(x, y):
    """
    Create a new :py:mod:`sympy` symbol for an input to the analysis filter.
    
    The new symbol will have a name of the form 'a_xxx_yyy'.
    """
    return Symbol("a_{}_{}".format(x, y))

def new_synthesis_input(level, subband, x, y):
    """
    Create a new :py:mod:`sympy` symbol for an input to the synthesis filter.
    
    The new symbol will have a name of the form 's_level_subband_xxx_yyy'.
    """
    return Symbol("s_{}_{}_{}_{}".format(level, subband, x, y))

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


class SymbolicValue(object):
    """
    A wrapper for symbolic :py:mod:`sympy` values which adds support for
    bit-shifts (which are translated into multiplications or divisions by
    powers of two with an added error term from :py:func:`new_error_term`).
    
    Usage::
    
        >>> from sympy import *
        
        >>> # Create SymbolicValues for some symbols
        >>> a, b = map(SymbolicValue, symbols("a b"))
        
        >>> # SymbolicValues can be used in arithmetic
        >>> a + b
        SymbolicValue(a + b)
        
        >>> # Shift can now be used within the arithmetic!
        >>> (a + b) << 3
        SymbolicValue(8(a + b))
        
        >>> # Right-shifting introduces an error term to represent the lost
        >>> # fractional bits
        >>> (a + b) >> 1
        SymbolicValue((a + b)/2 + e_1)
        
        >>> # Access the raw value later as required
        >>> sym_val = a + b
        >>> sym_val.value
        a + b
    """
    
    @classmethod
    def as_symbolic_value(cls, value):
        if type(value) is cls:
            return value
        else:
            return cls(value)
    
    @classmethod
    def apply(cls, a, b, fn):
        a = cls.as_symbolic_value(a)
        b = cls.as_symbolic_value(b)
        return cls(fn(a.value, b.value))
    
    def __init__(self, value):
        self.value = value
    
    def __add__(self, other):
        return self.apply(self, other, operator.add)
    
    def __sub__(self, other):
        return self.apply(self, other, operator.sub)
    
    def __mul__(self, other):
        return self.apply(self, other, operator.mul)
    
    def __rshift__(self, other):
        return self.apply(self, other, lambda a, b: a / (2**b) + new_error_term())
    
    def __lshift__(self, other):
        return self.apply(self, other, lambda a, b: a * (2**b))
    
    def __radd__(self, other):
        return self.apply(other, self, operator.add)
    
    def __rsub__(self, other):
        return self.apply(other, self, operator.sub)
    
    def __rmul__(self, other):
        return self.apply(other, self, operator.mul)
    
    def __rrshift__(self, other):
        return self.apply(other, self, lambda a, b: a / (2**b) + new_error_term())
    
    def __rlshift__(self, other):
        return self.apply(other, self, lambda a, b: a * (2**b))
    
    def __repr__(self):
        return "{}({!r})".format(type(self).__name__, self.value)
    
    def __str__(self):
        return str(self.value)


def extract_variables(expression):
    """
    Given a :py:mod:`sympy` expression containing a linear sum of weighted
    terms, return a dictionary giving the weight assigned to each term in the
    expression. Any constant value will be included under the key ``1``.
    
    Example::
    
        >>> a, b = symbols("a b")
        >>> extract_variables(10*a + 20*b + 30)
        {a: 10, b: 20, 1: 30}
    """
    variables = {}
    
    # Special case
    if expression == 0:
        return variables
    
    for term in sympify(expression).expand().as_ordered_terms():
        if len(term.free_symbols) == 0:
            variable = 1
            coeff = term
        elif len(term.free_symbols) == 1:
            variable = next(iter(term.free_symbols))
            coeff = term / variable
        else:
            raise ValueError("extract_variables expects a linear combination of symbols.")
        
        variables[variable] = variables.get(variable, 0) + coeff
    
    return variables


def total_error_magnitude(expression):
    """
    Given a :py:mod:`sympy` expression containing error terms (created by
    :py:func:`new_error_term`), return the total absolute magnitude of all of
    the error terms.
    """
    out = 0
    
    for variable, coeff in extract_variables(expression).items():
        if isinstance(variable, Symbol) and variable.name.startswith("e_"):
            out += abs(coeff)
    
    return out


def analysis_input_coefficients(expression):
    """
    Given an expression containing symbols produced by
    :py:func:`new_analysis_input`, return a dictionary {(x, y): coefficient,
    ...} for the coefficients in the expression.
    """
    out = {}
    
    for variable, coeff in extract_variables(expression).items():
        if isinstance(variable, Symbol) and variable.name.startswith("a_"):
            _, x, y = variable.name.split("_")
            out[(int(x), int(y))] = coeff
    
    return out


def synthesis_input_coefficients(expression):
    """
    Given an expression containing symbols produced by
    :py:func:`new_synthesis_input`, return a dictionary {(level, band, x, y):
    coefficient, ...} for the coefficients in the expression.
    """
    out = {}
    
    for variable, coeff in extract_variables(expression).items():
        if isinstance(variable, Symbol) and variable.name.startswith("s_"):
            _, level, subband, x, y = variable.name.split("_")
            out[(int(level), subband, int(x), int(y))] = coeff
    
    return out


def get_filter_input_sample_indices(output_sample_index, filter_parameters, depth, synthesis):
    """
    Compute the indices of the input samples used to compute a particular
    sample in the output.
    
    Parameters
    ==========
    output_sample_index : int
        The index of the output sample whose filter inputs are to be found.
    filter_parameters : :py:class:`vc2_conformance.tables.LiftingFilterParameters`
        The lifting filter specification.
    depth : int
        The filter transform depth.
    synthesis : bool
        Should be ``True`` for synthesis filters and ``False`` for analysis
        filters.
        
        .. note::
        
            The 'filter_parameters' argument must be provided with a set of
            filter parameters which implements the correct type of filter.
            Specifically, the lifting stages provided by the VC-2 specification
            and in :py:data:`vc2_conformance.tables.LIFTING_FILTERS` describe
            *synthesis* filters. If an analysis filter tap indices are
            required, the filter specification must be converted into an
            analysis filter first.
    
    Returns
    =======
    input_sample_indices : [int, ...]
        The input sample indices (in ascending order) used to compute the
        provided output index.
    """
    # This function uses a simple iterative process to determine the input
    # indices required to compute a given output. For each transform level and
    # lifting stage, a list of required input indices is updated with all
    # additional inputs used by that lifting stage. This process starts at the
    # output sample and works its way backwards through the lifting stages and
    # levels to eventually arrive at the input.
    #
    # As an aside, in the special case of analysis filters, this iterative
    # function can be simplified into a compact algebraic expression. However
    # no such simplification is possible for synthesis filters which typically
    # use an irregular and asymmetric sets of input samples, hence the
    # iterative approach used here.
    
    input_sample_indices = set([output_sample_index])

    # Warning: In this function, levels are numbered in the opposite order to
    # the VC-2 specification for reasons of mathematical convenience. That is,
    # at level '0' the lifting filters act on the non-subsampled signal while
    # level 'depth-1' acts on the maximally subsampled signal.
    
    # Work our way backwards through the filtering stages (bottom to top in the
    # diagrams)
    if synthesis:
        # E.g.
        #
        #     @  @  @  @  @  @  @  @  @   Input Samples
        #       ___/|\___   ___/|\___     \
        #      /    |    \ /    |    \     |
        #     @  @  @  @  @  @  @  @  @     > Level 1
        #     |\___ | ___/ \___ | ___/|    |
        #     |    \|/         \|/    |   /
        #     @  @  @  @  @  @  @  @  @
        #     |\ | / \ | / \ | / \ | /|   \
        #     | \|/   \|/   \|/   \|/ |    |
        #     @  @  @  @  @  @  @  @  @     > Level 0
        #     | / \ | / \ | / \ | / \ |    |
        #     |/   \|/   \|/   \|/   \|   /
        #     @  @  @  @  @  @  @  @  @   Output Samples
        levels = range(depth)
    else:
        # E.g.
        #
        #     @  @  @  @  @  @  @  @  @   Input Samples
        #     | / \ | / \ | / \ | / \ |   \
        #     |/   \|/   \|/   \|/   \|    |
        #     @  @  @  @  @  @  @  @  @     > Level 0
        #      \ | / \ | / \ | / \ | /     |
        #       \|/   \|/   \|/   \|/     /
        #     @  @  @  @  @  @  @  @  @
        #      \___ | ___/ \___ | ___/    \
        #          \|/         \|/         |
        #     @  @  @  @  @  @  @  @  @     > Level 1
        #       ___/|\___   ___/|\___      |
        #      /    |    \ /    |    \    /
        #     @  @  @  @  @  @  @  @  @   Output Samples
        levels = reversed(range(depth))
    
    for level in levels:
        # At this level, the lifting filter's taps will be spaced this many
        # samples apart, e.g.
        #
        #        step        step         step
        #    |<--------->|<--------->|<--------->|
        #    @  @  @  @  @  @  @  @  @  @  @  @  @   Lift input
        #     \___________\___ | ___/___________/
        #                     \|/
        #    @  @  @  @  @  @  @  @  @  @  @  @  @   Lift output
        #
        #    (Example shows length=3, delay=-1, Level=2)
        #
        step = 2**(level+1)
        
        # The lifting filter has a central tap which is offset this number
        # of samples from the tap with delay '0'.
        #
        #             center_offset
        #                |<--->|
        #    @  @  @  @  @  @  @  @  @  @  @  @  @   Lift input
        #     \___________\___ | ___/___________/
        #                     \|/
        #    @  @  @  @  @  @  @  @  @  @  @  @  @   Lift output
        #
        #    (Example shows length=3, delay=-1, Level=2)
        center_offset = 2**level
        
        for stage in reversed(filter_parameters.stages):
            # Which sample index is updated by the first filter in this lifting
            # stage (i.e. where is the first filter's central tap located)?
            start_offset = {
                # 'Even' samples to be updated
                LiftingFilterTypes.even_add_odd: 0,
                LiftingFilterTypes.even_subtract_odd: 0,
                # 'Odd' samples to be updated
                LiftingFilterTypes.odd_add_even: 2**level,
                LiftingFilterTypes.odd_subtract_even: 2**level,
            }[stage.lift_type]
            
            # For each sample index used so far, if any of these are output by
            # the current filter stage, this stage's inputs must also be
            # included.
            for sample_index in input_sample_indices.copy():
                if (sample_index - start_offset) % step == 0:
                    leftmost_tap_index = sample_index - center_offset + (step * stage.D)
                    for tap_index in range(stage.L):
                        input_sample_indices.add(leftmost_tap_index + (tap_index*step))

    return sorted(input_sample_indices)


def get_representative_synthesis_sample_indices(filter_parameters, depth):
    r"""
    Find the set of output sample indices which give a representative example
    of every filtering operation implemented by a given multi-level wavelet
    synthesis filter, free from edge effects.
    
    Parameters
    ==========
    filter_parameters : :py:class:`vc2_conformance.tables.LiftingFilterParameters`
        The lifting filter specification. Must define a synthesis filter.
    depth : int
        The filter transform depth.
    
    Returns
    =======
    minimum_width : int
        The minimum width the input (and output...) signal must have to ensure
        every output sample point is free from filter edge effects.
    output_sample_indices : [int, ...]
        A set of output sample indices (in ascending order) for output values
        filtered in each of the :math:`2^{\textrm{depth}}` different ways
        implemented by the specified wavelet.
    """
    minimum_width = 1
    output_sample_indices = []
    
    for ideal_output_sample_index in range(2**depth):
        input_sample_indices = get_filter_input_sample_indices(
            ideal_output_sample_index,
            filter_parameters,
            depth,
            synthesis=True,
        )
        
        # Find the first comparable output index which doesn't suffer from any
        # edge-effects
        left = min(input_sample_indices)
        right = max(input_sample_indices)
        output_sample_index = (
            (
                ((-left + 2**depth - 1)//2**depth) *
                2**depth
            ) +
            ideal_output_sample_index
        )
        
        minimum_width = max(
            minimum_width,
            output_sample_index + right - ideal_output_sample_index + 1,
        )
        
        output_sample_indices.append(output_sample_index)
    
    return minimum_width, sorted(output_sample_indices)


def get_representative_analysis_sample_indices(filter_parameters, depth):
    r"""
    Find the set of output subband sample indices which give a representative
    example of every filtering operation implemented by a given multi-level
    wavelet analysis filter, free from edge effects.
    
    Parameters
    ==========
    filter_parameters : :py:class:`vc2_conformance.tables.LiftingFilterParameters`
        The lifting filter specification. Must define an analysis filter.
    depth : int
        The filter transform depth.
    
    Returns
    =======
    minimum_width : int
        The minimum width the input signal must have to ensure
        every output sample point is free from filter edge effects.
    output_sample_indices : [(level, band, index) , ...]
        A set of :math:`\textrm{depth}+1` output sample indices (lowest
        frequency first) for output values filtered in each of the  different
        ways implemented by the specified wavelet.
        
        Level indices are given in the order used by VC-2, that is level
        :math:`0` contains the DC band, :math:`1` contains the lowest frequency
        high-pass band, and :math:`\textrm{depth}` contains the highest
        frequency high-pass band.
        
        Band names are either ``"L"`` for the low-frequency band and ``"H"``
        for the high-frequency band.
    """
    minimum_width = 1
    output_sample_indices = []
    
    for level in range(depth + 1):
        # Find the offset and spacing of values in this level/subband. For
        # example, for the subband whose in-place samples are in the positions
        # shown below, the subband offset and spacing are:
        #
        #     |<->| subband_offset == 1
        #
        #     +---+---+---+---+---+---+---+---+
        #     |   |###|   |###|   |###|   |###|
        #     +---+---+---+---+---+---+---+---+
        #
        #             |<----->| subband_spacing == 2
        #
        if level == 0:
            subband_offset = 0
            subband_spacing = 2**depth
        else:
            subband_offset = 2**(depth - level)
            subband_spacing = 2**(1 + depth - level)
        
        input_sample_indices = get_filter_input_sample_indices(
            subband_offset,
            filter_parameters,
            depth,
            synthesis=False,
        )
        
        # Find the first sample in this subband without any edge-effects
        left = min(input_sample_indices)
        right = max(input_sample_indices)
        subband_index = (-left + subband_spacing - 1)//subband_spacing
        output_sample_index = (subband_index * subband_spacing) + subband_offset
        
        minimum_width = max(
            minimum_width,
            output_sample_index + right - subband_offset + 1,
        )
        
        output_sample_indices.append((
            level,
            "L" if level == 0 else "H",
            subband_index,
        ))
    
    return minimum_width, output_sample_indices

