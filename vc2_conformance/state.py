"""
A :py:module:`structured_dict` for the 'state' object used by the pseudo code
in the VC-2 spec.
"""

from vc2_conformance._string_formatters import Hex

from vc2_conformance.tables import ParseCodes, WaveletFilters

from vc2_conformance.structured_dict import structured_dict, Value

__all__ = [
    "State",
]

@structured_dict
class State(object):
    """
    The global state variable type.
    """
    # (10.5.1) parse_info
    parse_code = Value(enum=ParseCodes, formatter=Hex(2))
    next_parse_offset = Value()
    previous_parse_offset = Value()
    
    # (11.2.1) parse_parameters
    major_version = Value()
    minor_version = Value()
    profile = Value()
    level = Value()
    
    # (11.6.2) picture_dimensions
    luma_width = Value()
    luma_height = Value()
    color_diff_width = Value()
    color_diff_height = Value()
    
    # (11.6.3) video_depth
    luma_depth = Value()
    color_diff_depth = Value()
    
    # (12.2) picture_header and (14.2) fragment_header
    picture_number = Value()
    
    # (12.4.1) transform_parameters
    wavelet_index = Value(enum=WaveletFilters)
    dwt_depth = Value()
    
    # (12.4.4.1) extended_transform_parameters
    wavelet_index_ho = Value(enum=WaveletFilters)
    dwt_depth_ho = Value()
    
    # (12.4.5.2) slice_parameters
    slices_x = Value()
    slices_y = Value()
    slice_bytes_numerator = Value()
    slice_bytes_denominator = Value()
    slice_prefix_bytes = Value()
    slice_size_scaler = Value()
    
    # (12.4.5.3) quant_matrix
    quant_matrix = Value()
    
    # (14.2) fragment_header
    fragment_data_length = Value()
    fragment_slice_count = Value()
    fragment_x_offset = Value()
    fragment_y_offset = Value()
    
    # (14.4) fragment_data
    slice_x = Value()
    slice_y = Value()
