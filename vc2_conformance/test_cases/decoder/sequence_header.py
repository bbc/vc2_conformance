"""
Tests which verify sequence header contents (11) are correctly read.
"""

from copy import deepcopy

from vc2_data_tables import ParseCodes

from vc2_conformance.test_cases import (
    TestCase,
    decoder_test_case_generator,
)

from vc2_conformance.bitstream import SequenceHeader

from vc2_conformance.video_parameters import set_source_defaults

from vc2_conformance.picture_generators import static_sprite

from vc2_conformance.encoder import (
    rank_base_video_format_similarity,
    iter_source_parameter_options,
    make_sequence,
)


def replace_sequence_header_options(
    sequence,
    base_video_format,
    source_parameters,
):
    r"""
    Replace the :py:class:`~vc2_data_tables.BaseVideoFormats` and
    :py:class:`~vc2_conformance.bitstream.SourceParameters` values of all
    :py:class:`~vc2_conformance.bitstream.SequenceHeader`\ s in a
    :py:class:`~vc2_conformance.bitstream.Sequence`.
    
    A new sequence is returned and the old sequence left unmodified. Likewise
    the ``source_parameters`` argument will be copied into the new sequence and
    not referenced.
    """
    sequence = deepcopy(sequence)
    for data_unit in sequence["data_units"]:
        if data_unit["parse_info"]["parse_code"] == ParseCodes.sequence_header:
            sequence_header = data_unit["sequence_header"]
            sequence_header["base_video_format"] = base_video_format
            sequence_header["video_parameters"] = deepcopy(source_parameters)
    
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
            codec_features["video_parameters"],
            codec_features["picture_coding_mode"],
        ),
    )
    
    base_video_formats = rank_base_video_format_similarity(
        codec_features["video_parameters"],
    )
    
    # Try using every possible setting of all custom override flags, starting
    # with the mostly closely matched base video format available.
    best_base_video_format = base_video_formats[0]
    source_parameter_sets = list(iter_source_parameter_options(
        set_source_defaults(best_base_video_format),
        codec_features["video_parameters"],
    ))
    for i, source_parameters in enumerate(source_parameter_sets):
        yield TestCase(
            replace_sequence_header_options(
                base_sequence,
                best_base_video_format,
                source_parameters,
            ),
            "custom_flags_combination_{}_of_{}_base_video_format_{:d}".format(
                i + 1,
                len(source_parameter_sets),
                best_base_video_format,
            )
        )
    
    # Try using all of the other base video formats (and using as few custom
    # overrides as possible to ensure the base format is supported correctly).
    for base_video_format in sorted(base_video_formats[1:]):
        source_parameters = next(iter(iter_source_parameter_options(
            set_source_defaults(base_video_format),
            codec_features["video_parameters"],
        )))
        yield TestCase(
            replace_sequence_header_options(
                base_sequence,
                base_video_format,
                source_parameters,
            ),
            "base_video_format_{:d}".format(
                base_video_format,
            )
        )
