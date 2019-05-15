import pytest

from decoder_test_utils import seriallise_to_bytes, bytes_to_state

from vc2_conformance.state import reset_state
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
        parse_parameters=bitstream.ParseParameters(minor_version=0),
    )
    sh2 = sequence_header_to_bytes(
        parse_parameters=bitstream.ParseParameters(minor_version=1),
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


def parse_parameters_to_bytes(**kwargs):
    """
    Seriallise a ParseParameters block, returning a bytes object.
    """
    return seriallise_to_bytes(
        bitstream.ParseParameters(**kwargs),
        bitstream.parse_parameters,
    )

@pytest.mark.parametrize("kwargs1,kwargs2,exc_type", [
    (
        {"profile": tables.Profiles.high_quality},
        {"profile": tables.Profiles.low_delay},
        decoder.ProfileChanged,
    ),
    (
        {"level": tables.Levels.unconstrained},
        {"level": tables.Levels.hd},
        decoder.LevelChanged,
    ),
])
def test_profile_and_level_must_not_change_between_sequences(kwargs1, kwargs2, exc_type):
    pp1 = parse_parameters_to_bytes(**kwargs1)
    pp2 = parse_parameters_to_bytes(**kwargs2)
    
    state = bytes_to_state(pp1 + pp1 + pp2)
    
    decoder.parse_parameters(state)
    reset_state(state)
    last_pp_offset = decoder.tell(state)
    decoder.parse_parameters(state)
    reset_state(state)
    this_pp_offset = decoder.tell(state)
    with pytest.raises(exc_type) as exc_info:
        decoder.parse_parameters(state)
    
    assert exc_info.value.last_parse_parameters_offset == last_pp_offset
    assert exc_info.value.this_parse_parameters_offset == this_pp_offset
    
    change_type = list(kwargs1.keys())[0]
    change_value1 = list(kwargs1.values())[0]
    change_value2 = list(kwargs2.values())[0]
    assert getattr(exc_info.value, "last_" + change_type) == change_value1
    assert getattr(exc_info.value, "this_" + change_type) == change_value2

def test_profile_must_be_valid():
    pp = parse_parameters_to_bytes(profile=1234567890)
    state = bytes_to_state(pp)
    
    with pytest.raises(decoder.BadProfile) as exc_info:
        decoder.parse_parameters(state)
    
    assert exc_info.value.profile == 1234567890

def test_level_must_be_valid():
    pp = parse_parameters_to_bytes(level=1234567890)
    state = bytes_to_state(pp)
    
    with pytest.raises(decoder.BadLevel) as exc_info:
        decoder.parse_parameters(state)
    
    assert exc_info.value.level == 1234567890
