import pytest

from io import BytesIO

import toy_vc2


@pytest.fixture
def dummy_stream():
    """For use in tests where no reading is done."""
    return BytesIO(b"")


@pytest.mark.parametrize("name", [
    "L", "H",
    "LL", "HL", "LH", "HH",
    "Y", "C1", "C2",
    "pic_num",
])
def test_sentinels_names_consistent(name):
    assert str(getattr(toy_vc2, name)) == "<{}>".format(name)


def test_state_constructor(dummy_stream):
    # Should be able to construct, only passing in the stream object
    s = toy_vc2.State(dummy_stream)
    s.stream == "foo"
    
    # Stream object must be required
    with pytest.raises(Exception):
        s = toy_vc2.State()

@pytest.mark.parametrize("value,expectation", [
    # Example values from (5.5.3)
    (25, 5),
    (32, 5),
    # Other values
    (1, 0),
    (2, 1),
    (3, 2),
    (4, 2),
    (5, 3),
    (6, 3),
    (7, 3),
    (8, 3),
    (9, 4),
])
def test_intlog2(value, expectation):
    out = toy_vc2.intlog2(value)
    assert out == expectation
    assert isinstance(out, int)

@pytest.mark.parametrize("value,expectation", [
    (-10, -1),
    (-1, -1),
    (0, 0),
    (1, 1),
    (10, 1),
])
def test_sign(value, expectation):
    out = toy_vc2.sign(value)
    assert out == expectation

@pytest.mark.parametrize("value,expectation", [
    (9, 10),
    (10, 10),
    (11, 11),
    (12, 12),
    (13, 13),
    (14, 14),
    (15, 15),
    (16, 15),
])
def test_clip(value, expectation):
    out = toy_vc2.clip(value, 10, 15)
    assert out == expectation

@pytest.mark.parametrize("values,expectation", [
    # Exactly divide
    ((15, 15), 15),
    ((10, 20), 15),
    ((20, 10), 15),
    ((10, 20, 30, 40), 25),
    # Rounding down
    ((10, 11, 13, 15), 12),  # Actually 12.25
    # Rounding up
    ((10, 11, 12, 13), 12),  # Actually 11.5
    ((10, 12, 14, 15), 13),  # Actually 12.75
])
def test_mean(values, expectation):
    out = toy_vc2.mean(values)
    assert isinstance(out, int)
    assert out == expectation

def test_array():
    a = toy_vc2.array(2, 3, 4)
    
    assert isinstance(a, list)
    assert len(a) == 3
    assert all(isinstance(row, list) for row in a)
    
    assert all(len(row) == 2 for row in a)
    assert all(all(value == 4 for value in row) for row in a)
    
    for i in range(3):
        for j in range(3):
            if i != j:
                assert a[i] is not a[j]

def test_width_height():
    a = toy_vc2.array(5, 10)
    assert toy_vc2.width(a) == 5
    assert toy_vc2.height(a) == 10

def test_read_byte():
    state = toy_vc2.State(BytesIO(b"\xAA\xAB\xAC"))
    
    # First byte should have been read on startup
    assert state.current_byte == 0xAA
    assert state.next_bit == 7
    
    toy_vc2.read_byte(state)
    assert state.current_byte == 0xAB
    assert state.next_bit == 7
    
    toy_vc2.read_byte(state)
    assert state.current_byte == 0xAC
    assert state.next_bit == 7

def test_read_bit():
    state = toy_vc2.State(BytesIO(b"\xF0\xA0"))
    
    bits = [toy_vc2.read_bit(state) for _ in range(16)]
    
    assert bits == [
        1, 1, 1, 1, 0, 0, 0, 0,
        1, 0, 1, 0, 0, 0, 0, 0,
    ]
    
    # Should fail if reading past end (not part of spec but a sanity check)
    with pytest.raises(Exception):
        toy_vc2.read_bit(state)

def test_byte_align():
    state = toy_vc2.State(BytesIO(b"\xF0\xA0"))
    
    # Calling on a byte boundary should do nothing
    toy_vc2.byte_align(state)
    
    bits = [toy_vc2.read_bit(state) for _ in range(6)]
    assert bits == [1, 1, 1, 1, 0, 0]
    
    # Calling off a boundary should advance
    toy_vc2.byte_align(state)
    
    bits = [toy_vc2.read_bit(state) for _ in range(6)]
    assert bits == [1, 0, 1, 0, 0, 0]
    
    # Shouldn't fail if we advance in the last byte of the file (not part of
    # spec, but probably useful for sanity check)
    toy_vc2.byte_align(state)

def test_read_bool():
    state = toy_vc2.State(BytesIO(b"\xF0\xA0"))
    
    bools = [toy_vc2.read_bool(state) for _ in range(16)]
    
    expected = [
        True, True, True, True, False, False, False, False,
        True, False, True, False, False, False, False, False,
    ]
    
    for b, e in zip(bools, expected):
        assert b is e
    
    # Should fail if reading past end (not part of spec but a sanity check)
    with pytest.raises(Exception):
        toy_vc2.read_bool(state)

def test_read_nbits():
    state = toy_vc2.State(BytesIO(b"\xAB\xCD"))
    
    # Non whole byte read
    assert toy_vc2.read_nbits(state, 4) == 0xA
    
    # Non-aligned first bit, reading accross byte boundary
    assert toy_vc2.read_nbits(state, 8) == 0xBC
    
    # Should fail if reading past end (not part of spec but a sanity check)
    with pytest.raises(Exception):
        toy_vc2.read_nbits(state, 8)

def test_read_uint_lit():
    state = toy_vc2.State(BytesIO(b"\x01\x23\x45\x67\x89"))
    
    # Already aligned, should just work
    assert toy_vc2.read_uint_lit(state, 2) == 0x0123
    
    # Not aligned, should advance to next byte
    toy_vc2.read_nbits(state, 4)
    assert toy_vc2.read_uint_lit(state, 1) == 0x67
    
    # Should fail if reading past end (not part of spec but a sanity check)
    with pytest.raises(Exception):
        toy_vc2.read_uint_lit(state, 2)

def test_read_bitb():
    state = toy_vc2.State(BytesIO(b"\xF0\xA0"))
    
    # Should fail if no bounds set (not part of spec but useful sanity check)
    with pytest.raises(Exception):
        toy_vc2.read_bitb(state)
    
    state.bits_left = 14
    
    bits = [toy_vc2.read_bitb(state) for _ in range(24)]
    
    assert bits == [
        1, 1, 1, 1, 0, 0, 0, 0,
        1, 0, 1, 0, 0, 0,  # Stop reading file at this point
        # Remaining 10 bits all ones
        1, 1,
        1, 1, 1, 1, 1, 1, 1, 1,
    ]
    
    # Should be able to read remaining bits (shouldn't have gone past them
    assert toy_vc2.read_bit(state) == 0
    assert toy_vc2.read_bit(state) == 0
    with pytest.raises(Exception):
        toy_vc2.read_bit(state)


def test_read_boolb():
    state = toy_vc2.State(BytesIO(b"\xF0"))
    
    # Should fail if no bounds set (not part of spec but useful sanity check)
    with pytest.raises(Exception):
        toy_vc2.read_boolb(state)
    
    state.bits_left = 6
    
    bools = [toy_vc2.read_boolb(state) for _ in range(12)]
    
    expected = [
        True, True, True, True, False, False,  # Stop at 6 bits
        # Remaining 6 bits will be True
        True, True, True, True, True, True,
    ]
    
    for b, e in zip(bools, expected):
        assert b is e
    
    # Should be able to read remaining bits (shouldn't have gone past them
    assert toy_vc2.read_bit(state) == 0
    assert toy_vc2.read_bit(state) == 0
    with pytest.raises(Exception):
        toy_vc2.read_bit(state)


def test_flush_inputb():
    state = toy_vc2.State(BytesIO(b"\xF0"))
    
    # Should fail if no bounds set (not part of spec but useful sanity check)
    with pytest.raises(Exception):
        toy_vc2.flush_inputb(state)
    
    state.bits_left = 6
    
    bits = [toy_vc2.read_bitb(state) for _ in range(5)]
    assert bits == [1, 1, 1, 1, 0]
    
    toy_vc2.flush_inputb(state)
    
    # Should now just read '1's
    bits = [toy_vc2.read_bitb(state) for _ in range(4)]
    assert bits == [1, 1, 1, 1]
    
    # Should be able to read remaining bits (should have advanced to them)
    assert toy_vc2.read_bit(state) == 0
    assert toy_vc2.read_bit(state) == 0
    with pytest.raises(Exception):
        toy_vc2.read_bit(state)

def test_read_uint():
    state = toy_vc2.State(BytesIO(b"\x0F"))
    
    assert toy_vc2.read_uint(state) == 3
    assert toy_vc2.read_uint(state) == 0
    assert toy_vc2.read_uint(state) == 0
    assert toy_vc2.read_uint(state) == 0
    
    # Should not advance past end (not part of spec but useful sanity check)
    with pytest.raises(Exception):
        toy_vc2.read_uint(state)

def test_read_uintb():
    state = toy_vc2.State(BytesIO(b"\x08"))
    
    # Should fail if no bounds set (not part of spec but useful sanity check)
    with pytest.raises(Exception):
        toy_vc2.read_uintb(state)
    
    state.bits_left = 6
    
    assert toy_vc2.read_uintb(state) == 3
    
    # Partially read past end
    assert toy_vc2.read_uintb(state) == 2
    
    # Fully past end
    assert toy_vc2.read_uintb(state) == 0
    assert toy_vc2.read_uintb(state) == 0

def test_read_sint():
    # 0b0010_0011_1_1_1_1_1_1_1_1
    state = toy_vc2.State(BytesIO(b"\x23\xFF"))
    
    assert toy_vc2.read_sint(state) == 1
    assert toy_vc2.read_sint(state) == -1
    for _ in range(8):
        assert toy_vc2.read_sint(state) == 0
    
    # Should not advance past end (not part of spec but useful sanity check)
    with pytest.raises(Exception):
        toy_vc2.read_sint(state)

def test_read_sintb():
    # 0b0010_0011_10000000
    state = toy_vc2.State(BytesIO(b"\x23\x80"))
    
    # Should fail if no bounds set (not part of spec but useful sanity check)
    with pytest.raises(Exception):
        toy_vc2.read_sintb(state)
    
    state.bits_left = 11
    
    assert toy_vc2.read_sintb(state) == 1
    assert toy_vc2.read_sintb(state) == -1
    assert toy_vc2.read_sintb(state) == 0
    
    # Reading partly off the end
    assert toy_vc2.read_sintb(state) == -1
    
    # Reading completely off end
    assert toy_vc2.read_sintb(state) == 0
    assert toy_vc2.read_sintb(state) == 0
    assert toy_vc2.read_sintb(state) == 0
