import pytest

from io import BytesIO

import vc2_conformance.decoder.toy_vc2 as toy_vc2


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


@pytest.mark.parametrize("fn", [toy_vc2.auxiliary_data, toy_vc2.padding])
def test_auxiliary_data_and_padding(fn):
    state = toy_vc2.State(BytesIO(b"\xAA"*100 + b"\xF1"))
    
    state.next_parse_offset = 13 + 100
    fn(state)
    
    # Should have advanced to correct place
    assert toy_vc2.read_nbits(state, 8) == 0xF1


@pytest.mark.parametrize("valid_id", [True, False])
def test_parse_info(valid_id):
    state = toy_vc2.State(BytesIO(
        (b"BBCD" if valid_id else b"nope") +
        b"\xE8" +  # high_quality_picture
        b"\x12\x34\x56\x78" +
        b"\x90\xAB\xCD\xEF"
    ))
    
    if valid_id:
        toy_vc2.parse_info(state)
        state.parse_code == 0xE8
        state.next_parse_offset == 0x12345678
        state.previous_parse_offset == 0x90ABCDEF
    else:
        with pytest.raises(Exception):
            toy_vc2.parse_info(state)


def test_parse_parameters():
    # 0b0000_1001_0110_1011 = 0x096B
    #   '----''-' '-''----'
    #      3   1   2    4
    state = toy_vc2.State(BytesIO(b"\x09\x6B" + b"\x09\x6B" + b"\xFF"))
    
    toy_vc2.parse_parameters(state)
    assert state.major_version == 3
    assert state.minor_version == 1
    assert state.profile == 2
    assert state.level == 6
    
    # If repeated and same, should be no problem
    toy_vc2.parse_parameters(state)
    assert state.major_version == 3
    assert state.minor_version == 1
    assert state.profile == 2
    assert state.level == 6
    
    # If repeated and not same, should fail (spec requires that streams do not
    # change these (11.2.1))
    with pytest.raises(Exception):
        toy_vc2.parse_parameters(state)


class TestSourceParameters(object):
    
    def test_no_overrides(self):
        # Exactly 8 'false' bools for disabling any overrides.
        state = toy_vc2.State(BytesIO(b"\x00"))
        
        # Arbitrary choice for this test: check loading of 'HD1080i-50' base
        # video format (12).
        video_parameters = toy_vc2.source_parameters(state, 12)
        
        assert video_parameters.frame_width == 1920
        assert video_parameters.frame_height == 1080
        
        assert video_parameters.color_diff_format_index == (
            toy_vc2.ColorDifferenceSamplingFormats.color_4_2_2)
        
        assert video_parameters.source_sampling == (
            toy_vc2.SourceSamplingModes.interlaced)
        
        assert video_parameters.top_field_first is True
        
        assert video_parameters.frame_rate_numer == 25
        assert video_parameters.frame_rate_denom == 1
        
        assert video_parameters.pixel_aspect_ratio_numer == 1
        assert video_parameters.pixel_aspect_ratio_denom == 1
        
        assert video_parameters.clean_width == 1920
        assert video_parameters.clean_height == 1080
        assert video_parameters.left_offset == 0
        assert video_parameters.top_offset == 0
        
        assert video_parameters.luma_offset == 64
        assert video_parameters.luma_excursion == 876
        assert video_parameters.color_diff_offset == 512
        assert video_parameters.color_diff_excursion == 896
        
        assert video_parameters.color_primaries is (
            toy_vc2.PRESET_COLOR_PRIMARIES[toy_vc2.PresetColorPrimaries.hdtv])
        
        assert video_parameters.color_matrix is (
            toy_vc2.PRESET_COLOR_MATRICES[toy_vc2.PresetColorMatrices.hdtv])
        
        assert video_parameters.transfer_function is (
            toy_vc2.PRESET_TRANSFER_FUNCTIONS[toy_vc2.PresetTransferFunctions.tv_gamma])
    
    def test_override_frame_size(self):
        # 0x9_____6____0___3____
        # 0b1_001_011_0000000_11
        #   | `+' `+' `--+--' `+
        #   |  |   |     |     |
        #   |  |   |     |     +- Arbitrary filler bits...
        #   |  |   |     +- Don't override anything else
        #   |  |   +-Height (2)
        #   |  +- Width (1)
        #   +- Override dimensions
        state = toy_vc2.State(BytesIO(b"\x96\x03"))
        
        # Arbitrary choice for this test: check loading of 'HD1080i-50' base
        # video format (12).
        video_parameters = toy_vc2.source_parameters(state, 12)
        
        assert video_parameters.frame_width == 1
        assert video_parameters.frame_height == 2
    
    def test_override_color_diff_sampling_format(self):
        # 0x6______0___7____F
        # 0b0_1_1_000000_1111111
        #     | | `--+-' `+'
        #     | |    |    |
        #     | |    |    +- Arbitrary filler bits...
        #     | |    +- Don't override anything else
        #     | +- Format index (0)
        #     +- Override color diff sampling format
        state = toy_vc2.State(BytesIO(b"\x60\x7F"))
        
        # Arbitrary choice for this test: check loading of 'HD1080i-50' base
        # video format (12).
        video_parameters = toy_vc2.source_parameters(state, 12)
        
        assert video_parameters.color_diff_format_index == 0
    
    def test_scan_format(self):
        # 0x3______0___7____F___
        # 0b00_1_1_00000_1111111
        #      | | `-+-' `+'
        #      | |   |    |
        #      | |   |    +- Arbitrary filler bits...
        #      | |   +- Don't override anything else
        #      | +- Progressive (0)
        #      +- Override scan format
        state = toy_vc2.State(BytesIO(b"\x30\x7F"))
        
        # Arbitrary choice for this test: check loading of 'HD1080i-50' base
        # video format (12).
        video_parameters = toy_vc2.source_parameters(state, 12)
        
        assert video_parameters.source_sampling == 0
    
    def test_frame_rate_indexed(self):
        # 0x1_____2____1____F___
        # 0b000_1_001_0000_11111
        #       | `-' `-+' `+'
        #       |  |    |   |
        #       |  |    |   +- Arbitrary filler bits...
        #       |  |    +- Don't override anything else
        #       |  +- 24/1.001 (1)
        #       +- Override frame rate
        state = toy_vc2.State(BytesIO(b"\x12\x1F"))
        
        # Arbitrary choice for this test: check loading of 'HD1080i-50' base
        # video format (12).
        video_parameters = toy_vc2.source_parameters(state, 12)
        
        assert video_parameters.frame_rate_numer == 24000
        assert video_parameters.frame_rate_denom == 1001
    
    def test_frame_rate_custom(self):
        # 0x1_____9_____6____1____
        # 0b000_1_1_001_011_0000_1
        #       | - `+'`+'  `-+' |
        #       | |  |  |     |  |
        #       | |  |  |     |  +- Arbitrary filler bit...
        #       | |  |  |     +- Don't override anything else
        #       | |  |  +- Denominator (2)
        #       | |  +- Numerator (1)
        #       | +- Custom frame rate (0)
        #       +- Override frame rate
        state = toy_vc2.State(BytesIO(b"\x19\x61"))
        
        # Arbitrary choice for this test: check loading of 'HD1080i-50' base
        # video format (12).
        video_parameters = toy_vc2.source_parameters(state, 12)
        
        assert video_parameters.frame_rate_numer == 1
        assert video_parameters.frame_rate_denom == 2
    
    def test_pixel_aspect_ratio_indexed(self):
        # 0x0____B_____1____F___
        # 0b0000_1_011_000_11111
        #        | `-' `+' `-+-'
        #        |  |   |    |
        #        |  |   |    +- Arbitrary filler bits...
        #        |  |   +- Don't override anything else
        #        |  +- 10:11 (2)
        #        +- Override pixel aspect ratio
        state = toy_vc2.State(BytesIO(b"\x0B\x1F"))
        
        # Arbitrary choice for this test: check loading of 'HD1080i-50' base
        # video format (12).
        video_parameters = toy_vc2.source_parameters(state, 12)
        
        assert video_parameters.pixel_aspect_ratio_numer == 10
        assert video_parameters.pixel_aspect_ratio_denom == 11
    
    def test_pixel_aspect_ratio_custom(self):
        # 0x0____C_____B_____1____
        # 0b0000_1_1_001_011_000_1
        #        | - `+' `+' `+' |
        #        | |  |   |   |  |
        #        | |  |   |   |  +- Arbitrary filler bit...
        #        | |  |   |   +- Don't override anything else
        #        | |  |   +- Denominator (2)
        #        | |  +- Numerator (1)
        #        | +- Custom pixel aspect ratio (0)
        #        +- Override pixel aspect ratio
        state = toy_vc2.State(BytesIO(b"\x0C\xB1"))
        
        # Arbitrary choice for this test: check loading of 'HD1080i-50' base
        # video format (12).
        video_parameters = toy_vc2.source_parameters(state, 12)
        
        assert video_parameters.pixel_aspect_ratio_numer == 1
        assert video_parameters.pixel_aspect_ratio_denom == 2
    
    def test_clean_area(self):
        # 0x0___4_____B_____0___8____C____
        # 0b00000_1_001_011_00001_00011_00
        #         | `+' `+' `-+-' `-+-' `+
        #         |  |   |    |     |    |
        #         |  |   |    |     |    +- Don't override anything else
        #         |  |   |    |     +- Top offset (4)
        #         |  |   |    +- Left offset (3)
        #         |  |   +- Clean height (2)
        #         |  +- Clean width (1)
        #         +- Override clean area
        state = toy_vc2.State(BytesIO(b"\x04\xB0\x8C"))
        
        # Arbitrary choice for this test: check loading of 'HD1080i-50' base
        # video format (12).
        video_parameters = toy_vc2.source_parameters(state, 12)
        
        assert video_parameters.clean_width == 1
        assert video_parameters.clean_height == 2
        assert video_parameters.left_offset == 3
        assert video_parameters.top_offset == 4
    
    def test_signal_range_indexed(self):
        # 0x0___2_____D_____F___
        # 0b000000_1_011_0_11111
        #          | `-' + `-+-'
        #          |  |  |   |
        #          |  |  |   +- Arbitrary filler bits...
        #          |  |  +- Don't override anything else
        #          |  +- '8-bit video' (2)
        #          +- Override signal range
        state = toy_vc2.State(BytesIO(b"\x02\xDF"))
        
        # Arbitrary choice for this test: check loading of 'HD1080i-50' base
        # video format (12).
        video_parameters = toy_vc2.source_parameters(state, 12)
        
        assert video_parameters.luma_offset == 16
        assert video_parameters.luma_excursion == 219
        assert video_parameters.color_diff_offset == 128
        assert video_parameters.color_diff_excursion == 224
    
    def test_signal_range_custom(self):
        # 0x0___3______2____C____2____3____7____F___
        # 0b000000_1_1_001_011_00001_00011_0_1111111
        #          | | `+' `+' `-+-' `-+-' | `--+--'
        #          | |  |   |    |     |   |    |
        #          | |  |   |    |     |   |    +- Arbitrary filler bits...
        #          | |  |   |    |     |   +- Don't override anything else
        #          | |  |   |    |     +- Color diff excursion (4)
        #          | |  |   |    +- Color diff offset (3)
        #          | |  |   +- Luma excursion (2)
        #          | |  +- Luma offset (1)
        #          | +- Custom signal range (0)
        #          +- Override signal range
        state = toy_vc2.State(BytesIO(b"\x03\x2C\x23\x7F"))
        
        # Arbitrary choice for this test: check loading of 'HD1080i-50' base
        # video format (12).
        video_parameters = toy_vc2.source_parameters(state, 12)
        
        assert video_parameters.luma_offset == 1
        assert video_parameters.luma_excursion == 2
        assert video_parameters.color_diff_offset == 3
        assert video_parameters.color_diff_excursion == 4
    
    def test_color_spec_indexed(self):
        # 0x0___1_____1___F____
        # 0b0000000_1_00011_111
        #           | `---' `+'
        #           |   |    |
        #           |   |    +- Arbitrary filler bits...
        #           |   +- 'D-Cinema' (4)
        #           +- Override color specifications
        state = toy_vc2.State(BytesIO(b"\x01\x1F"))
        
        # Arbitrary choice for this test: check loading of 'HD1080i-50' base
        # video format (12).
        video_parameters = toy_vc2.source_parameters(state, 12)
        
        assert video_parameters.color_primaries is (
            toy_vc2.PRESET_COLOR_PRIMARIES[toy_vc2.PresetColorPrimaries.d_cinema])
        
        assert video_parameters.color_matrix is (
            toy_vc2.PRESET_COLOR_MATRICES[toy_vc2.PresetColorMatrices.reversible])
        
        assert video_parameters.transfer_function is (
            toy_vc2.PRESET_TRANSFER_FUNCTIONS[toy_vc2.PresetTransferFunctions.d_cinema_transfer_function])
    
    def test_color_spec_custom_defaults(self):
        # 0x0___1_____8_______F___
        # 0b0000000_1_1_0_0_0_1111
        #           | | | | | `-+'
        #           | | | | |   |
        #           | | | | |   +- Arbitrary filler bits...
        #           | | | | +- No custom transfer function
        #           | | | +-No custom matrix
        #           | | +- No custom color primaries
        #           | +- Custom color spec
        #           +- Override color-spec
        state = toy_vc2.State(BytesIO(b"\x01\x8F"))
        
        # Arbitrary choice for this test: check loading of 'HD1080i-50' base
        # video format (12).
        video_parameters = toy_vc2.source_parameters(state, 12)
        
        assert video_parameters.color_primaries is (
            toy_vc2.PRESET_COLOR_PRIMARIES[toy_vc2.PresetColorPrimaries.hdtv])
        
        assert video_parameters.color_matrix is (
            toy_vc2.PRESET_COLOR_MATRICES[toy_vc2.PresetColorMatrices.hdtv])
        
        assert video_parameters.transfer_function is (
            toy_vc2.PRESET_TRANSFER_FUNCTIONS[toy_vc2.PresetTransferFunctions.tv_gamma])
    
    def test_color_spec_custom(self):
        # 0x0___1_____C_____D_____C_____3____
        # 0b0000000_1_1_1_001_1_011_1_00001_1
        #           | | | `+' | `+' | `-+-' |
        #           | | |  |  |  |  |   |   |
        #           | | |  |  |  |  |   |   +- Arbitrary filler bit...
        #           | | |  |  |  |  |   +- D-Cinema transfer function (3)
        #           | | |  |  |  |  +- Custom transfer function
        #           | | |  |  |  +- Reversible (2)
        #           | | |  |  +- Custom matrix
        #           | | |  +- SDTV-525 (1)
        #           | | +- Custom color primaries
        #           | +- Custom color spec
        #           +- Override color-spec
        state = toy_vc2.State(BytesIO(b"\x01\xCD\xC3"))
        
        # Arbitrary choice for this test: check loading of 'HD1080i-50' base
        # video format (12).
        video_parameters = toy_vc2.source_parameters(state, 12)
        
        assert video_parameters.color_primaries is (
            toy_vc2.PRESET_COLOR_PRIMARIES[toy_vc2.PresetColorPrimaries.sdtv_525])
        
        assert video_parameters.color_matrix is (
            toy_vc2.PRESET_COLOR_MATRICES[toy_vc2.PresetColorMatrices.reversible])
        
        assert video_parameters.transfer_function is (
            toy_vc2.PRESET_TRANSFER_FUNCTIONS[toy_vc2.PresetTransferFunctions.d_cinema_transfer_function])


@pytest.mark.parametrize(
    "color_diff_format_index,picture_coding_mode,"
    "luma_width,luma_height,color_diff_width,color_diff_height", [
        (toy_vc2.ColorDifferenceSamplingFormats.color_4_4_4.value,
         toy_vc2.PictureCodingModes.pictures_are_frames.value,
         1920, 1080, 1920, 1080),
        (toy_vc2.ColorDifferenceSamplingFormats.color_4_2_2.value,
         toy_vc2.PictureCodingModes.pictures_are_frames.value,
         1920, 1080, 960, 1080),
        (toy_vc2.ColorDifferenceSamplingFormats.color_4_2_0.value,
         toy_vc2.PictureCodingModes.pictures_are_frames.value,
         1920, 1080, 960, 540),
        (toy_vc2.ColorDifferenceSamplingFormats.color_4_2_0.value,
         toy_vc2.PictureCodingModes.pictures_are_fields.value,
         1920, 540, 960, 270),
    ],
)
def test_picture_dimensions(dummy_stream,
        color_diff_format_index, picture_coding_mode,
        luma_width, luma_height, color_diff_width, color_diff_height):
    state = toy_vc2.State(dummy_stream)
    
    vp = toy_vc2.VideoParameters(
        frame_width=1920,
        frame_height=1080,
        color_diff_format_index=color_diff_format_index,
        source_sampling=toy_vc2.SourceSamplingModes.interlaced.value,
        top_field_first=True,
        frame_rate_numer=1,
        frame_rate_denom=1,
        pixel_aspect_ratio_numer=1,
        pixel_aspect_ratio_denom=1,
        clean_width=1920,
        clean_height=1080,
        left_offset=0,
        top_offset=0,
        luma_offset=0,
        luma_excursion=1023,
        color_diff_offset=512,
        color_diff_excursion=1023,
        color_primaries=toy_vc2.PRESET_COLOR_PRIMARIES[toy_vc2.PresetColorPrimaries.hdtv],
        color_matrix=toy_vc2.PRESET_COLOR_MATRICES[toy_vc2.PresetColorMatrices.hdtv],
        transfer_function=toy_vc2.PRESET_TRANSFER_FUNCTIONS[toy_vc2.PresetTransferFunctions.tv_gamma],
    )
    
    toy_vc2.picture_dimensions(state, vp, picture_coding_mode)
    
    assert state.luma_width == luma_width
    assert state.luma_height == luma_height
    assert state.color_diff_width == color_diff_width
    assert state.color_diff_height == color_diff_height


def test_video_depth(dummy_stream):
    state = toy_vc2.State(dummy_stream)
    
    vp = toy_vc2.VideoParameters(
        frame_width=1920,
        frame_height=1080,
        color_diff_format_index=toy_vc2.ColorDifferenceSamplingFormats.color_4_4_4.value,
        source_sampling=toy_vc2.SourceSamplingModes.interlaced.value,
        top_field_first=True,
        frame_rate_numer=1,
        frame_rate_denom=1,
        pixel_aspect_ratio_numer=1,
        pixel_aspect_ratio_denom=1,
        clean_width=1920,
        clean_height=1080,
        left_offset=0,
        top_offset=0,
        luma_offset=0,
        luma_excursion=1023,
        color_diff_offset=128,
        color_diff_excursion=255,
        color_primaries=toy_vc2.PRESET_COLOR_PRIMARIES[toy_vc2.PresetColorPrimaries.hdtv],
        color_matrix=toy_vc2.PRESET_COLOR_MATRICES[toy_vc2.PresetColorMatrices.hdtv],
        transfer_function=toy_vc2.PRESET_TRANSFER_FUNCTIONS[toy_vc2.PresetTransferFunctions.tv_gamma],
    )
    
    toy_vc2.video_depth(state, vp)
    
    assert state.luma_depth == 10
    assert state.color_diff_depth == 8
