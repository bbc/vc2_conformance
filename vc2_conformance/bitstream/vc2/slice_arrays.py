"""
Token-emitting generators which read consecutive slice structures from a VC-2
bitstream.

The implementation is loosely based around the definitions from the VC-2
specification but differs in some places:

* To avoid performance overheads relating to Python object creation, the simple
  flat structures defined in ;py:class:`LDSliceArray` and
  ;py:class:`HQSliceArray` are used.
* Complications in the specification related to the need to later perform a
  wavelet transform (e.g. collecting and organising if coefficients) are
  omitted.

"""

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

from vc2_conformance.bitstream.generator_io import TokenTypes

from vc2_conformance.bitstream.vc2.structured_dicts import (
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
    
    "slice_array_begin",
    "slice_array_end",
]


################################################################################
# (13) Transform data syntax
################################################################################


def transform_data(state):
    """(13.5.2)"""
    # Transform data not captured here
    #state["y_transform"] = initialize_wavelet_data(state, "Y")
    #state["c1_transform"] = initialize_wavelet_data(state, "C1")
    #state["c2_transform"] = initialize_wavelet_data(state, "C2")
    
    yield (TokenTypes.use, slice_array_begin(state), None)
    
    for sy in range(state["slices_y"]):
        for sx in range(state["slices_x"]):
            yield (TokenTypes.use, slice(state, sx, sy), None)
    
    yield (TokenTypes.use, slice_array_end(state), None)
    
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

def slice(state, sx, sy):
    """(13.5.2)"""
    # Errata: check for both picture and fragment types
    if is_ld_picture(state) or is_ld_fragment(state):
        # NB: Return generator here (faster than a 'use' token)
        return ld_slice(state, sx, sy)
    elif is_hq_picture(state) or is_hq_fragment(state):
        # NB: Return generator here (faster than a 'use' token)
        return hq_slice(state, sx, sy)

def ld_slice(state, sx, sy):
    """(13.5.3.1)"""
    slice_bits_left = 8*slice_bytes(state, sx, sy)
    
    qindex = (yield (TokenTypes.nbits, 7, "qindex"))
    slice_bits_left -= 7
    
    # Not needed
    #slice_quantizers(state, qindex)
    
    length_bits = intlog2((8 * slice_bytes(state, sx, sy)) - 7)
    slice_y_length = (yield (TokenTypes.nbits, length_bits, "slice_y_length"))
    slice_bits_left -= length_bits
    
    # The following statement is not part of spec, here to ensure robustness in
    # the presence of invalid bitstreams
    if slice_y_length > slice_bits_left:
        slice_y_length = slice_bits_left
    
    yield (TokenTypes.bounded_block_begin, slice_y_length, None)
    if state["dwt_depth_ho"] == 0:
        # Errata: standard says 'luma_slice_band(state, 0, "LL", sx, sy)'
        yield (TokenTypes.use, slice_band(state, "y_transform", 0, "LL", sx, sy), None)
        for level in range(1, state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                yield (TokenTypes.use, slice_band(state, "y_transform", level, orient, sx, sy), None)
    else:
        # Errata: standard says 'luma_slice_band(state, 0, "L", sx, sy)'
        yield (TokenTypes.use, slice_band(state, "y_transform", 0, "L", sx, sy), None)
        for level in range(1, state["dwt_depth_ho"] + 1):
            yield (TokenTypes.use, slice_band(state, "y_transform", level, "H", sx, sy), None)
        for level in range(state["dwt_depth_ho"] + 1, 
                           state["dwt_depth_ho"] + state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                yield (TokenTypes.use, slice_band(state, "y_transform", level, orient, sx, sy), None)
    yield (TokenTypes.bounded_block_end, None, "y_block_padding")
    
    slice_bits_left -= slice_y_length
    
    # Errata: The standard shows only 2D transform slices being read
    yield (TokenTypes.bounded_block_begin, slice_bits_left, None)
    if state["dwt_depth_ho"] == 0:
        yield (TokenTypes.use, color_diff_slice_band(state, 0, "LL", sx, sy), None)
        for level in range(1, state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                yield (TokenTypes.use, color_diff_slice_band(state, level, orient, sx, sy), None)
    else:
        # Errata: standard says 'luma_slice_band(state, 0, "L", sx, sy)'
        yield (TokenTypes.use, color_diff_slice_band(state, 0, "L", sx, sy), None)
        for level in range(1, state["dwt_depth_ho"] + 1):
            yield (TokenTypes.use, color_diff_slice_band(state, level, "H", sx, sy), None)
        for level in range(state["dwt_depth_ho"] + 1, 
                           state["dwt_depth_ho"] + state["dwt_depth"] + 1):
            for orient in ["HL", "LH", "HH"]:
                yield (TokenTypes.use, color_diff_slice_band(state, level, orient, sx, sy), None)
    yield (TokenTypes.bounded_block_end, None, "c_block_padding")



def hq_slice(state, sx, sy):
    """(13.5.4)"""
    yield (TokenTypes.bytes, state["slice_prefix_bytes"], "prefix_bytes")
    
    qindex = (yield (TokenTypes.nbits, 8, "qindex"))
    
    # Not needed
    #slice_quantizers(state, qindex)
    
    for component in ["y", "c1", "c2"]:
        length = state["slice_size_scaler"] * (yield (TokenTypes.nbits, 8, "slice_{}_length".format(component)))
        
        transform = "{}_transform".format(component)
        yield (TokenTypes.bounded_block_begin, 8*length, None)
        if state["dwt_depth_ho"] == 0:
            yield (TokenTypes.use, slice_band(state, transform, 0, "LL", sx, sy), None)
            for level in range(1, state["dwt_depth"] + 1):
                for orient in ["HL", "LH", "HH"]:
                    yield (TokenTypes.use, slice_band(state, transform, level, orient, sx, sy), None)
        else:
            yield (TokenTypes.use, slice_band(state, transform, 0, "L", sx, sy), None)
            for level in range(1, state["dwt_depth_ho"] + 1):
                yield (TokenTypes.use, slice_band(state, transform, level, "H", sx, sy), None)
            for level in range(state["dwt_depth_ho"] + 1,
                               state["dwt_depth_ho"] + state["dwt_depth"] + 1):
                for orient in ["HL", "LH", "HH"]:
                    yield (TokenTypes.use, slice_band(state, transform, level, orient, sx, sy), None)
        yield (TokenTypes.bounded_block_end, None, "{}_block_padding".format(component))

def slice_band(state, transform, level, orient, sx, sy):
    """(13.5.6.3) Read and dequantize a subband in a slice."""
    for y in range(slice_top(state, sy, "Y", level), slice_bottom(state, sy, "Y", level)):
        for x in range(slice_left(state, sx, "Y", level), slice_right(state, sx, "Y", level)):
            val = (yield (TokenTypes.sint, None, transform))
            
            # Not needed
            #qi = state.quantizer[level][orient]
            #transform[level][orient][y][x] = inverse_quant(val, qi)

def color_diff_slice_band(state, level, orient, sx, sy):
    """(13.5.6.4) Read and dequantize interleaved color difference subbands in a slice."""
    # Not needed
    #qi = state.quantizer[level][orient]
    for y in range(slice_top(state, sy, "C1", level), slice_bottom(state, sy, "C1", level)):
        for x in range(slice_left(state, sx, "C1", level), slice_right(state, sx, "C1", level)):
            # Not needed
            #qi = state.quantizer[level][orient]
            
            val = (yield (TokenTypes.sint, None, "c1_transform"))
            # Not needed
            #state.c1_transform[level][orient][y][x] = inverse_quant(val, qi)
            
            val = (yield (TokenTypes.sint, None, "c2_transform"))
            # Not needed
            #state.c2_transform[level][orient][y][x] = inverse_quant(val, qi)


################################################################################
# (14.4) Fragment data
################################################################################

def fragment_data(state):
    """(14.4) Unpack and dequantize transform data from a fragment."""
    yield (TokenTypes.use, slice_array_begin(
        state,
        state["fragment_x_offset"],
        state["fragment_y_offset"],
        state["fragment_slice_count"],
    ), None)
    
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
        yield (TokenTypes.use, slice(state, state["slice_x"], state["slice_y"]), None)
        
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
    
    yield (TokenTypes.use, slice_array_end(state), None)


################################################################################
# Slice array begin/end methods (not part of spec)
################################################################################

def slice_array_begin(state, start_sx=0, start_sy=0, slice_count=None):
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
        yield (TokenTypes.nested_context_enter, None, "ld_slice_array")
        yield (TokenTypes.declare_context_type, LDSliceArray, None)
        yield (TokenTypes.computed_value, parameters, "_parameters")
        yield (TokenTypes.computed_value, state["slice_bytes_numerator"], "_slice_bytes_numerator")
        yield (TokenTypes.computed_value, state["slice_bytes_denominator"], "_slice_bytes_denominator")
        yield (TokenTypes.declare_list, None, "slice_y_length")
        yield (TokenTypes.declare_list, None, "y_block_padding")
        yield (TokenTypes.declare_list, None, "c_block_padding")
    elif is_hq_picture(state) or is_hq_fragment(state):
        yield (TokenTypes.nested_context_enter, None, "hq_slice_array")
        yield (TokenTypes.declare_context_type, HQSliceArray, None)
        yield (TokenTypes.computed_value, parameters, "_parameters")
        yield (TokenTypes.computed_value, state["slice_prefix_bytes"], "_slice_prefix_bytes")
        yield (TokenTypes.computed_value, state["slice_size_scaler"], "_slice_size_scaler")
        yield (TokenTypes.declare_list, None, "prefix_bytes")
        yield (TokenTypes.declare_list, None, "slice_y_length")
        yield (TokenTypes.declare_list, None, "slice_c1_length")
        yield (TokenTypes.declare_list, None, "slice_c2_length")
        yield (TokenTypes.declare_list, None, "y_block_padding")
        yield (TokenTypes.declare_list, None, "c1_block_padding")
        yield (TokenTypes.declare_list, None, "c2_block_padding")
    
    yield (TokenTypes.declare_list, None, "qindex")
    yield (TokenTypes.declare_list, None, "y_transform")
    yield (TokenTypes.declare_list, None, "c1_transform")
    yield (TokenTypes.declare_list, None, "c2_transform")


def slice_array_end(state):
    yield (TokenTypes.nested_context_leave, None, None)
