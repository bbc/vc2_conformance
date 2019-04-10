import pytest

from io import BytesIO

from bitarray import bitarray

from vc2_conformance.exceptions import OutOfRangeError

from vc2_conformance import bitstream


class TestBistreamReader(object):
    
    def test_reading(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xA5\x0F"))
        
        expected = [1, 0, 1, 0, 0, 1, 0, 1,  # 0xA5
                    0, 0, 0, 0, 1, 1, 1, 1]  # 0x0F
        for expected_bit in expected:
            assert r.read_bit() == expected_bit
        
        # Reading past the end should return 1...
        for _ in range(16):
            assert r.read_bit() == 1
    
    def test_tell(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xA5\x0F"))
        
        assert r.tell() == (0, 7)
        assert r.read_bit() == 1
        assert r.tell() == (0, 6)
        
        for _ in range(6):
            r.read_bit()
        
        assert r.tell() == (0, 0)
        
        assert r.read_bit() == 1
        assert r.tell() == (1, 7)
        
        for _ in range(8):
            r.read_bit()
        
        # Read past end
        assert r.tell() == (2, 7)
        assert r.read_bit() == 1
        assert r.tell() == (2, 7)
    
    def test_bits_past_eof(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xA5\x0F"))
        
        assert r.bits_past_eof == 0
        for _ in range(16):
            r.read_bit()
        assert r.bits_past_eof == 0
        
        # Read past end
        r.read_bit()
        assert r.bits_past_eof == 1
        r.read_bit()
        assert r.bits_past_eof == 2
        
        # Reset by seek
        r.seek(1, 7)
        assert r.bits_past_eof == 0
        for _ in range(8):
            r.read_bit()
        assert r.bits_past_eof == 0
        
        # Past end again
        r.read_bit()
        assert r.bits_past_eof == 1
        r.read_bit()
        assert r.bits_past_eof == 2
    
    def test_seek(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xA5\x0F"))
        
        r.seek(1)
        assert [r.read_bit() for _ in range(8)] == [0, 0, 0, 0, 1, 1, 1, 1]
        
        r.seek(0)
        assert [r.read_bit() for _ in range(8)] == [1, 0, 1, 0, 0, 1, 0, 1]
        
        r.seek(0, 3)
        assert [r.read_bit() for _ in range(8)] == [0, 1, 0, 1, 0, 0, 0, 0]
        
        # Past end of file
        r.seek(2, 7)
        assert r.read_bit() == 1
        r.seek(2, 0)
        assert r.read_bit() == 1
        r.seek(100, 7)
        assert r.read_bit() == 1


class TestBistreamWriter(object):
    
    def test_writing_whole_number_of_bytes(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        
        for bit in [1, 0, 1, 0, 0, 1, 0, 1,  # 0xA5
                    0, 0, 0, 0, 1, 1, 1, 1]:  # 0x0F
            w.write_bit(bit)
        
        assert f.getvalue() == b"\xA5\x0F"
    
    def test_writing_and_flush(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        
        assert f.getvalue() == b""
        
        w.write_bit(0)
        w.flush()
        assert f.getvalue() == b"\x00"
        
        w.write_bit(1)
        w.flush()
        assert f.getvalue() == b"\x40"
        
        w.write_bit(0)
        w.flush()
        assert f.getvalue() == b"\x40"
        
        w.write_bit(1)
        w.flush()
        assert f.getvalue() == b"\x50"
        
        for _ in range(4):
            w.write_bit(1)
        
        # Ending the byte normally should flush automatically and retain
        # existing bits
        assert f.getvalue() == b"\x5F"
    
    def test_tell(self):
        w = bitstream.BitstreamWriter(BytesIO())
        
        assert w.tell() == (0, 7)
        
        w.write_bit(0)
        assert w.tell() == (0, 6)
        
        for _ in range(6):
            w.write_bit(1)
        assert w.tell() == (0, 0)
        
        # Move into next byte
        w.write_bit(1)
        assert w.tell() == (1, 7)
        
        w.write_bit(1)
        assert w.tell() == (1, 6)
    
    def test_seek(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        
        w.seek(0, 3)
        w.write_bit(1)
        w.flush()
        
        assert f.getvalue() == b"\x08"
        
        w.seek(1, 0)
        w.write_bit(1)
        w.flush()
        
        assert f.getvalue() == b"\x08\x01"
        
        # Should overwrite existing value of first byte...
        w.seek(0, 6)
        w.write_bit(1)
        w.flush()
        
        assert f.getvalue() == b"\x40\x01"
    
    def test_bits_past_eof(self):
        w = bitstream.BitstreamWriter(BytesIO())
        
        # Always 0
        assert w.bits_past_eof == 0
        w.write_bit(True)
        assert w.bits_past_eof == 0


class TestBistreamPadAndTruncate(object):
    
    def test_tell(self):
        p = bitstream.BitstreamPadAndTruncate()
        
        assert p.tell() == (0, 7)
        
        p.advance_bit_offset(1)
        assert p.tell() == (0, 6)
        
        p.advance_bit_offset(6)
        assert p.tell() == (0, 0)
        
        # Move into next byte
        p.advance_bit_offset(1)
        assert p.tell() == (1, 7)
        
        p.advance_bit_offset(1)
        assert p.tell() == (1, 6)
    
    def test_seek(self):
        p = bitstream.BitstreamPadAndTruncate()
        for byte in range(2):
            for bit in range(8):
                p.seek(byte, bit)
                assert p.tell() == (byte, bit)


class TestReadNbits(object):
    
    def test_read_nothing(self):
        r = bitstream.BitstreamReader(BytesIO())
        assert r.read_nbits(0) == 0
        assert r.tell() == (0, 7)
    
    def test_read_bytes_msb_first(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xA0\x50"))
        assert r.read_nbits(12) == 0xA05
        assert r.tell() == (1, 3)
    
    def test_read_past_eof(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xA0"))
        assert r.read_nbits(12) == 0xA0F
        assert r.tell() == (1, 7)


class TestWriteNbits(object):
    
    @pytest.fixture
    def f(self):
        return BytesIO()
    
    @pytest.fixture
    def w(self, f):
        return bitstream.BitstreamWriter(f)
    
    def test_write_nothing(self, w):
        w.write_nbits(0, 0)
        assert w.tell() == (0, 7)
    
    def test_fail_on_too_many_bits(self, f, w):
        with pytest.raises(OutOfRangeError, match=r"0b1010 is 4 bits, not 2"):
            w.write_nbits(2, 0xA)
    
    def test_write_zeros_above_msb(self, f, w):
        w.write_nbits(16, 0xABC)
        assert w.tell() == (2, 7)
        w.flush()
        assert f.getvalue() == b"\x0A\xBC"
    
    def test_write_past_eof(self, f, w):
        bw = bitstream.BoundedWriter(w, 8)
        bw.write_nbits(12, 0xABF)
        assert w.tell() == (1, 7)
        w.flush()
        assert f.getvalue() == b"\xAB"


class TestPadAndTruncateNbits(object):
    
    @pytest.fixture
    def p(self):
        return bitstream.BitstreamPadAndTruncate()
    
    def test_nothing(self, p):
        assert p.pad_and_truncate_nbits(0) == 0
        assert p.tell() == (0, 7)
    
    def test_truncate_excess_bits(self, p):
        p.pad_and_truncate_nbits(12, 0xABCD) == 0xBCD
        assert p.tell() == (1, 3)
    
    def test_zero_pad(self, p):
        assert p.pad_and_truncate_nbits(16, 0xABC) == 0x0ABC
        assert p.tell() == (2, 7)


class TestReadBitArray(object):
    
    def test_read_nothing(self):
        r = bitstream.BitstreamReader(BytesIO())
        assert r.read_bitarray(0) == bitarray()
        assert r.tell() == (0, 7)
    
    def test_read_bytes_msb_first(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xA0"))
        assert r.read_bitarray(8) == bitarray([1, 0, 1, 0, 0, 0, 0, 0])
        assert r.tell() == (1, 7)
    
    def test_read_past_eof(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xA0"))
        assert r.read_bitarray(16) == bitarray([1, 0, 1, 0, 0, 0, 0, 0] + [1]*8)
        assert r.tell() == (1, 7)


class TestWriteBitArray(object):
    
    @pytest.fixture
    def f(self):
        return BytesIO()
    
    @pytest.fixture
    def w(self, f):
        return bitstream.BitstreamWriter(f)
    
    def test_write_nothing(self, w):
        w.write_bitarray(0, bitarray())
        assert w.tell() == (0, 7)
    
    def test_fails_on_wrong_length(self, f, w):
        # Too long
        with pytest.raises(OutOfRangeError, match=r"0b10 is 2 bits, not 1"):
            w.write_bitarray(1, bitarray("10"))
        
        # Too short
        with pytest.raises(OutOfRangeError, match=r"0b10 is 2 bits, not 3"):
            w.write_bitarray(3, bitarray("10"))
    
    def test_write(self, f, w):
        w.write_bitarray(8, bitarray([1, 0, 1, 0, 0, 0, 0, 0]))
        assert w.tell() == (1, 7)
        assert f.getvalue() == b"\xA0"
    
    def test_write_past_eof(self, f, w):
        bw = bitstream.BoundedWriter(w, 4)
        bw.write_bitarray(8, bitarray([1, 0, 1, 0, 1, 1, 1, 1]))
        assert w.tell() == (0, 3)
        w.flush()
        assert f.getvalue() == b"\xA0"


class TestPadAndTruncateBitArray(object):
    
    def test_nothing(self):
        p = bitstream.BitstreamPadAndTruncate()
        assert p.pad_and_truncate_bitarray(0) == bitarray()
        assert p.tell() == (0, 7)
    
    def test_zero_pad(self):
        p = bitstream.BitstreamPadAndTruncate()
        assert p.pad_and_truncate_bitarray(8, bitarray("1111")) == bitarray("00001111")
        assert p.tell() == (1, 7)
    
    def test_truncate(self):
        p = bitstream.BitstreamPadAndTruncate()
        assert p.pad_and_truncate_bitarray(4, bitarray("01011010")) == bitarray("1010")
        assert p.tell() == (0, 3)


class TestReadBytes(object):
    
    def test_read_nothing(self):
        r = bitstream.BitstreamReader(BytesIO())
        assert r.read_bytes(0) == b""
        assert r.tell() == (0, 7)
    
    def test_read_bytes_msb_first(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xDE\xAD\xBE\xEF"))
        assert r.read_bytes(2) == b"\xDE\xAD"
        assert r.tell() == (2, 7)
    
    def test_unaligned(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xDE\xAD\xBE\xEF"))
        r.seek(0, 3)
        assert r.read_bytes(2) == b"\xEA\xDB"
        assert r.tell() == (2, 3)
    
    def test_read_past_eof(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xDE"))
        assert r.read_bytes(2) == b"\xDE\xFF"
        assert r.tell() == (1, 7)


class TestWriteBytes(object):
    
    @pytest.fixture
    def f(self):
        return BytesIO()
    
    @pytest.fixture
    def w(self, f):
        return bitstream.BitstreamWriter(f)
    
    def test_write_nothing(self, w):
        w.write_bytes(0, b"")
        assert w.tell() == (0, 7)
    
    def test_fails_on_wrong_length(self, f, w):
        # Too long
        with pytest.raises(OutOfRangeError, match=r"0xAB_CD is 2 bytes, not 1"):
            w.write_bytes(1, b"\xAB\xCD")
        
        # Too short
        with pytest.raises(OutOfRangeError, match=r"0xAB_CD is 2 bytes, not 3"):
            w.write_bytes(3, b"\xAB\xCD")
    
    def test_write_aligned(self, f, w):
        w.write_bytes(2, b"\xAB\xCD")
        assert w.tell() == (2, 7)
        assert f.getvalue() == b"\xAB\xCD"
    
    def test_write_unaligned(self, f, w):
        w.seek(0, 3)
        w.write_bytes(2, b"\xAB\xCD")
        assert w.tell() == (2, 3)
        w.flush()
        assert f.getvalue() == b"\x0A\xBC\xD0"
    
    def test_write_past_eof(self, f, w):
        bw = bitstream.BoundedWriter(w, 8)
        bw.write_bytes(2, b"\xAB\xFF")
        assert w.tell() == (1, 7)
        w.flush()
        assert f.getvalue() == b"\xAB"


class TestPadAndTruncateBytes(object):
    
    def test_nothing(self):
        p = bitstream.BitstreamPadAndTruncate()
        assert p.pad_and_truncate_bytes(0) == bytes()
        assert p.tell() == (0, 7)
    
    def test_zero_pad(self):
        p = bitstream.BitstreamPadAndTruncate()
        assert p.pad_and_truncate_bytes(2, b"\xFF") == b"\x00\xFF"
        assert p.tell() == (2, 7)
    
    def test_truncate(self):
        p = bitstream.BitstreamPadAndTruncate()
        assert p.pad_and_truncate_bytes(1, b"\xAA\xBB") == b"\xBB"
        assert p.tell() == (1, 7)


class TestReadUint(object):
    
    @pytest.mark.parametrize("encoded,exp_value,exp_tell", [
        # Small values
        (b"\x80", 0, (0, 6)),
        (b"\x20", 1, (0, 4)),
        (b"\x60", 2, (0, 4)),
        (b"\x08", 3, (0, 2)),
        (b"\x18", 4, (0, 2)),
        (b"\x48", 5, (0, 2)),
        (b"\x58", 6, (0, 2)),
        (b"\x02", 7, (0, 0)),
        # Very large values
        (b"\x00"*32 + b"\x80", (1<<128) - 1, (32, 6)),
    ])
    def test_basic_reading(self, encoded, exp_value, exp_tell):
        r = bitstream.BitstreamReader(BytesIO(encoded))
        assert r.read_uint() == exp_value
        assert r.tell() == exp_tell
    
    def test_read_past_eof(self):
        # Odd bit falls off end
        r = bitstream.BitstreamReader(BytesIO(b"\x00"))
        r.seek(0, 7)
        assert r.read_uint() == 15
        
        # Even bit falls off end
        r = bitstream.BitstreamReader(BytesIO(b"\x00"))
        r.seek(0, 6)
        assert r.read_uint() == 16
        
        # Whole string falls off end
        r = bitstream.BitstreamReader(BytesIO(b"\x00"))
        r.seek(1, 7)
        assert r.read_uint() == 0


class TestWriteUint(object):
    
    @pytest.mark.parametrize("value,encoded,exp_tell", [
        # Small values
        (0, b"\x80", (0, 6)),
        (1, b"\x20", (0, 4)),
        (2, b"\x60", (0, 4)),
        (3, b"\x08", (0, 2)),
        (4, b"\x18", (0, 2)),
        (5, b"\x48", (0, 2)),
        (6, b"\x58", (0, 2)),
        (7, b"\x02", (0, 0)),
        # Very large values
        ((1<<128) - 1, b"\x00"*32 + b"\x80", (32, 6)),
    ])
    def test_basic_writing(self, value, encoded, exp_tell):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        w.write_uint(value)
        assert w.tell() == exp_tell
        w.flush()
        assert f.getvalue() == encoded
    
    def test_write_out_of_range(self):
        w = bitstream.BitstreamWriter(BytesIO())
        with pytest.raises(OutOfRangeError, match="-1 is negative, expected positive"):
            w.write_uint(-1)
    
    def test_write_past_eof(self):
        w = bitstream.BitstreamWriter(BytesIO())
        
        # Odd bit falls off end
        bw = bitstream.BoundedWriter(w, 8)
        bw.write_uint(15)
        
        # Even bit falls off end
        bw = bitstream.BoundedWriter(w, 7)
        bw.write_uint(16)
        
        # Whole string falls off end
        bw = bitstream.BoundedWriter(w, 0)
        bw.write_uint(0)


class TestPadAndTruncateUint(object):
    
    def test_nothing(self):
        p = bitstream.BitstreamPadAndTruncate()
        assert p.pad_and_truncate_uint() == 0
        assert p.tell() == (0, 6)
    
    def test_clamp_at_zero(self):
        p = bitstream.BitstreamPadAndTruncate()
        assert p.pad_and_truncate_uint(-5) == 0
        assert p.tell() == (0, 6)
    
    def test_length(self):
        p = bitstream.BitstreamPadAndTruncate()
        assert p.pad_and_truncate_uint(1) == 1
        assert p.tell() == (0, 4)


class TestReadSint(object):
    
    @pytest.mark.parametrize("encoded,exp_value,exp_tell", [
        # Zero
        (b"\x80", 0, (0, 6)),
        # Small values (+ve)
        (b"\x20", 1, (0, 3)),
        (b"\x60", 2, (0, 3)),
        (b"\x08", 3, (0, 1)),
        (b"\x18", 4, (0, 1)),
        (b"\x48", 5, (0, 1)),
        (b"\x58", 6, (0, 1)),
        (b"\x02", 7, (1, 7)),
        # Small values (-ve)
        (b"\x30", -1, (0, 3)),
        (b"\x70", -2, (0, 3)),
        (b"\x0C", -3, (0, 1)),
        (b"\x1C", -4, (0, 1)),
        (b"\x4C", -5, (0, 1)),
        (b"\x5C", -6, (0, 1)),
        (b"\x03", -7, (1, 7)),
        # Very large values
        (b"\x00"*32 + b"\x80", (1<<128) - 1, (32, 5)),
        (b"\x00"*32 + b"\xC0", -((1<<128) - 1), (32, 5)),
    ])
    def test_basic_reading(self, encoded, exp_value, exp_tell):
        r = bitstream.BitstreamReader(BytesIO(encoded))
        assert r.read_sint() == exp_value
        assert r.tell() == exp_tell
    
    
    def test_read_past_eof(self):
        # Sign bit falls off end
        r = bitstream.BitstreamReader(BytesIO(b"\x01"))
        r.seek(0, 6)
        assert r.read_sint() == -7
        
        # Odd bit falls off end
        r = bitstream.BitstreamReader(BytesIO(b"\x00"))
        r.seek(0, 7)
        assert r.read_sint() == -15
        
        # Even bit falls off end
        r = bitstream.BitstreamReader(BytesIO(b"\x00"))
        r.seek(0, 6)
        assert r.read_sint() == -16
        
        # Whole string falls off end
        r = bitstream.BitstreamReader(BytesIO(b"\x00"))
        r.seek(1, 7)
        assert r.read_sint() == 0


class TestWriteSint(object):
    
    @pytest.mark.parametrize("value,encoded,exp_tell", [
        # Zero
        (0, b"\x80", (0, 6)),
        # Small values (+ve)
        (1, b"\x20", (0, 3)),
        (2, b"\x60", (0, 3)),
        (3, b"\x08", (0, 1)),
        (4, b"\x18", (0, 1)),
        (5, b"\x48", (0, 1)),
        (6, b"\x58", (0, 1)),
        (7, b"\x02", (1, 7)),
        # Small values (-ve)
        (-1, b"\x30", (0, 3)),
        (-2, b"\x70", (0, 3)),
        (-3, b"\x0C", (0, 1)),
        (-4, b"\x1C", (0, 1)),
        (-5, b"\x4C", (0, 1)),
        (-6, b"\x5C", (0, 1)),
        (-7, b"\x03", (1, 7)),
        # Very large values
        ((1<<128) - 1, b"\x00"*32 + b"\x80", (32, 5)),
        (-((1<<128) - 1), b"\x00"*32 + b"\xC0", (32, 5)),
    ])
    def test_basic_writing(self, value, encoded, exp_tell):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        w.write_sint(value)
        assert w.tell() == exp_tell
        w.flush()
        assert f.getvalue() == encoded
    
    def test_write_past_eof(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        
        # Sign bit falls off end
        bw = bitstream.BoundedWriter(w, 9)
        bw.write_sint(-15)
        
        # Odd bit falls off end
        bw = bitstream.BoundedWriter(w, 8)
        bw.write_sint(-15)
        
        # Even bit falls off end
        bw = bitstream.BoundedWriter(w, 7)
        bw.write_sint(-16)
        
        # Whole string falls off end
        bw = bitstream.BoundedWriter(w, 0)
        bw.write_sint(0)


class TestPadAndTruncateSint(object):
    
    def test_nothing(self):
        p = bitstream.BitstreamPadAndTruncate()
        assert p.pad_and_truncate_sint() == 0
        assert p.tell() == (0, 6)
    
    def test_length(self):
        p = bitstream.BitstreamPadAndTruncate()
        
        assert p.pad_and_truncate_sint(1) == 1
        assert p.tell() == (0, 3)
        
        assert p.pad_and_truncate_sint(-1) == -1
        assert p.tell() == (1, 7)


def test_bounded_reader():
    r = bitstream.BitstreamReader(BytesIO(b"\xA0"))
    br = bitstream.BoundedReader(r, 12)
    
    for exp_tell, exp_value, exp_br_bits_remaining, exp_br_bits_past_eof in [
                # Within file
                ((0, 7), 1, 11, 0),
                ((0, 6), 0, 10, 0),
                ((0, 5), 1, 9, 0),
                ((0, 4), 0, 8, 0),
                ((0, 3), 0, 7, 0),
                ((0, 2), 0, 6, 0),
                ((0, 1), 0, 5, 0),
                ((0, 0), 0, 4, 0),
                # Past end of file
                ((1, 7), 1, 3, 0),
                ((1, 7), 1, 2, 0),
                ((1, 7), 1, 1, 0),
                ((1, 7), 1, 0, 0),
                # Past end of bounded block
                ((1, 7), 1, 0, 1),
                ((1, 7), 1, 0, 2),
                ((1, 7), 1, 0, 3),
                ((1, 7), 1, 0, 4),
            ]:
        assert br.tell() == exp_tell
        value = br.read_bit()
        assert value == exp_value
        assert br.bits_remaining == exp_br_bits_remaining
        assert br.bits_past_eof == exp_br_bits_past_eof


def test_bounded_writer():
    f = BytesIO()
    w = bitstream.BitstreamWriter(f)
    bw_outer = bitstream.BoundedWriter(w, 8)
    bw = bitstream.BoundedWriter(bw_outer, 12)
    
    for exp_tell, bit, exp_error, exp_bits_past_eof, exp_bw_bits_remaining, exp_bw_bits_past_eof in [
                # Within file
                ((0, 7), 1, False, 0, 11, 0),
                ((0, 6), 0, False, 0, 10, 0),
                ((0, 5), 1, False, 0, 9, 0),
                ((0, 4), 0, False, 0, 8, 0),
                ((0, 3), 0, False, 0, 7, 0),
                ((0, 2), 0, False, 0, 6, 0),
                ((0, 1), 0, False, 0, 5, 0),
                ((0, 0), 0, False, 0, 4, 0),
                # Outer bounded reader limit
                ((1, 7), 1, False, 1, 3, 0),
                ((1, 7), 1, False, 1, 2, 0),
                ((1, 7), 1, False, 1, 1, 0),
                ((1, 7), 1, False, 1, 0, 0),
                # Past bounded block end
                ((1, 7), 1, False, 1, 0, 1),
                ((1, 7), 0, True, 1, 0, 2),
            ]:
        assert bw.tell() == exp_tell
        if exp_error:
            with pytest.raises(ValueError):
                bw.write_bit(bit)
            bw.write_bit(1)
        else:
            bw.write_bit(bit)
        assert bw.bits_remaining == exp_bw_bits_remaining
        assert bw.bits_past_eof == exp_bw_bits_past_eof


def test_bounded_pad_and_truncate():
    p = bitstream.BitstreamPadAndTruncate()
    bp_outer = bitstream.BoundedPadAndTruncate(p, 8)
    bp = bitstream.BoundedPadAndTruncate(bp_outer, 12)
    
    for exp_tell, bit, exp_bits_past_eof, exp_bp_bits_remaining in [
                # Within file
                ((0, 7), 1, 0, 11),
                ((0, 6), 0, 0, 10),
                ((0, 5), 1, 0, 9),
                ((0, 4), 0, 0, 8),
                ((0, 3), 0, 0, 7),
                ((0, 2), 0, 0, 6),
                ((0, 1), 0, 0, 5),
                ((0, 0), 0, 0, 4),
                # Outer bounded reader limit
                ((1, 7), 1, 1, 3),
                ((1, 7), 1, 1, 2),
                ((1, 7), 1, 1, 1),
                ((1, 7), 1, 1, 0),
                # Past bounded block end
                ((1, 7), 1, 1, 0),
                ((1, 7), 0, 1, 0),
            ]:
        assert bp.tell() == exp_tell
        bp.pad_and_truncate_bit(bit)
        assert bp.bits_remaining == exp_bp_bits_remaining
