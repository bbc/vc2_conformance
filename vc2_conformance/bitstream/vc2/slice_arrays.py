"""
Transformations of the VC-2 pseudo-code which read slice structures from a VC-2
bitstream.

The implementation is based on the definitions from the VC-2 specification but
differs slightly in some places:

* To avoid performance overheads relating to Python object creation, a single
  'flat' context dictionary (;py:class:`LDSliceArray` and
  ;py:class:`HQSliceArray`) is used to hold all values associated with
  consecutive slices in the bitstream.
* Complications in the specification related to the need to later perform a
  wavelet transform (e.g. collecting and organising if coefficients) are
  omitted.
"""

from contextlib import contextmanager

from vc2_conformance.math import intlog2

from vc2_conformance.parse_code_functions import (
    is_ld_picture,
    is_hq_picture,
    is_ld_fragment,
    is_hq_fragment,
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

from vc2_conformance.bitstream.vc2.fixeddicts import (
    SliceArrayParameters,
    LDSliceArray,
    HQSliceArray,
)

__all__ = [
    "transform_data",
    "fragment_data",
    
    "slice",
    "ld_slice",
    "hq_slice",
    
    "slice_band",
    "color_diff_slice_band",
    
    "slice_array",
]


################################################################################
# (13) Transform data syntax
################################################################################


def transform_data(serdes, state):
    """(13.5.2)"""
    # Transform data not captured here
    #state["y_transform"] = initialize_wavelet_data(state, "Y")
    #state["c1_transform"] = initialize_wavelet_data(state, "C1")
    #state["c2_transform"] = initialize_wavelet_data(state, "C2")
    
    with slice_array(serdes, state):
        for sy in range(state["slices_y"]):
            for sx in range(state["slices_x"]):
                slice(serdes, state, sx, sy)
    
    # Transform data not captured here
    #if using_dc_prediction(state):
    #    if state["dwt_depth_ho"] == 0:
    #        dc_prediction(state["y_transform"][0]["LL"])
    #        dc_prediction(state["c1_transform"][0]["LL"])
    #        dc_prediction(state["c2_transform"][0]["LL"])
    #    else:
    #        dc_prediction(state["y_transform"][0]["L"])
    #        dc_prediction(state["c1_transform"][0]["L"])
    #        dc_prediction(state["c2_transform"][0]["L"])

def slice(serdes, state, sx, sy):
    """(13.5.2)"""
    # Errata: check for both picture and fragment types
    if is_ld_picture(state) or is_ld_fragment(state):
        ld_slice(serdes, state, sx, sy)
    elif is_hq_picture(state) or is_hq_fragment(state):
        hq_slice(serdes, state, sx, sy)

def ld_slice(serdes, state, sx, sy):
    """(13.5.3.1)"""
    slice_bits_left = 8*slice_bytes(state, sx, sy)
    
    qindex = serdes.nbits("qindex", 7)
    slice_bits_left -= 7
    
    # Not needed
    #slice_quantizers(state, qindex)
    
    length_bits = intlog2((8 * slice_bytes(state, sx, sy)) - 7)
    slice_y_length = serdes.nbits("slice_y_length", length_bits)
    slice_bits_left -= length_bits
    
    # The following statement is not part of spec, here to ensure robustness in
    # the presence of invalid bitstreams
    if slice_y_length > slice_bits_left:
        slice_y_length = slice_bits_left
    
    serdes.bounded_block_begin(slice_y_length)
    if state["dwt_depth_ho"] == 0:
        # Errata: standard says 'luma_slice_band(state, 0, "LL", sx, sy)'
        slice_band(serdes, state, "y_transform", 0, "LL", sx, sy)
        for level in range(1, state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                slice_band(serdes, state, "y_transform", level, orient, sx, sy)
    else:
        # Errata: standard says 'luma_slice_band(state, 0, "L", sx, sy)'
        slice_band(serdes, state, "y_transform", 0, "L", sx, sy)
        for level in range(1, state["dwt_depth_ho"] + 1):
            slice_band(serdes, state, "y_transform", level, "H", sx, sy)
        for level in range(state["dwt_depth_ho"] + 1, 
                           state["dwt_depth_ho"] + state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                slice_band(serdes, state, "y_transform", level, orient, sx, sy)
    serdes.bounded_block_end("y_block_padding")
    
    slice_bits_left -= slice_y_length
    
    # Errata: The standard shows only 2D transform slices being read
    serdes.bounded_block_begin(slice_bits_left)
    if state["dwt_depth_ho"] == 0:
        color_diff_slice_band(serdes, state, 0, "LL", sx, sy)
        for level in range(1, state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                color_diff_slice_band(serdes, state, level, orient, sx, sy)
    else:
        # Errata: standard says 'luma_slice_band(state, 0, "L", sx, sy)'
        color_diff_slice_band(serdes, state, 0, "L", sx, sy)
        for level in range(1, state["dwt_depth_ho"] + 1):
            color_diff_slice_band(serdes, state, level, "H", sx, sy)
        for level in range(state["dwt_depth_ho"] + 1, 
                           state["dwt_depth_ho"] + state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                color_diff_slice_band(serdes, state, level, orient, sx, sy)
    serdes.bounded_block_end("c_block_padding")



def hq_slice(serdes, state, sx, sy):
    """(13.5.4)"""
    serdes.bytes("prefix_bytes", state["slice_prefix_bytes"])
    
    qindex = serdes.nbits("qindex", 8)
    
    # Not needed
    #slice_quantizers(state, qindex)
    
    for component in ["y", "c1", "c2"]:
        length = state["slice_size_scaler"] * serdes.nbits("slice_{}_length".format(component), 8)
        
        transform = "{}_transform".format(component)
        serdes.bounded_block_begin(8*length)
        if state["dwt_depth_ho"] == 0:
            slice_band(serdes, state, transform, 0, "LL", sx, sy)
            for level in range(1, state["dwt_depth"] + 1):
                for orient in ["HL", "LH", "HH"]:
                    slice_band(serdes, state, transform, level, orient, sx, sy)
        else:
            slice_band(serdes, state, transform, 0, "L", sx, sy)
            for level in range(1, state["dwt_depth_ho"] + 1):
                slice_band(serdes, state, transform, level, "H", sx, sy)
            for level in range(state["dwt_depth_ho"] + 1,
                               state["dwt_depth_ho"] + state["dwt_depth"] + 1):
                for orient in ["HL", "LH", "HH"]:
                    slice_band(serdes, state, transform, level, orient, sx, sy)
        serdes.bounded_block_end("{}_block_padding".format(component))

def slice_band(serdes, state, transform, level, orient, sx, sy):
    """(13.5.6.3) Read and dequantize a subband in a slice."""
    # These values evaulated in the loop definition in the spec, moving them
    # here saves a lot of computation
    y1 = slice_top(state, sy, "Y", level)
    y2 = slice_bottom(state, sy, "Y", level)
    x1 = slice_left(state, sx, "Y", level)
    x2 = slice_right(state, sx, "Y", level)
    
    for y in range(y1, y2):
        for x in range(x1, x2):
            val = serdes.sint(transform)
            
            # Not needed
            #qi = state.quantizer[level][orient]
            #transform[level][orient][y][x] = inverse_quant(val, qi)

def color_diff_slice_band(serdes, state, level, orient, sx, sy):
    """(13.5.6.4) Read and dequantize interleaved color difference subbands in a slice."""
    # These values evaulated in the loop definition in the spec, moving them
    # here saves a lot of computation
    y1 = slice_top(state, sy, "C1", level)
    y2 = slice_bottom(state, sy, "C1", level)
    x1 = slice_left(state, sx, "C1", level)
    x2 = slice_right(state, sx, "C1", level)
    
    # Not needed
    #qi = state.quantizer[level][orient]
    for y in range(y1, y2):
        for x in range(x1, x2):
            # Not needed
            #qi = state.quantizer[level][orient]
            
            val = serdes.sint("c1_transform")
            # Not needed
            #state.c1_transform[level][orient][y][x] = inverse_quant(val, qi)
            
            val = serdes.sint("c2_transform")
            # Not needed
            #state.c2_transform[level][orient][y][x] = inverse_quant(val, qi)


################################################################################
# (14.4) Fragment data
################################################################################

def fragment_data(serdes, state):
    """(14.4) Unpack and dequantize transform data from a fragment."""
    with slice_array(serdes, state,
                     state["fragment_x_offset"],
                     state["fragment_y_offset"],
                     state["fragment_slice_count"]):
        # Errata: In the spec this loop goes from 0 to fragment_slice_count
        # inclusive but should be fragment_slice_count *exclusive (as below)
        for s in range(state["fragment_slice_count"]):
            state["slice_x"] = (
                ((state["fragment_y_offset"] * state["slices_x"]) +
                 state["fragment_x_offset"] + s) % state["slices_x"]
            )
            state["slice_y"] = (
                ((state["fragment_y_offset"] * state["slices_x"]) +
                 state["fragment_x_offset"] + s) // state["slices_x"]
            )
            slice(serdes, state, state["slice_x"], state["slice_y"])
            
            # Not needed
            #state["fragment_slices_received"] += 1
            #
            #if state["fragment_slices_received"] == (state["slice_x"] * state["slice_y"]):
            #    state["fragmented_picture_done"] = True
            #    if using_dc_prediction(state):
            #        if state["dwt_depth_ho"] == 0:
            #            dc_prediction(state["y_transform"][0][LL])
            #            dc_prediction(state["c1_transform"][0][LL])
            #            dc_prediction(state["c2_transform"][0][LL])
            #        else:
            #            dc_prediction(state["y_transform"][0][L])
            #            dc_prediction(state["c1_transform"][0][L])
            #            dc_prediction(state["c2_transform"][0][L])


################################################################################
# Slice array begin/end methods (not part of spec)
################################################################################

@contextmanager
def slice_array(serdes, state, start_sx=0, start_sy=0, slice_count=None):
    """
    Not part of spec. Initialises a :py:class:`LDSliceArray` or
    :py:class:`HQSliceArray` (and its inner computed values).
    """
    if slice_count is None:
        slice_count = state["slices_x"] * state["slices_y"]
    
    parameters = SliceArrayParameters(
        slices_x=state["slices_x"],
        slices_y=state["slices_y"],
        start_sx=start_sx,
        start_sy=start_sy,
        slice_count=slice_count,
        dwt_depth=state["dwt_depth"],
        dwt_depth_ho=state["dwt_depth_ho"],
        luma_width=state["luma_width"],
        luma_height=state["luma_height"],
        color_diff_width=state["color_diff_width"],
        color_diff_height=state["color_diff_height"],
    )
    
    if is_ld_picture(state) or is_ld_fragment(state):
        serdes.subcontext_enter("ld_slice_array")
        serdes.set_context_type(LDSliceArray)
        serdes.computed_value("_parameters", parameters)
        serdes.computed_value("_slice_bytes_numerator", state["slice_bytes_numerator"])
        serdes.computed_value("_slice_bytes_denominator", state["slice_bytes_denominator"])
        serdes.declare_list("slice_y_length")
        serdes.declare_list("y_block_padding")
        serdes.declare_list("c_block_padding")
    elif is_hq_picture(state) or is_hq_fragment(state):
        serdes.subcontext_enter("hq_slice_array")
        serdes.set_context_type(HQSliceArray)
        serdes.computed_value("_parameters", parameters)
        serdes.computed_value("_slice_prefix_bytes", state["slice_prefix_bytes"])
        serdes.computed_value("_slice_size_scaler", state["slice_size_scaler"])
        serdes.declare_list("prefix_bytes")
        serdes.declare_list("slice_y_length")
        serdes.declare_list("slice_c1_length")
        serdes.declare_list("slice_c2_length")
        serdes.declare_list("y_block_padding")
        serdes.declare_list("c1_block_padding")
        serdes.declare_list("c2_block_padding")
    
    serdes.declare_list("qindex")
    serdes.declare_list("y_transform")
    serdes.declare_list("c1_transform")
    serdes.declare_list("c2_transform")
    
    yield
    
    serdes.subcontext_leave()
