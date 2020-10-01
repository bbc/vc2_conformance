"""
Tests which verify that codecs correctly ignore padding data units (10.4.5).
"""

from copy import deepcopy

from vc2_data_tables import ParseCodes

from vc2_conformance.bitstream import Stream

from vc2_conformance.test_cases import (
    TestCase,
    decoder_test_case_generator,
)

from vc2_conformance.picture_generators import mid_gray, repeat_pictures

from vc2_conformance.encoder import (
    make_sequence,
    IncompatibleLevelAndDataUnitError,
)

from vc2_conformance.test_cases.decoder.common import make_dummy_end_of_sequence


def replace_padding_data(sequence, bytes):
    """
    Replace the bytes in all :py:class:`~vc2_conformance.bitstream.Padding`
    data units in a :py:class:`~vc2_conformance.bitstream.Sequence`.

    A new sequence is returned and the old sequence left unmodified.
    """
    sequence = deepcopy(sequence)
    for data_unit in sequence["data_units"]:
        if data_unit["parse_info"]["parse_code"] == ParseCodes.padding_data:
            data_unit["padding"]["bytes"] = bytes

    return sequence


@decoder_test_case_generator
def padding_data(codec_features):
    """
    **Tests that the contents of padding data units are ignored.**

    This test case consists of a sequence containing two blank frames in which
    every-other data unit is a padding data unit (10.4.5) of various lengths
    and contents (described below).

    ``padding_data[empty]``
        Padding data units containing zero padding bytes (i.e. just consisting
        of a parse info header).

    ``padding_data[zero]``
        Padding data units containing 32 bytes set to 0x00.

    ``padding_data[non_zero]``
        Padding data units containing 32 bytes containing the ASCII encoding of
        the text ``Ignore this padding data please!``.

    ``padding_data[dummy_end_of_sequence]``
        Padding data units containing 32 bytes containing an encoding of an end
        of sequence data unit (10.4.1).

    Where padding data units are not permitted by the VC-2 level in use, these
    test cases are omitted.
    """
    # Generate a base sequence in which we'll modify the padding data units. We
    # ensure there are always at least two pictures in the sequences to make
    # premature termination obvious.
    try:
        base_sequence = make_sequence(
            codec_features,
            repeat_pictures(
                mid_gray(
                    codec_features["video_parameters"],
                    codec_features["picture_coding_mode"],
                ),
                2,
            ),
            # Insert padding data between every data unit
            "sequence_header (padding_data .)* padding_data end_of_sequence $",
        )
    except IncompatibleLevelAndDataUnitError:
        # Padding not allowed in the supplied video format so just skip this
        # test
        return

    for description, data in [
        (
            "empty",
            b"",
        ),
        (
            "zero",
            b"\x00" * 32,
        ),
        (
            "non_zero",
            b"Ignore this padding data please!",
        ),
        (
            "dummy_end_of_sequence",
            make_dummy_end_of_sequence().ljust(32, b"\x00"),
        ),
    ]:
        yield TestCase(
            Stream(sequences=[replace_padding_data(base_sequence, data)]),
            description,
        )
