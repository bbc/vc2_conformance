"""
This module is the inverse of the
:py:mod:`vc2_conformance.pseudocode.picture_decoding` module and contains
functions for performing wavelet analysis filtering.

This functionality is not specified by the standard but is used to generate
simple bitstreams (and test cases) in this software (and its test suite).
"""

from vc2_data_tables import LIFTING_FILTERS, LiftingFilterTypes

from vc2_conformance.pseudocode.arrays import (
    new_array,
    width,
    height,
    row,
    column,
)

from vc2_conformance.pseudocode.slice_sizes import (
    subband_width,
    subband_height,
)

from vc2_conformance.pseudocode.picture_decoding import (
    filter_bit_shift,
    SYNTHESIS_LIFTING_FUNCTION_TYPES,
)


__all__ = [
    "picture_encode",
    "forward_wavelet_transform",
    "dwt",
    "h_analysis",
    "vh_analysis",
    "oned_analysis",
    "ANALYSIS_LIFTING_FUNCTION_TYPES",
    "dwt_pad_addition",
    "remove_offset_picture",
    "remove_offset_component",
]


def picture_encode(state, current_picture):
    """
    Inverse of picture_decode (15.2).

    Parameters
    ==========
    state : :py:class:`vc2_conformance.pseudocode.state.State`
        A state dictionary containing at least:

        * ``luma_width``
        * ``luma_height``
        * ``color_diff_width``
        * ``color_diff_height``
        * ``luma_depth``
        * ``color_diff_depth``
        * ``wavelet_index``
        * ``wavelet_index_ho``
        * ``dwt_depth``
        * ``dwt_depth_ho``

        The following entries will be added/replaced with the encoded picture.

        * ``y_transform``
        * ``c1_transform``
        * ``c3_transform``

    current_picture : {component: [[value, ...], ...], ...}
        The picture to be encoded.
    """
    remove_offset_picture(state, current_picture)
    forward_wavelet_transform(state, current_picture)


def forward_wavelet_transform(state, current_picture):
    """(15.3)"""
    for c in ["Y", "C1", "C2"]:
        dwt_pad_addition(state, current_picture[c], c)

    state["y_transform"] = dwt(state, current_picture["Y"])
    state["c1_transform"] = dwt(state, current_picture["C1"])
    state["c2_transform"] = dwt(state, current_picture["C2"])


################################################################################
# Forward (Analysis) Discrete Wavelet Transform
################################################################################


def dwt(state, picture):
    """
    Discrete Wavelet Transform, inverse of idwt (15.4.1)

    Parameters
    ==========
    state : :py:class:`~vc2_conformance.pseudocode.state.State`
        A state dictionary containing at least the following:

        * ``wavelet_index``
        * ``wavelet_index_ho``
        * ``dwt_depth``
        * ``dwt_depth_ho``

    picture : [[pixel_value, ...], ...]
        The synthesized picture.

    Returns
    =======
    coeff_data : {level: {orientation: [[coeff, ...], ...], ...}, ...}
        The complete (power-of-two dimensioned) transform coefficient data.
    """
    coeff_data = {}

    DC_band = picture
    for n in reversed(
        range(state["dwt_depth_ho"] + 1, state["dwt_depth_ho"] + state["dwt_depth"] + 1)
    ):
        (LL_data, HL_data, LH_data, HH_data) = vh_analysis(state, DC_band)
        DC_band = LL_data
        coeff_data[n] = {}
        coeff_data[n]["HL"] = HL_data
        coeff_data[n]["LH"] = LH_data
        coeff_data[n]["HH"] = HH_data
    for n in reversed(range(1, state["dwt_depth_ho"] + 1)):
        (L_data, H_data) = h_analysis(state, DC_band)
        DC_band = L_data
        coeff_data[n] = {}
        coeff_data[n]["H"] = H_data
    coeff_data[0] = {}
    if state["dwt_depth_ho"] == 0:
        coeff_data[0]["LL"] = DC_band
    else:
        coeff_data[0]["L"] = DC_band

    return coeff_data


def h_analysis(state, data):
    """
    Horizontal-only analysis, inverse of h_synthesis (15.4.2).

    Returns a tuple (L_data, H_data)
    """
    # Bit shift, if required
    shift = filter_bit_shift(state)
    if shift > 0:
        for y in range(0, height(data)):
            for x in range(0, width(data)):
                data[y][x] = data[y][x] << shift

    # Analysis
    for y in range(0, height(data)):
        oned_analysis(row(data, y), state["wavelet_index_ho"])

    # De-interleave the transform data
    L_data = new_array(height(data), width(data) // 2)
    H_data = new_array(height(data), width(data) // 2)
    for y in range(0, (height(data))):
        for x in range(0, (width(data) // 2)):
            L_data[y][x] = data[y][2 * x]
            H_data[y][x] = data[y][(2 * x) + 1]

    return (L_data, H_data)


def vh_analysis(state, data):
    """
    Interleaved vertical and horizontal analysis, inverse of vh_synthesis (15.4.3).

    Returns a tuple (LL_data, HL_data, LH_data, HH_data)
    """
    # Bit shift, if required
    shift = filter_bit_shift(state)
    if shift > 0:
        for y in range(0, height(data)):
            for x in range(0, width(data)):
                data[y][x] = data[y][x] << shift

    # Analysis
    for y in range(0, height(data)):
        oned_analysis(row(data, y), state["wavelet_index_ho"])
    for x in range(0, width(data)):
        oned_analysis(column(data, x), state["wavelet_index"])

    # De-interleave the transform data
    LL_data = new_array(height(data) // 2, width(data) // 2)
    HL_data = new_array(height(data) // 2, width(data) // 2)
    LH_data = new_array(height(data) // 2, width(data) // 2)
    HH_data = new_array(height(data) // 2, width(data) // 2)
    for y in range(0, (height(data) // 2)):
        for x in range(0, (width(data) // 2)):
            LL_data[y][x] = data[2 * y][2 * x]
            HL_data[y][x] = data[2 * y][2 * x + 1]
            LH_data[y][x] = data[2 * y + 1][2 * x]
            HH_data[y][x] = data[2 * y + 1][2 * x + 1]

    return (LL_data, HL_data, LH_data, HH_data)


def oned_analysis(A, filter_index):
    """
    Inverse of oned_synthesis (15.4.4.1) and (15.4.4.3). Acts in-place on 'A'
    """
    filter_params = LIFTING_FILTERS[filter_index]

    for stage in reversed(filter_params.stages):
        lift_fn = ANALYSIS_LIFTING_FUNCTION_TYPES[stage.lift_type]
        lift_fn(A, stage.L, stage.D, stage.taps, stage.S)


ANALYSIS_LIFTING_FUNCTION_TYPES = {
    new_type: SYNTHESIS_LIFTING_FUNCTION_TYPES[old_type]
    for (new_type, old_type) in [
        # Swap 'adds' for 'subtracts'
        (LiftingFilterTypes.even_add_odd, LiftingFilterTypes.even_subtract_odd),
        (LiftingFilterTypes.even_subtract_odd, LiftingFilterTypes.even_add_odd),
        (LiftingFilterTypes.odd_add_even, LiftingFilterTypes.odd_subtract_even),
        (LiftingFilterTypes.odd_subtract_even, LiftingFilterTypes.odd_add_even),
    ]
}
"""
Lookup from lifting function ID to function implementation for implementing
wavelet analysis.
"""


################################################################################
# Padding addition
################################################################################


def dwt_pad_addition(state, pic, c):
    """
    Inverse of idwt_pad_removal (15.4.5): pads a picture to a size compatible
    with wavelet filtering at the level specified by the provided
    :py:class:`~vc2_conformance.pseudocode.state.State`.

    Extra values are obtained by copying the final pixels in the existing rows
    and columns.
    """
    top_level = state["dwt_depth"] + state["dwt_depth_ho"] + 1
    width = subband_width(state, top_level, c)
    height = subband_height(state, top_level, c)

    # Copy-extend every row
    for pic_row in pic:
        value = pic_row[-1]
        while len(pic_row) < width:
            pic_row.append(value)

    # Copy extend every column
    while len(pic) < height:
        pic.append(pic[-1][:])


################################################################################
# Pixel value offset removal
################################################################################


def remove_offset_picture(state, current_picture):
    """Inverse of offset_picture (15.5). Centers picture values around zero."""
    for c in ["Y", "C1", "C2"]:
        remove_offset_component(state, current_picture[c], c)


def remove_offset_component(state, comp_data, c):
    """
    Inverse of offset_component (15.5). Centers picture values around zero.

    Parameters
    ==========
    state : :py:class:`vc2_conformance.pseudocode.state.State`
        Where ``luma_depth`` and ``color_diff_depth`` are defined.
    current_picture : {comp: [[pixel_value, ...], ...], ...}
        Will be mutated in-place.
    """
    for y in range(0, height(comp_data)):
        for x in range(0, width(comp_data)):
            if c == "Y":
                comp_data[y][x] -= 2 ** (state["luma_depth"] - 1)
            else:
                comp_data[y][x] -= 2 ** (state["color_diff_depth"] - 1)
