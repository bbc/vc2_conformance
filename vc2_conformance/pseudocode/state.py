"""
A :py:mod:`~vc2_conformance.fixeddict` for the 'state' object used by the
pseudocode in the VC-2 spec.
"""

from vc2_conformance.string_formatters import Hex

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
    Entry(
        "video_parameters",
        help_type=":py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`",
        help="Set by (10.4.1) parse_sequence",
    ),
    # (10.5.1) parse_info
    Entry(
        "parse_code",
        enum=ParseCodes,
        formatter=Hex(2),
        help_type=":py:class:`~vc2_data_tables.ParseCodes`",
        help="Set by (10.5.1) parse_info",
    ),
    Entry("next_parse_offset", help_type="int", help="Set by (10.5.1) parse_info"),
    Entry("previous_parse_offset", help_type="int", help="Set by (10.5.1) parse_info"),
    # (11.1) sequence_header
    Entry(
        "picture_coding_mode",
        help_type=":py:class:`~vc2_data_tables.PictureCodingModes`",
        help="Set by (11.1) sequence_header",
    ),
    # (11.2.1) parse_parameters
    Entry("major_version", help_type="int", help="Set by (11.2.1) parse_parameters"),
    Entry("minor_version", help_type="int", help="Set by (11.2.1) parse_parameters"),
    Entry(
        "profile",
        enum=Profiles,
        help_type=":py:class:`~vc2_data_tables.Profiles`",
        help="Set by (11.2.1) parse_parameters",
    ),
    Entry(
        "level",
        enum=Levels,
        help_type=":py:class:`~vc2_data_tables.Profiles`",
        help="Set by (11.2.1) parse_parameters",
    ),
    # (11.6.2) picture_dimensions
    Entry("luma_width", help_type="int", help="Set by (11.6.2) picture_dimensions"),
    Entry("luma_height", help_type="int", help="Set by (11.6.2) picture_dimensions"),
    Entry(
        "color_diff_width", help_type="int", help="Set by (11.6.2) picture_dimensions"
    ),
    Entry(
        "color_diff_height", help_type="int", help="Set by (11.6.2) picture_dimensions"
    ),
    # (11.6.3) video_depth
    Entry("luma_depth", help_type="int", help="Set by (11.6.3) video_depth"),
    Entry("color_diff_depth", help_type="int", help="Set by (11.6.3) video_depth"),
    # (12.2) picture_header and (14.2) fragment_header
    Entry(
        "picture_number",
        help_type="int",
        help="Set by (12.2) picture_header and (14.2) fragment_header",
    ),
    # (12.4.1) transform_parameters
    Entry(
        "wavelet_index",
        enum=WaveletFilters,
        help_type=":py:class:`~vc2_data_tables.WaveletFilters`",
        help="Set by (12.4.1) transform_parameters",
    ),
    Entry("dwt_depth", help_type="int", help="Set by (12.4.1) transform_parameters"),
    # (12.4.4.1) extended_transform_parameters
    Entry(
        "wavelet_index_ho",
        enum=WaveletFilters,
        help_type=":py:class:`~vc2_data_tables.WaveletFilters`",
        help="Set by (12.4.4.1) extended_transform_parameters",
    ),
    Entry("dwt_depth_ho"),
    Entry(
        "dwt_depth_ho",
        help_type="int",
        help="Set by (12.4.4.1) extended_transform_parameters",
    ),
    # (12.4.5.2) slice_parameters
    Entry("slices_x", help_type="int", help="Set by (12.4.5.2) slice_parameters"),
    Entry("slices_y", help_type="int", help="Set by (12.4.5.2) slice_parameters"),
    Entry(
        "slice_bytes_numerator",
        help_type="int",
        help="Set by (12.4.5.2) slice_parameters",
    ),
    Entry(
        "slice_bytes_denominator",
        help_type="int",
        help="Set by (12.4.5.2) slice_parameters",
    ),
    Entry(
        "slice_prefix_bytes", help_type="int", help="Set by (12.4.5.2) slice_parameters"
    ),
    Entry(
        "slice_size_scaler", help_type="int", help="Set by (12.4.5.2) slice_parameters"
    ),
    # (12.4.5.3) quant_matrix
    Entry(
        "quant_matrix",
        help_type="{level: {orient: int, ...}, ...}",
        help="Set by (12.4.5.3) quant_matrix",
    ),
    # (13.5.5) slice_quantizers
    Entry(
        "quantizer",
        help_type="{level: {orient: int, ...}, ...}",
        help="Set by (13.5.5) slice_quantizers",
    ),
    # (13.5.6.3) slice_band and (13.5.6.4) color_diff_slice_band
    Entry(
        "y_transform",
        help_type="{level: {orient: [[int, ...], ...], ...}, ...}",
        help="""
            Set by (13.5.6.3) slice_band. The dequantised luma transform data
            read from the bitstream. A 2D array for each subband, indexed as
            [level][orient][y][x].
        """,
    ),
    Entry(
        "c1_transform",
        help_type="{level: {orient: [[int, ...], ...], ...}, ...}",
        help="""
            Set by (13.5.6.3) slice_band and (13.5.6.4)
            color_diff_slice_band. The dequantised color difference 1 transform
            data read from the bitstream. A 2D array for each subband, indexed
            as [level][orient][y][x].
        """,
    ),
    Entry(
        "c2_transform",
        help_type="{level: {orient: [[int, ...], ...], ...}, ...}",
        help="""
            Set by (13.5.6.3) slice_band and (13.5.6.4)
            color_diff_slice_band. The dequantised color difference 2 transform
            data read from the bitstream. A 2D array for each subband, indexed
            as [level][orient][y][x].
        """,
    ),
    # (14.2) fragment_header
    Entry(
        "fragment_data_length", help_type="int", help="Set by (14.2) fragment_header"
    ),
    Entry(
        "fragment_slice_count", help_type="int", help="Set by (14.2) fragment_header"
    ),
    Entry("fragment_x_offset", help_type="int", help="Set by (14.2) fragment_header"),
    Entry("fragment_y_offset", help_type="int", help="Set by (14.2) fragment_header"),
    # (14.4) fragment_data
    Entry(
        "fragment_slices_received", help_type="int", help="Set by (14.4) fragment_data"
    ),
    Entry(
        "fragmented_picture_done", help_type="int", help="Set by (14.4) fragment_data"
    ),
    # (15.2) picture_decode
    Entry(
        "current_picture",
        help_type=(
            "{'pic_num': int, "
            "'Y': [[int, ...], ...], "
            "'C1': [[int, ...], ...], "
            "'C2': [[int, ...], ...]}"
        ),
        help="Set by (15.2) picture_decode, contains the decoded picture.",
    ),
    # (A.2.1) read_*
    Entry("next_bit", help_type="int", help="Set by (A.2.1) read_*"),
    Entry("current_byte", help_type="int", help="Set by (A.2.1) read_*"),
    # (A.4.2) bounded blocks
    Entry(
        "bits_left",
        help_type="int",
        help="Bits left in the current bounded block (A.4.2)",
    ),
    # The following values are not part of the VC-2 spec but are used by
    # vc2_conformance.decoder to interface with the outside world (which is
    # beyond the scope of the VC-2 spec).
    #
    # (10.4.1) parse_sequence related state
    Entry(
        "_generic_sequence_matcher",
        help_type=":py:class:`vc2_conformance.symbol_re.Matcher`",
        help="""
            Not in spec, used by :py:mod:`vc2_conformance.decoder`.
            A :py:class:`~vc2_conformance.symbol_re.Matcher` which checks that
            the sequence follows the specified general pattern of data units
            (10.4.1) (e.g. start with a sequence header, end with end of
            sequence).  Other matchers will test for, e.g. level-defined
            patterns.
        """,
    ),
    # (15.2) output_picture related state
    Entry(
        "_output_picture_callback",
        help_type=(
            "function("
            "{'pic_num': int, "
            "'Y': [[int, ...], ...], "
            "'C1': [[int, ...], ...], "
            "'C2': [[int, ...], ...]}, "
            ":py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`, "
            ":py:class:`~vc2_data_tables.PictureCodingModes`"
            ")"
        ),
        help="""
            Not in spec, used by :py:mod:`vc2_conformance.decoder`.
            A callback function to call when ``output_picture`` (15.2) is
            called. This callback (if defined) will be passed the picture,
            video parameters and picture coding mode.
        """,
    ),
    # (10.4.3) and (12.2)
    Entry(
        "_num_pictures_in_sequence",
        help_type="int",
        help="""
            Not in spec, used by :py:mod:`vc2_conformance.decoder`.
            (10.4.3) and (12.2) A counter of how many pictures have been
            encountered in the current sequence. Used to determine if all
            fields have been received (when pictures are fields) and that the
            earliest fields have an even picture number. Initialised in
            parse_sequence (10.4.1) and incremented in
            :py:func:`vc2_conformance.decoder.assertions.assert_picture_number_incremented_as_expected`,
            called in
            picture_header (12.2), and fragment_header (14.2).
        """,
    ),
    # (10.5.1) parse_info related state
    Entry(
        "_last_parse_info_offset",
        help_type="int",
        help="""
            Not in spec, used by :py:mod:`vc2_conformance.decoder`.
            (10.5.1) parse_info related state. The byte offset of the
            previously read parse_info block.
        """,
    ),
    # (11.1) sequence_header
    Entry(
        "_recorded_bytes",
        help_type=":py:class:`bytearray`",
        help="""
            Not in spec, used by :py:mod:`vc2_conformance.decoder`.
            (11.1) sequence_header requires that repeats must be byte-for-byte
            identical. To facilitate this, the
            :py:func:`vc2_conformance.decoder.io.record_bitstream_start`
            and :py:func:`vc2_conformance.decoder.io.record_bitstream_finish`
            functions are used to make a recording.  When this entry is absent,
            read_byte works as usual. If it is a :py:class:`bytearray`,
            whenever a byte has been completely read, it will be placed into
            this array.
        """,
    ),
    Entry(
        "_last_sequence_header_bytes",
        help_type=":py:class:`bytearray`",
        help="""
            Not in spec, used by :py:mod:`vc2_conformance.decoder`.
            (11.1) the bitstream bytes of the data which encoded the previous
            sequence_header in the sequence. Not present if no previous
            sequence_header has appeared.
        """,
    ),
    Entry(
        "_last_sequence_header_offset",
        help_type="int",
        help="""
            Not in spec, used by :py:mod:`vc2_conformance.decoder`.
            (11.1) the bitstream offset in bytes of the data which encoded the
            previous sequence_header in the sequence. Not present if no
            previous sequence_header has appeared.
        """,
    ),
    # (11.2.2) Version number constraint checking
    Entry(
        "_expected_major_version",
        help_type="int",
        help="""
            Not in spec, used by :py:mod:`vc2_conformance.decoder`. Used to
            record the expected major_version (11.2.1) for this sequence
            according to the constraints listed in (11.2.2). This field is set
            by
            :py:func:`~vc2_conformance.decoder.assertions.log_version_lower_bound`.
        """,
    ),
    # (12.2) picture_header and (14.2) fragment_header
    Entry(
        "_last_picture_number_offset",
        help_type="(byte offset, next bit)",
        help="""
            Not in spec, used by :py:mod:`vc2_conformance.decoder`.
            (12.2) picture_header and (14.2) fragment_header: The offset of the
            last picture number encountered in the sequence (or absent if no
            pictures have yet been encountered).
        """,
    ),
    Entry(
        "_last_picture_number",
        help_type="int",
        help="""
            Not in spec, used by :py:mod:`vc2_conformance.decoder`.
            (12.2) picture_header and (14.2) fragment_header: The last picture
            number encountered in the sequence (or absent if no pictures have
            yet been encountered).
        """,
    ),
    # (14) fragments
    Entry(
        "_picture_initial_fragment_offset",
        help_type="(byte offset, next bit)",
        help="""
            Not in spec, used by :py:mod:`vc2_conformance.decoder`.
            (14) The offset in the bitstream of the last fragment with
            fragment_slice_count==0.
        """,
    ),
    Entry(
        "_fragment_slices_remaining",
        help_type="int",
        help="""
            Not in spec, used by :py:mod:`vc2_conformance.decoder`.
            (14) The number of fragment slices which remain to be received in
            the current picture. Initialised to zero by parse_sequence
            (10.4.1), reset to the number of slices per picture by
            initialize_fragment_state (14.3) and decremented whenever a slice
            is received by fragment_data (14.4).
        """,
    ),
    # (A.2.1) read_byte
    Entry(
        "_file",
        help_type="file-like",
        help="""
            The Python file-like object from which the bitstream will be read
            by read_byte (A.2.1) .
        """,
    ),
    # (C.3) Level-related state
    Entry(
        "_level_sequence_matcher",
        help_type=":py:class:`vc2_conformance.symbol_re.Matcher`",
        help="""
            Not in spec, used by :py:mod:`vc2_conformance.decoder`.
            A :py:class:`~vc2_conformance.symbol_re.Matcher` which checks that
            the sequence follows the pattern dictated by the current level.
            Populated after the first (11.2.1) parse_parameters is encountered
            (and should therefore be ignored until that point).
        """,
    ),
    Entry(
        "_level_constrained_values",
        help_type="{key: value, ...}",
        help="""
            Not in spec, used by :py:mod:`vc2_conformance.decoder`.
            A dictionary which will be incrementally populated with values read or
            computed from the bitstream which are constrained by the level
            constraints table (see
            :py:data:`vc2_conformance.level_constraints.LEVEL_CONSTRAINTS` and
            :py:func:`vc2_conformance.decoder.assertions.assert_level_constraint`).
        """,
    ),
    help="""
        The global state variable type.

        Entries prefixed with an underscore (``_``) are not specified by the
        VC-2 pseudocode but may be used by the conformance software.
    """,
)


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
    Reset a :py:class:`~vc2_conformance.pseudocode.state.State` dictionary to only include
    values retained between sequences in a VC-2 stream. Modifies the dictionary
    in place.
    """
    for key in set(state.keys()) - set(retained_state_fields):
        del state[key]
