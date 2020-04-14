"""
:py:class:`vc2_conformance.state.State`
=======================================

A :py:mod:`fixeddict` for the 'state' object used by the pseudo code in the
VC-2 spec.

"""

from vc2_conformance._string_formatters import Hex

from vc2_data_tables import (
    ParseCodes,
    WaveletFilters,
    Profiles,
    Levels,
)

from vc2_conformance.fixeddict import fixeddict, Entry

__all__ = [
    "State",
    "reset_state",
]

State = fixeddict(
    "State",
    # (10.4.1) parse_sequence
    Entry("video_parameters"),
    # (10.5.1) parse_info
    Entry("parse_code", enum=ParseCodes, formatter=Hex(2)),
    Entry("next_parse_offset"),
    Entry("previous_parse_offset"),
    # (11.2.1) parse_parameters
    Entry("major_version"),
    Entry("minor_version"),
    Entry("profile", enum=Profiles),
    Entry("level", enum=Levels),
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
    # (13.5.5) slice_quantizers
    Entry("quantizer"),
    # (13.5.6.3) slice_band and (13.5.6.4) color_diff_slice_band: The transform
    # data read from the bitstream. Nested dictionaries of 2D arrays indexed as
    # [level][orient][y][x]
    Entry("y_transform"),
    Entry("c1_transform"),
    Entry("c2_transform"),
    # (14.2) fragment_header
    Entry("fragment_data_length"),
    Entry("fragment_slice_count"),
    Entry("fragment_x_offset"),
    Entry("fragment_y_offset"),
    # (14.4) fragment_data
    Entry("fragment_slices_received"),
    Entry("fragmented_picture_done"),
    Entry("slice_x"),
    Entry("slice_y"),
    # (15.2) picture_decode
    Entry("current_picture"),
    # (A.2.1) read_byte etc.
    Entry("next_bit"),
    Entry("current_byte"),
    # (A.4.2) bounded blocks
    Entry("bits_left"),
    # The following values are not part of the VC-2 spec but are used by
    # vc2_conformance.decoder to interface with the outside world (which is
    # beyond the scope of the VC-2 spec).
    # (10.4.1) parse_sequence related state
    # A vc2_conformance.symbol_re.Matcher which checks that the sequence
    # follows the specified general pattern of data units (other matchers will
    # test for, e.g. level-defined patterns).
    Entry("_generic_sequence_matcher"),
    # (10.4.999) output_picture related state
    # A callback function to call when output_picture is called. This callback
    # (if defined) will be passed the picture and video parameters as
    # arguments.
    Entry("_output_picture_callback"),
    # (10.4.3) and (12.2): A counter of how many pictures have been encountered
    # in the current sequence. Used to determine if all fields have been
    # received (when pictures are fields) and that the earliest fields have an
    # even picture number. Initialised in parse_sequence (10.4.1) and
    # incremented in assert_picture_number_incremented_as_expected, called in
    # picture_header (12.2), and fragment_header (14.2).
    Entry("_picture_coding_mode"),
    Entry("_num_pictures_in_sequence"),
    # (10.5.1) parse_info related state
    # The byte offset of the previously read parse_info block
    Entry("_last_parse_info_offset"),  # int (bytes)
    # (11.1) sequence_header requires that repeats must be byte-for-byte
    # identical. To facilitate this, the decode.io.record_bitstream_start and
    # decode.io.record_bitstream_finish functions are used to make a recording.
    # When the following variable is absent, read_byte works as usual.  If it
    # is a bytearray, whenever a byte has been completely read, it will be
    # placed into this array.
    Entry("_recorded_bytes"),
    # (11.1) the bitstream bytes and byte-offset of the data which encoded the
    # previous sequence_header in the sequence. Not present if no previous
    # sequence_header has appeared.
    Entry("_last_sequence_header_bytes"),
    Entry("_last_sequence_header_offset"),  # int (bytes)
    # (12.2) picture_header and (14.2) fragment_header: The last picture number
    # encountered in the sequence (or absent if no pictures have yet been
    # encountered).
    Entry("_last_picture_number_offset"),  # (int, int) tuple (byte offset, next bit)
    Entry("_last_picture_number"),
    # (14) The offset in the bitstream of the last fragment with
    # fragment_slice_count==0.
    Entry(
        "_picture_initial_fragment_offset"
    ),  # (int, int) tuple (byte offset, next bit)
    # (14) The number of fragment slices which remain to be received in the
    # current picture. Initialised to zero by parse_sequence (10.4.1), reset to
    # the number of slices per picture by initialize_fragment_state (14.3) and
    # decremented whenever a slice is receieved by fragment_data (14.4).
    Entry("_fragment_slices_remaining"),
    # (A.2.1) read_byte: The Python file-like object from which the bitstream
    # will be read by read_byte.
    Entry("_file"),
    # (C.3) Level-related state
    # A vc2_conformance.symbol_re.Matcher which checks that the sequence
    # follows the pattern dictated by the current level. Populated after the
    # first (11.2.1) parse_parameters is encountered (and should therefore be
    # ignored until that point).
    Entry("_level_sequence_matcher"),
    # A dictionary which will be incrementally populated with values read or
    # computed from the bitstream which are constrained by the level
    # constraints table (see
    # vc2_conformance.level_constraints.LEVEL_CONSTRAINTS and
    # vc2_conformance.decoder.assertions.assert_level_constraint).
    Entry("_level_constrained_values"),
)
"""
The global state variable type.
"""


retained_state_fields = [
    # The output_picture callback should remain so that subsequent sequences
    # trigger the same callback.
    "_output_picture_callback",
    # I/O state must be preserved to allow continuing to read the current file
    "next_bit",
    "current_byte",
    "_file",
    "_recorded_bytes",  # Not required in practice, here for consistency
]
"""
The list of fields in the :py:class:`State` dictionary which should be retained
between sequences in a stream.
"""


def reset_state(state):
    """
    Reset a :py:class:`~vc2_conformance.state.State` dictionary to only include
    values retained between sequences in a VC-2 stream. Modifies the dictionary
    in place.
    """
    for key in set(state.keys()) - set(retained_state_fields):
        del state[key]
