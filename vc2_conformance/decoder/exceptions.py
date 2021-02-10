"""
The :py:mod:`vc2_conformance.decoder.exceptions` module defines a number of
exceptions derived from :py:exc:`ConformanceError` representing different
conformance errors a bitstream may contain. These exceptions provide additional
methods which return detailed human-readable information about the conformance
error.

.. autoexception:: ConformanceError
    :members:

"""

from textwrap import dedent

from fractions import Fraction

from vc2_conformance.string_utils import wrap_paragraphs

from vc2_conformance.pseudocode.vc2_math import intlog2

from vc2_data_tables import (
    PARSE_INFO_PREFIX,
    PARSE_INFO_HEADER_BYTES,
    PRESET_FRAME_RATES,
    ParseCodes,
    Profiles,
    LEVELS,
    PresetSignalRanges,
    PresetColorSpecs,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    WaveletFilters,
)

from vc2_conformance.level_constraints import LEVEL_SEQUENCE_RESTRICTIONS

from vc2_conformance.version_constraints import (
    MINIMUM_MAJOR_VERSION,
    preset_frame_rate_version_implication,
    preset_signal_range_version_implication,
    preset_color_spec_version_implication,
    preset_color_primaries_version_implication,
    preset_color_matrix_version_implication,
    preset_transfer_function_version_implication,
    parse_code_version_implication,
    profile_version_implication,
)

from vc2_conformance.bitstream.io import to_bit_offset


def known_parse_code_to_string(parse_code):
    """
    Convert a known parse code (i.e. one in
    :py:class:`~vc2_data_tables.ParseCodes`) into a string such as::

        "end of sequence (0x10)"
    """
    return "{} (0x{:02X})".format(
        ParseCodes(parse_code).name.replace("_", " "),
        parse_code,
    )


def known_profile_to_string(profile):
    """
    Convert a known profile number (i.e. one in
    :py:class:`~vc2_data_tables.Profiles`) into a string such as::

        "high quality (3)"
    """
    return "{} ({:d})".format(
        Profiles(profile).name.replace("_", " "),
        profile,
    )


def known_wavelet_to_string(wavelet_index):
    """
    Convert a known wavelet index (i.e. one in
    :py:class:`~vc2_data_tables.WaveletFilters`) into a string such as::

        "Haar With Shift (4)"
    """
    return "{} ({:d})".format(
        WaveletFilters(wavelet_index).name.replace("_", " ").title(),
        wavelet_index,
    )


def explain_parse_code_sequence_structure_restrictions(
    actual_parse_code,
    expected_parse_codes,
    expected_end,
):
    """
    Produce an sentence explaining how a particular sequence requirement has
    been violated.

    Parameters
    ==========
    actual_parse_code : None, :py:class:`vc2_data_tables.ParseCodes`
        The (valid) parse code which was encountered which violated the stated
        sequencing requirements. If None, a premature end of sequence was encountered.
    expected_parse_codes : None or [:py:class:`vc2_data_tables.ParseCodes`, ...]
        If a list, enumerates the (valid) parse codes which would have been
        allowed instead. If None, any parse code would have been allowed.
    expected_end : bool
        If True, indicates that the sequence was expected to end (i.e. that no
        more parse codes were expected). If False, see expected_parse_codes.
    """
    return "{} was encountered but {} expected.".format(
        (
            "The parse code {}".format(
                known_parse_code_to_string(actual_parse_code),
            )
            if actual_parse_code is not None
            else "No further parse code"
        ),
        (
            "no further parse code"
            if expected_end is True
            else "any parse code"
            if expected_parse_codes is None
            else " or ".join(map(known_parse_code_to_string, expected_parse_codes))
        ),
    )


class ConformanceError(Exception):
    """
    Base class for all bitstream conformance failure exceptions.
    """

    def __str__(self):
        return wrap_paragraphs(self.explain()).partition("\n")[0]

    def explain(self):
        """
        Produce a detailed human readable explanation of the conformance
        failure.

        Should return a string which can be re-linewrapped by
        :py:func:`vc2_conformance.string_utils.wrap_paragraphs`.

        The first line will be used as a summary when the exception is printed
        using :py:func:`str`.
        """
        raise NotImplementedError()

    def bitstream_viewer_hint(self):
        """
        Return a set of sample command line arguments for the
        vc2-bitstream-viewer tool which will display the relevant portion of
        the bitstream.

        This string may include the following :py:meth:`str.format`
        substitutions which should be filled in before display:

        * ``{cmd}`` The command name of the bitstream viewer (i.e. usually
          ``vc2-bitstream-viewer``)
        * ``{file}`` The filename of the bitstream.
        * ``{offset}`` The bit offset of the next bit in the bitstream to be
          read.

        This returned string should *not* be line-wrapped but should be
        de-indented by :py:func:`textwrap.dedent`.
        """
        return """
            To view the offending part of the bitstream:

                {cmd} {file} --offset {offset}
        """

    def offending_offset(self):
        """
        If known, return the bit-offset of the offending part of the bitstream.
        Otherwise return None (and the current offset will be assumed).
        """
        return None


################################################################################
# Conformance failure exceptions
################################################################################


class UnexpectedEndOfStream(ConformanceError):
    """
    Reached the end of the stream while attempting to perform read operation.
    """

    def explain(self):
        return """
            Unexpectedly encountered the end of the stream.

            A VC-2 Stream shall be a concatenation of one or more VC-2
            sequences (10.3). Sequences shall end with a parse info header with
            an end of sequence parse code (0x10) (10.4.1)

            Did the sequence omit a terminating parse info with the end of
            sequence (0x10) parse code?
        """


class BadParseCode(ConformanceError):
    """
    parse_info (10.5.1) has been given an unrecognised parse code.

    The exception argument will contain the received parse code.
    """

    def __init__(self, parse_code):
        self.parse_code = parse_code
        super(BadParseCode, self).__init__()

    def explain(self):
        return """
            An invalid parse code, 0x{:02X}, was provided to a parse info
            header (10.5.1).

            See (Table 10.1) for the list of allowed parse codes.

            Perhaps this bitstream conforms to an earlier or later version of the
            VC-2 standard?
        """.format(
            self.parse_code
        )


class BadParseInfoPrefix(ConformanceError):
    """
    This exception is thrown when the parse_info (10.5.1) prefix value read
    from the bitstream doesn't match the expected value:

        The parse info prefix shall be 0x42 0x42 0x43 0x44

    The exception argument will contain the read prefix value.
    """

    def __init__(self, parse_info_prefix):
        self.parse_info_prefix = parse_info_prefix
        super(BadParseInfoPrefix, self).__init__()

    def explain(self):
        return """
            An invalid prefix, 0x{:08X}, was encountered in a parse info block
            (10.5.1). The expected prefix is 0x{:08X}.

            Is the parse_info block byte aligned (10.5.1)?

            Did the preceeding data unit over- or under-run the expected
            length? For example, were any unused bits in a picture slice filled
            with the correct number of padding bits (A.4.2)?
        """.format(
            self.parse_info_prefix,
            PARSE_INFO_PREFIX,
        )


class InconsistentNextParseOffset(ConformanceError):
    """
    This exception is thrown when a ``next_parse_offset`` value encoded in a
    parse_info (10.5.1) block does not match the offset of the next parse_info
    in the stream.

    Parameters
    ==========
    parse_info_offset : int
        The bitstream byte offset of the start of the parse_info block
        containing the bad next_parse_offset value.
    next_parse_offset : int
        The offending next_parse_offset value
    true_parse_offset : int
        The actual offset from parse_info_offset of the next parse_info block
        in the stream.
    """

    def __init__(self, parse_info_offset, next_parse_offset, true_parse_offset):
        self.parse_info_offset = parse_info_offset
        self.next_parse_offset = next_parse_offset
        self.true_parse_offset = true_parse_offset
        super(InconsistentNextParseOffset, self).__init__()

    def explain(self):
        return """
            Incorrect next_parse_offset value in parse info: got {} bytes,
            expected {} bytes (10.5.1).

            The erroneous parse info block begins at bit offset {} and is
            followed by the next parse info block at bit offset {}.

            Does the next_parse_offset include the {} bytes of the parse info
            header?

            Is next_parse_offset given in bits, not bytes?
        """.format(
            self.next_parse_offset,
            self.true_parse_offset,
            to_bit_offset(self.parse_info_offset),
            to_bit_offset(self.parse_info_offset + self.true_parse_offset),
            PARSE_INFO_HEADER_BYTES,
        )

    def bitstream_viewer_hint(self):
        return """
            To view the erroneous parse info block:

                {{cmd}} {{file}} --offset {} --after-context 144

            To view the following parse info block:

                {{cmd}} {{file}} --offset {{offset}} --after-context 144
        """.format(
            to_bit_offset(self.parse_info_offset)
        )

    def offending_offset(self):
        return to_bit_offset(self.parse_info_offset)


class MissingNextParseOffset(ConformanceError):
    """
    This exception is thrown when a ``next_parse_offset`` value is given as
    zero but is not optional and must be provided.

    The parse_code for the offending parse info block is provided as an
    argument.
    """

    def __init__(self, parse_code):
        self.parse_code = parse_code
        super(MissingNextParseOffset, self).__init__()

    def explain(self):
        return """
            A next_parse_offset value of zero was provided in a {} (parse_code
            = 0x{:02X}) parse info block where a valid next_parse_offset value
            is mandatory (10.5.1).

            Does the next_parse_offset include the {} bytes of the parse info
            header?
        """.format(
            ParseCodes(self.parse_code).name.replace("_", " "),
            self.parse_code,
            PARSE_INFO_HEADER_BYTES,
        )


class InvalidNextParseOffset(ConformanceError):
    """
    This exception is thrown when a ``next_parse_offset`` value contains a
    value between 1 and 12 (inclusive). All of these byte offsets refer to an
    offset in the stream which is still within the current parse_info block.

    The exception argument will contain the offending next_parse_offset value.
    """

    def __init__(self, next_parse_offset):
        self.next_parse_offset = next_parse_offset
        super(InvalidNextParseOffset, self).__init__()

    def explain(self):
        return """
            Invalid next_parse_offset value {} found in parse info header
            (10.5.1).

            The next_parse_offset value must account for the {} bytes taken by
            the parse info block. As a consequence this value must be strictly
            {} or greater (except in circumstances where it may be omitted when
            it must be 0) (15.5.1).

            Does the next_parse_offset include the {} bytes of the parse info
            header?
        """.format(
            self.next_parse_offset,
            PARSE_INFO_HEADER_BYTES,
            PARSE_INFO_HEADER_BYTES,
            PARSE_INFO_HEADER_BYTES,
        )


class NonZeroNextParseOffsetAtEndOfSequence(ConformanceError):
    """
    This exception is thrown when an end-of-sequence defining parse_info
    (10.5.1) has a non-zero next_parse_offset.

    The exception argument will contain the offending next_parse_offset value.
    """

    def __init__(self, next_parse_offset):
        self.next_parse_offset = next_parse_offset
        super(NonZeroNextParseOffsetAtEndOfSequence, self).__init__()

    def explain(self):
        return """
            Non-zero next_parse_offset value, {}, in the parse info at the end
            of the sequence (10.5.1).

            Does the next_parse_offset incorrectly include an offset into an
            adjacent sequence?
        """.format(
            self.next_parse_offset,
        )


class InconsistentPreviousParseOffset(ConformanceError):
    """
    This exception is thrown when the ``previous_parse_offset`` value encoded
    in a parse_info (10.5.1) block does not match the offset of the previous
    parse_info in the stream.

    Parameters
    ==========
    last_parse_info_offset : int
        The bitstream byte offset of the start of the previous parse_info
        block.
    previous_parse_offset : int
        The offending previous_parse_offset value
    true_parse_offset : int
        The actual byte offset from the last parse_info to the current one in
        the stream.
    """

    def __init__(
        self, last_parse_info_offset, previous_parse_offset, true_parse_offset
    ):
        self.last_parse_info_offset = last_parse_info_offset
        self.previous_parse_offset = previous_parse_offset
        self.true_parse_offset = true_parse_offset
        super(InconsistentPreviousParseOffset, self).__init__()

    def explain(self):
        return """
            Incorrect previous_parse_offset value in parse info: got {} bytes,
            expected {} bytes (10.5.1).

            The erroneous parse info block begins at offset {} bits and follows
            a parse info block at offset {} bits.

            Does the previous_parse_offset include the {} bytes of the parse info
            header?

            Is previous_parse_offset given in bits, not bytes?

            Was the previous_parse_offset incorrectly omitted after a data unit
            whose size was not initially known?

            Was this parse info block copied from another sequence without
            updating the previous_parse_offset?
        """.format(
            self.previous_parse_offset,
            self.true_parse_offset,
            to_bit_offset(self.last_parse_info_offset + self.true_parse_offset),
            to_bit_offset(self.last_parse_info_offset),
            PARSE_INFO_HEADER_BYTES,
        )

    def bitstream_viewer_hint(self):
        return """
            To view the erroneous parse info block:

                {{cmd}} {{file}} --offset {{offset}} --after-context 144

            To view the proceeding parse info block:

                {{cmd}} {{file}} --offset {} --after-context 144
        """.format(
            to_bit_offset(self.last_parse_info_offset)
        )


class NonZeroPreviousParseOffsetAtStartOfSequence(ConformanceError):
    """
    This exception is thrown when the first parse_info (10.5.1) has a non-zero
    previous_parse_offset.

    The exception argument will contain the offending previous_parse_offset value.
    """

    def __init__(self, previous_parse_offset):
        self.previous_parse_offset = previous_parse_offset
        super(NonZeroPreviousParseOffsetAtStartOfSequence, self).__init__()

    def explain(self):
        return """
            Non-zero previous_parse_offset, {}, in the parse info at the start
            of a sequence (10.5.1).

            Was this parse info block copied from another stream without the
            previous_parse_offset being updated?

            Does this parse info block incorrectly include an offset into an
            adjacent sequence?
        """.format(
            self.previous_parse_offset,
        )


class SequenceHeaderChangedMidSequence(ConformanceError):
    """
    This exception is thrown when a sequence_header (11.1) appears in the
    stream which does not match the previous sequence header byte-for-byte.

    Parameters
    ==========
    last_sequence_header_offset : int
    last_sequence_header_bytes : :py:class:`bytearray`
        The bitstream byte-offset and raw bytes for the previous
        sequence_header in the stream.
    this_sequence_header_offset : int
    this_sequence_header_bytes : :py:class:`bytearray`
        The bitstream byte-offset and raw bytes for the offending
        sequence_header in the stream.
    """

    def __init__(
        self,
        last_sequence_header_offset,
        last_sequence_header_bytes,
        this_sequence_header_offset,
        this_sequence_header_bytes,
    ):
        self.last_sequence_header_offset = last_sequence_header_offset
        self.last_sequence_header_bytes = last_sequence_header_bytes
        self.this_sequence_header_offset = this_sequence_header_offset
        self.this_sequence_header_bytes = this_sequence_header_bytes
        super(SequenceHeaderChangedMidSequence, self).__init__()

    def explain(self):
        first_difference_offset = 0
        for old, new in zip(
            bytearray(self.last_sequence_header_bytes),
            bytearray(self.this_sequence_header_bytes),
        ):
            if old != new:
                for i in reversed(range(8)):
                    if (old & (1 << i)) != (new & (1 << i)):
                        first_difference_offset += 7 - i
                        break
                break
            else:
                first_difference_offset += 8

        return """
            Sequence header is not byte-for-byte identical to the previous
            sequence header in the same sequence (11.1).

            The previous sequence header begins at bit offset {} and the
            current sequence header begins at bit offset {}.

            This sequence header differs from its predecessor starting with bit
            {}. That is, bit offset {} in the previous sequence header is
            different to bit offset {} in the current sequence header.

            Did the video format change without beginning a new sequence?

            Did the sequence header attempt to encode the same parameters in a
            different way (e.g. switching to a custom value rather than an
            equivalent preset)?
        """.format(
            to_bit_offset(self.last_sequence_header_offset),
            to_bit_offset(self.this_sequence_header_offset),
            first_difference_offset,
            to_bit_offset(self.last_sequence_header_offset) + first_difference_offset,
            to_bit_offset(self.this_sequence_header_offset) + first_difference_offset,
        )

    def bitstream_viewer_hint(self):
        return """
            To view the previous sequence header

                {{cmd}} {{file}} --from-offset {} --to-offset {}

            To view the current sequence header

                {{cmd}} {{file}} --from-offset {} --to-offset {}
        """.format(
            to_bit_offset(self.last_sequence_header_offset),
            to_bit_offset(
                self.last_sequence_header_offset + len(self.last_sequence_header_bytes)
            )
            - 1,
            to_bit_offset(self.this_sequence_header_offset),
            to_bit_offset(
                self.this_sequence_header_offset + len(self.this_sequence_header_bytes)
            )
            - 1,
        )

    def offending_offset(self):
        return to_bit_offset(self.this_sequence_header_offset)


class BadProfile(ConformanceError):
    """
    parse_parameters (11.2.3) has been given an unrecognised profile number.

    The exception argument will contain the received profile number.
    """

    def __init__(self, profile):
        self.profile = profile
        super(BadProfile, self).__init__()

    def explain(self):
        return """
            An invalid profile number, {}, was provided in the parse parameters
            (11.2.3).

            See (C.2) for the list of allowed profile numbers.

            Perhaps this bitstream conforms to an earlier or later version of
            the VC-2 standard?
        """.format(
            self.profile
        )


class BadLevel(ConformanceError):
    """
    parse_parameters (11.2.3) has been given an unrecognised level number.

    The exception argument will contain the received level number.
    """

    def __init__(self, level):
        self.level = level
        super(BadLevel, self).__init__()

    def explain(self):
        return """
            An invalid level number, {}, was provided in the parse parameters
            (11.2.3).

            See (C.3) or SMPTE ST 2042-2 'VC-2 Level Definitions' for details
            of the supported levels and their codes.

            Perhaps this bitstream conforms to an earlier or later version of
            the VC-2 standard?
        """.format(
            self.level
        )


class GenericInvalidSequence(ConformanceError):
    """
    The sequence of data units in the VC-2 sequence does not match the generic
    sequence structure specified in (10.4.1)

    The offending parse code will be given in :py:attr:`parse_code` if it does
    not match the expected sequence structure. If the sequence ends prematurely
    ``None`` will be passed instead.

    :py:attr:`expected_parse_codes` enumerates the parse codes which would have
    been allowed.  This may be ``None`` if any parse code would be permitted.

    :py:attr:`expected_end` is True if it would have been acceptable for the
    sequence to have ended at this point.
    """

    def __init__(self, parse_code, expected_parse_codes, expected_end):
        self.parse_code = parse_code
        self.expected_parse_codes = expected_parse_codes
        self.expected_end = expected_end
        super(GenericInvalidSequence, self).__init__()

    def explain(self):
        return """
            The current sequence does not match the structure defined for VC-2
            sequences in (10.4.1).

            {}

            Did the sequence begin with a non-sequence header data unit?
        """.format(
            explain_parse_code_sequence_structure_restrictions(
                self.parse_code,
                self.expected_parse_codes,
                self.expected_end,
            )
        )

    def bitstream_viewer_hint(self):
        return """
            To view the offending part of the bitstream:

                {cmd} {file} --from-offset 0 --to-offset {offset} --show parse_info
        """


class LevelInvalidSequence(ConformanceError):
    """
    The sequence of data units in the VC-2 sequence does not match the
    sequence structure specified for the current level (C.3).

    The offending parse code will be given in :py:attr:`parse_code` if it does
    not match the expected sequence structure. If the sequence ends prematurely
    ``None`` will be passed instead.

    :py:attr:`expected_parse_codes` enumerates the parse codes which would have
    been allowed.  This may be ``None`` if any parse code would be permitted.

    :py:attr:`expected_end` is True if it would have been acceptable for the
    sequence to have ended at this point.

    :py:attr:`level` is the current VC-2 level.
    """

    def __init__(self, parse_code, expected_parse_codes, expected_end, level):
        self.parse_code = parse_code
        self.expected_parse_codes = expected_parse_codes
        self.expected_end = expected_end
        self.level = level
        super(LevelInvalidSequence, self).__init__()

    def explain(self):
        return """
            The current sequence does not match the structure required by the
            current level, {}, ({}).

            {}

            {}
        """.format(
            self.level,
            LEVELS[self.level].standard,
            LEVEL_SEQUENCE_RESTRICTIONS[self.level].sequence_restriction_explanation,
            explain_parse_code_sequence_structure_restrictions(
                self.parse_code,
                self.expected_parse_codes,
                self.expected_end,
            ),
        )

    def bitstream_viewer_hint(self):
        return """
            To view the offending part of the bitstream:

                {cmd} {file} --from-offset 0 --to-offset {offset} --show parse_info
        """


class ParseCodeNotAllowedInProfile(ConformanceError):
    """
    The parse code encountered is not allowed in the current profile (C.2).

    The offending parse_code and profile combination will be provided in
    :py:attr:`parse_code` and :py;attr:`profile`.
    """

    def __init__(self, parse_code, profile):
        self.parse_code = parse_code
        self.profile = profile
        super(ParseCodeNotAllowedInProfile, self).__init__()

    def explain(self):
        return """
            The parse code {} is not allowed in the {} profile (C.2).
        """.format(
            known_parse_code_to_string(self.parse_code),
            known_profile_to_string(self.profile),
        )


class ValueNotAllowedInLevel(ConformanceError):
    """
    A value was encountered in the bitstream which was not allowed by the
    current level. See
    :py:data:`vc2_conformance.level_constraints.LEVEL_CONSTRAINTS` for details
    of the constrained keys.

    :py:attr:`level_constrained_values` will be the previously specified
    values which were allowed by the level constraints.

    The offending key and value will be placed in :py:attr:`key` and
    :py:attr:`value` respectively.

    The allowed :py:class:`~vc2_conformance.constraint_table.ValueSet` will be
    placed in :py:attr:`allowed_values`.
    """

    def __init__(self, level_constrained_values, key, value, allowed_values):
        self.level_constrained_values = level_constrained_values
        self.key = key
        self.value = value
        self.allowed_values = allowed_values
        super(ValueNotAllowedInLevel, self).__init__()

    def explain(self):
        level = self.level_constrained_values["level"]

        return dedent(
            """
            The {} value {} is not allowed by level {}, expected {} ({}).

            The restriction above may be more constrained than expected due to
            one of the following previously encountered options:

            {}
        """
        ).format(
            self.key,
            self.value,
            level,
            str(self.allowed_values),
            LEVELS[level].standard,
            "\n".join(
                "* {} = {!r}".format(key, value)
                for key, value in self.level_constrained_values.items()
            ),
        )


class BadBaseVideoFormat(ConformanceError):
    """
    sequence_header (11.1) has been given an unrecognised base video format
    number.

    The exception argument will contain the received base video format number.
    """

    def __init__(self, base_video_format):
        self.base_video_format = base_video_format
        super(BadBaseVideoFormat, self).__init__()

    def explain(self):
        return """
            An invalid base video format, {}, was provided in a sequence header
            (11.3).

            See (Table 11.1) for a list of allowed video format numbers.

            Perhaps this bitstream conforms to an earlier or later version of
            the VC-2 standard?
        """.format(
            self.base_video_format
        )


class BadPictureCodingMode(ConformanceError):
    """
    sequence_header (11.1) has been given an unrecognised picture coding mode.

    The exception argument will contain the received picture coding mode value
    """

    def __init__(self, picture_coding_mode):
        self.picture_coding_mode = picture_coding_mode
        super(BadPictureCodingMode, self).__init__()

    def explain(self):
        return """
            An invalid picture coding mode, {:d}, was provided in a sequence
            header (11.5).

            See (11.5) for an enumeration of allowed values.
        """.format(
            self.picture_coding_mode
        )


class ZeroPixelFrameSize(ConformanceError):
    """
    (11.4.3) A custom frame size with a zero width or height was specified.

    The actual dimensions are specified as arguments.
    """

    def __init__(self, frame_width, frame_height):
        self.frame_width = frame_width
        self.frame_height = frame_height
        super(ZeroPixelFrameSize, self).__init__()

    def explain(self):
        return """
            An invalid custom frame size, {}x{} was provided containing zero
            pixels (11.4.3).
        """.format(
            self.frame_width, self.frame_height
        )


class BadColorDifferenceSamplingFormat(ConformanceError):
    """
    color_diff_sampling_format (11.4.4) has been given an unrecognised color
    difference format index.

    The exception argument will contain the index.
    """

    def __init__(self, color_diff_format_index):
        self.color_diff_format_index = color_diff_format_index
        super(BadColorDifferenceSamplingFormat, self).__init__()

    def explain(self):
        return """
            An invalid color difference sampling format, {:d}, was provided
            (11.4.4).

            See (Table 11.2) for an enumeration of allowed values.
        """.format(
            self.color_diff_format_index
        )


class BadSourceSamplingMode(ConformanceError):
    """
    scan_format (11.4.5) has been given an unrecognised source sampling mode.

    The exception argument will contain the offending mode.
    """

    def __init__(self, source_sampling):
        self.source_sampling = source_sampling
        super(BadSourceSamplingMode, self).__init__()

    def explain(self):
        return """
            An invalid source sampling mode, {:d}, was provided (11.4.5).

            See (11.4.5) for an enumeration of allowed values.
        """.format(
            self.source_sampling
        )


class BadPresetFrameRateIndex(ConformanceError):
    """
    frame_rate (11.4.6) has been given an unrecognised preset frame rate index

    The exception argument will contain the offending index.
    """

    def __init__(self, index):
        self.index = index
        super(BadPresetFrameRateIndex, self).__init__()

    def explain(self):
        return """
            An invalid preset frame rate index, {:d}, was provided (11.4.6).

            See (Table 11.3) for an enumeration of allowed values.
        """.format(
            self.index
        )


class FrameRateHasZeroNumerator(ConformanceError):
    """
    (11.4.6) specifies that custom frame rates must not be zero (i.e. have a
    zero numerator)

    The denominator is provided as an argument.
    """

    def __init__(self, frame_rate_denom):
        self.frame_rate_denom = frame_rate_denom
        super(FrameRateHasZeroNumerator, self).__init__()

    def explain(self):
        return """
            An invalid frame rate, 0/{} fps, was provided (11.4.6).

            Frame rates must not be zero.
        """.format(
            self.frame_rate_denom
        )


class FrameRateHasZeroDenominator(ConformanceError):
    """
    (11.4.6) specifies that custom frame rates must not have zero in the
    denominator.

    The numerator is provided as an argument.
    """

    def __init__(self, frame_rate_numer):
        self.frame_rate_numer = frame_rate_numer
        super(FrameRateHasZeroDenominator, self).__init__()

    def explain(self):
        return """
            An invalid frame rate, {}/0 fps, was provided (11.4.6).

            The frame rate specification contains a division by zero.
        """.format(
            self.frame_rate_numer
        )


class BadPresetPixelAspectRatio(ConformanceError):
    """
    pixel_aspect_ratio_index (11.4.7) has been given an unrecognised preset
    index

    The exception argument will contain the offending index.
    """

    def __init__(self, index):
        self.index = index
        super(BadPresetPixelAspectRatio, self).__init__()

    def explain(self):
        return """
            An invalid preset pixel aspect ratio index, {:d}, was provided
            (11.4.7).

            See (Table 11.4) for an enumeration of allowed values.
        """.format(
            self.index
        )


class PixelAspectRatioContainsZeros(ConformanceError):
    """
    (11.4.7) specifies that custom pixel aspect ratios must not have zeros.

    The ratio numerator/denominator is provided.
    """

    def __init__(self, pixel_aspect_ratio_numer, pixel_aspect_ratio_denom):
        self.pixel_aspect_ratio_numer = pixel_aspect_ratio_numer
        self.pixel_aspect_ratio_denom = pixel_aspect_ratio_denom
        super(PixelAspectRatioContainsZeros, self).__init__()

    def explain(self):
        return """
            An invalid pixel aspect ratio, {}:{}, was provided (11.4.7).

            Pixel aspect ratios must be valid ratios (i.e. not contain zeros).
        """.format(
            self.pixel_aspect_ratio_numer,
            self.pixel_aspect_ratio_denom,
        )


class CleanAreaOutOfRange(ConformanceError):
    """
    clean_area (11.4.8) specifies a clean area which goes beyond the boundaries
    of the picture.

    The offending clean area width, height, left and top offset will be
    included as exception arguments, followed by the picture width and height.
    """

    def __init__(
        self,
        clean_width,
        clean_height,
        left_offset,
        top_offset,
        frame_width,
        frame_height,
    ):
        self.clean_width = clean_width
        self.clean_height = clean_height
        self.left_offset = left_offset
        self.top_offset = top_offset
        self.frame_width = frame_width
        self.frame_height = frame_height
        super(CleanAreaOutOfRange, self).__init__()

    def explain(self):
        offending_dimensions = []
        if self.clean_width + self.left_offset > self.frame_width:
            offending_dimensions.append("width")
        if self.clean_height + self.top_offset > self.frame_height:
            offending_dimensions.append("height")

        return """
            The clean area {} extend{} beyond the frame boundary (11.4.8).

            * video_parameters[frame_width] = {}
            * left_offset ({}) + clean_width ({}) = {}
            * video_parameters[frame_height] = {}
            * top_offset ({}) + clean_height ({}) = {}

            Has a custom frame size been used and the clean area not been
            updated to match?
        """.format(
            " and ".join(offending_dimensions),
            ("s" if len(offending_dimensions) == 1 else ""),
            self.frame_width,
            self.left_offset,
            self.clean_width,
            self.left_offset + self.clean_width,
            self.frame_height,
            self.top_offset,
            self.clean_height,
            self.top_offset + self.clean_height,
        )


class BadCustomSignalExcursion(ConformanceError):
    """
    signal_range (11.4.9) requires that signal excursions must be at least 1.

    A string "luma" or "color_diff" followed by the offending excursion value
    should be provided as arguments.
    """

    def __init__(
        self,
        component_type_name,
        excursion,
    ):
        self.component_type_name = component_type_name
        self.excursion = excursion
        super(BadCustomSignalExcursion, self).__init__()

    def explain(self):
        return """
            Custom signal range {}_excursion must be at least 1 but {} was
            provided (11.4.9).
        """.format(
            self.component_type_name,
            self.excursion,
        )


class BadPresetSignalRange(ConformanceError):
    """
    signal_range (11.4.9) has been given an unrecognised preset index

    The exception argument will contain the offending index.
    """

    def __init__(self, index):
        self.index = index
        super(BadPresetSignalRange, self).__init__()

    def explain(self):
        return """
            An invalid preset signal range index, {:d}, was provided (11.4.9).

            See (Table 11.5) for an enumeration of allowed values.
        """.format(
            self.index
        )


class BadPresetColorSpec(ConformanceError):
    """
    color_spec (11.4.10.1) has been given an unrecognised preset index

    The exception argument will contain the offending index.
    """

    def __init__(self, index):
        self.index = index
        super(BadPresetColorSpec, self).__init__()

    def explain(self):
        return """
            An invalid preset color spec index, {:d}, was provided (11.4.10.1).

            See (Table 11.6) for an enumeration of allowed values.
        """.format(
            self.index
        )


class BadPresetColorPrimaries(ConformanceError):
    """
    color_primaries (11.4.10.2) has been given an unrecognised preset index

    The exception argument will contain the offending index.
    """

    def __init__(self, index):
        self.index = index
        super(BadPresetColorPrimaries, self).__init__()

    def explain(self):
        return """
            An invalid color primaries index, {:d}, was provided (11.4.10.2).

            See (Table 11.7) for an enumeration of allowed values.
        """.format(
            self.index
        )


class BadPresetColorMatrix(ConformanceError):
    """
    color_matrix (11.4.10.3) has been given an unrecognised preset index

    The exception argument will contain the offending index.
    """

    def __init__(self, index):
        self.index = index
        super(BadPresetColorMatrix, self).__init__()

    def explain(self):
        return """
            An invalid color matrix index, {:d}, was provided (11.4.10.3).

            See (Table 11.8) for an enumeration of allowed values.
        """.format(
            self.index
        )


class BadPresetTransferFunction(ConformanceError):
    """
    transfer_function (11.4.10.4) has been given an unrecognised preset index

    The exception argument will contain the offending index.
    """

    def __init__(self, index):
        self.index = index
        super(BadPresetTransferFunction, self).__init__()

    def explain(self):
        return """
            An invalid transfer function index, {:d}, was provided (11.4.10.4).

            See (Table 11.9) for an enumeration of allowed values.
        """.format(
            self.index
        )


class PictureDimensionsNotMultipleOfFrameDimensions(ConformanceError):
    """
    (11.6.2) specifies that the picture dimensions (luma_width, luma_height,
    color_diff_width and color_diff_height) must be a whole factor of the
    frame dimensions (i.e. frame_width and frame_height).

    The actual dimensions are specified as arguments.
    """

    def __init__(
        self,
        luma_width,
        luma_height,
        color_diff_width,
        color_diff_height,
        frame_width,
        frame_height,
    ):
        self.luma_width = luma_width
        self.luma_height = luma_height
        self.color_diff_width = color_diff_width
        self.color_diff_height = color_diff_height
        self.frame_width = frame_width
        self.frame_height = frame_height
        super(PictureDimensionsNotMultipleOfFrameDimensions, self).__init__()

    def explain(self):
        (
            luma_width_message,
            luma_height_message,
            color_diff_width_message,
            color_diff_height_message,
        ) = (
            " (not a factor of {})".format(frame_dimen)
            if component_dimen == 0 or (frame_dimen % component_dimen) != 0
            else ""
            for (component_dimen, frame_dimen) in [
                (self.luma_width, self.frame_width),
                (self.luma_height, self.frame_height),
                (self.color_diff_width, self.frame_width),
                (self.color_diff_height, self.frame_height),
            ]
        )

        return """
            The frame dimensions cannot be evenly divided by the current color
            difference sampling format and picture coding mode (11.6.2)

            Frame dimensions:

            * frame_width: {}
            * frame_height: {}

            The dimensions computed by picture_dimensions were:

            * luma_width: {}{}
            * luma_height: {}{}
            * color_diff_width: {}{}
            * color_diff_height: {}{}

            Was a frame size with an odd width or height used along with a
            non-4:4:4 color difference sampling mode or when pictures are
            fields?

            Was the source sampling mode (11.4.5) used instead of the picture
            coding mode (11.5) to determine the picture size?
        """.format(
            self.frame_width,
            self.frame_height,
            self.luma_width,
            luma_width_message,
            self.luma_height,
            luma_height_message,
            self.color_diff_width,
            color_diff_width_message,
            self.color_diff_height,
            color_diff_height_message,
        )


class NonConsecutivePictureNumbers(ConformanceError):
    """
    (12.2) and (14.2) Picture numbers for each picture must contain consecutive
    picture numbers (wrapping at 2**32).

    :py:attr:`last_picture_number_offset` contains the (byte_offset, next_bit)
    offset of the previous picture number in the sequence.

    :py:attr:`last_picture_number` contains the picture number of the previous
    picture in the sequence.

    :py:attr:`picture_number_offset` contains the (byte_offset, next_bit)
    offset of the offending picture number in the sequence.

    :py:attr:`picture_number` contains the picture number of the offending
    picture in the sequence.
    """

    def __init__(
        self,
        last_picture_number_offset,
        last_picture_number,
        picture_number_offset,
        picture_number,
    ):
        self.last_picture_number_offset = last_picture_number_offset
        self.last_picture_number = last_picture_number
        self.picture_number_offset = picture_number_offset
        self.picture_number = picture_number
        super(NonConsecutivePictureNumbers, self).__init__()

    def explain(self):
        return """
            Non-consecutive picture number, got {} after {} (12.2) and (14.2).

            Picture numbers must have consecutive, ascending integer values,
            wrapping at (2**32)-1 back to 0.

            * Previous picture number defined at bit offset {}
            * Current picture number defined at bit offset {}

            Was this picture taken from another sequence without being assigned
            a new picture number?
        """.format(
            self.picture_number,
            self.last_picture_number,
            to_bit_offset(*self.last_picture_number_offset),
            to_bit_offset(*self.picture_number_offset),
        )

    def bitstream_viewer_hint(self):
        return """
            To view the erroneous picture number definition:

                {{cmd}} {{file}} --offset {}

            To view the previous picture number definition:

                {{cmd}} {{file}} --offset {}
        """.format(
            to_bit_offset(*self.picture_number_offset),
            to_bit_offset(*self.last_picture_number_offset),
        )


class OddNumberOfFieldsInSequence(ConformanceError):
    """
    (10.4.3) When pictures are fields, a sequence must have a whole number of
    frames (i.e. an even number of fields).

    The actual number of fields/pictures in the offending sequence will be
    included as an argument.
    """

    def __init__(self, num_fields_in_sequence):
        self.num_fields_in_sequence = num_fields_in_sequence
        super(OddNumberOfFieldsInSequence, self).__init__()

    def explain(self):
        return """
            Sequence contains a non-whole number of frames ({} fields)
            (10.4.3).

            When pictures are fields, an even number of fields/pictures must be
            included in each sequence.

            Was the sequence truncated mid-frame?
        """.format(
            self.num_fields_in_sequence,
        )

    def bitstream_viewer_hint(self):
        return """
            To view the offending part of the bitstream:

                {cmd} {file} --from-offset 0 --to-offset {offset} --show picture_parse --show fragment_parse
        """


class EarliestFieldHasOddPictureNumber(ConformanceError):
    """
    (12.2) The earliest field of each frame must have an even picture number.

    The offending picture number will be included as an argument.
    """

    def __init__(self, picture_number):
        self.picture_number = picture_number
        super(EarliestFieldHasOddPictureNumber, self).__init__()

    def explain(self):
        return """
            First field in sequence has an odd picture number, {} (12.2).

            When pictures are fields, the earliest field/picture in each frame
            in the sequence must have an even picture number.

            Was the sequence truncated mid-frame?
        """.format(
            self.picture_number,
        )


class BadWaveletIndex(ConformanceError):
    """
    transform_parameters (12.4.1) has been given an unrecognised wavelet index.

    The exception argument will contain the offending wavelet index
    """

    def __init__(self, wavelet_index):
        self.wavelet_index = wavelet_index
        super(BadWaveletIndex, self).__init__()

    def explain(self):
        return """
            An invalid wavelet index, {:d}, was provided in the transform
            parameters (12.4.1).

            See (Table 12.1) for an enumeration of allowed values.
        """.format(
            self.wavelet_index
        )


class BadHOWaveletIndex(ConformanceError):
    """
    extended_transform_parameters (12.4.4.2) has been given an unrecognised
    wavelet index.

    The exception argument will contain the offending wavelet index
    """

    def __init__(self, wavelet_index_ho):
        self.wavelet_index_ho = wavelet_index_ho
        super(BadHOWaveletIndex, self).__init__()

    def explain(self):
        return """
            An invalid horizontal only wavelet index, {:d}, was provided in the
            extended transform parameters (12.4.4.2).

            See (Table 12.1) for an enumeration of allowed values.
        """.format(
            self.wavelet_index_ho
        )


class ZeroSlicesInCodedPicture(ConformanceError):
    """
    (12.4.5.2) slice_parameters must not allow either slice count to be zero.

    The exception argument will contain the offending slice counts
    """

    def __init__(self, slices_x, slices_y):
        self.slices_x = slices_x
        self.slices_y = slices_y
        super(ZeroSlicesInCodedPicture, self).__init__()

    def explain(self):
        return """
            Invalid slice count, {}x{}, specified in slice parameters
            (12.4.5.2).

            There must be at least one slice in either dimension.
        """.format(
            self.slices_x,
            self.slices_y,
        )


class SliceBytesHasZeroDenominator(ConformanceError):
    """
    (12.4.5.2) specifies that slice_bytes_denominator must not be zero (to
    avoid division by zero)

    The numerator is provided as an argument.
    """

    def __init__(self, slice_bytes_numerator):
        self.slice_bytes_numerator = slice_bytes_numerator
        super(SliceBytesHasZeroDenominator, self).__init__()

    def explain(self):
        return """
            Invalid slice bytes count, {}/0, in slice parameters (12.4.5.2).

            Division by zero.
        """.format(
            self.slice_bytes_numerator,
        )


class SliceBytesIsLessThanOne(ConformanceError):
    """
    (12.4.5.2) specifies that slice_bytes_numerator/slice_bytes_denominator
    must be greater or equal to one byte.

    The offending numerator and denominator is provided as an argument.
    """

    def __init__(self, slice_bytes_numerator, slice_bytes_denominator):
        self.slice_bytes_numerator = slice_bytes_numerator
        self.slice_bytes_denominator = slice_bytes_denominator
        super(SliceBytesIsLessThanOne, self).__init__()

    def explain(self):
        return """
            Slice bytes count, {}/{}, in slice parameters is less than one
            (12.4.5.2).

            Slices must be at least 1 byte.
        """.format(
            self.slice_bytes_numerator,
            self.slice_bytes_denominator,
        )


class NoQuantisationMatrixAvailable(ConformanceError):
    """
    (12.4.5.3) specifies that custom quantisation matrices must be used in
    cases where a default is not defined by the standard.

    The offending combination of wavelet_index, wavelet_index_ho, dwt_depth,
    and dwt_depth_ho are provided as arguments.
    """

    def __init__(self, wavelet_index, wavelet_index_ho, dwt_depth, dwt_depth_ho):
        self.wavelet_index = wavelet_index
        self.wavelet_index_ho = wavelet_index_ho
        self.dwt_depth = dwt_depth
        self.dwt_depth_ho = dwt_depth_ho
        super(NoQuantisationMatrixAvailable, self).__init__()

    def explain(self):
        return """
            A default quantisation matrix is not available for current
            transform and no custom quantisation matrix has been supplied
            (12.4.5.3).

            The current transform is defined as:

            * wavelet_index = {}
            * dwt_depth = {}
            * wavelet_index_ho = {}
            * dwt_depth_ho = {}
        """.format(
            known_wavelet_to_string(self.wavelet_index),
            self.dwt_depth,
            known_wavelet_to_string(self.wavelet_index_ho),
            self.dwt_depth_ho,
        )


class QuantisationMatrixValueNotAllowedInLevel(ConformanceError):
    """
    (C.3) A custom quantisation matrix value was used which was not allowed by the
    current level.

    The value and expected values (as a
    :py:class:`~vc2_conformance.constraint_table.ValueSet`) will be passed as
    arguments along with the current level constraint dictionary.
    """

    def __init__(self, value, allowed_values, level_constrained_values):
        self.value = value
        self.allowed_values = allowed_values
        self.level_constrained_values = level_constrained_values
        super(QuantisationMatrixValueNotAllowedInLevel, self).__init__()

    def explain(self):
        level = self.level_constrained_values["level"]

        return dedent(
            """
            Custom quantisation matrix contains a value, {}, outside the
            range {} allowed by the current level, {} ({}).

            The restriction above may be more constrained than expected due to
            one of the following previously encountered options:

            {}
        """
        ).format(
            self.value,
            self.allowed_values,
            level,
            LEVELS[level].standard,
            "\n".join(
                "* {} = {!r}".format(key, value)
                for key, value in self.level_constrained_values.items()
            ),
        )


class SliceSizeScalerIsZero(ConformanceError):
    """
    (12.4.5.2) A slice_size_scaler value of zero was given.
    """

    def explain(self):
        return """
            Slice parameter slice_size_scaler must not be zero (12.4.5.2)
        """


class InvalidSliceYLength(ConformanceError):
    """
    (13.5.3.1) ld_slice must have its slice_y_length value be within the length
    of the whole slice.

    The offending slice_y_length, the number of bytes allowed in the slice and
    the slice coordinates are provided as an argument.
    """

    def __init__(self, slice_y_length, slice_bytes, sx, sy):
        self.slice_y_length = slice_y_length
        self.slice_bytes = slice_bytes
        self.sx = sx
        self.sy = sy
        super(InvalidSliceYLength, self).__init__()

    def explain(self):
        slice_bits_left = 8 * self.slice_bytes

        # Account for qindex
        slice_bits_left -= 7

        # Account for length field
        length_bits = intlog2(slice_bits_left)
        slice_bits_left -= length_bits

        return """
            Low-delay slice_y_length value, {slice_y_length}, is out of range,
            expected a value no greater than {max_slice_y_length} (13.5.3.1).

            * The current slice (sx={sx}, sy={sy}) is {slice_bytes} bytes
              ({slice_bits} bits) long (see slice_bytes() (13.5.3.2)).
            * 7 bits are reserved for the qindex field.
            * intlog2({slice_minus_qindex_bits}) = {length_bits} bits are
              reserved for the slice_y_length field.
            * This leaves {max_slice_y_length} bits to split between the
              luminance and color difference components.

            Was the size of this slice correctly computed?

            Were the size of the qindex and slice_y_length fields accounted
            for?
        """.format(
            slice_y_length=self.slice_y_length,
            max_slice_y_length=slice_bits_left,
            sx=self.sx,
            sy=self.sy,
            slice_bytes=self.slice_bytes,
            slice_bits=self.slice_bytes * 8,
            slice_minus_qindex_bits=(self.slice_bytes * 8) - 7,
            length_bits=length_bits,
        )


class FragmentedPictureRestarted(ConformanceError):
    """
    (14.2) Not all of the slices in a fragmented picture arrived before a new
    fragment with fragment_slice_count==0 arrived.

    The (byte_offset, next_bit_offset) offset of the first fragment header in
    the incomplete picture and of this fragment header are included as
    arguments along with the number of slices received and remaining.
    """

    def __init__(
        self,
        initial_fragment_offset,
        this_fragment_offset,
        fragment_slices_received,
        fragment_slices_remaining,
    ):
        self.initial_fragment_offset = initial_fragment_offset
        self.this_fragment_offset = this_fragment_offset
        self.fragment_slices_received = fragment_slices_received
        self.fragment_slices_remaining = fragment_slices_remaining
        super(FragmentedPictureRestarted, self).__init__()

    def explain(self):
        return """
            A picture fragment with fragment_slice_count=0 was encountered
            while {} slice{} still outstanding (14.2).

            The previous fragmented picture started at bit offset {} and {} of
            {} expected slices were received before the current picture
            fragment with fragment_slice_count=0 arrived at bit offset {}.

            Was a picture fragment with fragment_slice_count=0 incorrectly used
            as padding while waiting for some picture slices to be ready?

            Were some picture fragments omitted when copying a fragmented
            picture from another sequence?
        """.format(
            self.fragment_slices_remaining,
            " is" if self.fragment_slices_remaining == 1 else "s are",
            to_bit_offset(*self.initial_fragment_offset),
            self.fragment_slices_received,
            self.fragment_slices_received + self.fragment_slices_remaining,
            to_bit_offset(*self.this_fragment_offset),
        )

    def bitstream_viewer_hint(self):
        return """
            To view the offending part of the bitstream:

                {{cmd}} {{file}} --from-offset {} --to_offset {{offset}} --show fragment_parse --hide slice
        """.format(
            to_bit_offset(*self.initial_fragment_offset)
        )


class SequenceContainsIncompleteFragmentedPicture(ConformanceError):
    """
    (14.2) Sequences must not terminate mid-fragmented picture.

    The (byte_offset, next_bit_offset) offset of the first fragment header in
    the incomplete picture is included an argument along with the number of
    slices received and remaining.
    """

    def __init__(
        self,
        initial_fragment_offset,
        fragment_slices_received,
        fragment_slices_remaining,
    ):
        self.initial_fragment_offset = initial_fragment_offset
        self.fragment_slices_received = fragment_slices_received
        self.fragment_slices_remaining = fragment_slices_remaining
        super(SequenceContainsIncompleteFragmentedPicture, self).__init__()

    def explain(self):
        return """
            A sequence terminated while {} slice{} still outstanding in a
            fragmented picture (14.2).

            The fragmented picture started at bit offset {} and {} of
            {} expected slices were received before the end of the sequence was
            encountered.

            Were some picture fragments omitted when copying a fragmented
            picture from another sequence?
        """.format(
            self.fragment_slices_remaining,
            " is" if self.fragment_slices_remaining == 1 else "s are",
            to_bit_offset(*self.initial_fragment_offset),
            self.fragment_slices_received,
            self.fragment_slices_received + self.fragment_slices_remaining,
        )

    def bitstream_viewer_hint(self):
        return """
            To view the offending part of the bitstream:

                {{cmd}} {{file}} --from-offset {} --to_offset {{offset}} --show parse_info --show fragment_parse --hide slice
        """.format(
            to_bit_offset(*self.initial_fragment_offset)
        )


class PictureInterleavedWithFragmentedPicture(ConformanceError):
    """
    (14.2) Picture data units may not be interleaved with in-progress
    fragmented pictures.

    The (byte_offset, next_bit_offset) offset of the first fragment header in
    the incomplete picture and the offending picture data unit's header is
    included an argument along with the number of slices received and remaining
    for the fragmented picture.
    """

    def __init__(
        self,
        initial_fragment_offset,
        this_offset,
        fragment_slices_received,
        fragment_slices_remaining,
    ):
        self.initial_fragment_offset = initial_fragment_offset
        self.this_offset = this_offset
        self.fragment_slices_received = fragment_slices_received
        self.fragment_slices_remaining = fragment_slices_remaining
        super(PictureInterleavedWithFragmentedPicture, self).__init__()

    def explain(self):
        return """
            A non-fragmented picture was encountered while {} slice{} still
            outstanding in a fragmented picture (14.2).

            The fragmented picture started at bit offset {} and {} of {}
            expected slices were received before the non-fragmented picture was
            encountered at bit offset {}.

            Were some picture fragments omitted when copying a fragmented
            picture from another sequence?
        """.format(
            self.fragment_slices_remaining,
            " is" if self.fragment_slices_remaining == 1 else "s are",
            to_bit_offset(*self.initial_fragment_offset),
            self.fragment_slices_received,
            self.fragment_slices_received + self.fragment_slices_remaining,
            to_bit_offset(*self.this_offset),
        )

    def bitstream_viewer_hint(self):
        return """
            To view the offending part of the bitstream:

                {{cmd}} {{file}} --from-offset {} --to_offset {{offset}} --show parse_info --show fragment_parse --show picture_parse --hide slice
        """.format(
            to_bit_offset(*self.initial_fragment_offset)
        )


class PictureNumberChangedMidFragmentedPicture(ConformanceError):
    """
    (14.2) Picture numbers in fragment_headers which are part of the same
    fragmented picture must be identical.

    :py:attr:`last_picture_number_offset` contains the (byte_offset, next_bit)
    offset of the previous picture number in the sequence.

    :py:attr:`last_picture_number` contains the picture number of the previous
    fragment in the sequence.

    :py:attr:`picture_number_offset` contains the (byte_offset, next_bit)
    offset of the offending picture number in the sequence.

    :py:attr:`picture_number` contains the picture number of the offending
    fragment in the sequence.
    """

    def __init__(
        self,
        last_picture_number_offset,
        last_picture_number,
        picture_number_offset,
        picture_number,
    ):
        self.last_picture_number_offset = last_picture_number_offset
        self.last_picture_number = last_picture_number
        self.picture_number_offset = picture_number_offset
        self.picture_number = picture_number
        super(PictureNumberChangedMidFragmentedPicture, self).__init__()

    def explain(self):
        return """
            The picture number changed from {} to {} within the same fragmented
            picture (14.2).

            The previous fragment in this fragmented picture defined its
            picture number at bit offset {}. The current fragment provided a
            different picture number at bit offset {}.

            Was the picture number incremented for every fragment rather than
            for every complete picture in the stream?
        """.format(
            self.last_picture_number,
            self.picture_number,
            to_bit_offset(*self.last_picture_number_offset),
            to_bit_offset(*self.picture_number_offset),
        )

    def bitstream_viewer_hint(self):
        return """
            To view the offending part of the bitstream:

                {{cmd}} {{file}} --from-offset {} --to_offset {{offset}} --show fragment_parse --hide slice
        """.format(
            to_bit_offset(*self.last_picture_number_offset),
        )


class TooManySlicesInFragmentedPicture(ConformanceError):
    """
    (14.2) A fragmented picture must not contain more slices than necessary.

    The (byte_offset, next_bit_offset) offset of the first fragment header in
    the picture and the offending fragment's header is
    included an argument along with the number of slices received, remaining
    and included in the offending fragment.
    """

    def __init__(
        self,
        initial_fragment_offset,
        this_fragment_offset,
        fragment_slices_received,
        fragment_slices_remaining,
        fragment_slice_count,
    ):
        self.initial_fragment_offset = initial_fragment_offset
        self.this_fragment_offset = this_fragment_offset
        self.fragment_slices_received = fragment_slices_received
        self.fragment_slices_remaining = fragment_slices_remaining
        self.fragment_slice_count = fragment_slice_count
        super(TooManySlicesInFragmentedPicture, self).__init__()

    def explain(self):
        total_slices = self.fragment_slices_received + self.fragment_slices_remaining

        return """
            The current fragmented picture contains too many picture slices
            (14.2).

            This fragmented picture (starting at bit offset {}) consists of a
            total of {} picture slices. {} slices have already been received
            but the current fragment (at bit offset {}) contains {} slices
            while only {} more are expected.
        """.format(
            to_bit_offset(*self.initial_fragment_offset),
            total_slices,
            self.fragment_slices_received,
            to_bit_offset(*self.this_fragment_offset),
            self.fragment_slice_count,
            self.fragment_slices_remaining,
        )

    def bitstream_viewer_hint(self):
        return """
            To view the offending part of the bitstream:

                {{cmd}} {{file}} --from-offset {} --to_offset {{offset}} --show fragment_parse --hide slice
        """.format(
            to_bit_offset(*self.initial_fragment_offset),
        )


class FragmentSlicesNotContiguous(ConformanceError):
    """
    (14.2) A fragmented picture must contain every slice in the picture exactly
    once, provided in raster-scan order and starting at (sx=0, sy=0).

    The (byte_offset, next_bit_offset) offset of the first fragment header in
    the picture and the offending fragment's header is included an argument
    along with the offending slice coordinates and expected slice coordinates.
    """

    def __init__(
        self,
        initial_fragment_offset,
        this_fragment_offset,
        fragment_x_offset,
        fragment_y_offset,
        expected_fragment_x_offset,
        expected_fragment_y_offset,
    ):
        self.initial_fragment_offset = initial_fragment_offset
        self.this_fragment_offset = this_fragment_offset
        self.fragment_x_offset = fragment_x_offset
        self.fragment_y_offset = fragment_y_offset
        self.expected_fragment_x_offset = expected_fragment_x_offset
        self.expected_fragment_y_offset = expected_fragment_y_offset
        super(FragmentSlicesNotContiguous, self).__init__()

    def explain(self):
        return """
            The current picture fragment's slices are non-contiguous (14.2).

            The fragmented picture starting at bit offset {} contains a
            fragment at bit offset {} with an unexpected start offset:

            * fragment_x_offset = {} (should be {})
            * fragment_y_offset = {} (should be {})

            Fragmented pictures must include picture slices in raster-scan
            order starting with sx=0, sy=0 and without leaving any gaps.
        """.format(
            to_bit_offset(*self.initial_fragment_offset),
            to_bit_offset(*self.this_fragment_offset),
            self.fragment_x_offset,
            self.expected_fragment_x_offset,
            self.fragment_y_offset,
            self.expected_fragment_y_offset,
        )

    def bitstream_viewer_hint(self):
        return """
            To view the offending part of the bitstream:

                {{cmd}} {{file}} --from-offset {} --to_offset {{offset}} --show fragment_parse --hide slice
        """.format(
            to_bit_offset(*self.initial_fragment_offset),
        )


class PresetFrameRateNotSupportedByVersion(ConformanceError):
    """
    preset_frame_rate (11.4.6) was given a value not supported by stream
    version specified specified (11.2.2).

    The exception argument will contain the offending index and specified
    version number.
    """

    def __init__(self, index, major_version):
        self.index = index
        self.major_version = major_version
        super(PresetFrameRateNotSupportedByVersion, self).__init__()

    def explain(self):
        return """
            The preset frame rate index {:d} ({} FPS) (11.4.6) is only supported
            when major_version is at least {} but major_version is {}.  See
            (11.2.2).
        """.format(
            self.index,
            Fraction(*PRESET_FRAME_RATES[self.index]),
            preset_frame_rate_version_implication(self.index),
            self.major_version,
        )


class PresetSignalRangeNotSupportedByVersion(ConformanceError):
    """
    preset_signal_range (11.4.9) was given a value not supported by stream
    version specified specified (11.2.2).

    The exception argument will contain the offending index and specified
    version number.
    """

    def __init__(self, index, major_version):
        self.index = index
        self.major_version = major_version
        super(PresetSignalRangeNotSupportedByVersion, self).__init__()

    def explain(self):
        return """
            The preset signal range index {:d} ({}) (11.4.9) is only supported
            when major_version is at least {} but major_version is {}. See
            (11.2.2).
        """.format(
            self.index,
            PresetSignalRanges(self.index).name,
            preset_signal_range_version_implication(self.index),
            self.major_version,
        )


class PresetColorSpecNotSupportedByVersion(ConformanceError):
    """
    preset_color_spec (11.4.10.1) was given a value not supported by stream
    version specified specified (11.2.2).

    The exception argument will contain the offending index and specified
    version number.
    """

    def __init__(self, index, major_version):
        self.index = index
        self.major_version = major_version
        super(PresetColorSpecNotSupportedByVersion, self).__init__()

    def explain(self):
        return """
            The preset color spec index {:d} ({}) (11.4.10.1) is only supported
            when major_version is at least {} but major_version is {}.  See
            (11.2.2).
        """.format(
            self.index,
            PresetColorSpecs(self.index).name,
            preset_color_spec_version_implication(self.index),
            self.major_version,
        )


class PresetColorPrimariesNotSupportedByVersion(ConformanceError):
    """
    preset_color_primaries (11.4.10.2) was given a value not supported by
    stream version specified specified (11.2.2).

    The exception argument will contain the offending index and specified
    version number.
    """

    def __init__(self, index, major_version):
        self.index = index
        self.major_version = major_version
        super(PresetColorPrimariesNotSupportedByVersion, self).__init__()

    def explain(self):
        return """
            The preset color primaries index {:d} ({}) (11.4.10.2) is only
            supported when major_version is at least {} but major_version is
            {}. See (11.2.2).
        """.format(
            self.index,
            PresetColorPrimaries(self.index).name,
            preset_color_primaries_version_implication(self.index),
            self.major_version,
        )


class PresetColorMatrixNotSupportedByVersion(ConformanceError):
    """
    preset_color_matrix (11.4.10.3) was given a value not supported by
    stream version specified specified (11.2.2).

    The exception argument will contain the offending index and specified
    version number.
    """

    def __init__(self, index, major_version):
        self.index = index
        self.major_version = major_version
        super(PresetColorMatrixNotSupportedByVersion, self).__init__()

    def explain(self):
        return """
            The preset color matrix index {:d} ({}) (11.4.10.3) is only
            supported when major_version is at least {} but major_version is
            {}. See (11.2.2).
        """.format(
            self.index,
            PresetColorMatrices(self.index).name,
            preset_color_matrix_version_implication(self.index),
            self.major_version,
        )


class PresetTransferFunctionNotSupportedByVersion(ConformanceError):
    """
    preset_transfer_function (11.4.10.4) was given a value not supported by
    stream version specified specified (11.2.2).

    The exception argument will contain the offending index and specified
    version number.
    """

    def __init__(self, index, major_version):
        self.index = index
        self.major_version = major_version
        super(PresetTransferFunctionNotSupportedByVersion, self).__init__()

    def explain(self):
        return """
            The preset transfer function index {:d} ({}) (11.4.10.4) is only
            supported when major_version is at least {} but major_version is
            {}. See (11.2.2).
        """.format(
            self.index,
            PresetTransferFunctions(self.index).name,
            preset_transfer_function_version_implication(self.index),
            self.major_version,
        )


class ParseCodeNotSupportedByVersion(ConformanceError):
    """
    parse_code (10.5.1) specified a data unit type which is not supported by
    stream version specified specified (11.2.2).

    The exception argument will contain the parse code and specified version number.
    """

    def __init__(self, parse_code, major_version):
        self.parse_code = parse_code
        self.major_version = major_version
        super(ParseCodeNotSupportedByVersion, self).__init__()

    def explain(self):
        return """
            The parse code (10.5.1) specifies a {} data unit but this is only
            supported when major_version is at least {} but major_version is
            {}. See (11.2.2).
        """.format(
            known_parse_code_to_string(self.parse_code),
            parse_code_version_implication(self.parse_code),
            self.major_version,
        )


class ProfileNotSupportedByVersion(ConformanceError):
    """
    parse_parameters (11.2.1) specified a profile which is not supported by
    stream version specified specified (11.2.2).

    The exception argument will contain the profile and specified version number.
    """

    def __init__(self, profile, major_version):
        self.profile = profile
        self.major_version = major_version
        super(ProfileNotSupportedByVersion, self).__init__()

    def explain(self):
        return """
            The {} profile is only supported when major_version is at least {}
            but major_version is {}. See (11.2.2).
        """.format(
            known_profile_to_string(self.profile),
            profile_version_implication(self.profile),
            self.major_version,
        )


class MajorVersionTooLow(ConformanceError):
    """
    Thrown when a sequence specifies a major_version (11.2.1) which is less
    than 1 as required by (11.2.2).

    The exception argument will contain the major_version given in the
    sequence.
    """

    def __init__(self, major_version):
        self.major_version = major_version
        super(MajorVersionTooLow, self).__init__()

    def explain(self):
        return """
            The major_version (11.2.1) must be at least {} but {} was given
            instead, see (11.2.2).
        """.format(
            MINIMUM_MAJOR_VERSION,
            self.major_version,
        )


class MinorVersionNotZero(ConformanceError):
    """
    Thrown when a sequence specifies a minor_version (11.2.1) which is not 0 as
    required by (11.2.2).

    The exception argument will contain the minor_version given in the
    sequence.
    """

    def __init__(self, minor_version):
        self.minor_version = minor_version
        super(MinorVersionNotZero, self).__init__()

    def explain(self):
        return """
            The minor_version (11.2.1) must be 0 but {} was given instead, see
            (11.2.2).
        """.format(
            self.minor_version,
        )


class MajorVersionTooHigh(ConformanceError):
    """
    Thrown when a sequence specifies a major_version (11.2.1) which is higher
    than required for the features actually used in the sequence.

    The exception argument will contain the major_version given in the
    sequence and the expected major_version.
    """

    def __init__(self, major_version, expected_major_version):
        self.major_version = major_version
        self.expected_major_version = expected_major_version
        super(MajorVersionTooHigh, self).__init__()

    def explain(self):
        return """
            The major_version (11.2.1) specified, {}, is too high: only
            features requiring major_version {} were used in the sequence, see
            (11.2.2).
        """.format(
            self.major_version,
            self.expected_major_version,
        )
