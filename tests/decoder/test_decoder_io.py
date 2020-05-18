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


@pytest.mark.parametrize(
    "func,args",
    [
        (decoder.read_bit, ()),
        (decoder.read_bool, ()),
        (decoder.read_nbits, (8,)),
        (decoder.read_uint_lit, (1,)),
        (decoder.read_bitb, ()),
        (decoder.read_boolb, ()),
        (decoder.flush_inputb, ()),
        (decoder.read_uint, ()),
        (decoder.read_uintb, ()),
        (decoder.read_sint, ()),
        (decoder.read_sintb, ()),
    ],
)
def test_read_past_eof_crashes(func, args):
    f = BytesIO()
    state = State(bits_left=1)
    decoder.init_io(state, f)

    with pytest.raises(decoder.UnexpectedEndOfStream):
        func(state, *args)


class TestRecordBitstream(object):
    def test_empty_recording(self):
        f = BytesIO()
        state = State()
        decoder.init_io(state, f)

        decoder.record_bitstream_start(state)
        assert "_recorded_bytes" in state
        assert decoder.record_bitstream_finish(state) == bytearray()
        assert "_recorded_bytes" not in state

    def test_record_whole_number_of_bytes(self):
        # Also records reading right up to the EOF
        f = BytesIO(b"\xAA\xBF")
        state = State()
        decoder.init_io(state, f)

        decoder.record_bitstream_start(state)
        assert decoder.read_nbits(state, 16) == 0xAABF
        assert decoder.record_bitstream_finish(state) == b"\xAA\xBF"

    def test_record_partial_bytes(self):
        f = BytesIO(b"\xAA\xFF")
        state = State()
        decoder.init_io(state, f)

        decoder.record_bitstream_start(state)
        assert decoder.read_nbits(state, 12) == 0xAAF
        assert decoder.record_bitstream_finish(state) == b"\xAA\xF0"
        assert decoder.read_nbits(state, 4) == 0xF


def test_tell():
    f = BytesIO(b"\xAA\xFF")
    state = State()
    decoder.init_io(state, f)

    # At start of stream
    assert decoder.tell(state) == (0, 7)

    # Part-way through byte
    decoder.read_nbits(state, 4)
    assert decoder.tell(state) == (0, 3)

    # In next byte
    decoder.read_nbits(state, 8)
    assert decoder.tell(state) == (1, 3)

    # At EOF
    decoder.read_nbits(state, 4)
    assert decoder.tell(state) == (2, 7)


def test_is_end_of_stream():
    f = BytesIO(b"\xFF")
    state = State()
    decoder.init_io(state, f)

    # At start of stream
    assert decoder.is_end_of_stream() is False

    # Part-way through byte
    decoder.read_nbits(state, 4)
    assert decoder.is_end_of_stream() is False

    # At end of stream
    decoder.read_nbits(state, 4)
    assert decoder.is_end_of_stream() is False
