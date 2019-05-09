import pytest

from io import BytesIO

from vc2_conformance.state import State

from vc2_conformance import decoder


class TestInitIO(object):

    def test_non_empty_file(self):
        f = BytesIO(b"\xAA\xFF")
        state = State()
        decoder.init_io(state, f)
        assert decoder.read_nbits(state, 16) == 0xAAFF
    
    def test_empty_file(self):
        f = BytesIO()
        state = State()
        decoder.init_io(state, f)
        assert state["next_bit"] == 7
        assert state["current_byte"] is None
        
        # Shouldn't crash!
        decoder.byte_align(state)
        assert state["next_bit"] == 7
        assert state["current_byte"] is None


@pytest.mark.parametrize("func,args", [
    (decoder.read_bit, ()),
    (decoder.read_bool, ()),
    (decoder.read_nbits, (8, )),
    (decoder.read_uint_lit, (1, )),
    (decoder.read_bitb, ()),
    (decoder.read_boolb, ()),
    (decoder.flush_inputb, ()),
    (decoder.read_uint, ()),
    (decoder.read_uintb, ()),
    (decoder.read_sint, ()),
    (decoder.read_sintb, ()),
])
def test_read_past_eof_crashes(func, args):
    f = BytesIO()
    state = State(bits_left=1)
    decoder.init_io(state, f)
    
    with pytest.raises(decoder.UnexpectedEndOfStream):
        func(state, *args)
