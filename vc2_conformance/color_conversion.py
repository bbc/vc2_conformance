"""
Color conversion routines
=========================

This module implements simple color format conversion routines for converting
between arbitrary VC-2 color formats via floating point CIE XYZ colour. These
routines are intended for producing plausible pictures in all VC-2 color
formats for test purposes. They may not implement the most faithful possible
conersions due to simplistic numerical implementation choices.

The process is automated by the following functions:

.. autofunction:: to_xyz

.. autofunction:: from_xyz

.. warning::

    Support for converting *into* CIE XYZ format is limited to only formats
    using the :py:data:`~vc2_data_tables.PresetTransferFunctions.tv_gamma`
    transfer function. All formats are supported when converting *from* XYZ
    color.

Process internals
-----------------

The conversion processes used by :py:func:`to_xyz` and :py:func:`from_xyz` are
illustrated as follows::

      (Original Format)                                           (New Format)
       Integer Y C1 C2                                           Integer Y C1 C2
              |                                                         ^
              | int_to_float                               float_to_int |
              V                                                         |
    Floating Point Y C1 C2                                 Chroma Subsampled Y C1 C2
              |                                                         ^
              | to_444                                         from_444 |
              V                                                         |
     Interpolated Y C1 C2                                    Floating Point Y C1 C2
              |                                                         ^
              | INVERSE_COLOR_MATRICES                   COLOR_MATRICES |
              V                                                         |
      Non-linear ErEgEb                                         Non-linear ErEgEb
              |                                                         ^
              | INVERSE_TRANSFER_FUNCTIONS           TRANSFER_FUNCTIONS |
              V                                                         |
         Linear RGB                                                 Linear RGB
              |                                                         ^
              | LINEAR_RGB_TO_XYZ                     XYZ_TO_LINEAR_RGB |
              |                                                         |
              `----------------------->  CIE XYZ -----------------------'

These steps build on the following conversion functions and matrices. These are
implemented based on the specifications cited by the VC-2 specification.

.. note::

    Whilst every effort has been made to ensure that these implementations are
    correct, these should be considered informative, not normative.

.. autofunction:: float_to_int

.. autofunction:: int_to_float

.. autofunction:: from_444

.. autofunction:: to_444

.. autodata:: COLOR_MATRICES

.. autodata:: INVERSE_COLOR_MATRICES

.. autodata:: TRANSFER_FUNCTIONS

.. autodata:: INVERSE_TRANSFER_FUNCTIONS

.. autodata:: XYZ_TO_LINEAR_RGB

.. autodata:: LINEAR_RGB_TO_XYZ


Additional utility functions
----------------------------

The following additional utility functions are provided for the manual
evaluation of certain transform steps.

.. autofunction:: matmul_colors

.. autofunction:: swap_primaries

"""

import numpy as np

import warnings

from collections import namedtuple

from vc2_data_tables import (
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    ColorDifferenceSamplingFormats,
)

from vc2_conformance.vc2_math import intlog2


__all__ = [
    "to_xyz",
    "from_xyz",
    "float_to_int",
    "int_to_float",
    "from_444",
    "to_444",
    "COLOR_MATRICES",
    "INVERSE_COLOR_MATRICES",
    "TRANSFER_FUNCTIONS",
    "INVERSE_TRANSFER_FUNCTIONS",
    "XYZ_TO_LINEAR_RGB",
    "LINEAR_RGB_TO_XYZ",
    "matmul_colors",
    "swap_primaries",
]


################################################################################
# Linear RGB <--> CIE XYZ Conversion
#
# This conversion step may be implemented using a simple 3x3 matrix
# multiplication. In practice, color primaries are not specified in terms of
# this matrix but instead as a series of chromacities (little-x, little-y) for
# the R, G and B components and the white point. The xy_to_xyz and
# primary_chromacities_to_matrix functions below are used to perform the
# necessary conversions.
################################################################################


PrimaryChromacities = namedtuple("PrimaryChromacities", "xw,yw,xr,yr,xg,yg,xb,yb",)
"""
A specification of a set of colour primaries in terms of whitepoint (xw, yx)
and red (xr, yr), green (xg, yg) and blue (xb, yb) chromacities. Colours are
specified as :math:`x` and :math:`y` coordinates in the xyY colour system.
"""


def xy_to_xyz(x, y):
    """
    Convert a CIE :math:`x` :math:`y` chromacity into XYZ components with unit
    luminance.
    """
    # By definition:
    #
    #    x = X / (X + Y + Z)    and    y = Y / (X + Y + Z)
    #
    # So, by simple rearrangement:

    Y = 1.0
    X = (x / y) * Y
    Z = ((1.0 - x - y) / y) * Y

    return (X, Y, Z)


def primary_chromacities_to_matrix(pc):
    r"""
    Convert a :py:class:`PrimaryChromacities` tuple into a :math:`3 \times 3`
    matrix which converts from linear RGB to XYZ.
    """
    # We want to find a 3x3 matrix m such that:
    #
    #    [ X ]     [       ] [ R ]
    #    [ Y ]  =  [   m   ] [ G ]
    #    [ Z ]     [       ] [ B ]
    #
    # For the supplied set of primaries/whitepoint. We know that for RGB values
    # [1, 0, 0] we get an XYZ value: [Xr, Yr, Zr]:
    #
    #    [ Xr ]     [ xr/yr * Yr         NA NA ] [ 1 ]
    #    [ Yr ]  =  [ Yr                 NA NA ] [ 0 ]
    #    [ Zr ]     [ (1-xr-yr)/yr * Yr  NA NA ] [ 0 ]
    #
    # Due to the definition of x and y w.r.t. XYZ. The middle and rightmost
    # columns are similar but with xg, yg and xb and yb respectively.
    # Consequently we see that m is of the form:
    #
    #    [ X ]     [ xr/yr * Yr         xg/yg * Yg         xb/yb * Yb        ] [ R ]
    #    [ Y ]  =  [ Yr                 Yg                 Yb                ] [ G ]
    #    [ Z ]     [ (1-xr-yr)/yr * Yr  (1-xg-yg)/yg * Yg  (1-xb-yb)/yb * Yb ] [ B ]
    #
    # Lets factor out the currently unknown Y* terms:
    #
    #    [ X ]     [ xr/yr        xg/yg        xb/yb        ] [ Yr  0  0 ] [ R ]
    #    [ Y ]  =  [ 1            1            1            ] [  0 Yg  0 ] [ G ]
    #    [ Z ]     [ (1-xr-yr)/yr (1-xg-yg)/yg (1-xb-yb)/yb ] [  0  0 Yb ] [ B ]
    #
    # We'll refer to the remaining matrix as relative_m:
    #
    #    [ X ]     [            ] [ Yr  0  0 ] [ R ]
    #    [ Y ]  =  [ relative_m ] [  0 Yg  0 ] [ G ]
    #    [ Z ]     [            ] [  0  0 Yb ] [ B ]

    relative_m = np.array(
        [xy_to_xyz(pc.xr, pc.yr), xy_to_xyz(pc.xg, pc.yg), xy_to_xyz(pc.xb, pc.yb),]
    ).T

    # Also by definition, the white point with chromacity xw, yw, and XYZ Xw,
    # Yw, Zw is the colour produced by RGB [1, 1, 1]:
    #
    #    [ Xw ]     [            ] [ Yr  0  0 ] [ 1 ]
    #    [ Yw ]  =  [ relative_m ] [  0 Yg  0 ] [ 1 ]
    #    [ Zw ]     [            ] [  0  0 Yb ] [ 1 ]
    #
    # Rearranging
    #
    #    [            ]-1 [ Xw ]     [ Yr  0  0 ] [ 1 ]
    #    [ relative_m ]   [ Yw ]  =  [  0 Yg  0 ] [ 1 ]
    #    [            ]   [ Zw ]     [  0  0 Yb ] [ 1 ]
    #
    #    [            ]-1 [ Xw ]     [ Yr ]
    #    [ relative_m ]   [ Yw ]  =  [ Yg ]
    #    [            ]   [ Zw ]     [ Yb ]
    #
    # By defining the luminance of the whitepoint, Yw, to be 1.0, we can
    # find Xw and Zw from xw and yw:
    #
    #    [            ]-1 [ xw/yw        ]     [ Yr ]     [       ]
    #    [ relative_m ]   [ 1            ]  =  [ Yg ]  =  [ scale ]
    #    [            ]   [ (1-xw-yw)/yw ]     [ Yb ]     [       ]
    #
    # This equation now contains no unknowns other than Yr, Yg and Yb which we
    # can now solve for and together refer to as 'scale':

    scale = np.matmul(np.linalg.inv(relative_m), xy_to_xyz(pc.xw, pc.yw),)

    # We can now apply this to relative_m to get the matrix m:

    m = np.matmul(relative_m, np.diag(scale),)

    return m


LINEAR_RGB_TO_XYZ = {
    PresetColorPrimaries.hdtv:
    # (ITU-R BT.709)
    primary_chromacities_to_matrix(
        PrimaryChromacities(
            xw=0.3127,
            yw=0.3290,
            xr=0.640,
            yr=0.330,
            xg=0.300,
            yg=0.600,
            xb=0.150,
            yb=0.060,
        )
    ),
    PresetColorPrimaries.sdtv_525:
    # (ITU-R BT.601)
    primary_chromacities_to_matrix(
        PrimaryChromacities(
            xw=0.3127,
            yw=0.3290,
            xr=0.630,
            yr=0.340,
            xg=0.310,
            yg=0.595,
            xb=0.155,
            yb=0.070,
        )
    ),
    PresetColorPrimaries.sdtv_625:
    # (ITU-R BT.601)
    primary_chromacities_to_matrix(
        PrimaryChromacities(
            xw=0.3127,
            yw=0.3290,
            xr=0.640,
            yr=0.330,
            xg=0.290,
            yg=0.600,
            xb=0.150,
            yb=0.060,
        )
    ),
    PresetColorPrimaries.d_cinema:
    # (SMPTE ST 428-1)
    np.eye(3),
    PresetColorPrimaries.uhdtv:
    # (ITU-R BT.2020)
    primary_chromacities_to_matrix(
        PrimaryChromacities(
            xw=0.3127,
            yw=0.3290,
            xr=0.708,
            yr=0.292,
            xg=0.170,
            yg=0.797,
            xb=0.131,
            yb=0.046,
        )
    ),
}
r"""
For each set of colour primaries in
:py:class:`~vc2_data_tables.PresetColorPrimaries`, a :math:`3 \times 3` matrix
which converts from linear RGB into CIE XYZ.
"""

XYZ_TO_LINEAR_RGB = {key: np.linalg.inv(m) for key, m in LINEAR_RGB_TO_XYZ.items()}
"""
For each set of colour primaries in
:py:class:`~vc2_data_tables.PresetColorPrimaries`, a :math:`3 \times 3` matrix
which converts from CIE XYZ into linear RGB.
"""

################################################################################
# Transfer functions
#
# The following functions implement the transfer functions (gamma functions)
# supported by VC-2. In all cases, these functions are designed such that they
# may be passed either a single value or a numpy array in which an element-wise
# conversion will be performed.
################################################################################


def tv_gamma_transfer_function(l):
    """
    The transfer function from (ITU-R BT.2020).
    """
    alpha = 1.09929682680944
    beta = 0.018053968510807

    # NB: In case of undershoot (l < 0), np.power produces a warning here. The
    # effected values will be overwritten later however so this can be ignored.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        e = alpha * np.power(l, 0.45) - (alpha - 1)
    e = np.where(l < beta, 4.5 * l, e)

    return e


def tv_gamma_inverse_transfer_function(e):
    """
    The reverse of the transfer function from (ITU-R BT.2020).
    """
    alpha = 1.09929682680944
    beta = 0.018053968510807

    # NB: In case of undershoot (l < 0), np.power produces a warning here. The
    # effected values will be overwritten later however so this can be ignored.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        l = np.power((e + 0.099) / alpha, 1 / 0.45)
    l = np.where(e < tv_gamma_transfer_function(beta), e / 4.5, l)

    return l


def extended_gamut_transfer_function(l):
    """
    The transfer function from (ITU-R BT.1361).
    """
    # NB: In case of undershoot (l < 0), np.power produces a warning here. The
    # effected values will be overwritten later however so this can be ignored.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        e = 1.099 * np.power(l, 0.45) - 0.099

    e = np.where(l < 0.018, 4.5 * l, e,)

    # NB: In case of undershoot (-4 * l < 0), the effected value will not be
    # used
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        e = np.where(l < -0.0045, -(1.099 * np.power(-4 * l, 0.45) - 0.099) / 4, e,)

    return e


def linear_transfer_function(l):
    """
    A linear transfer function (for completeness).
    """
    return l


def d_cinema_transfer_function(l):
    """
    The transfer function from (ST 428-1).
    """
    peak_luminance = 52.37  # cd/m^2
    reference_luminance = 48.0  # cd/m^2

    # Clamp 'l' at 0 as not defined in case of undershoots
    e = np.power((reference_luminance * np.maximum(l, 0)) / peak_luminance, (1 / 2.6))

    return e


def pq_transfer_function(l):
    """
    The Optical-Eelectical Transfer Function (OETF) for Dolby Perceptual
    Quantizer (PQ) (ITU-R BT.2100-2).
    """
    m1 = 2610.0 / 16384.0
    m2 = 2523.0 / 4096.0 * 128
    c1 = 3424.0 / 4096.0
    c2 = 2413.0 / 4096.0 * 32.0
    c3 = 2392.0 / 4096.0 * 32.0

    # Clamp 'l' at 0 as not defined in case of undershoots
    l_m1 = np.power(np.maximum(l, 0), m1)

    e = np.power((c1 + c2 * l_m1) / (1 + c3 * l_m1), m2)

    return e


def hlg_transfer_function(l):
    """
    The Hybrid Log Gamma (HLG) transfer function (ITU-R BT.2100-2).
    """
    a = 0.17883277
    b = 1 - 4 * a
    c = 0.5 - a * np.log(4 * a)

    # NB: In case of undershoot (l < 0), np.log produces a warning here. The
    # effected values will be overwritten later however so this can be ignored.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        e = a * np.log(12 * l - b) + c

    # Clamp 'l' at 0 as not defined in case of undershoots
    e = np.where(l <= 1 / 12.0, np.sqrt(3 * np.maximum(l, 0)), e,)

    return e


TRANSFER_FUNCTIONS = {
    PresetTransferFunctions.tv_gamma: tv_gamma_transfer_function,
    PresetTransferFunctions.extended_gamut: extended_gamut_transfer_function,
    PresetTransferFunctions.linear: linear_transfer_function,
    PresetTransferFunctions.d_cinema: d_cinema_transfer_function,
    PresetTransferFunctions.perceptual_quality: pq_transfer_function,
    PresetTransferFunctions.hybrid_log_gamma: hlg_transfer_function,
}
"""
For each set of VC-2's, supported transfer functions, a Numpy implementation of
that function. These functions implement the transform from linear to
non-linear RGB, :math:`E_R E_G E_B`.
"""


INVERSE_TRANSFER_FUNCTIONS = {
    PresetTransferFunctions.tv_gamma: tv_gamma_inverse_transfer_function,
    PresetTransferFunctions.linear: linear_transfer_function,
}
"""
For (a subset of) VC-2's, supported transfer functions, a Numpy implementation
of the inverse function. These functions implement the transform from
non-linear to linear RGB.

.. warning::

    An inverse transfer function is currently only provided for
    :py:data:`~vc2_data_tables.PresetTransferFunctions.tv_gamma` because this
    is all that is needed for the intended application of this module.
"""


################################################################################
# RGB <--> Y C1 C2 (Color Matrices)
#
# Color matrices are often specified indirectly by a pair of weights, Kr and
# Kb. These are converted into the equivalent 3x3 matrix by
# kr_kb_to_color_matrix.
################################################################################


def kr_kb_to_color_matrix(kr, kb):
    r"""
    Given a description of a Y' Cb Cr color matrix as a :math:`K_r`,
    :math:`K_b` pair, return a :math:`3 \times 3` :math:`E_R E_G E_B` to Y' Cb
    Cr color matrix.
    """
    # The luma component of a Y' Cb Cr signal, Y', is defined as:
    #
    #     Y' = Kr R' + Kg G' + Kb B'
    #
    # Where:
    #
    #     Kr + Kg + Kb = 1
    #
    # So:

    kg = 1 - kr - kb

    # Conceptually raw colour difference signals are then given as:
    #
    #     Cb_conceptual = B' - Y'
    #     Cr_conceptual = R' - Y'
    #
    # However these signals must be weighted to give a unity gain. To do this,
    # lets expand Cb_conceptual:
    #
    #     Cb_conceptual = B' - Y'
    #                   = B' - Kr R' - Kg G' - Kb B'
    #                   = (1 - Kb) B' - Kr R' - Kg G'
    #
    # So, manipulating our equation for the unity of Kr, Kg and Kb we can work
    # out what the weighting should be for the equation above:
    #
    #     Kr + Kg + Kb       = 1
    #     Kr + Kg            = 1 - Kb
    #     Kr + Kg + (1 - Kb) = (1 - Kb) + (1 - Kb)
    #                        = 2(1 - Kb)
    #
    # This tells us that the equation above sums to a gain of 2(1 - Kb) so:
    #
    #     Cb = (B' - Y') / 2(1 - Kb)
    #        = ((1 - Kb) B' - Kr R' - Kg G') / 2(1 - Kb)
    #        = (- (Kr / 2(1-Kb)) R' - (Kg / 2(1-Kb)) G' + 0.5 B')
    #
    # And simillarly:
    #
    #     Cr = (R' - Y') / 2(1 - Kr)
    #        = (0.5 R' - (Kg / 2(1-Kr)) G' - (Kb / 2(1-Kr)) B')
    #
    # Given these we can now directly construct the color matrix:

    return np.array(
        [
            [kr, kg, kb],
            [-kr / (2 * (1 - kb)), -kg / (2 * (1 - kb)), 0.5],
            [0.5, -kg / (2 * (1 - kr)), -kb / (2 * (1 - kr))],
        ]
    )


COLOR_MATRICES = {
    # (ITU-R BT.709)
    PresetColorMatrices.hdtv: kr_kb_to_color_matrix(kr=0.2126, kb=0.0722),
    # (ITU-R BT.601)
    PresetColorMatrices.sdtv: kr_kb_to_color_matrix(kr=0.2990, kb=0.1140),
    # (ITU-T H.264)
    PresetColorMatrices.reversible: np.array(
        [[+0.25, +0.50, +0.25], [-0.25, +0.50, -0.25], [+0.50, +0.00, -0.50],]
    ),
    # GBR -> Y C1 C2
    PresetColorMatrices.rgb: np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0],]),
    # (ITU-R BT.2020)
    PresetColorMatrices.uhdtv: kr_kb_to_color_matrix(kr=0.2627, kb=0.0593),
}
r"""
For each colour matrix supported by VC-2, a :math:`3 \times 3` matrix which
transforms from non-linear RGB (:math:`E_R E_G E_B`) to Y C1 C2.
"""


INVERSE_COLOR_MATRICES = {key: np.linalg.inv(m) for key, m in COLOR_MATRICES.items()}
"""
For each colour matrix supported by VC-2, a :math:`3 \times 3` matrix which
transforms from Y C1 C2 to non-linear RGB (:math:`E_R E_G E_B`).
"""


################################################################################
# integer <--> float conversion (11.4.9)
#
# VC-2, like many video systems, deal entirely in positive integer values which
# nominally represent values in the range 0 to +1 or -0.5 to +0.5. These
# functions perform the conversion between these two representations, the
# latter of which is necessary for the colour conversion routines and matrices
# above.
################################################################################


def int_to_float(a, offset, excursion):
    """
    Convert (an array of) integer sample values from integers (with the
    specified offset and excursion) to floating point values nominally in the
    range 0 to +1 or -0.5 to +0.5.
    """
    a = np.array(a, dtype=float)
    return (a - offset) / excursion


def float_to_int(a, offset, excursion):
    """
    Convert (an array of) float sample values in the nominal range 0 to +1 or
    -0.5 to +0.5 to integers (with the specified offset and excursion).

    Values which fall outside the range of the integer representation are
    clipped.
    """
    a = np.array(a, dtype=float)

    # Scale/offset
    a = (a * excursion) + offset

    # Convert to expected integer format/range
    a = np.round(a).astype(int)
    a = np.clip(a, 0, (2 ** (intlog2(excursion + 1))) - 1)

    return a


################################################################################
# Chroma subsampling format conversion
#
# The funtions below are provided for quick-and-dirty color subsampling
# purposes. The antialiasing filters used are completely inadequate for real
# applications but are sufficient for the production of simple test pictures.
################################################################################


def from_444(chroma, subsampling):
    """
    Subsample a chroma picture component into the specified
    :py:class:`~vc2_data_tables.ColorDifferenceSamplingFormats`.

    .. warning::

        This function uses an extremely crude low-pass filter during
        downsampling which is likely to produce aliasing artefacts. As such,
        pictures produced by this function should not be used for anything
        where high fidelity is required.
    """

    if subsampling == ColorDifferenceSamplingFormats.color_4_4_4:
        return chroma
    elif subsampling == ColorDifferenceSamplingFormats.color_4_2_2:
        h, w = chroma.shape
        new_chroma = np.empty((h, w // 2), dtype=chroma.dtype)

        new_chroma[:, :] = chroma[:, 0::2]
        new_chroma[:, :] += chroma[:, 1::2]
        new_chroma /= 2.0

        return new_chroma
    elif subsampling == ColorDifferenceSamplingFormats.color_4_2_0:
        h, w = chroma.shape
        new_chroma = np.empty((h // 2, w // 2), dtype=chroma.dtype)

        new_chroma[:, :] = chroma[0::2, 0::2]
        new_chroma[:, :] += chroma[0::2, 1::2]
        new_chroma[:, :] += chroma[1::2, 0::2]
        new_chroma[:, :] += chroma[1::2, 1::2]
        new_chroma /= 4.0

        return new_chroma


def to_444(chroma, subsampling):
    """
    Given a chroma picture subsampled according to the specified
    :py:class:`~vc2_data_tables.ColorDifferenceSamplingFormats`, return an
    upsampled chroma signal.

    .. warning::

        This function uses an extremely crude anti-aliasing filter during
        upsampling which is likely to produce artefacts. As such, pictures
        produced by this function should not be used for anything where high
        fidelity is required.
    """
    if subsampling == ColorDifferenceSamplingFormats.color_4_4_4:
        return chroma
    elif subsampling == ColorDifferenceSamplingFormats.color_4_2_2:
        return np.repeat(chroma, 2, axis=1)
    elif subsampling == ColorDifferenceSamplingFormats.color_4_2_0:
        return np.repeat(np.repeat(chroma, 2, axis=1), 2, axis=0)


################################################################################
# High-level utility functions
################################################################################


def to_xyz(y, c1, c2, video_parameters):
    r"""
    Convert a picture from a native VC-2 integer Y C1 C2 format into floating
    point CIE XYZ format.

    Parameters
    ==========
    y, c1, c2 : :py:class:`numpy.array`
        Three 2D :py:class:`numpy.array`\ s containing integer Y C1 C2 values
        for a picture.
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
        The VC-2 parameters describing the video format in use. The following
        fields are required:

        * ``color_diff_format_index``
        * ``luma_offset``
        * ``luma_excursion``
        * ``color_diff_offset``
        * ``color_diff_excursion``
        * ``color_primaries``
        * ``color_matrix``
        * ``transfer_function``

    Returns
    =======
    yxz : :py:class:`numpy.array`
        A 3D :py:class:`numpy.array` with dimensions ``(height, width, 3)``
        containing floating point CIE XYZ values for a picture.
    """
    # Convert each component into floating point, 0 - +1 or -0.5 - +0.5 form
    y_float = int_to_float(
        y, video_parameters["luma_offset"], video_parameters["luma_excursion"],
    )
    c1_float = int_to_float(
        c1,
        video_parameters["color_diff_offset"],
        video_parameters["color_diff_excursion"],
    )
    c2_float = int_to_float(
        c2,
        video_parameters["color_diff_offset"],
        video_parameters["color_diff_excursion"],
    )

    # Upsample to 4:4:4
    c1_upsampled = to_444(c1_float, video_parameters["color_diff_format_index"])
    c2_upsampled = to_444(c2_float, video_parameters["color_diff_format_index"])

    # Produce a Nx3 matrix with each column containing a Y C1 C2 value.
    yc1c2_cols = np.stack(
        [y_float.reshape(-1), c1_upsampled.reshape(-1), c2_upsampled.reshape(-1),],
        axis=0,
    )

    # Convert to non-linear RGB
    inverse_color_matrix = INVERSE_COLOR_MATRICES[
        video_parameters["color_matrix_index"]
    ]
    eregeb_cols = np.matmul(inverse_color_matrix, yc1c2_cols)

    # Convert to linear RGB
    inverse_transfer_function = INVERSE_TRANSFER_FUNCTIONS[
        video_parameters["transfer_function_index"]
    ]
    linear_rgb_cols = inverse_transfer_function(eregeb_cols)

    # Convert to CIE XYZ
    rgb_to_xyz_matrix = LINEAR_RGB_TO_XYZ[video_parameters["color_primaries_index"]]
    xyz_cols = np.matmul(rgb_to_xyz_matrix, linear_rgb_cols)

    # Convert to 3D array of XYZ values
    xyz = xyz_cols.T.reshape(y.shape + (3,))

    return xyz


def from_xyz(xyz, video_parameters):
    """
    Convert a picture from CIE XYZ format into a native VC-2 integer, chroma
    subsampled Y C1 C2 format.

    Parameters
    ==========
    yxz : :py:class:`numpy.array`
        A 3D :py:class:`numpy.array` with dimensions ``(height, width, 3)``
        containing floating point CIE XYZ values for a picture.
    video_parameters : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
        The VC-2 parameters describing the video format to produce. The following
        fields are required:

        * ``color_diff_format_index``
        * ``luma_offset``
        * ``luma_excursion``
        * ``color_diff_offset``
        * ``color_diff_excursion``
        * ``color_primaries``
        * ``color_matrix``
        * ``transfer_function``

    Returns
    =======
    y, c1, c2 : :py:class:`numpy.array`
        A set of three 2D :py:class:`numpy.array` containing integer Y C1 C2
        values for a picture. If chroma subsampling is used, the C1 and C2
        arrays may differ in size from the Y component.
    """
    # Convert to columns of XYZ values
    xyz_cols = xyz.reshape(-1, 3).T

    # Convert to linear RGB
    xyz_to_rgb_matrix = XYZ_TO_LINEAR_RGB[video_parameters["color_primaries_index"]]
    linear_rgb_cols = np.matmul(xyz_to_rgb_matrix, xyz_cols)

    # Convert to non-linear RGB
    transfer_function = TRANSFER_FUNCTIONS[video_parameters["transfer_function_index"]]
    eregeb_cols = transfer_function(linear_rgb_cols)

    # Convert to Y C1 C2
    color_matrix = COLOR_MATRICES[video_parameters["color_matrix_index"]]
    yc1c2_cols = np.matmul(color_matrix, eregeb_cols)

    # Convert to 3D
    yc1c2 = yc1c2_cols.T.reshape(xyz.shape)

    # Color subsample
    y = yc1c2[:, :, 0]
    c1 = yc1c2[:, :, 1]
    c2 = yc1c2[:, :, 2]

    c1_subsampled = from_444(c1, video_parameters["color_diff_format_index"])
    c2_subsampled = from_444(c2, video_parameters["color_diff_format_index"])

    # Convert to integer ranges
    y_int = float_to_int(
        y, video_parameters["luma_offset"], video_parameters["luma_excursion"],
    )
    c1_int = float_to_int(
        c1_subsampled,
        video_parameters["color_diff_offset"],
        video_parameters["color_diff_excursion"],
    )
    c2_int = float_to_int(
        c2_subsampled,
        video_parameters["color_diff_offset"],
        video_parameters["color_diff_excursion"],
    )

    return (y_int, c1_int, c2_int)


def matmul_colors(matrix, array):
    r"""
    Given a (height, width, 3) 3D array, return a new 3D array where each
    triple in the first array has been multiplied by the specified :math:`3
    \times 3` matrix.
    """
    return np.matmul(matrix, array.reshape(-1, 3).T,).T.reshape(array.shape)


def swap_primaries(xyz, video_parameters_before, video_parameters_after):
    r"""
    Given an image defined in terms of one set of primaries, return a new image
    defined in terms of a different set of primaries but with the same
    numerical R, G and B values under the new set of primaries.

    This transformation is useful when an image is defined not by absolute
    colours but rather colors relative to whatever primaries are in use. For
    example, a test pattern designed to show swatches of pure color primaries
    may be given relative to a particular set of primaries but needs to be
    adapted for use with another set of primaries.

    Parameters
    ==========
    xyz : :math:`3 \times 3` array (height, width, 3)
    video_parameters_before : :py:class:`~vc2_conformance.video_parameters.VideoParameters`
    video_parameters_after : :py:class:`~vc2_conformance.video_parameters.VideoParameters`

    Returns
    =======
    xyz : :math:`3 \times 3` array (height, width, 3)
    """
    xyz_to_linear_rgb_before = XYZ_TO_LINEAR_RGB[
        video_parameters_before["color_primaries_index"]
    ]
    linear_rgb_after_to_xyz = LINEAR_RGB_TO_XYZ[
        video_parameters_after["color_primaries_index"]
    ]

    m = np.matmul(linear_rgb_after_to_xyz, xyz_to_linear_rgb_before)

    return matmul_colors(m, xyz)
