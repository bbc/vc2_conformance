import pytest

from io import BytesIO

from vc2_conformance.bitstream import (
    BitstreamReader,
    BitstreamWriter,
    BoundedWriter,
)

from vc2_conformance.bitstream._fsm_io import (
    Token,
    TokenTypes,
    read_fsm,
    write_fsm,
    fsm_target_at_offset,
)


class TestReadFSM(object):
    
    @pytest.mark.parametrize("token_type,argument,expected_value,bits,expected_tell", [
        # N-bit unsigned integers
        (TokenTypes.nbits, 8, 0xAB, b"\xAB", (1, 7)),
        (TokenTypes.nbits, 4, 0xA, b"\xA0", (0, 3)),
        # Bytes strings
        (TokenTypes.nbytes, 2, b"\xAB\xCD", b"\xAB\xCD", (2, 7)),
        # Unsigned exp-golomb
        (TokenTypes.uint, None, 0, b"\x80", (0, 6)),
        (TokenTypes.uint, None, 1, b"\x20", (0, 4)),
        # Signed exp-golomb
        (TokenTypes.sint, None, 0, b"\x80", (0, 6)),
        (TokenTypes.sint, None, 1, b"\x20", (0, 3)),
        (TokenTypes.sint, None, -1, b"\x30", (0, 3)),
    ])
    def test_read_primitive_types(self, token_type, argument, expected_value,
                                  bits, expected_tell):
        def token_generator():
            read_value = yield Token(token_type, argument, "target")
            assert read_value == expected_value
        
        reader = BitstreamReader(BytesIO(bits))
        values = {"target": [None]}
        assert read_fsm(reader, token_generator(), values) == 0
        assert values["target"][0] == expected_value
        assert reader.tell() == expected_tell
    
    def test_generic_tuple_tokens(self):
        def token_generator():
            assert (yield (TokenTypes.nbits, 8, "target")) == 0xAB
        
        reader = BitstreamReader(BytesIO(b"\xAB"))
        values = {"target": [None]}
        assert read_fsm(reader, token_generator(), values) == 0
        assert values["target"][0] == 0xAB
    
    @pytest.mark.parametrize("token_type,argument,expected_value,expected_bits_past_eof", [
        # N-bit unsigned integers
        (TokenTypes.nbits, 12, 0xFFF, 12),
        # Unsigned exp-golomb
        (TokenTypes.uint, None, 0, 1),
        # Signed exp-golomb
        (TokenTypes.sint, None, 0, 1),
    ])
    def test_read_primitive_past_eof(self, token_type, argument,
                                     expected_value, expected_bits_past_eof):
        def token_generator():
            read_value = yield Token(token_type, argument, "target")
            assert read_value == expected_value
        
        reader = BitstreamReader(BytesIO())
        values = {"target": [None]}
        assert read_fsm(reader, token_generator(), values) == expected_bits_past_eof
        assert values["target"][0] == expected_value
    
    def test_bounded_block(self):
        def token_generator(nbits, expected_padding):
            yield Token(TokenTypes.bounded_block_begin, 16, None)
            yield Token(TokenTypes.nbits, nbits, "target")
            padding = yield Token(TokenTypes.bounded_block_end, None, "padding")
            assert padding == expected_padding
        
        # Value is bigger than its bounded block
        reader = BitstreamReader(BytesIO(b"\xAB"))
        values = {"target": [None], "padding": [None]}
        assert read_fsm(reader, token_generator(24, 0), values) == 8
        assert values["target"][0] == 0xABFFFF
        assert values["padding"][0] == 0
        
        # Value is shorter than bounded blocks
        reader = BitstreamReader(BytesIO(b"\xAB"))
        values = {"target": [None], "padding": [None]}
        assert read_fsm(reader, token_generator(4, 0xBFF), values) == 8
        assert values["target"][0] == 0xA
        assert values["padding"][0] == 0xBFF
    
    def test_nested_bounded_block(self):
        def token_generator(nbits, expected_inner_padding, expected_outer_padding):
            yield Token(TokenTypes.bounded_block_begin, 8, None)
            yield Token(TokenTypes.bounded_block_begin, 12, None)
            
            yield Token(TokenTypes.nbits, nbits, "target")
            
            inner_padding = yield Token(TokenTypes.bounded_block_end, None, "inner_padding")
            assert inner_padding == expected_inner_padding
            
            outer_padding = yield Token(TokenTypes.bounded_block_end, None, "outer_padding")
            assert outer_padding == expected_outer_padding
        
        # Inner value is bigger than its bounded blocks
        reader = BitstreamReader(BytesIO(b"\xAB"))
        values = {"target": [None], "inner_padding": [None],  "outer_padding": [None]}
        assert read_fsm(reader, token_generator(16, 0, 0), values) == 0
        assert values["target"][0] == 0xABFF
        assert values["inner_padding"][0] == 0
        assert values["outer_padding"][0] == 0
        
        # Inner value is shorter than bounded blocks
        reader = BitstreamReader(BytesIO(b"\xAB"))
        values = {"target": [None], "inner_padding": [None],  "outer_padding": [None]}
        assert read_fsm(reader, token_generator(4, 0xBF, 0), values) == 0
        assert values["target"][0] == 0xA
        assert values["inner_padding"][0] == 0xBF
        assert values["outer_padding"][0] == 0
    
    def test_unclosed_bounded_blocks(self):
        def token_generator():
            yield Token(TokenTypes.bounded_block_begin, 8, None)
            yield Token(TokenTypes.bounded_block_begin, 12, None)
            yield Token(TokenTypes.bounded_block_end, None, None)
        
        reader = BitstreamReader(BytesIO())
        values = {}
        with pytest.raises(ValueError):
            read_fsm(reader, token_generator(), values)
    
    def test_unused_values(self):
        def token_generator():
            yield Token(TokenTypes.uint, None, "a")
            yield Token(TokenTypes.uint, None, "a")
            yield Token(TokenTypes.uint, None, "b")
        
        reader = BitstreamReader(BytesIO())
        
        # A too long
        values = {"a": [None, None, None], "b": [None]}
        with pytest.raises(ValueError):
            read_fsm(reader, token_generator(), values)
        
        # B too long
        values = {"a": [None, None], "b": [None, None]}
        with pytest.raises(ValueError):
            read_fsm(reader, token_generator(), values)


class TestWriteFSM(object):
    
    @pytest.mark.parametrize("token_type,argument,value,expected_bits,expected_tell", [
        # N-bit unsigned integers
        (TokenTypes.nbits, 8, 0xAB, b"\xAB", (1, 7)),
        (TokenTypes.nbits, 4, 0xA, b"\xA0", (0, 3)),
        # Bytes strings
        (TokenTypes.nbytes, 2, b"\xAB\xCD", b"\xAB\xCD", (2, 7)),
        # Unsigned exp-golomb
        (TokenTypes.uint, None, 0, b"\x80", (0, 6)),
        (TokenTypes.uint, None, 1, b"\x20", (0, 4)),
        # Signed exp-golomb
        (TokenTypes.sint, None, 0, b"\x80", (0, 6)),
        (TokenTypes.sint, None, 1, b"\x20", (0, 3)),
        (TokenTypes.sint, None, -1, b"\x30", (0, 3)),
    ])
    def test_write_primitive_types(self, token_type, argument, value,
                                   expected_bits, expected_tell):
        def token_generator():
            written_value = yield Token(token_type, argument, "target")
            assert written_value == value
        
        f = BytesIO()
        writer = BitstreamWriter(f)
        values = {"target": [value]}
        assert write_fsm(writer, token_generator(), values) == 0
        
        assert writer.tell() == expected_tell
        
        writer.flush()
        assert f.getvalue() == expected_bits
    
    def test_generic_tuple_tokens(self):
        def token_generator():
            assert (yield (TokenTypes.nbits, 8, "target")) == 0xAB
        
        f = BytesIO()
        writer = BitstreamWriter(f)
        values = {"target": [0xAB]}
        assert write_fsm(writer, token_generator(), values) == 0
        assert f.getvalue() == b"\xAB"
    
    @pytest.mark.parametrize("token_type,argument,value,expected_bits_past_eof", [
        # N-bit unsigned integers
        (TokenTypes.nbits, 12, 0xFFF, 12),
        # Unsigned exp-golomb
        (TokenTypes.uint, None, 0, 1),
        # Signed exp-golomb
        (TokenTypes.sint, None, 0, 1),
    ])
    def test_write_primitive_past_eof(self, token_type, argument,
                                     value, expected_bits_past_eof):
        def token_generator():
            written_value = yield Token(token_type, argument, "target")
            assert written_value == value
        
        writer = BitstreamWriter(BytesIO())
        bounded_writer = BoundedWriter(writer, 0)
        values = {"target": [value]}
        assert write_fsm(bounded_writer, token_generator(), values) == expected_bits_past_eof
    
    def test_bounded_block(self):
        def token_generator(nbits, expected_inner_padding, expected_outer_padding):
            yield Token(TokenTypes.bounded_block_begin, 8, None)
            yield Token(TokenTypes.bounded_block_begin, 12, None)
            
            yield Token(TokenTypes.nbits, nbits, "target")
            
            inner_padding = yield Token(TokenTypes.bounded_block_end, None, "inner_padding")
            assert inner_padding == expected_inner_padding
            
            outer_padding = yield Token(TokenTypes.bounded_block_end, None, "outer_padding")
            assert outer_padding == expected_outer_padding
        
        # Inner value is bigger than its bounded blocks
        f = BytesIO()
        writer = BitstreamWriter(f)
        values = {"target": [0xABFF], "inner_padding": [0],  "outer_padding": [0]}
        assert write_fsm(writer, token_generator(16, 0, 0), values) == 0
        writer.flush()
        assert f.getvalue() == b"\xAB"
        
        # Inner value is shorter than bounded blocks
        f = BytesIO()
        writer = BitstreamWriter(f)
        values = {"target": [0xA], "inner_padding": [0x5BF],  "outer_padding": [0]}
        assert write_fsm(writer, token_generator(4, 0x5BF, 0), values) == 0
        writer.flush()
        assert f.getvalue() == b"\xAB"
    
    def test_unclosed_bounded_blocks(self):
        def token_generator():
            yield Token(TokenTypes.bounded_block_begin, 8, None)
            yield Token(TokenTypes.bounded_block_begin, 12, None)
            yield Token(TokenTypes.bounded_block_end, None, None)
        
        writer = BitstreamWriter(BytesIO())
        values = {}
        with pytest.raises(ValueError):
            write_fsm(writer, token_generator(), values)
    
    def test_unused_values(self):
        def token_generator():
            yield Token(TokenTypes.uint, None, "a")
            yield Token(TokenTypes.uint, None, "a")
            yield Token(TokenTypes.uint, None, "b")
        
        writer = BitstreamWriter(BytesIO())
        
        # A too long
        values = {"a": [0, 0, 0], "b": [0]}
        with pytest.raises(ValueError):
            write_fsm(writer, token_generator(), values)
        
        # B too long
        values = {"a": [0, 0], "b": [0, 0]}
        with pytest.raises(ValueError):
            write_fsm(writer, token_generator(), values)
    
    @pytest.mark.parametrize("token_type,argument,value", [
        (TokenTypes.nbits, 4, 0b10000),
        (TokenTypes.nbits, 4, -1),
        (TokenTypes.uint, None, -1),
    ])
    def test_out_of_range_values(self, token_type, argument, value):
        def token_generator():
            yield Token(token_type, argument, "target")
        
        writer = BitstreamWriter(BytesIO())
        values = {"target": [value]}
        with pytest.raises(ValueError):
            write_fsm(writer, token_generator(), values)


class TestFSMTargetAtOffset(object):
    
    def test_primitive_types(self):
        def token_generator():
            assert (yield Token(TokenTypes.nbits, 4, "nbits1")) == 1
            assert (yield Token(TokenTypes.nbytes, 2, "nbytes1")) == 2
            assert (yield Token(TokenTypes.uint, None, "uint1")) == 3
            assert (yield Token(TokenTypes.sint, None, "sint1")) == 4
            assert (yield Token(TokenTypes.nbits, 8, "nbits2")) == 5
            assert (yield Token(TokenTypes.nbytes, 2, "nbytes2")) == 6
            assert (yield Token(TokenTypes.uint, None, "uint2")) == 7
            assert (yield Token(TokenTypes.sint, None, "sint2")) == 8
        
        values = {
            "nbits1": [1], "nbytes1": [2], "uint1": [3], "sint1": [4],
            "nbits2": [5], "nbytes2": [6], "uint2": [7], "sint2": [8],
        }
        
        expected_targets = [
            "nbits1", "nbytes1", "uint1", "sint1",
            "nbits2", "nbytes2", "uint2", "sint2",
        ]
        expected_widths = [
            4, 16, 5, 6,
            8, 16, 7, 8,
        ]
        
        target_offset = 0
        for target, width in zip(expected_targets, expected_widths):
            for i in range(width):
                assert fsm_target_at_offset(
                    token_generator(), values, target_offset) == (target, 0)
                target_offset += 1
        
        with pytest.raises(IndexError):
            fsm_target_at_offset(token_generator(), values, target_offset)
    
    def test_generic_tuple_tokens(self):
        def token_generator():
            assert (yield (TokenTypes.nbits, 8, "target")) == 0xAB
        
        values = {"target": [0xAB]}
        assert fsm_target_at_offset(token_generator(), values, 0) == ("target", 0)
    
    def test_return_targets_and_indices(self):
        def token_generator():
            assert (yield Token(TokenTypes.nbits, 4, "target1")) == 1
            assert (yield Token(TokenTypes.nbits, 4, "target2")) == 2
            assert (yield Token(TokenTypes.nbits, 4, "target1")) == 3
            assert (yield Token(TokenTypes.nbits, 4, "target2")) == 4
            assert (yield Token(TokenTypes.nbits, 4, "target1")) == 5
            assert (yield Token(TokenTypes.nbits, 4, "target2")) == 6
        values = {
            "target1": [1, 3, 5],
            "target2": [2, 4, 6],
        }
        
        for n in range(0, 4):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target1", 0)
        for n in range(4, 8):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target2", 0)
        for n in range(8, 12):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target1", 1)
        for n in range(12, 16):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target2", 1)
        for n in range(16, 20):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target1", 2)
        for n in range(20, 24):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target2", 2)
        
        with pytest.raises(IndexError):
            fsm_target_at_offset(token_generator(), values, 24)
    
    def test_bounded_block_contains_whole_values_past_boundary(self):
        def token_generator():
            yield Token(TokenTypes.bounded_block_begin, 8, None)
            assert (yield Token(TokenTypes.nbits, 4, "target1")) == 1
            assert (yield Token(TokenTypes.nbits, 4, "target2")) == 2
            assert (yield Token(TokenTypes.nbits, 4, "target3")) == 3
            assert (yield Token(TokenTypes.bounded_block_end, None, "padding")) == 4
            assert (yield Token(TokenTypes.nbits, 4, "target4")) == 5
        values = {
            "padding": [4],
            "target1": [1], "target2": [2], "target3": [3], "target4": [5],
        }
        
        for n in range(0, 4):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target1", 0)
        for n in range(4, 8):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target2", 0)
        for n in range(8, 12):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target4", 0)
        
        with pytest.raises(IndexError):
            fsm_target_at_offset(token_generator(), values, 12)
    
    def test_bounded_block_contains_partial_values_past_boundary(self):
        def token_generator():
            yield Token(TokenTypes.bounded_block_begin, 6, None)
            assert (yield Token(TokenTypes.nbits, 4, "target1")) == 1
            assert (yield Token(TokenTypes.nbits, 4, "target2")) == 2
            assert (yield Token(TokenTypes.nbits, 4, "target3")) == 3
            assert (yield Token(TokenTypes.bounded_block_end, None, "padding")) == 4
            assert (yield Token(TokenTypes.nbits, 4, "target4")) == 5
        values = {
            "padding": [4],
            "target1": [1], "target2": [2], "target3": [3], "target4": [5],
        }
        
        for n in range(0, 4):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target1", 0)
        for n in range(4, 6):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target2", 0)
        for n in range(6, 10):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target4", 0)
        
        with pytest.raises(IndexError):
            fsm_target_at_offset(token_generator(), values, 10)
    
    def test_bounded_block_has_padding(self):
        def token_generator():
            yield Token(TokenTypes.bounded_block_begin, 16, None)
            assert (yield Token(TokenTypes.nbits, 4, "target1")) == 1
            assert (yield Token(TokenTypes.nbits, 4, "target2")) == 2
            assert (yield Token(TokenTypes.nbits, 4, "target3")) == 3
            assert (yield Token(TokenTypes.bounded_block_end, None, "padding")) == 4
            assert (yield Token(TokenTypes.nbits, 4, "target4")) == 5
        values = {
            "padding": [4],
            "target1": [1], "target2": [2], "target3": [3], "target4": [5],
        }
        
        for n in range(0, 4):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target1", 0)
        for n in range(4, 8):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target2", 0)
        for n in range(8, 12):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target3", 0)
        for n in range(12, 16):
            assert fsm_target_at_offset(token_generator(), values, n) == ("padding", 0)
        for n in range(16, 20):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target4", 0)
        
        with pytest.raises(IndexError):
            fsm_target_at_offset(token_generator(), values, 20)
    
    @pytest.mark.parametrize("nested_block_length", [2, 4, 8])
    def test_nested_bounded_block(self, nested_block_length):
        def token_generator():
            yield Token(TokenTypes.bounded_block_begin, 4, None)
            yield Token(TokenTypes.bounded_block_begin, nested_block_length, None)
            assert (yield Token(TokenTypes.nbits, 4, "target1")) == 1
            assert (yield Token(TokenTypes.nbits, 4, "target2")) == 2
            assert (yield Token(TokenTypes.nbits, 4, "target3")) == 3
            assert (yield Token(TokenTypes.bounded_block_end, None, "padding2")) == 5
            assert (yield Token(TokenTypes.bounded_block_end, None, "padding1")) == 4
            assert (yield Token(TokenTypes.nbits, 4, "target4")) == 6
        values = {
            "padding1": [4], "padding2": [5],
            "target1": [1], "target2": [2], "target3": [3], "target4": [6],
        }
        
        for n in range(0, min(nested_block_length, 4)):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target1", 0)
        for n in range(min(nested_block_length, 4), 4):
            assert fsm_target_at_offset(token_generator(), values, n) == ("padding1", 0)
        for n in range(4, 8):
            assert fsm_target_at_offset(token_generator(), values, n) == ("target4", 0)
        
        with pytest.raises(IndexError):
            fsm_target_at_offset(token_generator(), values, 8)
