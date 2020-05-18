import pytest

from io import BytesIO

from bitarray import bitarray

from vc2_conformance.bitstream.exceptions import OutOfRangeError

from vc2_conformance import bitstream


@pytest.mark.parametrize(
    "bytes,bits,offset",
    [
        (0, 7, 0),
        (0, 6, 1),
        (0, 5, 2),
        (0, 4, 3),
        (0, 3, 4),
        (0, 2, 5),
        (0, 1, 6),
        (0, 0, 7),
        (1, 7, 8),
        (1, 6, 9),
        (2, 6, 17),
    ],
)
def test_to_and_from_bit_offset(bytes, bits, offset):
    assert bitstream.to_bit_offset(bytes, bits) == offset
    assert bitstream.from_bit_offset(offset) == (bytes, bits)


class TestBistreamReader(object):
    def test_reading(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xA5\x0F"))

        expected = [1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1]  # 0xA5  # 0x0F
        for expected_bit in expected:
            assert r.read_bit() == expected_bit

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

    def test_read_past_eof_and_is_end_of_stream(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xA5\x0F"))

        for _ in range(16):
            assert r.is_end_of_stream() is False
            r.read_bit()

        # Read past end
        assert r.is_end_of_stream() is True
        with pytest.raises(EOFError):
            r.read_bit()

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
        with pytest.raises(EOFError):
            r.read_bit()
        r.seek(2, 0)
        with pytest.raises(EOFError):
            r.read_bit()
        r.seek(100, 7)
        with pytest.raises(EOFError):
            r.read_bit()

    def test_bounded_block(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xA0"))

        r.bounded_block_begin(4)

        # Can't nest bounded blocks
        with pytest.raises(Exception, match=r".*nest.*"):
            r.bounded_block_begin(1)

        # Read bits from stream
        assert r.read_bit() == 1
        assert r.bits_remaining == 3
        assert r.tell() == (0, 6)

        assert r.read_bit() == 0
        assert r.bits_remaining == 2
        assert r.tell() == (0, 5)

        assert r.read_bit() == 1
        assert r.bits_remaining == 1
        assert r.tell() == (0, 4)

        assert r.read_bit() == 0
        assert r.bits_remaining == 0
        assert r.tell() == (0, 3)

        # End of bounded block, read all '1's but otherwise don't advance
        assert r.read_bit() == 1
        assert r.bits_remaining == -1
        assert r.tell() == (0, 3)

        assert r.read_bit() == 1
        assert r.bits_remaining == -2
        assert r.tell() == (0, 3)

        # At end of bounded block, remaining bits are reported
        assert r.bounded_block_end() == 0

        # Can't double-close bounded blocks
        with pytest.raises(Exception, match=r"Not in bounded block"):
            r.bounded_block_end()

        # Now outside of block can read again
        assert r.read_bit() == 0
        assert r.bits_remaining is None
        assert r.tell() == (0, 2)

        # If unused bits remain in block, those are reported
        r.bounded_block_begin(3)
        assert r.bounded_block_end() == 3

    def test_bounded_block_seek(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xA0"))

        r.bounded_block_begin(4)
        assert r.tell() == (0, 7)
        assert r.bits_remaining == 4

        # Should be able to seek to current position and succeed
        r.seek(0, 7)
        assert r.tell() == (0, 7)
        assert r.bits_remaining == 4

        # Should be able to seek to end of bounded block and succeed
        r.seek(0, 3)
        assert r.tell() == (0, 3)
        assert r.bits_remaining == 0

        # Should be able to come back again
        r.seek(0, 4)
        assert r.tell() == (0, 4)
        assert r.bits_remaining == 1

        # After reading past the end of the block, seeking to the end of the
        # block shouldn't change bits remaining
        assert r.read_nbits(5) == 0b01111
        assert r.tell() == (0, 3)
        assert r.bits_remaining == -4
        r.seek(0, 3)
        assert r.tell() == (0, 3)
        assert r.bits_remaining == -4

        # Moving before the end of block again should adjust the count
        # accordingly, however.
        r.seek(0, 4)
        assert r.tell() == (0, 4)
        assert r.bits_remaining == 1

        # Should not be able to seek past the end of the block
        with pytest.raises(Exception):
            r.seek(0, 2)
        assert r.tell() == (0, 4)
        assert r.bits_remaining == 1

    def test_try_read_bitarray(self):
        # Read next few bits
        r = bitstream.BitstreamReader(BytesIO(b"\xAA"))
        assert r.try_read_bitarray(4).to01() == "1010"

        # Try to read past EOF
        r = bitstream.BitstreamReader(BytesIO(b"\xAA"))
        assert r.try_read_bitarray(16).to01() == "10101010"

        # Read past bounded block
        r = bitstream.BitstreamReader(BytesIO(b"\xAA"))
        r.bounded_block_begin(4)
        assert r.try_read_bitarray(8).to01() == "10101010"


class TestBistreamWriter(object):
    def test_writing_whole_number_of_bytes(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)

        for bit in [1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1]:  # 0xA5  # 0x0F
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

    def test_is_end_of_stream(self):
        w = bitstream.BitstreamWriter(BytesIO())
        assert w.is_end_of_stream() is True

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

    def test_bounded_block(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)

        w.bounded_block_begin(4)

        # Can't nest bounded blocks
        with pytest.raises(Exception, match=r".*nest.*"):
            w.bounded_block_begin(1)

        # Write bits to stream
        w.write_bit(1)
        assert w.bits_remaining == 3
        assert w.tell() == (0, 6)

        w.write_bit(0)
        assert w.bits_remaining == 2
        assert w.tell() == (0, 5)

        w.write_bit(1)
        assert w.bits_remaining == 1
        assert w.tell() == (0, 4)

        w.write_bit(0)
        assert w.bits_remaining == 0
        assert w.tell() == (0, 3)

        # End of bounded block, can write '1's but otherwise don't advance
        w.write_bit(1)
        assert w.bits_remaining == -1
        assert w.tell() == (0, 3)

        w.write_bit(1)
        assert w.bits_remaining == -2
        assert w.tell() == (0, 3)

        # Can't write 0s past end of bounded block
        with pytest.raises(ValueError, match=r".*bounded block.*"):
            w.write_bit(0)

        # Expected value should have been written
        w.flush()
        assert f.getvalue() == b"\xA0"

        # At end of bounded block, remaining bits are reported
        assert w.bounded_block_end() == 0

        # Can't double-close bounded blocks
        with pytest.raises(Exception, match=r"Not in bounded block"):
            w.bounded_block_end()

        # Now outside of block can write again
        w.write_bit(0)
        assert w.bits_remaining is None
        assert w.tell() == (0, 2)
        w.write_bit(1)
        assert w.bits_remaining is None
        assert w.tell() == (0, 1)

        w.flush()
        assert f.getvalue() == b"\xA4"

        # If unused bits remain in block, those are reported
        w.bounded_block_begin(2)
        assert w.bounded_block_end() == 2

    def test_bounded_block_seek(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)

        w.bounded_block_begin(4)
        assert w.tell() == (0, 7)
        assert w.bits_remaining == 4

        # Should be able to seek to current position and succeed
        w.seek(0, 7)
        assert w.tell() == (0, 7)
        assert w.bits_remaining == 4

        # Should be able to seek to end of bounded block and succeed
        w.seek(0, 3)
        assert w.tell() == (0, 3)
        assert w.bits_remaining == 0

        # Should be able to come back again
        w.seek(0, 4)
        assert w.tell() == (0, 4)
        assert w.bits_remaining == 1

        # After writing past the end of the block, seeking to the end of the
        # block shouldn't change bits remaining
        w.write_nbits(5, 0b01111)
        assert w.tell() == (0, 3)
        assert w.bits_remaining == -4
        w.seek(0, 3)
        assert w.tell() == (0, 3)
        assert w.bits_remaining == -4

        # Moving before the end of block again should adjust the count
        # accordingly, however.
        w.seek(0, 4)
        assert w.tell() == (0, 4)
        assert w.bits_remaining == 1

        # Should not be able to seek past the end of the block
        with pytest.raises(Exception):
            w.seek(0, 2)
        assert w.tell() == (0, 4)
        assert w.bits_remaining == 1


class TestReadNbits(object):
    def test_read_nothing(self):
        r = bitstream.BitstreamReader(BytesIO())
        assert r.read_nbits(0) == 0
        assert r.tell() == (0, 7)

    def test_read_bytes_msb_first(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xA0\x50"))
        assert r.read_nbits(12) == 0xA05
        assert r.tell() == (1, 3)


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


class TestReadUIntLit(object):
    def test_read_nothing(self):
        r = bitstream.BitstreamReader(BytesIO())
        assert r.read_uint_lit(0) == 0
        assert r.tell() == (0, 7)

    def test_read_bytes_msb_first(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xA0\x50\xFF"))
        assert r.read_uint_lit(2) == 0xA050
        assert r.tell() == (2, 7)


class TestWriteUintLit(object):
    @pytest.fixture
    def f(self):
        return BytesIO()

    @pytest.fixture
    def w(self, f):
        return bitstream.BitstreamWriter(f)

    def test_write_nothing(self, w):
        w.write_uint_lit(0, 0)
        assert w.tell() == (0, 7)

    def test_fail_on_too_many_bits(self, f, w):
        with pytest.raises(OutOfRangeError, match=r"0b101000000000 is 12 bits, not 8"):
            w.write_uint_lit(1, 0xA00)

    def test_write_zeros_above_msb(self, f, w):
        w.write_uint_lit(2, 0xABC)
        assert w.tell() == (2, 7)
        w.flush()
        assert f.getvalue() == b"\x0A\xBC"


class TestReadBitArray(object):
    def test_read_nothing(self):
        r = bitstream.BitstreamReader(BytesIO())
        assert r.read_bitarray(0) == bitarray()
        assert r.tell() == (0, 7)

    def test_read_bytes_msb_first(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xA0"))
        assert r.read_bitarray(8) == bitarray([1, 0, 1, 0, 0, 0, 0, 0])
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

    def test_fails_if_too_long(self, f, w):
        with pytest.raises(OutOfRangeError, match=r"0b10 is 2 bits, not 1"):
            w.write_bitarray(1, bitarray("10"))

    def test_write(self, f, w):
        w.write_bitarray(8, bitarray([1, 0, 1, 0, 0, 0, 0, 0]))
        assert w.tell() == (1, 7)
        assert f.getvalue() == b"\xA0"

    def test_zero_pads_if_too_short(self, f, w):
        w.write_bitarray(8, bitarray([1, 1, 1, 1]))
        assert w.tell() == (1, 7)
        assert f.getvalue() == b"\xF0"


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

    def test_fails_if_too_long(self, f, w):
        with pytest.raises(OutOfRangeError, match=r"0xAB_CD is 2 bytes, not 1"):
            w.write_bytes(1, b"\xAB\xCD")

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

    def test_zero_pads_if_too_short(self, f, w):
        w.write_bytes(2, b"\xFF")
        assert w.tell() == (2, 7)
        assert f.getvalue() == b"\xFF\x00"


class TestReadUint(object):
    @pytest.mark.parametrize(
        "encoded,exp_value,exp_tell",
        [
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
            (b"\x00" * 32 + b"\x80", (1 << 128) - 1, (32, 6)),
        ],
    )
    def test_basic_reading(self, encoded, exp_value, exp_tell):
        r = bitstream.BitstreamReader(BytesIO(encoded))
        assert r.read_uint() == exp_value
        assert r.tell() == exp_tell


class TestWriteUint(object):
    @pytest.mark.parametrize(
        "value,encoded,exp_tell",
        [
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
            ((1 << 128) - 1, b"\x00" * 32 + b"\x80", (32, 6)),
        ],
    )
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


class TestReadSint(object):
    @pytest.mark.parametrize(
        "encoded,exp_value,exp_tell",
        [
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
            (b"\x00" * 32 + b"\x80", (1 << 128) - 1, (32, 5)),
            (b"\x00" * 32 + b"\xC0", -((1 << 128) - 1), (32, 5)),
        ],
    )
    def test_basic_reading(self, encoded, exp_value, exp_tell):
        r = bitstream.BitstreamReader(BytesIO(encoded))
        assert r.read_sint() == exp_value
        assert r.tell() == exp_tell


class TestWriteSint(object):
    @pytest.mark.parametrize(
        "value,encoded,exp_tell",
        [
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
            ((1 << 128) - 1, b"\x00" * 32 + b"\x80", (32, 5)),
            (-((1 << 128) - 1), b"\x00" * 32 + b"\xC0", (32, 5)),
        ],
    )
    def test_basic_writing(self, value, encoded, exp_tell):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        w.write_sint(value)
        assert w.tell() == exp_tell
        w.flush()
        assert f.getvalue() == encoded
