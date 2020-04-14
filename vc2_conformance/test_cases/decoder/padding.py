"""
Tests which verify that codecs correctly ignore padding data units (10.4.5).
"""

from copy import deepcopy

from vc2_data_tables import ParseCodes

from vc2_conformance.symbol_re import ImpossibleSequenceError

from vc2_conformance.test_cases import (
    TestCase,
    decoder_test_case_generator,
)

from vc2_conformance.picture_generators import mid_gray, repeat_pictures

from vc2_conformance.encoder import make_sequence

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
    This series of test cases verify that padding data units in a sequence are
    correctly ignored.

    Sequences are generated in which every-other data unit is a padding data
    unit. These padding data units are filled with the following (in different
    test sequences):

    * Empty
    * 32 bytes of zeros
    * 32 bytes of non-zero data
    * 32 bytes containing a the values for an end-of-sequence data unit (which
      must be ignored!).

    Where padding data is not permitted by the VC-2 level chosen, no test cases
    will be generated.
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
    except ImpossibleSequenceError:
        # Padding not allowed in the supplied video format so just skip this
        # test
        return

    for description, data in [
        ("empty", b"",),
        ("zero", b"\x00" * 32,),
        ("non_zero", b"Ignore this padding data please!",),
        ("dummy_end_of_sequence", make_dummy_end_of_sequence().ljust(32, b"\x00"),),
    ]:
        yield TestCase(
            replace_padding_data(base_sequence, data), description,
        )
