"""
:py:mod:`vc2_conformance.wavelet_filtering`: (15) Generic Wavelet-filtering routines
====================================================================================

This module collects the wavelet synthesis filters from (15) and augments these
with complementary analysis filters (inferred from, but not defined by the
standard).
"""

from vc2_conformance.metadata import ref_pseudocode

from vc2_conformance.tables import LIFTING_FILTERS, LiftingFilterTypes

from vc2_conformance.arrays import (
    new_array,
    width,
    height,
    row,
    column,
)

__all__ = [
    "idwt",
    "dwt",
    "h_synthesis",
    "h_analysis",
    "vh_synthesis",
    "vh_analysis",
    "oned_synthesis",
    "oned_analysis",
    "lift1",
    "lift2",
    "lift3",
    "lift4",
    "SYNTHESIS_LIFTING_FUNCTION_TYPES",
    "ANALYSIS_LIFTING_FUNCTION_TYPES",
]


@ref_pseudocode
def idwt(state, coeff_data):
    """
    (15.4.1)
    
    Inverse Discrete Wavelet Transform.
    
    Parameters
    ==========
    state : :py:class:`~vc2_conformance.state.State`
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
    if (state["dwt_depth_ho"] == 0):
        DC_band = coeff_data[0]["LL"]
    else:
        DC_band = coeff_data[0]["L"]
    for n in range(1, state["dwt_depth_ho"] + 1):
        new_DC_band = h_synthesis(state, DC_band, coeff_data[n]["H"])
        DC_band = new_DC_band
    for n in range(state["dwt_depth_ho"] + 1,
                   state["dwt_depth_ho"] + state["dwt_depth"] + 1):
        new_DC_band = vh_synthesis(state, DC_band, coeff_data[n]["HL"],
                                   coeff_data[n]["LH"],coeff_data[n]["HH"])
        DC_band = new_DC_band
    return DC_band


def dwt(state, picture):
    """
    Discrete Wavelet Transform, inverse of idwt (15.4.1)
    
    Parameters
    ==========
    state : :py:class:`~vc2_conformance.state.State`
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
    for n in reversed(range(state["dwt_depth_ho"] + 1,
                            state["dwt_depth_ho"] + state["dwt_depth"] + 1)):
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
    if (state["dwt_depth_ho"] == 0):
        coeff_data[0]["LL"] = DC_band
    else:
        coeff_data[0]["L"] = DC_band
    
    return coeff_data


@ref_pseudocode
def h_synthesis(state, L_data, H_data):
    """(15.4.2) Horizontal-only synthesis."""
    synth = new_array(2 * width(L_data), height(L_data))
    
    # Interleave transform data (as expected by synthesis routine)
    for y in range(0, (height(synth))):
        for x in range(0, (width(synth)//2)):
            synth[y][2*x] = L_data[y][x]
            synth[y][(2*x) + 1] = H_data[y][x]
    
    # Synthesis
    for y in range(0, height(synth)):
        oned_synthesis(row(synth, y), state["wavelet_index_ho"])
    
    # Bit shift, if required
    shift = filter_bit_shift(state)
    if shift > 0:
        for y in range(0, height(synth)):
            for x in range(0, width(synth)):
                synth[y][x] = (synth[y][x] + (1 << (shift - 1))) >> shift
    
    return synth


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
    L_data = new_array(width(data) // 2, height(data))
    H_data = new_array(width(data) // 2, height(data))
    for y in range(0, (height(data))):
        for x in range(0, (width(data) // 2)):
            L_data[y][x] = data[y][2*x]
            H_data[y][x] = data[y][(2*x) + 1]
    
    return (L_data, H_data)


@ref_pseudocode
def vh_synthesis(state, LL_data, HL_data, LH_data, HH_data):
    """(15.4.3) Interleaved vertical and horizontal synthesis."""
    synth = new_array(2 * width(LL_data), 2 * height(LL_data))
    
    # Interleave transform data (as expected by synthesis routine)
    for y in range(0, (height(synth)//2)):
        for x in range(0, (width(synth)//2)):
            synth[2*y][2*x] = LL_data[y][x]
            synth[2*y][2*x + 1] = HL_data[y][x]
            synth[2*y + 1][2*x] = LH_data[y][x]
            synth[2*y + 1][2*x + 1] = HH_data[y][x]
    
    # Synthesis
    for x in range(0, width(synth)):
        oned_synthesis(column(synth, x), state["wavelet_index"])
    for y in range(0, height(synth)):
        oned_synthesis(row(synth, y), state["wavelet_index_ho"])
    
    # Bit shift, if required
    shift = filter_bit_shift(state)
    if shift > 0:
        for y in range(0, height(synth)):
            for x in range(0, width(synth)):
                synth[y][x] = (synth[y][x] + (1 << (shift - 1))) >> shift
    
    return synth


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
    LL_data = new_array(width(data) // 2, height(data) // 2)
    HL_data = new_array(width(data) // 2, height(data) // 2)
    LH_data = new_array(width(data) // 2, height(data) // 2)
    HH_data = new_array(width(data) // 2, height(data) // 2)
    for y in range(0, (height(data) // 2)):
        for x in range(0, (width(data) // 2)):
            LL_data[y][x] = data[2*y][2*x]
            HL_data[y][x] = data[2*y][2*x + 1]
            LH_data[y][x] = data[2*y + 1][2*x]
            HH_data[y][x] = data[2*y + 1][2*x + 1]
    
    return (LL_data, HL_data, LH_data, HH_data)


@ref_pseudocode(deviation="inferred_implementation")
def oned_synthesis(A, filter_index):
    """(15.4.4.1) and (15.4.4.3). Acts in-place on 'A'"""
    filter_params = LIFTING_FILTERS[filter_index]
    
    for stage in filter_params.stages:
        lift_fn = SYNTHESIS_LIFTING_FUNCTION_TYPES[stage.lift_type]
        lift_fn(A, stage.L, stage.D, stage.taps, stage.S)


def oned_analysis(A, filter_index):
    """
    Inverse of oned_synthesis (15.4.4.1) and (15.4.4.3). Acts in-place on 'A'
    """
    filter_params = LIFTING_FILTERS[filter_index]
    
    for stage in reversed(filter_params.stages):
        lift_fn = ANALYSIS_LIFTING_FUNCTION_TYPES[stage.lift_type]
        lift_fn(A, stage.L, stage.D, stage.taps, stage.S)



@ref_pseudocode(deviation="inferred_implementation")
def filter_bit_shift(state):
    """(15.4.2) Return the bit shift for the current horizontal-only filter."""
    filter_params = LIFTING_FILTERS[state["wavelet_index_ho"]]
    return filter_params.filter_bit_shift


@ref_pseudocode
def lift1(A, L, D, taps, S):
    """(15.4.4.1) Update even, add odd."""
    for n in range(0, (len(A)//2)):
        sum = 0
        for i in range(D, L + D):
            pos = 2*(n + i) - 1
            pos = min(pos, len(A) - 1)
            pos = max(pos, 1)
            sum += taps[i-D]* A[pos]
        if S>0:
            sum += (1<<(S - 1))
        A[2*n] += (sum >> S)


@ref_pseudocode
def lift2(A, L, D, taps, S):
    """(15.4.4.1) Update even, subtract odd."""
    for n in range(0, (len(A)//2)):
        sum = 0
        for i in range(D, L + D):
            pos = 2*(n + i) - 1
            pos = min(pos, len(A) - 1)
            pos = max(pos, 1)
            sum += taps[i-D] * A[pos]
        if S>0:
            sum += (1<<(S - 1))
        A[2*n] -= (sum >> S)


@ref_pseudocode
def lift3(A, L, D, taps, S):
    """(15.4.4.1) Update odd, add even."""
    for n in range(0, (len(A)//2)):
        sum = 0
        for i in range(D, L + D):
            pos = 2*(n + i)
            pos = min(pos, len(A) - 2)
            pos = max(pos, 0)
            sum += taps[i-D] * A[pos]
        if S>0:
            sum += (1<<(S - 1))
        A[2*n + 1] += (sum >> S)


@ref_pseudocode
def lift4(A, L, D, taps, S):
    """(15.4.4.1) Update odd, subtract even."""
    for n in range(0, (len(A)//2)):
        sum = 0
        for i in range(D, L + D):
            pos = 2*(n + i)
            pos = min(pos, len(A) - 2)
            pos = max(pos, 0)
            sum += taps[i-D] * A[pos]
        if S>0:
            sum += (1<<(S - 1))
        A[2*n + 1] -= (sum >> S)


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

ANALYSIS_LIFTING_FUNCTION_TYPES = {
    LiftingFilterTypes(2): lift1,
    LiftingFilterTypes(1): lift2,
    LiftingFilterTypes(4): lift3,
    LiftingFilterTypes(3): lift4,
}
"""
Lookup from lifting function ID to function implementation for implementing
wavelet analysis.
"""
