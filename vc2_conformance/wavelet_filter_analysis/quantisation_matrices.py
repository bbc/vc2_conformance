r"""
Wavelet Filter Quantisation Matrix Computation
==============================================

This (heavily annotated) module implements the procedure required to compute
quantisation matrices for arbitrary combinations of VC-2 filters and transform
depths.

If you're not interested in the details, you can skip directly to the
convenience function for computing quantisation matrices:
:py:func:`derive_quantisation_matrix`.

Motivation/Background
---------------------

VC-2 achieves lossy compression by quantizing wavelet transform coefficients.
This quantisation introduces errors (noise) into the transformed signal. When a
picture is later synthesised from these transform values, this picture too will
have added noise.

The transformed signal is broken up into several individual bands,
approximately corresponding to different spatial frequency components. Noise
added to each of these bands has a differing effect on the final picture.
Depending on the specific filter in use, a certain amount of noise added in one
band may have a greater impact on the final picture than the same noise added
to a different band.

As a result, a uniform source of noise (e.g. quantisation) can result in a
skewed distribution of noise in the resulting picture (e.g.  excessive low- or
high-frequency noise with little in other spatial frequencies). This is
undesirable since the noise level at some spatial frequencies will become much
higher than it otherwise would be.

VC-2's quantisation matrices allow the quantisation levels in different
transform bands to be adjusted relative to each other. In this way, for
example, bands which are very sensitive to noise can be assigned lower
quantisation levels than bands which are relatively insensitive.

The default quantisation matrices provided with VC-2 are chosen such that
quantisation noise results in noise which is evenly spread across the frequency
spectrum in the synthesised picture. It is the calculation of these matrices
which is the focus of this module.

It is worth emphasising that the default quantisation matrices are *not*
intended to exploit psycho-visual phenomena (for example by preserving
low-frequency components at the expense of higher frequencies). VC-2 users are
free to define custom quantisation matrices which exploit these phenomena if
required, but this will not be discussed further here.


Implementation
--------------

This module performs all of the necessary steps required to compute
quantisation matrices for VC-2's wavelet filters.  Internally the SymPy_
computer algebra system is used for all calculations. This means that all
operations are carried out symbolically in much the same way they would be
performed on paper.

.. _SymPy: https://www.sympy.org/


Filter Noise Gain
-----------------

The noise-gain of a FIR filter with coefficients :math:`h_1`, ..., :math:`h_m`
is:

.. math::
    
    \sqrt{\sum_M h_m^2}

This figure indicates the gain the filter will introduce to a white-noise
signal. This function is implemented as:

.. autofunction:: fir_filter_noise_gain

If we make the (mostly reasonable) assumption that quantisation introduces
white noise, it is the filter noise gains (of the synthesis wavelet filters)
which our quantisation matrix must attempt to even out. To be able to do this
we need to find the FIR filter coefficients which are to be fed to
:py:func:`fir_filter_noise_gain`.


From lifting to classical filters
---------------------------------

For reasons of efficiency and perfect reconstruction, the VC-2 wavelet filters
are specified in terms of lifting operations:

.. image:: /_static/quantisation_matrices/lifting_filters.svg
    :alt: VC-2's lifting filter architecture.

This figure shows both the analysis (picture to transform coefficients) and
synthesis (transform coefficients to picture) filtering processes.  Both
filters are defined by :math:`N` update (:math:`U_n`) and predict (:math:`P_n`)
stages which operate on sub-sampled signals. In most (but not all) of the VC-2
filters, only a single predict and update pair is used (i.e. :math:`N = 1`).

By contrast, the :py:func:`fir_filter_noise_gain` function requires our filters
to be defined as classical Finite Impulse Response (FIR) filters. That is, we
must transform the picture above into the one below:

.. image:: /_static/quantisation_matrices/classical_filters.svg
    :alt: The classical FIR filter architecture.


Matrix form
```````````

The first step in transforming the lifting filter representation into classical
form is producing a matrix representation for the lifting procedure.

In this section we'll use the :math:`z`-domain representation of all the
filters and signals involved. (See section 7.1 in "Ripples in Mathematics" for
a targeted, whirl-wind introduction.)


The figure below shows the lifting representation of the analysis (top) and
synthesis (bottom) filters again, additionally labelled according to the
convention used here:

.. image:: /_static/quantisation_matrices/lifting_z_transform.svg
    :alt: Names used for synthesis z-transform representation.

Using a :math:`z`\ -domain representation then our picture signal,
:math:`X(z)`, is split into even (:math:`X_0(z)`) and odd (:math:`X_1(z)`)
samples:

.. math::

    \begin{array}{ll}
        X_0(z) = \sum_n X[2n] z^{-n} & \text{Even samples} \\
        X_1(z) = \sum_n X[2n + 1] z^{-n} & \text{Odd samples} \\
    \end{array}

Likewise the transform signal is made up of a Low Frequency (LF) component,
:math:`Y_0(z)` and a High Frequency (HF) component :math:`Y_1(z)`. We define
:math:`Y(z)` to be an interleaving of these two signals where the LF component
makes up the even samples and the HF component the odd samples:

.. math::

    \begin{array}{ll}
        Y_0(z) = \sum_n Y[2n] z^{-n} & \text{LF samples (even)} \\
        Y_1(z) = \sum_n Y[2n + 1] z^{-n} & \text{HF samples (odd)} \\
    \end{array}

The resulting :math:`z`-domain matrix forms of the analysis and synthesis
lifting processes respectively are:


.. math::

    \begin{bmatrix}
        Y_0(z) \\
        Y_1(z)
    \end{bmatrix}
    &=
    \begin{bmatrix}
        1 & -U_N(z) \\
        0 & 1 \\
    \end{bmatrix}
    \begin{bmatrix}
        1 & 0 \\
        -P_N(z) & 1 \\
    \end{bmatrix}
    \cdots
    \begin{bmatrix}
        1 & -U_2(z) \\
        0 & 1 \\
    \end{bmatrix}
    \begin{bmatrix}
        1 & 0 \\
        -P_2(z) & 1 \\
    \end{bmatrix}
    \begin{bmatrix}
        1 & -U_1(z) \\
        0 & 1 \\
    \end{bmatrix}
    \begin{bmatrix}
        1 & 0 \\
        -P_1(z) & 1 \\
    \end{bmatrix}
    \begin{bmatrix}
        X_0(z) \\
        X_1(z)
    \end{bmatrix}
    \\
    \begin{bmatrix}
        X_0(z) \\
        X_1(z)
    \end{bmatrix}
    &=
    \begin{bmatrix}
        1 & 0 \\
        P_1(z) & 1 \\
    \end{bmatrix}
    \begin{bmatrix}
        1 & U_1(z) \\
        0 & 1 \\
    \end{bmatrix}
    \begin{bmatrix}
        1 & 0 \\
        P_2(z) & 1 \\
    \end{bmatrix}
    \begin{bmatrix}
        1 & U_2(z) \\
        0 & 1 \\
    \end{bmatrix}
    \cdots
    \begin{bmatrix}
        1 & 0 \\
        P_N(z) & 1 \\
    \end{bmatrix}
    \begin{bmatrix}
        1 & U_N(z) \\
        0 & 1 \\
    \end{bmatrix}
    \begin{bmatrix}
        Y_0(z) \\
        Y_1(z)
    \end{bmatrix}

Where :math:`U_n(z)` and :math:`P_n(z)` are the :math:`z`-transform
representations of the lifting step filters. These functions can be found for
a given wavelet transform using:

.. autofunction:: lifting_stage_to_z_transform

.. autoclass:: StageType

If the left-most parts of the above matrices are multiplied together into
:math:`2 \times 2` matrices: :math:`\textbf{H}(z)` (the analysis filter in
matrix form) and :math:`\textbf{G}(z)` (the synthesis filter in matrix form)
yielding:

.. math::

    \begin{bmatrix}
        Y_0(z) \\
        Y_1(z)
    \end{bmatrix}
    &=
    \textbf{H}(z)
    \begin{bmatrix}
        X_0(z) \\
        X_1(z)
    \end{bmatrix}

    \begin{bmatrix}
        X_0(z) \\
        X_1(z)
    \end{bmatrix}
    &=
    \textbf{G}(z)
    \begin{bmatrix}
        Y_0(z) \\
        Y_1(z)
    \end{bmatrix}

For the analysis filter and synthesis filters respectively.

The following function may be used to convert a
:py:class:`vc2_conformance.tables.LiftingFilterParameters` into a :math:`2
\times 2` matrix.

.. autofunction:: wavelet_filter_to_matrix_form

.. note::

    All of the wavelet specifications in the VC-2 specification (and therefore
    in :py:data:`vc2_conformance.tables.LIFTING_FILTERS`) define *synthesis*
    filter lifting stages. As suggested by the figures above, these are easily
    converted into analysis filter specifications by reversing the order and
    changing the operation. The following function may be used to convert
    between analysis and synthesis lifting filters:
    
    .. autofunction:: convert_between_synthesis_and_analysis


Matrix form to classical form
`````````````````````````````

The matrix form representation achieved above implements the following
(slightly more formally illustrated, this time) analysis/synthesis filtering
processes:

.. image:: /_static/quantisation_matrices/matrix_form_formal.svg
    :alt: Formal z-domain matrix representation.

In this new diagram, the 'split' and 'interleave' processes are shown in terms
of their :math:`z`-domain operations.

From the matrix based representation (where our filters are defined by the
matrices :math:`\textbf{H}(z)` (analysis) and :math:`\textbf{G}(z)` (synthesis)
we now wish to decompose this into the classical form below:

.. image:: /_static/quantisation_matrices/classical_form_formal.svg
    :alt: Formal z-domain classical representation.

In this representation, the analysis filter is defined by :math:`H_0(z^2)` and
:math:`H_1(z^2)` and synthesis filter is defined by :math:`G_0(z^2)` and
:math:`G_1(z^2)`.

.. note::
    
    For those new to the :math:`z`-transform, for some signal :math:`[a_0, a_1,
    a_2, \ldots]`, whose :math:`z`-transform is :math:`A(z) = a_0 z^{0} + a_1
    z^{-1} + a_2 z^{-2} + \ldots` then :math:`A(z^2) = a_0 z^{0} + a_1 z^{-2} +
    a_2 z^{-4} + \ldots` which is equivalent to a signal :math:`[a_0, 0, a_1,
    0, a_2, 0, \ldots]`.

Full-rate filter matrix
~~~~~~~~~~~~~~~~~~~~~~~

The first step is to modify the :math:`\textbf{H}(z)` and :math:`\textbf{G}(z)`
filters to work on full-rate signals (i.e. to move the decimation step after
analysis or before synthesis, as illustrated below:

.. image:: /_static/quantisation_matrices/matrix_form_formal_decimate_inside.svg
    :alt: Decimation stages moved other side of filters.

The modification is straight-forward -- the filter coefficients are interleaved
with zeros; yielding the filters :math:`\textbf{H}(z^2)` and
:math:`\textbf{G}(z^2)` for the analysis and synthesis stages respectively.

If we ignore the decimation and upsampling steps in the diagram above (which
now directly cancel eachother out) we get the following matrix representation:

.. math::

    \begin{array}{cl}
        \begin{bmatrix}
            Y_0(z^2) \\
            Y_1(z^2) \\
        \end{bmatrix}
        =
        \mathbf{H}(z^2)
        \begin{bmatrix}
            X(z) \\
            z X(z) \\
        \end{bmatrix}
        & \quad\text{Analysis filter}\\
        \begin{bmatrix}
            X_0(z^2) \\
            X_1(z^2) \\
        \end{bmatrix}
        =
        \mathbf{G}(z^2)
        \begin{bmatrix}
            Y_0(z^2) \\
            Y_1(z^2) \\
        \end{bmatrix}
        & \quad\text{Synthesis filter} \\
    \end{array}

These can be written in expanded form like so:

.. math::

    \begin{array}{cl}
        \begin{bmatrix}
            Y_0(z^2) \\
            Y_1(z^2) \\
        \end{bmatrix}
        =
        \begin{bmatrix}
            H_{00}(z^2) & H_{01}(z^2) \\
            H_{10}(z^2) & H_{11}(z^2) \\
        \end{bmatrix}
        \begin{bmatrix}
            X(z) \\
            z X(z) \\
        \end{bmatrix}
        & \quad\text{Analysis filter}\\
        \begin{bmatrix}
            X_0(z^2) \\
            X_1(z^2) \\
        \end{bmatrix}
        =
        \begin{bmatrix}
            G_{00}(z^2) & G_{01}(z^2) \\
            G_{10}(z^2) & G_{11}(z^2) \\
        \end{bmatrix}
        \begin{bmatrix}
            Y_0(z^2) \\
            Y_1(z^2) \\
        \end{bmatrix}
        & \quad\text{Synthesis filter} \\
    \end{array}


Deriving the classical analysis filter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rewriting the matrix form of the analysis filter as two equations and
rearranging:

.. math::

    Y_0(z^2) &=
        H_{00}(z^2)X(z) + z H_{01}(z^2) X(z) \\
    &=
        \big( H_{00}(z^2) + z H_{01}(z^2) \big) X(z) \\
    
    Y_1(z^2) &=
        H_{10}(z^2)X(z) + z H_{11}(z^2) X(z) \\
    &=
        \big( H_{10}(z^2) + z H_{11}(z^2) \big) X(z) \\

This leads us to the following expressions for the classical analysis filter
representations:

.. math::

      H_0(z^2) &= H_{00}(z^2) + z H_{01}(z^2) \\
      H_1(z^2) &= H_{10}(z^2) + z H_{11}(z^2) \\

Deriving the classical synthesis filter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Next, we repeat the same process of producing a formulaic representation of the
matrix equation:

.. math::

    X_\text{even}(z) &=
        G_{00}(z^2) Y_0(z^2) + G_{01}(z^2) Y_1(z^2) \\
    
    zX_\text{odd}(z) &=
        G_{10}(z^2) Y_0(z^2) + G_{11}(z^2) Y_1(z^2) \\

In the diagrams we have defined :math:`X(z) = X_0(z^2) + z^{-1} X_1(z^2)`.
Substituting the formulae above into this expression and then rearranging we
get:

.. math::

    X(z) &= X_0(z^1) + z^{-1}X_1(z^2) \\
    &=
        G_{00}(z^2) Y_0(z^2) + G_{01}(z^2) Y_1(z^2) +
        z^{-1} \big( G_{10}(z^2) Y_0(z^2) + G_{11}(z^2) Y_1(z^2) \big) \\
    &=
        G_{00}(z^2) Y_0(z^2) + G_{01}(z^2) Y_1(z^2) +
        z^{-1} G_{10}(z^2) Y_0(z^2) + z^{-1} G_{11}(z^2) Y_1(z^2) \\
    &=
        \big( G_{00}(z^2) + z^{-1} G_{10}(z^2) \big) Y_0(z^2) +
        \big( G_{01}(z^2) + z^{-1} G_{11}(z^2) \big) Y_1(z^2) \\

From this we get the following expressions for the classical filter bank
representation.

.. math::

    G_0(z^2) &= G_{00}(z^2) + z^{-1} G_{10}(z^2) \\
    G_1(z^2) &= G_{01}(z^2) + z^{-1} G_{11}(z^2) \\

Implementation
~~~~~~~~~~~~~~

The steps above which convert from the matrix
representation of a filter to classical filters are implemented as:

.. autofunction:: analysis_matrix_to_classical_form

.. autofunction:: synthesis_matrix_to_classical_form

The filter coefficients can then be extracted from the resulting algebraic
expressions using

.. autofunction:: z_to_coeffs

The resulting coefficients may then finally be passed to
:py:func:`fir_filter_noise_gain` to determine the filter noise gain for that
filter.


Convenience function
````````````````````

A convenience function is provided which carries out all of the above steps for
**synthesis** filters, yielding the low-pass band synthesis filter noise gain
(:math:`\alpha`) and high-pass band synthesis filter noise gain
(:math:`\beta`).

.. autofunction:: wavelet_filter_to_alpha_beta


Computing Quantisation Matrices
-------------------------------

The :math:`\alpha` and  :math:`\beta` values found by
:py:func:`wavelet_filter_to_alpha_beta` may now be used to create the
quantisation matrices for a given transform.

During the VC-2 2D wavelet transform, the filtering process is applied
recursively. The consequence of this is that the noise gains accumulate
(multiplicatively). This is illustrated below:

.. image:: /_static/quantisation_matrices/noise_gain_accumulation.svg
    :alt: Noise-gain accumulation during filtering.

The :math:`s` term is the scaling factor due to the bit shift used by VC-2
between every transform layer. This scaling factor is simply:

.. math::
    
    s = 2^{-\textrm{bitshift}}

And is computed by:

.. autofunction:: wavelet_filter_to_synthesis_bit_shift_scale

.. note::
    
    When an asymmetric transform is used, the bit shift for the horizontal
    transform is used (see ``filter_bit_shift`` (15.4.2)).

The weighting of :math:`\alpha`, :math:`\beta` and :math:`s` for all bands and
levels may be computed automatically using:

.. autofunction:: accumulated_noise_gains

The objective of the quantisation matrix is for quantisation to have the same
impact on every band. As such we only care about the relative noise gains. The
noise gains computed by :py:func:`accumulated_noise_gains` can be normalised
using:

.. autofunction:: normalize_noise_gains

In principle, the values returned by :py:func:`normalize_noise_gains` should be
used to scale the quantisation factors used for each frequency band. In
practice, VC-2 specifies quantisation factors via exponential quantisation
indices:

.. math::
    
    \textrm{quantisation factor} = 2^{^\textrm{quantisation index}/_4}

Therefore, the best approximation to the desired scaling factor is achieved by
subtracting from the quantisation index:

.. math::
    
    \textrm{quantisation index adjustment} = \textrm{round}(4 \log_2(\textrm{normalised noise gain}))

This conversion is performed by:

.. autofunction:: normalized_noise_gains_to_quantisation_matrix


Convenience Function
--------------------

The following convenience function is provided which carries out the entire
process described above:

.. autofunction:: derive_quantisation_matrix

"""

from enum import Enum

from sympy import (
    symbols,
    sqrt,
    log,
    MatMul,
    Matrix,
    Rational,
    Add,
    expand,
    collect,
    Min,
)

from sympy.abc import z

from vc2_conformance.tables import (
    LiftingFilterTypes,
    LiftingFilterParameters,
    LiftingStage,
    LIFTING_FILTERS,
)


__all__ = [
    "StageType",
    "fir_filter_noise_gain",
    "lifting_stage_to_z_transform",
    "wavelet_filter_to_matrix_form",
    "convert_between_synthesis_and_analysis",
    "analysis_matrix_to_classical_form",
    "synthesis_matrix_to_classical_form",
    "z_to_coeffs",
    "wavelet_filter_to_alpha_beta",
    "wavelet_filter_to_synthesis_bit_shift_scale",
    "accumulated_noise_gains",
    "normalize_noise_gains",
    "normalized_noise_gains_to_quantisation_matrix",
    "derive_quantisation_matrix",
]


class StageType(Enum):
    """
    Lifting stage type specifier.
    """
    predict = "P"
    update = "U"


def fir_filter_noise_gain(coefficients):
    """
    Compute the noise-gain of a FIR filter with the specified list of filter
    coefficients.
    """
    return sqrt(sum(c**2 for c in coefficients))


def lifting_stage_to_z_transform(stage):
    """
    Given a :py:class:`vc2_conformance.tables.LiftingStage` describing wavelet
    filter stage, return the type of lifting stage (either predict or update)
    and a :math:`z`-domain representation of the filtering operation as used in
    the matrix filter representation.
    
    Parameters
    ==========
    stage : :py:class:`vc2_conformance.tables.LiftingStage`
    
    Returns
    =======
    stage_type : :py:class:`StageType`
    z_transform
    """
    stage_type = {
        LiftingFilterTypes.even_add_odd: StageType.update,  # type 1
        LiftingFilterTypes.even_subtract_odd: StageType.update,  # type 2
        LiftingFilterTypes.odd_add_even: StageType.predict,  # type 3
        LiftingFilterTypes.odd_subtract_even: StageType.predict,  # type 4
    }[stage.lift_type]
    
    uses_odd_samples = stage.lift_type in (
        LiftingFilterTypes.even_add_odd,  # type 1
        LiftingFilterTypes.even_subtract_odd,  # type 2
    )
    
    subtracts = stage.lift_type in (
        LiftingFilterTypes.even_subtract_odd,  # type 2
        LiftingFilterTypes.odd_subtract_even,  # type 4
    )
    
    z_transform = sum(
        z**(n + stage.D + (-1 if uses_odd_samples else 0)) *
        tap *
        (-1 if subtracts else +1)
        for n, tap in enumerate(stage.taps)
    ) * Rational(1, 2**stage.S)
    
    return stage_type, z_transform


def wavelet_filter_to_matrix_form(lifting_filter_parameters):
    """
    Convert a :py:class:`vc2_conformance.tables.LiftingFilterParameters` filter
    specification into :math:`z`-domain matrix form.
    """
    matrix = None
    
    for stage in lifting_filter_parameters.stages:
        stage_type, z_transform = lifting_stage_to_z_transform(stage)
        if stage_type is StageType.update:
            this_matrix = Matrix([
                [1, z_transform],
                [0, 1],
            ])
        elif stage_type is StageType.predict:
            this_matrix = Matrix([
                [1, 0],
                [z_transform, 1],
            ])
        
        if matrix is None:
            matrix = this_matrix
        else:
            matrix = MatMul(this_matrix, matrix)
    
    assert matrix is not None
    
    return matrix


def convert_between_synthesis_and_analysis(lifting_filter_parameters):
    """
    Given a synthesis wavelet filter specification, return the complementary
    analysis filter (or visa versa).
    
    Parameters
    ==========
    lifting_filter_parameters : :py:class:`vc2_conformance.tables.LiftingFilterParameters`
    
    Returns
    =======
    lifting_filter_parameters : :py:class:`vc2_conformance.tables.LiftingFilterParameters`
    """
    return LiftingFilterParameters(
        stages=[
            LiftingStage(
                lift_type={
                    LiftingFilterTypes.even_add_odd: LiftingFilterTypes.even_subtract_odd,
                    LiftingFilterTypes.even_subtract_odd: LiftingFilterTypes.even_add_odd,
                    LiftingFilterTypes.odd_add_even: LiftingFilterTypes.odd_subtract_even,
                    LiftingFilterTypes.odd_subtract_even: LiftingFilterTypes.odd_add_even,
                }[stage.lift_type],
                S=stage.S,
                L=stage.L,
                D=stage.D,
                taps=stage.taps,
            )
            for stage in reversed(lifting_filter_parameters.stages)
        ],
        filter_bit_shift=lifting_filter_parameters.filter_bit_shift,
    )


def analysis_matrix_to_classical_form(H):
    r"""
    Given an analysis filter matrix, :math:`\textbf{H}(z)` as produced by, e.g.
    :py:func:`wavelet_filter_to_matrix_form`, return the equivalent pair of
    classical filters, :math:`H_0(z^2)` and  :math:`H_1(z^2)`.
    """
    # NB: .doit() used to apply all matrix multiplications to produce a single
    # 2x2 matrix (if not already in this form)
    H_sq = H.doit().subs(z, z**2)
    
    H_0 = H_sq[0, 0] + (z * H_sq[0, 1])
    H_1 = H_sq[1, 0] + (z * H_sq[1, 1])
    
    return (H_0, H_1)


def synthesis_matrix_to_classical_form(G):
    r"""
    Given an synthesis filter matrix, :math:`\textbf{G}(z)` as produced by, e.g.
    :py:func:`wavelet_filter_to_matrix_form`, return the equivalent pair of
    classical filters, :math:`G_0(z^2)` and  :math:`G_1(z^2)`.
    """
    # NB: .doit() used to apply all matrix multiplications to produce a single
    # 2x2 matrix (if not already in this form)
    G_sq = G.doit().subs(z, z**2)
    
    G_0 = G_sq[0, 0] + (z**-1 * G_sq[1, 0])
    G_1 = G_sq[0, 1] + (z**-1 * G_sq[1, 1])
    
    return (G_0, G_1)


def z_to_coeffs(poly):
    """
    Get a dictionary ``{delay: coeff, ...}`` from a z-transform expressed as a
    polynomial.
    
    The returned dictionary will contain :py:class:`int` ``delay`` values and
    SymPy expressions for the coefficients.
    """
    # NB: Ideally you'd use SymPy's polynomial-related functions for this job
    # but, alas, SymPy doesn't support Laurent polynomials (where powers may be
    # negative). As a consequence, we do everything 'by hand'; using algebraic
    # operations rather than inspecting the SymPy data structures for reasons
    # of robustness.
    
    # Simplify the polynomial into a summation of multiples of powers of z.
    poly = collect(expand(poly), z)
    
    out = {}
    for arg in Add.make_args(poly):
        arg_no_z = arg.subs(z, 1)
        arg_z = arg / arg_no_z
        delay = -int((log(arg_z) / log(z)).expand(force=True))
        out[delay] = arg_no_z
    
    # Add missing zeros terms (for completeness...)
    for delay in range(min(out), max(out)):
        out.setdefault(delay, 0)
    
    return out


def wavelet_filter_to_alpha_beta(synthesis_lifting_filter_parameters):
    r"""
    Given synthesis filter definition (in a
    :py:class:`vc2_conformance.tables.LiftingFilterParameters`) return the
    low-pass and high-pass filter noise gains (:math:`\alpha` and
    :math:`\beta`).
    """
    # Convert from lifting definition to classical form
    G = wavelet_filter_to_matrix_form(synthesis_lifting_filter_parameters)
    G_0, G_1 = synthesis_matrix_to_classical_form(G)
    
    # Compute filter noise gains
    alpha = fir_filter_noise_gain(z_to_coeffs(G_0).values())
    beta = fir_filter_noise_gain(z_to_coeffs(G_1).values())
    
    return (alpha, beta)


def wavelet_filter_to_synthesis_bit_shift_scale(synthesis_lifting_filter_parameters):
    r"""
    Given synthesis filter definition (in a
    :py:class:`vc2_conformance.tables.LiftingFilterParameters`) return the
    scaling factor, :math:`s`, imposed after each 2D or horizontal-only
    transform level.
    """
    return Rational(1, 2**synthesis_lifting_filter_parameters.filter_bit_shift)


def accumulated_noise_gains(alpha_v, beta_v, alpha_h, beta_h, s, dwt_depth, dwt_depth_ho):
    """
    Compute the total accumulated noise gain for all bands of a given wavelet
    transform.
    
    Parameters
    ==========
    alpha_v, beta_v
        The LF and HF filter noise gains for the vertical wavelet synthesis
        filter (from, e.g. :py:func:`wavelet_filter_to_alpha_beta`).
    alpha_h, beta_h
        The LF and HF filter noise gains for the horizontal wavelet synthesis
        filter (from, e.g. :py:func:`wavelet_filter_to_alpha_beta`).
    s
        The scaling applied by the bit-shift of the horizontal wavelet
        synthesis filter.
    dwt_depth, dwt_depth_ho
        The wavelet transform depth (and horizontal-only transform depth).
    
    Returns
    =======
    {level: {band: noise_gain, ...}, ...}
        A list with one dictionary per level in the same layout as the
        quantisation matrices in
        :py:data:`vc2_conformance.tables.QUANTISATION_MATRICES`.
    """
    gains = [{"LL": 1}]
    
    for _ in range(dwt_depth):
        last_LL_gain = gains[0].pop("LL")
        gains.insert(0, {
            "LL": last_LL_gain * s * alpha_h * alpha_v,
            "HL": last_LL_gain * s * beta_h * alpha_v,
            "LH": last_LL_gain * s * alpha_h * beta_v,
            "HH": last_LL_gain * s * beta_h * beta_v,
        })
    
    for _ in range(dwt_depth_ho):
        last_L_gain = gains[0].pop("L") if "L" in gains[0] else gains[0].pop("LL") 
        gains.insert(0, {
            "L": last_L_gain * s * alpha_h,
            "H": last_L_gain * s * beta_h,
        })
    
    # As is convention in the VC-2 spec, the final band is placed in its own
    # level
    dc_band = "LL" if "LL" in gains[0] else "L"
    gains.insert(0, {dc_band: gains[0].pop(dc_band)})
    
    return {
        level: values
        for level, values in enumerate(gains[:-1])  # Skip the now empty starting dictionary
    }


def normalize_noise_gains(noise_gains):
    """
    Normalize a set of noise gains such that the minimum gain is 1.
    
    This operation will be performed symbolically and the resulting noise gains
    will be SymPy values.
    """
    minimum_gain = Min(*(gain for level in noise_gains.values() for gain in level.values()))
    
    return {
        level: {
            orientation: gain / minimum_gain
            for orientation, gain in gains.items()
        }
        for level, gains in noise_gains.items()
    }


def normalized_noise_gains_to_quantisation_matrix(normalized_noise_gains):
    r"""
    Given a set of normalised noise gains, returns the equivalent quantisation
    index adjustments.
    
    All results will be :py:class:`int`\ s.
    """
    return {
        level: {
            orientation: int(round(float(4 * (log(gain) / log(2)))))
            for orientation, gain in gains.items()
        }
        for level, gains in normalized_noise_gains.items()
    }


def derive_quantisation_matrix(wavelet_index, wavelet_index_ho, dwt_depth, dwt_depth_ho):
    """
    Derive a quantisation matrix for the specified wavelet transform. This
    quantisation matrix will seek to cause quantisation noise to be spread
    evenly over all wavelet levels and bands.
    
    Parameters
    ==========
    wavelet_index, wavelet_index_ho : :py:class:`vc2_conformance.tables.WaveletFilters`
        The vertical and horizontal wavelet filter indices respectively.
    dwt_depth, dwt_depth_ho
        The wavelet transform depth (2D depth and horizontal only depth).
    
    Returns
    =======
    {level: {band: int, ...}, ...}
        A quantisation matrix, as laid out in
        :py:data:`vc2_conformance.tables.QUANTISATION_MATRICES`.
    """
    wavelet_v = LIFTING_FILTERS[wavelet_index]
    wavelet_h = LIFTING_FILTERS[wavelet_index_ho]
    
    alpha_v, beta_v = wavelet_filter_to_alpha_beta(wavelet_v)
    alpha_h, beta_h = wavelet_filter_to_alpha_beta(wavelet_h)
    s = wavelet_filter_to_synthesis_bit_shift_scale(wavelet_h)
    
    noise_gains = accumulated_noise_gains(
        alpha_v,
        beta_v,
        alpha_h,
        beta_h,
        s,
        dwt_depth,
        dwt_depth_ho,
    )
    normalized_noise_gains = normalize_noise_gains(noise_gains)
    return normalized_noise_gains_to_quantisation_matrix(normalized_noise_gains)
