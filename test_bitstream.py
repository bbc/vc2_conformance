import pytest

from io import BytesIO

import bitstream


class TestBistreamReader(object):
    
    def test_reading(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xA5\x0F"))
        
        expected = [1, 0, 1, 0, 0, 1, 0, 1,  # 0xA5
                    0, 0, 0, 0, 1, 1, 1, 1]  # 0x0F
        for expected_bit in expected:
            assert r.read_bit() == expected_bit
        
        # Reading past the end should return None...
        for _ in range(16):
            assert r.read_bit() is None
    
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
        assert r.read_bit() is None
        assert r.tell() == (2, 7)
    
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
        assert r.read_bit() is None
        r.seek(2, 0)
        assert r.read_bit() is None
        r.seek(100, 7)
        assert r.read_bit() is None


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


class TestBool(object):
    
    def test_value(self):
        b = bitstream.Bool()
        assert b.value is False
        assert b.length == 1
        
        b = bitstream.Bool(False)
        assert b.value is False
        assert b.length == 1
        
        b = bitstream.Bool(True)
        assert b.value is True
        assert b.length == 1
    
    def test_read(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xAA"))
        b = bitstream.Bool()
        
        b.read(r)
        assert b.value is True
        assert b.offset == (0, 7)
        assert b.bits_past_eof == 0
        
        b.read(r)
        assert b.value is False
        assert b.offset == (0, 6)
        assert b.bits_past_eof == 0
    
    def test_read_past_eof(self):
        r = bitstream.BitstreamReader(BytesIO(b""))
        b = bitstream.Bool()
        
        for _ in range(8):
            b.read(r)
            assert b.value is True
            assert b.offset == (0, 7)
            assert b.bits_past_eof == 1
    
    def test_write(self):
        f = BytesIO(b"")
        w = bitstream.BitstreamWriter(f)
        b = bitstream.Bool()
        
        for i in range(8):
            b.value = bool(i % 2 == 0)
            b.write(w)
            assert b.offset == (0, 7-i)
        
        assert f.getvalue() == b"\xAA"


class TestNBits(object):
    
    def test_value(self):
        n = bitstream.NBits()
        assert n.value == 0
        assert n.length == 0
        
        n = bitstream.NBits(123, 8)
        assert n.value == 123
        assert n.length == 8
    
    @pytest.mark.parametrize("value,length", [
        # Negative values should always fail
        (-1, 0),
        (-1, 100),
        # Too-large values
        (1, 0),
        (128, 7),
    ])
    def test_validation(self, value, length):
        with pytest.raises(ValueError):
            b = bitstream.NBits(value, length)
        
        b = bitstream.NBits(length=1000)
        b.length = length
        with pytest.raises(ValueError):
            b.value = value
        assert b.length == length
        assert b.value == 0
        
        if value >= 0:
            b = bitstream.NBits(length=1000)
            b.value = value
            with pytest.raises(ValueError):
                b.length = length
            assert b.value == value
            assert b.length == 1000
    
    def test_read(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xAA"))
        n = bitstream.NBits(length=3)
        
        n.read(r)
        assert n.value == 5
        assert n.offset == (0, 7)
        assert n.bits_past_eof == 0
        
        n.read(r)
        assert n.value == 2
        assert n.offset == (0, 4)
        assert n.bits_past_eof == 0
    
    def test_read_past_eof(self):
        r = bitstream.BitstreamReader(BytesIO(b"\x00"))
        n = bitstream.NBits(length=10)
        
        n.read(r)
        assert n.value == 3
        assert n.offset == (0, 7)
        assert n.bits_past_eof == 2
        
        n.read(r)
        assert n.value == 0b1111111111
        assert n.offset == (1, 7)
        assert n.bits_past_eof == 10
    
    def test_write(self):
        f = BytesIO(b"")
        w = bitstream.BitstreamWriter(f)
        n = bitstream.NBits(length=4)
        
        n.value = 0xA
        n.write(w)
        assert n.offset == (0, 7)
        
        n.value = 0x5
        n.write(w)
        assert n.offset == (0, 3)
        
        assert f.getvalue() == b"\xA5"


class TestByteAlign(object):
    
    def test_value(self):
        b = bitstream.ByteAlign()
        assert b.value == 0
        
        b = bitstream.ByteAlign(123)
        assert b.value == 123
    
    def test_read(self):
        r = bitstream.BitstreamReader(BytesIO(b"\xAA"))
        b = bitstream.ByteAlign(7)
        
        # No need to advance
        b.read(r)
        assert b.offset == (0, 7)
        assert b.value == 0
        assert b.length == 0
        assert r.tell() == (0, 7)
        
        assert r.read_bit() == 1
        
        # Advance to end of byte
        b.read(r)
        assert b.offset == (0, 6)
        assert b.value == 0x2A
        assert b.length == 7
        assert r.tell() == (1, 7)
    
    def test_read_past_eof(self):
        r = bitstream.BitstreamReader(BytesIO(b""))
        b = bitstream.ByteAlign()
        
        b.read(r)
        assert b.value == 0
        assert b.offset == (0, 7)
        assert b.bits_past_eof == 0
    
    def test_write(self):
        f = BytesIO(b"")
        w = bitstream.BitstreamWriter(f)
        b = bitstream.ByteAlign()
        
        b.value = 0xFA
        b.write(w)
        assert b.offset == (0, 7)
        assert b.length == 0
        assert b.value == 0xFA

        w.flush()
        assert f.getvalue() == b""
        
        w.write_bit(0)
        
        b.write(w)
        assert b.offset == (0, 6)
        assert b.length == 7
        assert b.value == 0xFA
        
        assert f.getvalue() == b"\x7A"


class TestUInt(object):
    
    def test_value_and_length(self):
        u = bitstream.UInt()
        assert u.value == 0
        assert u.length == 1
        
        u = bitstream.UInt(1)
        assert u.value == 1
        assert u.length == 3
        
        u.value = 2
        assert u.value == 2
        assert u.length == 3
        
        u.value = 3
        assert u.value == 3
        assert u.length == 5
    
    def test_non_negative(self):
        with pytest.raises(ValueError):
            bitstream.UInt(-1)
        
        u = bitstream.UInt()
        with pytest.raises(ValueError):
            u.value = -1
        assert u.value == 0
    
    def test_read(self):
        r = bitstream.BitstreamReader(BytesIO(b"\x1F"))
        u = bitstream.UInt()
        
        u.read(r)
        assert u.value == 4
        assert u.length == 5
        assert u.offset == (0, 7)
        assert u.bits_past_eof == 0
        
        u.read(r)
        assert u.value == 0
        assert u.length == 1
        assert u.offset == (0, 2)
        assert u.bits_past_eof == 0
    
    def test_read_past_eof(self):
        r = bitstream.BitstreamReader(BytesIO(b"\x00"))
        u = bitstream.UInt()
        
        # The even-bit falls off the end
        u.read(r)
        assert u.value == 15
        assert u.length == 9
        assert u.offset == (0, 7)
        assert u.bits_past_eof == 1
        
        # The whole string falls off the end
        u.read(r)
        assert u.value == 0
        assert u.length == 1
        assert u.offset == (1, 7)
        assert u.bits_past_eof == 1
        
        r = bitstream.BitstreamReader(BytesIO(b"\x00"))
        r.read_bit()
        u = bitstream.UInt()
        
        # The odd-bit falls off the end
        u.read(r)
        assert u.value == 16
        assert u.length == 9
        assert u.offset == (0, 6)
        assert u.bits_past_eof == 2
    
    def test_write(self):
        f = BytesIO(b"")
        w = bitstream.BitstreamWriter(f)
        u = bitstream.UInt()
        
        u.value = 0
        u.write(w)
        w.flush()
        assert u.offset == (0, 7)
        assert f.getvalue() == b"\x80"
        
        u.value = 1
        u.write(w)
        w.flush()
        assert u.offset == (0, 6)
        assert f.getvalue() == b"\x90"
    
    
    @pytest.mark.parametrize("value", [
        # Simple values
        0, 1, 2, 3, 4, 5, 6,
        # "Large" values
        1234567890,
        # The largest value a Python 2 int can hold (before being promoted to a
        # long) on 32-bit and 64-bit platforms
        int((1<<31) - 1),
        int((1<<63) - 1),
        # A very large (certainly Python 2 long) value
        0xDEADBEEF<<128,
    ])
    def test_write_read_and_length_are_consistent(self, value):
        # A 'fuzz'-style test to see if the three different functions which
        # rely on correctly interpreting the exp Golomb code are consistent
        # with eachother
        f = BytesIO(b"")
        w = bitstream.BitstreamWriter(f)
        u = bitstream.UInt(value)
        
        u.write(w)
        
        # Length written should match computed length
        assert u.length == ((w.tell()[0] * 8) + (7 - w.tell()[1]))
        
        w.flush()
        r = bitstream.BitstreamReader(BytesIO(f.getvalue()))
        
        # Value read back should have been correctly reconstructed
        u.value = 999
        u.read(r)
        assert u.value == value
        assert u.bits_past_eof == 0
        
        # Ammount read should be exactly the ammount written
        assert r.tell() == w.tell()


class TestSInt(object):
    
    def test_value_and_length(self):
        s = bitstream.SInt()
        assert s.value == 0
        assert s.length == 1
        
        s = bitstream.SInt(1)
        assert s.value == 1
        assert s.length == 4
        
        s.value = -1
        assert s.value == -1
        assert s.length == 4
        
        s.value = 3
        assert s.value == 3
        assert s.length == 6
        
        s.value = -3
        assert s.value == -3
        assert s.length == 6
    
    def test_read(self):
        r = bitstream.BitstreamReader(BytesIO(b"\x06\x07\xFF"))
        s = bitstream.SInt()
        
        s.read(r)
        assert s.value == 8
        assert s.length == 8
        assert s.offset == (0, 7)
        assert s.bits_past_eof == 0
        
        s.read(r)
        assert s.value == -8
        assert s.length == 8
        assert s.offset == (1, 7)
        assert s.bits_past_eof == 0
        
        s.read(r)
        assert s.value == 0
        assert s.length == 1
        assert s.offset == (2, 7)
        assert s.bits_past_eof == 0
    
    def test_read_past_eof(self):
        r = bitstream.BitstreamReader(BytesIO(b""))
        s = bitstream.SInt()
        
        # The whole string falls off the end
        s.read(r)
        assert s.value == 0
        assert s.length == 1
        assert s.offset == (0, 7)
        assert s.bits_past_eof == 1
        
        r = bitstream.BitstreamReader(BytesIO(b"\x00"))
        s = bitstream.SInt()
        
        # The even-bit and sign fall off the end
        s.read(r)
        assert s.value == -15
        assert s.length == 10
        assert s.offset == (0, 7)
        assert s.bits_past_eof == 2
        
        r = bitstream.BitstreamReader(BytesIO(b"\x00"))
        r.read_bit()
        s = bitstream.SInt()
        
        # The odd-bit and sign falls off the end
        s.read(r)
        assert s.value == -16
        assert s.length == 10
        assert s.offset == (0, 6)
        assert s.bits_past_eof == 3
        
        r = bitstream.BitstreamReader(BytesIO(b"\x01"))
        r.read_bit()
        s = bitstream.SInt()
        
        # The sign falls off the end
        s.read(r)
        assert s.value == -7
        assert s.length == 8
        assert s.offset == (0, 6)
        assert s.bits_past_eof == 1
    
    def test_write(self):
        f = BytesIO(b"")
        w = bitstream.BitstreamWriter(f)
        s = bitstream.SInt()
        
        s.value = 0
        s.write(w)
        w.flush()
        assert s.offset == (0, 7)
        assert f.getvalue() == b"\x80"
        
        s.value = 1
        s.write(w)
        w.flush()
        assert s.offset == (0, 6)
        assert f.getvalue() == b"\x90"
        
        s.value = -1
        s.write(w)
        w.flush()
        assert s.offset == (0, 2)
        assert f.getvalue() == b"\x91\x80"
    
    
    @pytest.mark.parametrize("value", [
        # Zero
        0,
        # Small values
        1, 2, 3, 4, 5, 6,
        -1, -2, -3, -4, -5, -6,
        # "Large" values
        1234567890,
        -1234567890,
        # The largest value a Python 2 int can hold (before being promoted to a
        # long) on 32-bit and 64-bit platforms
        int((1<<31) - 1),
        (-1<<31),
        int((1<<63) - 1),
        (-1<<63),
        # A very large (certainly Python 2 long) value
        0xDEADBEEF<<128,
        -0xDEADBEEF<<128,
    ])
    def test_write_read_and_length_are_consistent(self, value):
        # A 'fuzz'-style test to see if the three different functions which
        # rely on correctly interpreting the exp Golomb code are consistent
        # with eachother
        f = BytesIO(b"")
        w = bitstream.BitstreamWriter(f)
        s = bitstream.SInt(value)
        
        s.write(w)
        
        # Length written should match computed length
        assert s.length == ((w.tell()[0] * 8) + (7 - w.tell()[1]))
        
        w.flush()
        r = bitstream.BitstreamReader(BytesIO(f.getvalue()))
        
        # Value read back should have been correctly reconstructed
        s.value = 999
        s.read(r)
        assert s.value == value
        assert s.bits_past_eof == 0
        
        # Ammount read should be exactly the ammount written
        assert r.tell() == w.tell()


class TestBoundedBlock(object):
    
    def test_read(self):
        r = bitstream.BitstreamReader(BytesIO(b"\x12\x34\x56"))
        b = bitstream.BoundedBlock(8)
        
        # Read exactly the whole block
        with b.read(r) as br:
            n1 = bitstream.NBits(length=4)
            n2 = bitstream.NBits(length=4)
            
            n1.read(br)
            n2.read(br)
            
            assert n1.value == 0x1
            assert n1.offset == (0, 7)
            assert n1.bits_past_eof == 0
            
            assert n2.value == 0x2
            assert n2.offset == (0, 3)
            assert n2.bits_past_eof == 0
        
        assert b.offset == (0, 7)
        assert b.value == 0
        assert b.unused_bits == 0
        assert b.bits_past_eof == 0
        
        
        # Read less than the whole block
        with b.read(r) as br:
            n3 = bitstream.NBits(length=4)
            
            n3.read(br)
            
            assert n3.value == 0x3
            assert n3.offset == (1, 7)
            assert n3.bits_past_eof == 0
        
        assert b.value == 0x4
        assert b.offset == (1, 7)
        assert b.unused_bits == 4
        assert b.bits_past_eof == 0
        
        # Read more than the whole block
        with b.read(r) as br:
            n4 = bitstream.NBits(length=4)
            n5 = bitstream.NBits(length=8)
            
            n4.read(br)
            n5.read(br)
            
            assert n4.value == 0x5
            assert n4.offset == (2, 7)
            assert n4.bits_past_eof == 0
            
            assert n5.value == 0x6F
            assert n5.offset == (2, 3)
            assert n5.bits_past_eof == 4
        
        assert b.value == 0
        assert b.offset == (2, 7)
        assert b.unused_bits == 0
        assert b.bits_past_eof == 0
    
    def test_read_past_end(self):
        # If the block extends past the end of the file, both the block and its
        # contents should have bits_past_eof set accordingly, in addition to
        # any bits beyond the end of the block.
        r = bitstream.BitstreamReader(BytesIO(b"\x12"))
        b = bitstream.BoundedBlock(16)
        
        with b.read(r) as br:
            u = bitstream.NBits(length=24)
            u.read(br)
            
            assert u.value == 0x12FFFF
            assert u.bits_past_eof == 8 + 8
        
        assert b.value == 0
        assert b.bits_past_eof == 8
    
    def test_write(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        b = bitstream.BoundedBlock(8)
        b.value = 0xAB
        
        # Write exactly the whole block
        with b.write(w) as bw:
            n1 = bitstream.NBits(0x1, 4)
            n2 = bitstream.NBits(0x2, 4)
            
            n1.write(bw)
            n2.write(bw)
            
            assert n1.offset == (0, 7)
            assert n2.offset == (0, 3)
        
        assert b.unused_bits == 0
        assert b.offset == (0, 7)
        
        # Write less than the whole block
        with b.write(w) as bw:
            n3 = bitstream.NBits(0x3, 4)
            
            n3.write(bw)
            
            assert n3.offset == (1, 7)
        
        assert b.unused_bits == 4
        assert b.offset == (1, 7)
        
        # Write more than the whole block
        with b.write(w) as bw:
            n4 = bitstream.NBits(0x4, 4)
            n5 = bitstream.NBits(0x5, 4)
            n6 = bitstream.NBits(0xF, 4)
            n7 = bitstream.NBits(0xF, 4)
            
            n4.write(bw)
            n5.write(bw)
            n6.write(bw)
            n7.write(bw)
            
            assert n4.offset == (2, 7)
            assert n5.offset == (2, 3)
            assert n6.offset == (3, 7)
            assert n7.offset == (3, 7)
        
        assert b.unused_bits == 0
        assert b.offset == (2, 7)
        
        assert f.getvalue() == b"\x12\x3B\x45"
    
    def test_write_zero_past_end_of_block_fails(self):
        w = bitstream.BitstreamWriter(BytesIO())
        b = bitstream.BoundedBlock(8)
        
        with b.write(w) as bw:
            n = bitstream.NBits(0, 16)
            with pytest.raises(ValueError):
                n.write(bw)


class TestConcatenation(object):
    
    def test_validate(self):
        # Empty is OK
        c = bitstream.Concatenation()
        assert list(c.value) == []
        
        # OK
        u1 = bitstream.UInt()
        u2 = bitstream.UInt()
        u3 = bitstream.UInt()
        c = bitstream.Concatenation(u1, u2, u3)
        assert list(c.value) == [u1, u2, u3]
        
        # OK
        c.value = [u3, u2,u1]
        assert list(c.value) == [u3, u2,u1]
        
        # Not OK
        with pytest.raises(ValueError):
            bitstream.Concatenation(123)  # Not a BitstreamValue
        
        # Not OK
        with pytest.raises(ValueError):
            c.value = u1  # Not an iterable
        with pytest.raises(ValueError):
            c.value = 123  # Not an iterable/BitstreamValue
        with pytest.raises(ValueError):
            c.value = [123]  # Not a BitstreamValue
        assert list(c.value) == [u3, u2,u1]
    
    def test_length(self):
        u0 = bitstream.UInt(0)
        u1 = bitstream.UInt(1)
        u2 = bitstream.UInt(2)
        
        c = bitstream.Concatenation(u0, u1, u2)
        assert c.length == 1 + 3 + 3
        
        # Should update length as values change...
        u0.value = 3
        assert c.length == 5 + 3 + 3
    
    def test_read(self):
        r = bitstream.BitstreamReader(BytesIO(b"\x36"))
        
        u1 = bitstream.SInt()
        u2 = bitstream.SInt()
        
        c = bitstream.Concatenation(u1, u2)
        
        c.read(r)
        
        assert u1.value == -1
        assert u1.offset == (0, 7)
        
        assert u2.value == 2
        assert u2.offset == (0, 3)
        
        assert c.offset == (0, 7)
    
    def test_write(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        
        u1 = bitstream.SInt(-1)
        u2 = bitstream.SInt(2)
        
        c = bitstream.Concatenation(u1, u2)
        
        c.write(w)
        
        assert u1.offset == (0, 7)
        assert u2.offset == (0, 3)
        assert c.offset == (0, 7)
        
        assert f.getvalue() == b"\x36"
    
    def test_length(self):
        r = bitstream.BitstreamReader(BytesIO())
        
        b = bitstream.ByteAlign()
        u = bitstream.UInt()
        
        c = bitstream.Concatenation(b, u)
        
        # One of the parts is unknown so the whole is also unknown
        assert c.length is None
        
        # After reading/writing, the value becomes known
        c.read(r)
        assert c.length == 1
    
    def test_bits_past_eof(self):
        r = bitstream.BitstreamReader(BytesIO(b"\x00"))
        
        n1 = bitstream.NBits(length=5)
        n2 = bitstream.NBits(length=5)
        
        c = bitstream.Concatenation(n1, n2)
        
        assert c.bits_past_eof is None
        
        # After reading/writing, the value becomes known
        c.read(r)
        assert c.bits_past_eof == 2
