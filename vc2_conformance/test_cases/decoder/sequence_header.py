"""
Tests which verify sequence header contents (11) are correctly read.
"""

from copy import deepcopy

from vc2_data_tables import ParseCodes

from vc2_conformance.bitstream import Stream

from vc2_conformance.test_cases import (
    TestCase,
    decoder_test_case_generator,
)

from vc2_conformance.picture_generators import (
    static_sprite,
    repeat_pictures,
)

from vc2_conformance.encoder import (
    IncompatibleLevelAndDataUnitError,
    iter_sequence_headers,
    make_sequence,
)


def replace_sequence_headers(sequence, sequence_header):
    r"""
    Replace the :py:class:`SequenceHeaders
    <vc2_conformance.bitstream.SequenceHeader>` in a
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
    **Tests the decoder can decode different encodings of the video format
    metadata.**

    This series of test cases each contain the same source parameters (11.4),
    but in different ways.

    ``source_parameters_encodings[custom_flags_combination_?_base_video_format_?]``
        For these test cases, the base video format which most closely matches
        the desired video format is used. Each test case incrementally checks
        that source parameters may be explicitly set to their desired values
        (e.g. by setting ``custom_*_flag`` bits to 1).

    ``source_parameters_encodings[base_video_format_?]``
        These test cases, check that other base video formats may be used (and
        overridden) to specify the desired video format. Each of these test
        cases will explicitly specify as few video parameters as possible (e.g.
        setting as many ``custom_*_flag`` fields to 0 as possible).

    .. tip::

        The :ref:`vc2-bitstream-viewer` may be used to display the encoding
        used in a given test case as follows::

            $ vc2-bitstream-viewer --show sequence_header path/to/test_case.vc2

    .. note::

        Some VC-2 levels constrain the allowed encoding of source parameters in
        the bit stream and so fewer test cases will be produced in this
        instance.

    .. note::

        Not all base video formats can be used as the basis for encoding a
        specific video format. For example, the 'top field first' flag (11.3)
        set by a base video format cannot be overridden. As a result, test
        cases will not include every base video format index.

    """
    # Generate a base sequence in which we'll replace the sequence headers
    # later
    base_sequence = make_sequence(
        codec_features,
        static_sprite(
            codec_features["video_parameters"],
            codec_features["picture_coding_mode"],
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
                Stream(
                    sequences=[replace_sequence_headers(base_sequence, sequence_header)]
                ),
                "custom_flags_combination_{}_base_video_format_{:d}".format(
                    i + 1,
                    base_video_format,
                ),
            )
        elif first_example_of_base_video_format:
            yield TestCase(
                Stream(
                    sequences=[replace_sequence_headers(base_sequence, sequence_header)]
                ),
                "base_video_format_{:d}".format(base_video_format),
            )


@decoder_test_case_generator
def repeated_sequence_headers(codec_features):
    """
    **Tests the decoder can handle a stream with repeated sequence headers.**

    This test case consists of a sequence containing two frames in which the
    sequence header is repeated before every picture.

    This test may be omitted if the VC-2 level prohibits the repetition of the
    sequence header.
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
    except IncompatibleLevelAndDataUnitError:
        # Do not try to force levels which don't support this level of sequence
        # header interleaving to accept it.
        return None

    return Stream(sequences=[sequence])
