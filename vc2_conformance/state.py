"""
:py:class:`vc2_conformance.state.State`
=======================================

A :py:mod:`fixeddict` for the 'state' object used by the pseudo code in the
VC-2 spec.

"""

from vc2_conformance._string_formatters import Hex

from vc2_conformance.tables import ParseCodes, WaveletFilters

from vc2_conformance.fixeddict import fixeddict, Entry

__all__ = [
    "State",
]

State = fixeddict(
    "State",
    
    # (10.5.1) parse_info
    Entry("parse_code", enum=ParseCodes, formatter=Hex(2)),
    Entry("next_parse_offset"),
    Entry("previous_parse_offset"),
    
    # (11.2.1) parse_parameters
    Entry("major_version"),
    Entry("minor_version"),
    Entry("profile"),
    Entry("level"),
    
    # (11.6.2) picture_dimensions
    Entry("luma_width"),
    Entry("luma_height"),
    Entry("color_diff_width"),
    Entry("color_diff_height"),
    
    # (11.6.3) video_depth
    Entry("luma_depth"),
    Entry("color_diff_depth"),
    
    # (12.2) picture_header and (14.2) fragment_header
    Entry("picture_number"),
    
    # (12.4.1) transform_parameters
    Entry("wavelet_index", enum=WaveletFilters),
    Entry("dwt_depth"),
    
    # (12.4.4.1) extended_transform_parameters
    Entry("wavelet_index_ho", enum=WaveletFilters),
    Entry("dwt_depth_ho"),
    
    # (12.4.5.2) slice_parameters
    Entry("slices_x"),
    Entry("slices_y"),
    Entry("slice_bytes_numerator"),
    Entry("slice_bytes_denominator"),
    Entry("slice_prefix_bytes"),
    Entry("slice_size_scaler"),
    
    # (12.4.5.3) quant_matrix
    Entry("quant_matrix"),
    
    # (14.2) fragment_header
    Entry("fragment_data_length"),
    Entry("fragment_slice_count"),
    Entry("fragment_x_offset"),
    Entry("fragment_y_offset"),
    
    # (14.4) fragment_data
    Entry("slice_x"),
    Entry("slice_y"),
    
    # (A.2.1) read_byte etc.
    Entry("next_bit"),
    Entry("current_byte"),
    
    # The following values are not part of the VC-2 spec but are used by
    # vc2_conformance.decoder to interface with the outside world (which is
    # beyond the scope of the VC-2 spec).
    
    # (A.2.1) read_byte: The Python file-like object from which the bitstream
    # will be read by read_byte.
    Entry("_file"),
)
"""
The global state variable type.
"""
