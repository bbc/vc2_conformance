"""
:py:mod:`vc2_conformance.transform_data_syntax`: (13) Transform Data Syntax
===========================================================================
"""

from vc2_conformance.metadata import ref_pseudocode

from vc2_conformance.vc2_math import (
    sign,
    intlog2,
    mean,
)

from vc2_conformance.arrays import (
    array,
    width,
    height,
)

from vc2_conformance.slice_sizes import (
    subband_width,
    subband_height,
    slice_bytes,
    slice_left,
    slice_right,
    slice_top,
    slice_bottom,
)

from vc2_conformance.parse_code_functions import (
    is_ld_picture,
    is_hq_picture,
    is_ld_fragment,
    is_hq_fragment,
    using_dc_prediction,
)

from vc2_conformance.decoder.exceptions import (
    InvalidSliceYLength,
)

from vc2_conformance.decoder.assertions import (
    assert_level_constraint,
)

from vc2_conformance.decoder.io import (
    tell,
    read_uint_lit,
    read_nbits,
    read_sintb,
    flush_inputb,
)


__all__ = [
    "inverse_quant",
    "quant_factor",
    "quant_offset",
    "initialize_wavelet_data",
    "dc_prediction",
    "transform_data",
    "slice",
    "ld_slice",
    "hq_slice",
    "slice_quantizers",
    "slice_band",
    "color_diff_slice_band",
]


@ref_pseudocode
def inverse_quant(quantized_coeff, quant_index):
    """(13.3.1)"""
    magnitude = abs(quantized_coeff)
    if magnitude != 0:
        magnitude *= quant_factor(quant_index)
        magnitude += quant_offset(quant_index)
        magnitude += 2
        magnitude //= 4
    return sign(quantized_coeff) * magnitude


@ref_pseudocode
def quant_factor(index):
    """(13.3.2)"""
    base = 2**(index//4)
    if (index%4) == 0:
        return (4 * base)
    elif (index%4) == 1:
        return(((503829 * base) + 52958) // 105917)
    elif (index%4) == 2:
        return(((665857 * base) + 58854) // 117708)
    elif (index%4) == 3:
        return(((440253 * base) + 32722) // 65444)


@ref_pseudocode
def quant_offset(index):
    """(13.3.2)"""
    if index == 0:
        offset = 1
    elif index == 1:
        offset = 2
    else:
        offset = (quant_factor(index) + 1)//2
    return offset


@ref_pseudocode
def dc_prediction(band):
    """(13.4)"""
    for y in range(0, height(band)):
        for x in range(0, width(band)):
            if x > 0 and y > 0:
                prediction = mean([band[y][x-1], band[y-1][x-1], band[y-1][x]])
            elif x > 0 and y == 0:
                prediction = band[0][x - 1]
            elif x == 0 and y > 0:
                prediction = band[y - 1][0]
            else:
                prediction = 0
            band[y][x] += prediction


@ref_pseudocode(deviation="inferred_implementation")
def initialize_wavelet_data(state, comp):
    """(13.2.2) Return a ready-to-fill array of transform data arrays."""
    out = {}
    
    if state["dwt_depth_ho"] == 0:
        out[0] = {"LL": array(subband_width(state, 0, comp),
                              subband_height(state, 0, comp))}
    else:
        out[0] = {"L": array(subband_width(state, 0, comp),
                             subband_height(state, 0, comp))}
        for level in range(1, state["dwt_depth_ho"] + 1):
            out[level] = {"H": array(subband_width(state, level, comp),
                                     subband_height(state, level, comp))}
    
    for level in range(state["dwt_depth_ho"] + 1,
                       state["dwt_depth_ho"] + state["dwt_depth"] + 1):
        out[level] = {orient: array(subband_width(state, level, comp),
                                    subband_height(state, level, comp))
                      for orient in ["HL", "LH", "HH"]}
    return out


@ref_pseudocode
def transform_data(state):
    """(13.5.2)"""
    state["y_transform"] = initialize_wavelet_data(state, "Y")
    state["c1_transform"] = initialize_wavelet_data(state, "C1")
    state["c2_transform"] = initialize_wavelet_data(state, "C2")
    for sy in range(state["slices_y"]):
        for sx in range(state["slices_x"]):
            slice(state, sx, sy)
    if using_dc_prediction(state):
        if state["dwt_depth_ho"] == 0:
            dc_prediction(state["y_transform"][0]["LL"])
            dc_prediction(state["c1_transform"][0]["LL"])
            dc_prediction(state["c2_transform"][0]["LL"])
        else:
            dc_prediction(state["y_transform"][0]["L"])
            dc_prediction(state["c1_transform"][0]["L"])
            dc_prediction(state["c2_transform"][0]["L"])


@ref_pseudocode
def slice(state, sx, sy):
    """(13.5.2)"""
    if is_ld_picture(state) or is_ld_fragment(state):
        ld_slice(state, sx, sy)
    elif is_hq_picture(state) or is_hq_fragment(state):
        hq_slice(state, sx, sy)


@ref_pseudocode
def ld_slice(state, sx, sy):
    """(13.5.3.1)"""
    slice_bits_left = 8*slice_bytes(state, sx, sy)
    
    qindex = read_nbits(state, 7)
    slice_bits_left -= 7
    # Errata: none of the levels currently restrict the qindex
    #
    # (C.3) The quantisation index may be restricted by some levels
    assert_level_constraint(state, "qindex", qindex) ## Not in spec
    
    slice_quantizers(state, qindex)
    
    length_bits = intlog2(8*slice_bytes(state, sx, sy)-7)
    slice_y_length = read_nbits(state, length_bits)
    slice_bits_left -= length_bits
    
    # (13.5.3.1) The slice_y_length is restricted to be within the remaining
    # space in this slice
    ## Begin not in spec
    # NB: slice_bits_left = 8*slice_bytes(state, sx, sy) - 7 - length_bits
    if slice_y_length > slice_bits_left:
        raise InvalidSliceYLength(slice_y_length, slice_bits_left)
    ## End not in spec
    
    state["bits_left"] = slice_y_length
    if state["dwt_depth_ho"] == 0:
        slice_band(state, "y_transform", 0, "LL", sx, sy)
        for level in range(1, state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                slice_band(state, "y_transform", level, orient, sx, sy)
    else:
        slice_band(state, "y_transform", 0, "L", sx, sy)
        for level in range(1, state["dwt_depth_ho"] + 1):
            slice_band(state, "y_transform", level, "H", sx, sy)
        for level in range(state["dwt_depth_ho"] + 1,
                           state["dwt_depth_ho"] + state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                slice_band(state, "y_transform", level, orient, sx, sy)
    flush_inputb(state)
    
    slice_bits_left -= slice_y_length
    state["bits_left"] = slice_bits_left
    if state["dwt_depth_ho"] == 0:
        color_diff_slice_band(state, 0, "LL", sx, sy)
        for level in range(1, state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                color_diff_slice_band(state, level, orient, sx, sy)
    else:
        color_diff_slice_band(state, 0, "L", sx, sy)
        for level in range(1, state["dwt_depth_ho"] + 1):
            color_diff_slice_band(state, level, "H", sx, sy)
        for level in range(state["dwt_depth_ho"] + 1,
                           state["dwt_depth_ho"] + state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                color_diff_slice_band(state, level, orient, sx, sy)
    flush_inputb(state)


@ref_pseudocode
def hq_slice(state, sx, sy):
    """(13.5.4)"""
    byte_offset_start = tell(state)[0]  ## Not in spec
    
    read_uint_lit(state, state["slice_prefix_bytes"])
    
    qindex = read_uint_lit(state, 1)
    # Errata: none of the levels currently restrict the qindex
    #
    # (C.3) The quantisation index may be restricted by some levels
    assert_level_constraint(state, "qindex", qindex) ## Not in spec
    
    slice_quantizers(state, qindex)
    
    for transform in ["y_transform", "c1_transform", "c2_transform"]:
        length = state["slice_size_scaler"] * read_uint_lit(state, 1)
        state["bits_left"] = 8*length
        if state["dwt_depth_ho"] == 0:
            slice_band(state, transform, 0, "LL", sx, sy)
            for level in range(1, state["dwt_depth"] + 1):
                for orient in ["HL", "LH", "HH"]:
                    slice_band(state, transform, level, orient, sx, sy)
        else:
            slice_band(state, transform, 0, "L", sx, sy)
            for level in range(1, state["dwt_depth_ho"] + 1):
                slice_band(state, transform, level, "H", sx, sy)
            for level in range(state["dwt_depth_ho"] + 1,
                               state["dwt_depth_ho"] + state["dwt_depth"] + 1):
                for orient in ["HL", "LH", "HH"]:
                    slice_band(state, transform, level, orient, sx, sy)
        flush_inputb(state)
    
    # (C.3) Some levels restrict the total size of HQ slices
    ## Begin not in spec
    byte_offset_end = tell(state)[0]
    total_slice_bytes = byte_offset_end - byte_offset_start
    assert_level_constraint(state, "total_slice_bytes", total_slice_bytes)
    ## End not in spec


@ref_pseudocode
def slice_quantizers(state, qindex):
    """(13.5.5)"""
    state["quantizer"] = {}
    if state["dwt_depth_ho"] == 0:
        state["quantizer"][0] = {}
        state["quantizer"][0]["LL"] = max(qindex - state["quant_matrix"][0]["LL"], 0)
        for level in range(1, state["dwt_depth"] + 1):
            state["quantizer"][level] = {}
            for orient in ["HL", "LH", "HH"]:
                qval = max(qindex - state["quant_matrix"][level][orient], 0)
                state["quantizer"][level][orient] = qval
    else:
        state["quantizer"][0] = {}
        state["quantizer"][0]["L"] = max(qindex - state["quant_matrix"][0]["L"], 0)
        for level in range(1, state["dwt_depth_ho"] + 1):
            state["quantizer"][level] = {}
            qval = max(qindex - state["quant_matrix"][level]["H"], 0)
            state["quantizer"][level]["H"] = qval
        for level in range(state["dwt_depth_ho"] + 1,
                           state["dwt_depth_ho"] + state["dwt_depth"] + 1):
            state["quantizer"][level] = {}
            for orient in ["HL", "LH", "HH"]:
                qval = max(qindex - state["quant_matrix"][level][orient], 0)
                state["quantizer"][level][orient] = qval


@ref_pseudocode
def slice_band(state, transform, level, orient, sx, sy):
    """(13.5.6.3)"""
    comp = "Y" if transform.startswith("y") else "C1"
    
    # These values evaulated in the loop definition in the spec, moving them
    # here saves a lot of computation
    ## Begin not in spec
    y1 = slice_top(state, sy, comp, level)
    y2 = slice_bottom(state, sy, comp, level)
    x1 = slice_left(state, sx, comp, level)
    x2 = slice_right(state, sx, comp, level)
    ## End not in spec
    
    ### for y in range(slice_top(state, sy,comp,level), slice_bottom(state, sy,comp,level)):
    ###     for x in range(slice_left(state, sx,comp,level), slice_right(state, sx,comp,level)):
    for y in range(y1, y2):  ## Not in spec
        for x in range(x1, x2):  ## Not in spec
            val = read_sintb(state)
            qi = state["quantizer"][level][orient]
            state[transform][level][orient][y][x] = inverse_quant(val, qi)


@ref_pseudocode
def color_diff_slice_band(state, level, orient, sx, sy):
    """(13.5.6.4)"""
    # These values evaulated in the loop definition in the spec, moving them
    # here saves a lot of computation
    ## Begin not in spec
    y1 = slice_top(state, sy, "C1", level)
    y2 = slice_bottom(state, sy, "C1", level)
    x1 = slice_left(state, sx, "C1", level)
    x2 = slice_right(state, sx, "C1", level)
    ## End not in spec
    
    ### for y in range(slice_top(state,sy,"C1",level), slice_bottom(state,sy,"C1",level)):
    ###     for x in range(slice_left(state,sx,"C1",level), slice_right(state,sx,"C1",level)):
    for y in range(y1, y2):  ## Not in spec
        for x in range(x1, x2):  ## Not in spec
            qi = state["quantizer"][level][orient]
            val = read_sintb(state)
            state["c1_transform"][level][orient][y][x] = inverse_quant(val, qi)
            val = read_sintb(state)
            state["c2_transform"][level][orient][y][x] = inverse_quant(val, qi)
