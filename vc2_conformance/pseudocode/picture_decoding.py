"""
This module contains the wavelet synthesis filters and associated functions
defined in the pseudocode of the VC-2 standard (15).

See also :py:mod:`vc2_conformance.pseudocode.picture_encoding`.
"""

from vc2_conformance.pseudocode.metadata import ref_pseudocode

from vc2_data_tables import LIFTING_FILTERS, LiftingFilterTypes

from vc2_conformance.pseudocode.vc2_math import clip

from vc2_conformance.pseudocode.arrays import (
    new_array,
    width,
    height,
    row,
    column,
    delete_rows_after,
    delete_columns_after,
)

__all__ = [
    "inverse_wavelet_transform",
    "idwt",
    "h_synthesis",
    "vh_synthesis",
    "oned_synthesis",
    "filter_bit_shift",
    "lift1",
    "lift2",
    "lift3",
    "lift4",
    "SYNTHESIS_LIFTING_FUNCTION_TYPES",
    "idwt_pad_removal",
    "offset_picture",
    "offset_component",
    "clip_picture",
    "clip_component",
]


@ref_pseudocode
def picture_decode(state):
    """(15.2)"""
    state["current_picture"] = {}
    state["current_picture"]["pic_num"] = state["picture_number"]
    inverse_wavelet_transform(state)
    clip_picture(state, state["current_picture"])
    offset_picture(state, state["current_picture"])

    # In this concrete implementation, the 'output_picture' function is
    # provided via the _output_picture_callback comes via State.

    ### output_picture(
    ###     state["current_picture"],
    ###     state["video_parameters"],
    ###     state["picture_coding_mode"],
    ### )

    ## Begin not in spec
    if "_output_picture_callback" in state:
        state["_output_picture_callback"](
            state["current_picture"],
            state["video_parameters"],
            state["picture_coding_mode"],
        )
    ## End not in spec


@ref_pseudocode
def inverse_wavelet_transform(state):
    """(15.3)"""
    state["current_picture"]["Y"] = idwt(state, state["y_transform"])
    state["current_picture"]["C1"] = idwt(state, state["c1_transform"])
    state["current_picture"]["C2"] = idwt(state, state["c2_transform"])
    for c in ["Y", "C1", "C2"]:
        idwt_pad_removal(state, state["current_picture"][c], c)


################################################################################
# Inverse (Synthesis) Discrete Wavelet Transform
################################################################################


@ref_pseudocode
def idwt(state, coeff_data):
    """
    (15.4.1)

    Inverse Discrete Wavelet Transform.

    Parameters
    ==========
    state : :py:class:`~vc2_conformance.pseudocode.state.State`
        A state dictionary containing at least the following:

        * ``wavelet_index``
        * ``wavelet_index_ho``
        * ``dwt_depth``
        * ``dwt_depth_ho``

    coeff_data : {level: {orientation: [[coeff, ...], ...], ...}, ...}
        The complete (power-of-two dimensioned) transform coefficient data.

    Returns
    =======
    picture : [[pixel_value, ...], ...]
        The synthesized picture.
    """
    if state["dwt_depth_ho"] == 0:
        DC_band = coeff_data[0]["LL"]
    else:
        DC_band = coeff_data[0]["L"]
    for n in range(1, state["dwt_depth_ho"] + 1):
        new_DC_band = h_synthesis(state, DC_band, coeff_data[n]["H"])
        DC_band = new_DC_band
    for n in range(
        state["dwt_depth_ho"] + 1, state["dwt_depth_ho"] + state["dwt_depth"] + 1
    ):
        new_DC_band = vh_synthesis(
            state,
            DC_band,
            coeff_data[n]["HL"],
            coeff_data[n]["LH"],
            coeff_data[n]["HH"],
        )
        DC_band = new_DC_band
    return DC_band


@ref_pseudocode
def h_synthesis(state, L_data, H_data):
    """(15.4.2) Horizontal-only synthesis."""
    synth = new_array(height(L_data), 2 * width(L_data))

    # Interleave transform data (as expected by synthesis routine)
    for y in range(height(synth)):
        for x in range(width(synth) // 2):
            synth[y][2 * x] = L_data[y][x]
            synth[y][(2 * x) + 1] = H_data[y][x]

    # Synthesis
    for y in range(height(synth)):
        oned_synthesis(row(synth, y), state["wavelet_index_ho"])

    # Bit shift, if required
    shift = filter_bit_shift(state)
    if shift > 0:
        for y in range(height(synth)):
            for x in range(width(synth)):
                synth[y][x] = (synth[y][x] + (1 << (shift - 1))) >> shift

    return synth


@ref_pseudocode
def vh_synthesis(state, LL_data, HL_data, LH_data, HH_data):
    """(15.4.3) Interleaved vertical and horizontal synthesis."""
    synth = new_array(2 * height(LL_data), 2 * width(LL_data))

    # Interleave transform data (as expected by synthesis routine)
    for y in range(height(synth) // 2):
        for x in range(width(synth) // 2):
            synth[2 * y][2 * x] = LL_data[y][x]
            synth[2 * y][2 * x + 1] = HL_data[y][x]
            synth[2 * y + 1][2 * x] = LH_data[y][x]
            synth[2 * y + 1][2 * x + 1] = HH_data[y][x]

    # Synthesis
    for x in range(width(synth)):
        oned_synthesis(column(synth, x), state["wavelet_index"])
    for y in range(height(synth)):
        oned_synthesis(row(synth, y), state["wavelet_index_ho"])

    # Bit shift, if required
    shift = filter_bit_shift(state)
    if shift > 0:
        for y in range(height(synth)):
            for x in range(width(synth)):
                synth[y][x] = (synth[y][x] + (1 << (shift - 1))) >> shift

    return synth


@ref_pseudocode(deviation="inferred_implementation")
def oned_synthesis(A, filter_index):
    """(15.4.4.1) and (15.4.4.3). Acts in-place on 'A'"""
    filter_params = LIFTING_FILTERS[filter_index]

    for stage in filter_params.stages:
        lift_fn = SYNTHESIS_LIFTING_FUNCTION_TYPES[stage.lift_type]
        lift_fn(A, stage.L, stage.D, stage.taps, stage.S)


@ref_pseudocode(deviation="inferred_implementation")
def filter_bit_shift(state):
    """(15.4.2) Return the bit shift for the current horizontal-only filter."""
    filter_params = LIFTING_FILTERS[state["wavelet_index_ho"]]
    return filter_params.filter_bit_shift


@ref_pseudocode
def lift1(A, L, D, taps, S):
    """(15.4.4.1) Update even, add odd."""
    for n in range(len(A) // 2):
        sum = 0
        for i in range(D, L + D):
            pos = 2 * (n + i) - 1
            pos = min(pos, len(A) - 1)
            pos = max(pos, 1)
            sum += taps[i - D] * A[pos]
        if S > 0:
            sum += 1 << (S - 1)
        A[2 * n] += sum >> S


@ref_pseudocode
def lift2(A, L, D, taps, S):
    """(15.4.4.1) Update even, subtract odd."""
    for n in range(len(A) // 2):
        sum = 0
        for i in range(D, L + D):
            pos = 2 * (n + i) - 1
            pos = min(pos, len(A) - 1)
            pos = max(pos, 1)
            sum += taps[i - D] * A[pos]
        if S > 0:
            sum += 1 << (S - 1)
        A[2 * n] -= sum >> S


@ref_pseudocode
def lift3(A, L, D, taps, S):
    """(15.4.4.1) Update odd, add even."""
    for n in range(len(A) // 2):
        sum = 0
        for i in range(D, L + D):
            pos = 2 * (n + i)
            pos = min(pos, len(A) - 2)
            pos = max(pos, 0)
            sum += taps[i - D] * A[pos]
        if S > 0:
            sum += 1 << (S - 1)
        A[2 * n + 1] += sum >> S


@ref_pseudocode
def lift4(A, L, D, taps, S):
    """(15.4.4.1) Update odd, subtract even."""
    for n in range(len(A) // 2):
        sum = 0
        for i in range(D, L + D):
            pos = 2 * (n + i)
            pos = min(pos, len(A) - 2)
            pos = max(pos, 0)
            sum += taps[i - D] * A[pos]
        if S > 0:
            sum += 1 << (S - 1)
        A[2 * n + 1] -= sum >> S


SYNTHESIS_LIFTING_FUNCTION_TYPES = {
    LiftingFilterTypes(1): lift1,
    LiftingFilterTypes(2): lift2,
    LiftingFilterTypes(3): lift3,
    LiftingFilterTypes(4): lift4,
}
"""
Lookup from lifting function ID to function implementation for implementing
wavelet synthesis.
"""


################################################################################
# Padding removal
################################################################################


@ref_pseudocode
def idwt_pad_removal(state, pic, c):
    """(15.4.5)"""
    if c == "Y":
        width = state["luma_width"]
        height = state["luma_height"]
    elif (c == "C1") or (c == "C2"):
        width = state["color_diff_width"]
        height = state["color_diff_height"]

    delete_rows_after(pic, height)
    delete_columns_after(pic, width)


################################################################################
# Pixel value offsetting and clipping
################################################################################


@ref_pseudocode
def offset_picture(state, current_picture):
    """(15.5) Remove picture value offsets (added during encoding).

    Parameters
    ==========
    state : :py:class:`vc2_conformance.pseudocode.state.State`
        Where ``luma_depth`` and ``color_diff_depth`` are defined.
    current_picture : {comp: [[pixel_value, ...], ...], ...}
        Will be mutated in-place.
    """
    for c in ["Y", "C1", "C2"]:
        offset_component(state, current_picture[c], c)


@ref_pseudocode
def offset_component(state, comp_data, c):
    """(15.5) Remove picture value offsets from a single component."""
    for y in range(height(comp_data)):
        for x in range(width(comp_data)):
            if c == "Y":
                comp_data[y][x] += 2 ** (state["luma_depth"] - 1)
            else:
                comp_data[y][x] += 2 ** (state["color_diff_depth"] - 1)


@ref_pseudocode
def clip_picture(state, current_picture):
    """(15.5)"""
    for c in ["Y", "C1", "C2"]:
        clip_component(state, current_picture[c], c)


@ref_pseudocode
def clip_component(state, comp_data, c):
    """(15.5)"""
    for y in range(height(comp_data)):
        for x in range(width(comp_data)):
            if c == "Y":
                comp_data[y][x] = clip(
                    comp_data[y][x],
                    -(2 ** (state["luma_depth"] - 1)),
                    2 ** (state["luma_depth"] - 1) - 1,
                )
            else:
                comp_data[y][x] = clip(
                    comp_data[y][x],
                    -(2 ** (state["color_diff_depth"] - 1)),
                    2 ** (state["color_diff_depth"] - 1) - 1,
                )
