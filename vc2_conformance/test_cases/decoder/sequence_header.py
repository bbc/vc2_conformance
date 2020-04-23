"""
Tests which verify sequence header contents (11) are correctly read.
"""

from copy import deepcopy

from vc2_data_tables import ParseCodes

from vc2_conformance.test_cases import (
    TestCase,
    decoder_test_case_generator,
)

from vc2_conformance.symbol_re import ImpossibleSequenceError

from vc2_conformance.picture_generators import (
    static_sprite,
    repeat_pictures,
)

from vc2_conformance.encoder import (
    iter_sequence_headers,
    make_sequence,
)


def replace_sequence_headers(sequence, sequence_header):
    r"""
    Replace the :py:class:`~vc2_conformance.bitstream.SequenceHeader`\ s in a
    :py:class:`~vc2_conformance.bitstream.Sequence` with the provided
    alternative.

    A new sequence is returned and the old sequence left unmodified. Likewise
    the ``sequence_header`` argument will be copied.
    """
    sequence = deepcopy(sequence)
    for data_unit in sequence["data_units"]:
        if data_unit["parse_info"]["parse_code"] == ParseCodes.sequence_header:
            data_unit["sequence_header"] = deepcopy(sequence_header)

    return sequence


@decoder_test_case_generator
def source_parameters_encodings(codec_features):
    """
    This series of test cases contain examples of different ways the source
    parameters (11.4) may be encoded in a stream.

    These test cases range from relying as much as possible on base video
    formats (11.3) to explicitly specifying every parameter using the various
    ``custom_*_flag`` options. In every example, the video parameters encoded
    are identical.
    """
    # Generate a base sequence in which we'll replace the sequence headers
    # later
    base_sequence = make_sequence(
        codec_features,
        static_sprite(
            codec_features["video_parameters"], codec_features["picture_coding_mode"],
        ),
    )

    # To keep the number of tests sensible, we'll include all sequence header
    # encodings using the best-matching base video format followed by the
    # least-custom-overridden encoding for all other base video formats. This
    # checks out as many 'custom' flags as possible (against the best-matching
    # base video format) and also checks (as best possible) the other base
    # video format values are correct.
    best_base_video_format = None
    last_base_video_format = None
    for i, sequence_header in enumerate(iter_sequence_headers(codec_features)):
        base_video_format = sequence_header["base_video_format"]

        # The iter_sequence_headers function returns headers with the best
        # matching base video format first
        if best_base_video_format is None:
            best_base_video_format = base_video_format

        # The iter_source_parameter_options produces sequence headers with
        # base video formats grouped consecutively. The first example of each
        # will use the fewest possible 'custom' flags and therefore best tests
        # that the base video format parameters are correct in the decoder.
        first_example_of_base_video_format = base_video_format != last_base_video_format
        last_base_video_format = base_video_format

        if base_video_format == best_base_video_format:
            yield TestCase(
                replace_sequence_headers(base_sequence, sequence_header),
                "custom_flags_combination_{}_base_video_format_{:d}".format(
                    i + 1, base_video_format,
                ),
            )
        elif first_example_of_base_video_format:
            yield TestCase(
                replace_sequence_headers(base_sequence, sequence_header),
                "base_video_format_{:d}".format(base_video_format),
            )


@decoder_test_case_generator
def repeated_sequence_headers(codec_features):
    """
    This test case ensures that a decoder can handle streams which include more
    than one sequence header.
    """
    try:
        # Generate a base sequence in which we'll replace the sequence headers
        # later. We ensure we have at least two pictures to ensure we get
        # pictures and sequence headers being interleaved.
        sequence = make_sequence(
            codec_features,
            repeat_pictures(
                static_sprite(
                    codec_features["video_parameters"],
                    codec_features["picture_coding_mode"],
                ),
                2,
            ),
            # Force an extra sequence header between every data unit
            "(sequence_header .)+",
        )
    except ImpossibleSequenceError:
        # Do not try to force levels which don't support this level of sequence
        # header interleaving to accept it.
        return

    yield sequence
