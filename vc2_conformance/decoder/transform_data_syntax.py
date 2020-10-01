"""
The :py:mod:`vc2_conformance.decoder.transform_data_syntax` module contains pseudocode
functions from (13) Transform data syntax.
"""

from vc2_conformance.pseudocode.metadata import ref_pseudocode

from vc2_conformance.pseudocode.vc2_math import (
    intlog2,
    mean,
)

from vc2_conformance.pseudocode.arrays import (
    new_array,
    width,
    height,
)

from vc2_conformance.pseudocode.slice_sizes import (
    subband_width,
    subband_height,
    slice_bytes,
    slice_left,
    slice_right,
    slice_top,
    slice_bottom,
)

from vc2_conformance.pseudocode.parse_code_functions import (
    is_ld,
    is_hq,
    using_dc_prediction,
)

from vc2_conformance.decoder.exceptions import InvalidSliceYLength

from vc2_conformance.decoder.assertions import assert_level_constraint

from vc2_conformance.decoder.io import (
    tell,
    read_uint_lit,
    read_nbits,
    read_sintb,
    flush_inputb,
)

from vc2_conformance.pseudocode.quantization import inverse_quant

__all__ = [
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
def dc_prediction(band):
    """(13.4)"""
    for y in range(height(band)):
        for x in range(width(band)):
            if x > 0 and y > 0:
                prediction = mean(band[y][x - 1], band[y - 1][x - 1], band[y - 1][x])
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
        out[0] = {
            "LL": new_array(
                subband_height(state, 0, comp), subband_width(state, 0, comp)
            )
        }
    else:
        out[0] = {
            "L": new_array(
                subband_height(state, 0, comp), subband_width(state, 0, comp)
            )
        }
        for level in range(1, state["dwt_depth_ho"] + 1):
            out[level] = {
                "H": new_array(
                    subband_height(state, level, comp),
                    subband_width(state, level, comp),
                )
            }

    for level in range(
        state["dwt_depth_ho"] + 1, state["dwt_depth_ho"] + state["dwt_depth"] + 1
    ):
        out[level] = {
            orient: new_array(
                subband_height(state, level, comp), subband_width(state, level, comp)
            )
            for orient in ["HL", "LH", "HH"]
        }
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
    if is_ld(state):
        ld_slice(state, sx, sy)
    elif is_hq(state):
        hq_slice(state, sx, sy)


@ref_pseudocode
def ld_slice(state, sx, sy):
    """(13.5.3.1)"""
    slice_bits_left = 8 * slice_bytes(state, sx, sy)

    qindex = read_nbits(state, 7)
    slice_bits_left -= 7
    # Errata: none of the levels currently restrict the qindex
    #
    # (C.3) The quantisation index may be restricted by some levels
    assert_level_constraint(state, "qindex", qindex)  ## Not in spec

    slice_quantizers(state, qindex)

    length_bits = intlog2(8 * slice_bytes(state, sx, sy) - 7)
    slice_y_length = read_nbits(state, length_bits)
    slice_bits_left -= length_bits

    # (13.5.3.1) The slice_y_length is restricted to be within the remaining
    # space in this slice
    ## Begin not in spec
    # NB: slice_bits_left = 8*slice_bytes(state, sx, sy) - 7 - length_bits
    if slice_y_length > slice_bits_left:
        raise InvalidSliceYLength(
            slice_y_length,
            slice_bytes(state, sx, sy),
            sx,
            sy,
        )
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
        for level in range(
            state["dwt_depth_ho"] + 1, state["dwt_depth_ho"] + state["dwt_depth"] + 1
        ):
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
        for level in range(
            state["dwt_depth_ho"] + 1, state["dwt_depth_ho"] + state["dwt_depth"] + 1
        ):
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
    assert_level_constraint(state, "qindex", qindex)  ## Not in spec

    slice_quantizers(state, qindex)

    for transform in ["y_transform", "c1_transform", "c2_transform"]:
        length = state["slice_size_scaler"] * read_uint_lit(state, 1)
        state["bits_left"] = 8 * length
        if state["dwt_depth_ho"] == 0:
            slice_band(state, transform, 0, "LL", sx, sy)
            for level in range(1, state["dwt_depth"] + 1):
                for orient in ["HL", "LH", "HH"]:
                    slice_band(state, transform, level, orient, sx, sy)
        else:
            slice_band(state, transform, 0, "L", sx, sy)
            for level in range(1, state["dwt_depth_ho"] + 1):
                slice_band(state, transform, level, "H", sx, sy)
            for level in range(
                state["dwt_depth_ho"] + 1,
                state["dwt_depth_ho"] + state["dwt_depth"] + 1,
            ):
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
    # NB: For historical reasons, we use a dict not an array in this
    # implementation.
    ### state["quantizer"] = new_array(state["dwt_depth_ho"] + state["dwt_depth"] + 1)
    state["quantizer"] = {}  ## Not in spec
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
        for level in range(
            state["dwt_depth_ho"] + 1, state["dwt_depth_ho"] + state["dwt_depth"] + 1
        ):
            state["quantizer"][level] = {}
            for orient in ["HL", "LH", "HH"]:
                qval = max(qindex - state["quant_matrix"][level][orient], 0)
                state["quantizer"][level][orient] = qval


@ref_pseudocode
def slice_band(state, transform, level, orient, sx, sy):
    """(13.5.6.3)"""
    if transform == "y_transform":
        comp = "Y"
    elif transform == "c1_transform":
        comp = "C1"
    elif transform == "c2_transform":
        comp = "C2"

    qi = state["quantizer"][level][orient]

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
            state[transform][level][orient][y][x] = inverse_quant(val, qi)


@ref_pseudocode
def color_diff_slice_band(state, level, orient, sx, sy):
    """(13.5.6.4)"""
    qi = state["quantizer"][level][orient]

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
            val = read_sintb(state)
            state["c1_transform"][level][orient][y][x] = inverse_quant(val, qi)
            val = read_sintb(state)
            state["c2_transform"][level][orient][y][x] = inverse_quant(val, qi)
