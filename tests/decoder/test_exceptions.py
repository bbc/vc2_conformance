import pytest

from textwrap import dedent

from collections import OrderedDict

import vc2_data_tables as tables

from vc2_conformance._string_utils import wrap_paragraphs

from vc2_conformance._constraint_table import ValueSet

from vc2_conformance.decoder import exceptions


def test_known_parse_code_to_string():
    assert (
        exceptions.known_parse_code_to_string(tables.ParseCodes.end_of_sequence)
        == "end of sequence (0x10)"
    )


def test_known_profile_to_string():
    assert (
        exceptions.known_profile_to_string(tables.Profiles.high_quality,)
        == "high quality (3)"
    )


def test_known_wavelet_to_string():
    assert (
        exceptions.known_wavelet_to_string(tables.WaveletFilters.haar_with_shift,)
        == "Haar With Shift (4)"
    )


class TestExplainParseCodeSequenceStructureRestrictions(object):
    @pytest.mark.parametrize(
        "expected_parse_codes", [None, [], [tables.ParseCodes.end_of_sequence]]
    )
    def test_expected_end(self, expected_parse_codes):
        assert exceptions.explain_parse_code_sequence_structure_restrictions(
            tables.ParseCodes.end_of_sequence, expected_parse_codes, True,
        ) == (
            "The parse code end of sequence (0x10) was encountered "
            "but no further parse code expected."
        )

    def test_one_alternative(self):
        assert exceptions.explain_parse_code_sequence_structure_restrictions(
            tables.ParseCodes.end_of_sequence,
            [tables.ParseCodes.high_quality_picture],
            False,
        ) == (
            "The parse code end of sequence (0x10) was encountered "
            "but high quality picture (0xE8) expected."
        )

    def test_several_alternatives(self):
        assert exceptions.explain_parse_code_sequence_structure_restrictions(
            tables.ParseCodes.end_of_sequence,
            [
                tables.ParseCodes.sequence_header,
                tables.ParseCodes.high_quality_picture,
                tables.ParseCodes.high_quality_picture_fragment,
            ],
            False,
        ) == (
            "The parse code end of sequence (0x10) was encountered "
            "but sequence header (0x00) or "
            "high quality picture (0xE8) or "
            "high quality picture fragment (0xEC) expected."
        )

    def test_any_allowed_and_end_of_sequence(self):
        assert exceptions.explain_parse_code_sequence_structure_restrictions(
            None, None, False,
        ) == ("No further parse code was encountered " "but any parse code expected.")


def test_conformance_error_str():
    class TestError(exceptions.ConformanceError):
        def explain(self):
            return """
                A brief summary
                over several lines.

                A longer explanation follows.
            """

    e = TestError()
    assert str(e) == "A brief summary over several lines."


def test_bad_parse_code():
    e = exceptions.BadParseCode(0xABCD)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid parse code, 0xABCD, was provided to a parse info header
        (10.5.1).

        See (Table 10.1) for the list of allowed parse codes.

        Perhaps this bitstream conforms to an earlier or later version of the
        VC-2 standard?
    """
    )


def test_bad_parse_info_prefix():
    e = exceptions.BadParseInfoPrefix(0xAABBCCDD)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid prefix, 0xAABBCCDD, was encountered in a parse info block
        (10.5.1). The expected prefix is 0x42424344.

        Is the parse_info block byte aligned (10.5.1)?

        Did the preceeding data unit over- or under-run the expected length?
        For example, were any unused bits in a picture slice filled with the
        correct number of padding bits (A.4.2)?
    """
    )


def test_inconsistent_next_parse_offset():
    e = exceptions.InconsistentNextParseOffset(100, 15, 20,)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        Incorrect next_parse_offset value in parse info: got 15 bytes, expected
        20 bytes (10.5.1).

        The erroneous parse info block begins at bit offset 800 and is
        followed by the next parse info block at bit offset 960.

        Does the next_parse_offset include the 13 bytes of the parse info
        header?

        Is next_parse_offset given in bytes, not bits?
    """
    )

    assert dedent(e.bitstream_viewer_hint()) == dedent(
        """
        To view the erroneous parse info block:

            {cmd} {file} --offset 800 --after-context 144

        To view the following parse info block:

            {cmd} {file} --offset {offset} --after-context 144
    """
    )

    assert e.offending_offset() == 800


def test_missing_next_parse_offset():
    e = exceptions.MissingNextParseOffset(tables.ParseCodes.padding_data)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        A next_parse_offset value of zero was provided in a padding data
        (parse_code = 0x30) parse info block where a valid next_parse_offset
        value is mandatory (10.5.1).

        Does the next_parse_offset include the 13 bytes of the parse info
        header?
    """
    )


def test_invalid_next_parse_offset():
    e = exceptions.InvalidNextParseOffset(10)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        Invalid next_parse_offset value 10 found in parse info header (10.5.1).

        The next_parse_offset value must account for the 13 bytes taken by the
        parse info block. As a consequence this value must be strictly 13 or
        greater (except in circumstances where it may be omitted when it must
        be 0) (15.5.1).

        Does the next_parse_offset include the 13 bytes of the parse info
        header?
    """
    )


def test_non_zero_next_parse_offset_at_end_of_sequence():
    e = exceptions.NonZeroNextParseOffsetAtEndOfSequence(13)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        Non-zero next_parse_offset value, 13, in the parse info at the end of
        the sequence (10.5.1).

        Does the next_parse_offset incorrectly include an offset into an
        adjacent sequence?
    """
    )


def test_inconsistent_previous_parse_offset():
    e = exceptions.InconsistentPreviousParseOffset(100, 15, 20,)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        Incorrect previous_parse_offset value in parse info: got 15 bytes,
        expected 20 bytes (10.5.1).

        The erroneous parse info block begins at offset 960 bits and follows
        a parse info block at offset 800 bits.

        Does the previous_parse_offset include the 13 bytes of the parse info
        header?

        Is previous_parse_offset given in bytes, not bits?

        Was the previous_parse_offset incorrectly omitted after a data unit
        whose size was not initially known?

        Was this parse info block copied from another sequence without
        updating the previous_parse_offset?
    """
    )

    assert dedent(e.bitstream_viewer_hint()) == dedent(
        """
        To view the erroneous parse info block:

            {cmd} {file} --offset {offset} --after-context 144

        To view the proceeding parse info block:

            {cmd} {file} --offset 800 --after-context 144
    """
    )


def test_non_zero_previous_parse_offfset_at_start_of_sequence():
    e = exceptions.NonZeroPreviousParseOffsetAtStartOfSequence(100)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        Non-zero previous_parse_offset, 100, in the parse info at the start of
        a sequence (10.5.1).

        Was this parse info block copied from another stream without the
        previous_parse_offset being updated?

        Does this parse info block incorrectly include an offset into an
        adjacent sequence?
    """
    )


def test_sequence_header_changed_mid_sequence():
    e = exceptions.SequenceHeaderChangedMidSequence(100, b"\x00\xFF", 200, b"\x00\xBF",)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        Sequence header is not byte-for-byte identical to the previous sequence
        header in the same sequence (11.1).

        The previous sequence header begins at bit offset 800 and the current
        sequence header begins at bit offset 1600.

        This sequence header differs from its predecessor starting with bit 9.
        That is, bit offset 809 in the previous sequence header is different to
        bit offset 1609 in the current sequence header.

        Did the video format change without beginning a new sequence?

        Did the sequence header attempt to encode the same parameters in a
        different way (e.g. switching to a custom value rather than an
        equivalent preset)?
    """
    )

    assert dedent(e.bitstream_viewer_hint()) == dedent(
        """
        To view the previous sequence header

            {cmd} {file} --from-offset 800 --to-offset 815

        To view the current sequence header

            {cmd} {file} --from-offset 1600 --to-offset 1615
    """
    )

    assert e.offending_offset() == 1600


def test_bad_profile():
    e = exceptions.BadProfile(999)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid profile number, 999, was provided in the parse parameters
        (11.2.3).

        See (C.2) for the list of allowed profile numbers.

        Perhaps this bitstream conforms to an earlier or later version of
        the VC-2 standard?
    """
    )


def test_bad_level():
    e = exceptions.BadLevel(999)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid level number, 999, was provided in the parse parameters
        (11.2.3).

        See (C.3) or SMPTE ST 2042-2 'VC-2 Level Definitions' for details
        of the supported levels and their codes.

        Perhaps this bitstream conforms to an earlier or later version of
        the VC-2 standard?
    """
    )


def test_generic_invalid_sequence():
    e = exceptions.GenericInvalidSequence(
        tables.ParseCodes.high_quality_picture,
        [tables.ParseCodes.sequence_header],
        False,
    )

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        The current sequence does not match the structure defined for VC-2
        sequences in (10.4.1).

        The parse code high quality picture (0xE8) was encountered but sequence
        header (0x00) expected.

        Did the sequence begin with a non-sequence header data unit?
    """
    )


def test_level_invalid_sequence():
    e = exceptions.LevelInvalidSequence(
        tables.ParseCodes.high_quality_picture_fragment,
        [
            tables.ParseCodes.end_of_sequence,
            tables.ParseCodes.padding_data,
            tables.ParseCodes.auxiliary_data,
            tables.ParseCodes.high_quality_picture,
            tables.ParseCodes.low_delay_picture,
        ],
        False,
        tables.Levels.sub_sd,
    )

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        The current sequence does not match the structure required by the
        current level, 1, (SMPTE ST 2042-2:2017).

        Either pictures or picture fragments may be used in a stream, but not both.

        The parse code high quality picture fragment (0xEC) was encountered but
        end of sequence (0x10) or padding data (0x30) or auxiliary data (0x20)
        or high quality picture (0xE8) or low delay picture (0xC8) expected.
    """
    )


def test_parse_code_not_allowed_in_profile():
    e = exceptions.ParseCodeNotAllowedInProfile(
        tables.ParseCodes.high_quality_picture, tables.Profiles.low_delay,
    )

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        The parse code high quality picture (0xE8) is not allowed in the low
        delay (0) profile (C.2).
    """
    )


def test_value_not_allowed_in_level():
    e = exceptions.ValueNotAllowedInLevel(
        level_constrained_values=OrderedDict(
            [("level", 1), ("foo", "bar"), ("qux", "quo")]
        ),
        key="base_video_format",
        value=999,
        allowed_values=ValueSet((1, 6)),
    )

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        The base_video_format value 999 is not allowed by level 1, expected
        {1-6} (SMPTE ST 2042-2:2017).

        The restriction above may be more constrained than expected due to
        one of the following previously encountered options:

        * level = 1
        * foo = 'bar'
        * qux = 'quo'
    """
    )


def test_bad_base_video_format():
    e = exceptions.BadBaseVideoFormat(999)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid base video format, 999, was provided in a sequence header
        (11.3).

        See (Table 11.1) for a list of allowed video format numbers.

        Perhaps this bitstream conforms to an earlier or later version of
        the VC-2 standard?
    """
    )


def test_bad_picture_coding_mode():
    e = exceptions.BadPictureCodingMode(999)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid picture coding mode, 999, was provided in a sequence
        header (11.5).

        See (11.5) for an enumeration of allowed values.
    """
    )


def test_zero_pixel_frame_size():
    e = exceptions.ZeroPixelFrameSize(10, 0)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid custom frame size, 10x0 was provided containing zero pixels
        (11.4.3).
    """
    )


def test_bad_color_difference_sampling_format():
    e = exceptions.BadColorDifferenceSamplingFormat(999)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid colour difference sampling format, 999, was provided
        (11.4.4).

        See (Table 11.2) for an enumeration of allowed values.
    """
    )


def test_bad_source_sampling_mode():
    e = exceptions.BadSourceSamplingMode(999)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid source sampling mode, 999, was provided (11.4.5).

        See (11.4.5) for an enumeration of allowed values.
    """
    )


def test_bad_preset_frame_rate_index():
    e = exceptions.BadPresetFrameRateIndex(999)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid preset frame rate index, 999, was provided (11.4.6).

        See (Table 11.3) for an enumeration of allowed values.
    """
    )


def test_frame_rate_has_zero_numerator():
    e = exceptions.FrameRateHasZeroNumerator(10)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid frame rate, 0/10 fps, was provided (11.4.6).

        Frame rates must not be zero.
    """
    )


def test_frame_rate_has_zero_denominator():
    e = exceptions.FrameRateHasZeroDenominator(10)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid frame rate, 10/0 fps, was provided (11.4.6).

        The frame rate specification contains a division by zero.
    """
    )


def test_bad_preset_pixel_aspect_ratio():
    e = exceptions.BadPresetPixelAspectRatio(999)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid preset pixel aspect ratio index, 999, was provided (11.4.7).

        See (Table 11.4) for an enumeration of allowed values.
    """
    )


def test_pixel_aspect_ratio_contains_zeros():
    e = exceptions.PixelAspectRatioContainsZeros(2, 0)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid pixel aspect ratio, 2:0, was provided (11.4.7).

        Pixel aspect ratios must be valid ratios (i.e. not contain zeros).
    """
    )


class TestCleanAreaOutOfRange(object):
    def test_both_out_of_range(self):
        e = exceptions.CleanAreaOutOfRange(
            clean_width=2000,
            clean_height=1000,
            left_offset=200,
            top_offset=100,
            frame_width=2100,
            frame_height=1050,
        )

        assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
            """
            The clean area width and height extend beyond the frame boundary
            (11.4.8).

            * video_parameters[frame_width] = 2100
            * left_offset (200) + clean_width (2000) = 2200
            * video_parameters[frame_height] = 1050
            * top_offset (100) + clean_height (1000) = 1100

            Has a custom frame size been used and the clean area not been
            updated to match?
        """
        )

    def test_width_only(self):
        e = exceptions.CleanAreaOutOfRange(
            clean_width=2000,
            clean_height=1000,
            left_offset=200,
            top_offset=50,
            frame_width=2100,
            frame_height=1050,
        )

        assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
            """
            The clean area width extends beyond the frame boundary (11.4.8).

            * video_parameters[frame_width] = 2100
            * left_offset (200) + clean_width (2000) = 2200
            * video_parameters[frame_height] = 1050
            * top_offset (50) + clean_height (1000) = 1050

            Has a custom frame size been used and the clean area not been
            updated to match?
        """
        )

    def test_height_only(self):
        e = exceptions.CleanAreaOutOfRange(
            clean_width=2000,
            clean_height=1000,
            left_offset=100,
            top_offset=100,
            frame_width=2100,
            frame_height=1050,
        )

        assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
            """
            The clean area height extends beyond the frame boundary (11.4.8).

            * video_parameters[frame_width] = 2100
            * left_offset (100) + clean_width (2000) = 2100
            * video_parameters[frame_height] = 1050
            * top_offset (100) + clean_height (1000) = 1100

            Has a custom frame size been used and the clean area not been
            updated to match?
        """
        )


def test_bad_preset_signal_range():
    e = exceptions.BadPresetSignalRange(999)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid preset signal range index, 999, was provided (11.4.9).

        See (Table 11.5) for an enumeration of allowed values.
    """
    )


def test_bad_preset_color_spec():
    e = exceptions.BadPresetColorSpec(999)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid preset color spec index, 999, was provided (11.4.10.1).

        See (Table 11.6) for an enumeration of allowed values.
    """
    )


def test_bad_preset_color_primaries():
    e = exceptions.BadPresetColorPrimaries(999)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid color primaries index, 999, was provided (11.4.10.2).

        See (Table 11.7) for an enumeration of allowed values.
    """
    )


def test_bad_preset_color_matrix():
    e = exceptions.BadPresetColorMatrix(999)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid color matrix index, 999, was provided (11.4.10.3).

        See (Table 11.8) for an enumeration of allowed values.
    """
    )


def test_bad_preset_transfer_function():
    e = exceptions.BadPresetTransferFunction(999)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid transfer function index, 999, was provided (11.4.10.4).

        See (Table 11.9) for an enumeration of allowed values.
    """
    )


class TestPictureDimensionsNotMultipleOfFrameDimensions(object):
    def test_all_non_factors(self):
        e = exceptions.PictureDimensionsNotMultipleOfFrameDimensions(
            luma_width=1999,
            luma_height=999,
            color_diff_width=999,
            color_diff_height=499,
            frame_width=2000,
            frame_height=1000,
        )

        assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
            """
            The frame dimensions cannot be evenly divided by the current colour
            difference sampling format and picture coding mode (11.6.2)

            Frame dimensions:

            * frame_width: 2000
            * frame_height: 1000

            The dimensions computed by picture_dimensions were:

            * luma_width: 1999 (not a factor of 2000)
            * luma_height: 999 (not a factor of 1000)
            * color_diff_width: 999 (not a factor of 2000)
            * color_diff_height: 499 (not a factor of 1000)

            Was a frame size with an odd width or height used along with a
            non-4:4:4 colour difference sampling mode or when pictures are
            fields?

            Was the source sampling mode (11.4.5) used instead of the picture
            coding mode (11.5) to determine the picture size?
        """
        )

    def test_all_zeros(self):
        e = exceptions.PictureDimensionsNotMultipleOfFrameDimensions(
            luma_width=0,
            luma_height=0,
            color_diff_width=0,
            color_diff_height=0,
            frame_width=2000,
            frame_height=1000,
        )

        assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
            """
            The frame dimensions cannot be evenly divided by the current colour
            difference sampling format and picture coding mode (11.6.2)

            Frame dimensions:

            * frame_width: 2000
            * frame_height: 1000

            The dimensions computed by picture_dimensions were:

            * luma_width: 0 (not a factor of 2000)
            * luma_height: 0 (not a factor of 1000)
            * color_diff_width: 0 (not a factor of 2000)
            * color_diff_height: 0 (not a factor of 1000)

            Was a frame size with an odd width or height used along with a
            non-4:4:4 colour difference sampling mode or when pictures are
            fields?

            Was the source sampling mode (11.4.5) used instead of the picture
            coding mode (11.5) to determine the picture size?
        """
        )

    def test_all_factors(self):
        # Nbt actually a situation this will be used in but tests that all of
        # the 'not a factor' notes disappear.
        e = exceptions.PictureDimensionsNotMultipleOfFrameDimensions(
            luma_width=2000,
            luma_height=1000,
            color_diff_width=1000,
            color_diff_height=500,
            frame_width=2000,
            frame_height=1000,
        )

        assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
            """
            The frame dimensions cannot be evenly divided by the current colour
            difference sampling format and picture coding mode (11.6.2)

            Frame dimensions:

            * frame_width: 2000
            * frame_height: 1000

            The dimensions computed by picture_dimensions were:

            * luma_width: 2000
            * luma_height: 1000
            * color_diff_width: 1000
            * color_diff_height: 500

            Was a frame size with an odd width or height used along with a
            non-4:4:4 colour difference sampling mode or when pictures are
            fields?

            Was the source sampling mode (11.4.5) used instead of the picture
            coding mode (11.5) to determine the picture size?
        """
        )


def test_non_conseuctive_picture_numbers():
    e = exceptions.NonConsecutivePictureNumbers(
        last_picture_number_offset=(10, 6),
        last_picture_number=100,
        picture_number_offset=(20, 6),
        picture_number=200,
    )

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        Non-consecutive picture number, got 200 after 100 (12.2) and (14.2).

        Picture numbers must have consecutive, ascending integer values,
        wrapping at (2**32)-1 back to 0.

        * Previous picture number defined at bit offset 81
        * Current picture number defined at bit offset 161

        Was this picture taken from another sequence without being assigned
        a new picture number?
    """
    )

    assert dedent(e.bitstream_viewer_hint()) == dedent(
        """
        To view the erroneous picture number definition:

            {cmd} {file} --offset 161

        To view the previous picture number definition:

            {cmd} {file} --offset 81
    """
    )


def test_odd_number_of_fields_in_sequence():
    e = exceptions.OddNumberOfFieldsInSequence(11)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        Sequence contains a non-whole number of frames (11 fields) (10.4.3).

        When pictures are fields, an even number of fields/pictures must be
        included in each sequence.

        Was the sequence truncated mid-frame?
    """
    )


def test_earliest_field_has_odd_picture_number():
    e = exceptions.EarliestFieldHasOddPictureNumber(11)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        First field in sequence has an odd picture number, 11 (12.2).

        When pictures are fields, the earliest field/picture in each frame
        in the sequence must have an even picture number.

        Was the sequence truncated mid-frame?
    """
    )


def test_bad_wavelet_index():
    e = exceptions.BadWaveletIndex(999)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid wavelet index, 999, was provided in the transform parameters
        (12.4.1).

        See (Table 12.1) for an enumeration of allowed values.
    """
    )


def test_bad_ho_wavelet_index():
    e = exceptions.BadHOWaveletIndex(999)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        An invalid horizontal only wavelet index, 999, was provided in the
        extended transform parameters (12.4.4.2).

        See (Table 12.1) for an enumeration of allowed values.
    """
    )


def test_zero_slices_in_coded_picture():
    e = exceptions.ZeroSlicesInCodedPicture(10, 0)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        Invalid slice count, 10x0, specified in slice parameters (12.4.5.2).

        There must be at least one slice in either dimension.
    """
    )


def test_slice_bytes_has_zero_denom():
    e = exceptions.SliceBytesHasZeroDenominator(10)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        Invalid slice bytes count, 10/0, in slice parameters (12.4.5.2).

        Division by zero.
    """
    )


def test_slice_bytes_is_less_than_one():
    e = exceptions.SliceBytesIsLessThanOne(10, 11)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        Slice bytes count, 10/11, in slice parameters is less than one
        (12.4.5.2).

        Slices must be at least 1 byte.
    """
    )


def test_no_quantisation_matrix_available():
    e = exceptions.NoQuantisationMatrixAvailable(
        wavelet_index=tables.WaveletFilters.daubechies_9_7,
        wavelet_index_ho=tables.WaveletFilters.haar_with_shift,
        dwt_depth=10,
        dwt_depth_ho=20,
    )

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        A default quantisation matrix is not available for current transform
        and no custom quantisation matrix has been supplied (12.4.5.3).

        The current transform is defined as:

        * wavelet_index = Daubechies 9 7 (6)
        * dwt_depth = 10
        * wavelet_index_ho = Haar With Shift (4)
        * dwt_depth_ho = 20
    """
    )


def test_quantisation_matrix_value_not_allowed_in_level():
    e = exceptions.QuantisationMatrixValueNotAllowedInLevel(
        value=999,
        allowed_values=ValueSet((0, 127)),
        level_constrained_values=OrderedDict(
            [("level", 1), ("custom_quant_matrix", True), ("foo", "bar")]
        ),
    )

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        Custom quantisation matrix contains a value, 999, outside the range
        {0-127} allowed by the current level, 1 (SMPTE ST 2042-2:2017).

        The restriction above may be more constrained than expected due to
        one of the following previously encountered options:

        * level = 1
        * custom_quant_matrix = True
        * foo = 'bar'
    """
    )


def test_invalid_slice_y_length():
    e = exceptions.InvalidSliceYLength(slice_y_length=100, slice_bytes=10, sx=1, sy=2,)

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        Low-delay slice_y_length value, 100, is out of range, expected a value
        no greater than 66 (13.5.3.1).

        * The current slice (sx=1, sy=2) is 10 bytes (80 bits) long (see
          slice_bytes() (13.5.3.2)).
        * 7 bits are reserved for the qindex field.
        * intlog2(73) = 7 bits are reserved for the slice_y_length field.
        * This leaves 66 bits to split between the luminance and color
          difference components.

        Was the size of this slice correctly computed?

        Were the size of the qindex and slice_y_length fields accounted
        for?
    """
    )


def test_fragmented_picture_restarted():
    e = exceptions.FragmentedPictureRestarted(
        initial_fragment_offset=(10, 6),
        this_fragment_offset=(20, 6),
        fragment_slices_received=10,
        fragment_slices_remaining=5,
    )

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        A picture fragment with fragment_slice_count=0 was encountered while 5
        slices are still outstanding (14.2).

        The previous fragmented picture started at bit offset 81 and 10 of 15
        expected slices were received before the current picture fragment with
        fragment_slice_count=0 arrived at bit offset 161.

        Was a picture fragment with fragment_slice_count=0 incorrectly used
        as padding while waiting for some picture slices to be ready?

        Were some picture fragments omitted when copying a fragmented
        picture from another sequence?
    """
    )

    assert dedent(e.bitstream_viewer_hint()) == dedent(
        """
        To view the offending part of the bitstream:

            {cmd} {file} --from-offset 81 --to_offset {offset} --show fragment_parse --hide slice
    """
    )


def test_sequence_contains_incomplete_fragmented_picture():
    e = exceptions.SequenceContainsIncompleteFragmentedPicture(
        initial_fragment_offset=(10, 6),
        fragment_slices_received=10,
        fragment_slices_remaining=5,
    )

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        A sequence terminated while 5 slices are still outstanding in a
        fragmented picture (14.2).

        The fragmented picture started at bit offset 81 and 10 of 15 expected
        slices were received before the end of the sequence was encountered.

        Were some picture fragments omitted when copying a fragmented
        picture from another sequence?
    """
    )

    assert dedent(e.bitstream_viewer_hint()) == dedent(
        """
        To view the offending part of the bitstream:

            {cmd} {file} --from-offset 81 --to_offset {offset} --show parse_info --show fragment_parse --hide slice
    """
    )


def test_picture_interleaved_with_fragmented_picture():
    e = exceptions.PictureInterleavedWithFragmentedPicture(
        initial_fragment_offset=(10, 6),
        this_offset=(20, 6),
        fragment_slices_received=10,
        fragment_slices_remaining=5,
    )

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        A non-fragmented picture was encountered while 5 slices are still
        outstanding in a fragmented picture (14.2).

        The fragmented picture started at bit offset 81 and 10 of 15 expected
        slices were received before the non-fragmented picture was encountered
        at bit offset 161.

        Were some picture fragments omitted when copying a fragmented picture
        from another sequence?
    """
    )

    assert dedent(e.bitstream_viewer_hint()) == dedent(
        """
        To view the offending part of the bitstream:

            {cmd} {file} --from-offset 81 --to_offset {offset} --show parse_info --show fragment_parse --show picture_parse --hide slice
    """
    )


def test_picture_number_changed_mid_fragmented_picture():
    e = exceptions.PictureNumberChangedMidFragmentedPicture(
        last_picture_number_offset=(10, 6),
        last_picture_number=100,
        picture_number_offset=(20, 6),
        picture_number=101,
    )

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        The picture number changed from 100 to 101 within the same fragmented
        picture (14.2).

        The previous fragment in this fragmented picture defined its
        picture number at bit offset 81. The current fragment provided a
        different picture number at bit offset 161.

        Was the picture number incremented for every fragment rather than
        for every complete picture in the stream?
    """
    )

    assert dedent(e.bitstream_viewer_hint()) == dedent(
        """
        To view the offending part of the bitstream:

            {cmd} {file} --from-offset 81 --to_offset {offset} --show fragment_parse --hide slice
    """
    )


def test_too_many_slices_in_fragmented_picture():
    e = exceptions.TooManySlicesInFragmentedPicture(
        initial_fragment_offset=(10, 6),
        this_fragment_offset=(20, 6),
        fragment_slices_received=10,
        fragment_slices_remaining=5,
        fragment_slice_count=6,
    )

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        The current fragmented picture contains too many picture slices (14.2).

        This fragmented picture (starting at bit offset 81) consists of a total
        of 15 picture slices. 10 slices have already been received but the
        current fragment (at bit offset 161) contains 6 slices while only 5
        more are expected.
    """
    )

    assert dedent(e.bitstream_viewer_hint()) == dedent(
        """
        To view the offending part of the bitstream:

            {cmd} {file} --from-offset 81 --to_offset {offset} --show fragment_parse --hide slice
    """
    )


def test_fragment_slices_not_contiguous():
    e = exceptions.FragmentSlicesNotContiguous(
        initial_fragment_offset=(10, 6),
        this_fragment_offset=(20, 6),
        fragment_x_offset=10,
        fragment_y_offset=11,
        expected_fragment_x_offset=12,
        expected_fragment_y_offset=13,
    )

    assert wrap_paragraphs(e.explain()) == wrap_paragraphs(
        """
        The current picture fragment's slices are non-contiguous (14.2).

        The fragmented picture starting at bit offset 81 contains a fragment at
        bit offset 161 with an unexpected start offset:

        * fragment_x_offset = 10 (should be 12)
        * fragment_y_offset = 11 (should be 13)

        Fragmented pictures must include picture slices in raster-scan
        order starting with sx=0, sy=0 and without leaving any gaps.
    """
    )

    assert dedent(e.bitstream_viewer_hint()) == dedent(
        """
        To view the offending part of the bitstream:

            {cmd} {file} --from-offset 81 --to_offset {offset} --show fragment_parse --hide slice
    """
    )
