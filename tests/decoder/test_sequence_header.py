import pytest

from decoder_test_utils import seriallise_to_bytes, bytes_to_state

from vc2_conformance import bitstream
from vc2_conformance import tables
from vc2_conformance import decoder


def sequence_header_to_bytes(**kwargs):
    """
    Seriallise a SequenceHeader block, returning a bytes object.
    """
    return seriallise_to_bytes(
        bitstream.SequenceHeader(**kwargs),
        bitstream.sequence_header,
    )


def test_sequence_header_byte_for_byte_identical():
    sh1 = sequence_header_to_bytes(
        parse_parameters=bitstream.ParseParameters(major_version=3),
    )
    sh2 = sequence_header_to_bytes(
        parse_parameters=bitstream.ParseParameters(major_version=2),
    )
    
    state = bytes_to_state(sh1 + sh1 + sh2)
    
    decoder.sequence_header(state)
    decoder.sequence_header(state)
    with pytest.raises(decoder.SequenceHeaderChangedMidSequence) as exc_info:
        decoder.sequence_header(state)
    
    assert exc_info.value.last_sequence_header_offset == len(sh1)
    assert exc_info.value.last_sequence_header_bytes == sh1
    assert exc_info.value.this_sequence_header_offset == len(sh1)*2
    assert exc_info.value.this_sequence_header_bytes == sh2
