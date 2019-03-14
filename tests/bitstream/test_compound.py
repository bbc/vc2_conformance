import pytest

from io import BytesIO

from vc2_conformance import bitstream


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


class TestMaybe(object):
    
    def test_validation(self):
        u1 = bitstream.UInt()
        u2 = bitstream.UInt()
        
        # OK
        m = bitstream.Maybe(u1, lambda: False)
        assert m.value is u1
        assert m.flag_fn() is False
        
        # OK
        m.value = u2
        m.flag_fn = lambda: True
        
        assert m.value is u2
        assert m.flag_fn() is True
        
        # Not OK
        with pytest.raises(ValueError):
            bitstream.Maybe(lambda: False, u1)
        with pytest.raises(ValueError):
            m.value = lambda: False
        
        assert m.value is u2
    
    def test_value_present(self):
        value = bitstream.UInt()
        
        # Should cast to bool
        m = bitstream.Maybe(value, lambda: 123)
        assert m.flag is True
        m.flag_fn = lambda: None
        assert m.flag is False
    
    def test_length(self):
        value = bitstream.UInt()
        
        m = bitstream.Maybe(value, lambda: True)
        
        value.value = 3
        
        assert m.length == 5
        
        m.flag_fn = lambda: False
        assert m.length == 0
    
    def test_bits_past_eof(self):
        r = bitstream.BitstreamReader(BytesIO())
        
        value = bitstream.UInt()
        
        m = bitstream.Maybe(value, lambda: False)
        
        value.read(r)
        
        m.flag_fn = lambda: True
        assert m.bits_past_eof == 1
        
        m.flag_fn = lambda: False
        assert m.bits_past_eof == 0
    
    def test_read(self):
        r = bitstream.BitstreamReader(BytesIO(b"\x00"))
        
        value = bitstream.UInt()
        
        m = bitstream.Maybe(value, lambda: False)
        
        m.flag_fn = lambda: False
        m.read(r)
        assert r.tell() == (0, 7)
        assert m.offset == (0, 7)
        assert value.offset is None  # Value not read
        
        m.flag_fn = lambda: True
        m.read(r)
        assert value.value == 15
        assert r.tell() == (1, 7)
        assert m.offset == (0, 7)
        assert value.offset == (0, 7)  # Value was read
    
    def test_write(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        
        value = bitstream.UInt(15)
        
        m = bitstream.Maybe(value, lambda: False)
        
        m.flag_fn = lambda: False
        m.write(w)
        w.flush()
        assert f.getvalue() == b""
        assert w.tell() == (0, 7)
        assert m.offset == (0, 7)
        assert value.offset is None  # Value not written
        
        m.flag_fn = lambda: True
        m.write(w)
        w.flush()
        assert f.getvalue() == b"\x00\x80"
        assert w.tell() == (1, 6)
        assert m.offset == (0, 7)
        assert value.offset == (0, 7)  # Value was written


class TestBoundedBlock(object):
    
    def test_read(self):
        r = bitstream.BitstreamReader(BytesIO(b"\x12\x34\x56"))
        
        # Read exactly the whole block
        n1 = bitstream.NBits(length=8)
        b = bitstream.BoundedBlock(n1, 8)
        b.read(r)
        
        assert n1.value == 0x12
        assert n1.offset == (0, 7)
        assert n1.bits_past_eof == 0
        
        assert b.offset == (0, 7)
        assert b.pad_value == 0
        assert b.unused_bits == 0
        assert b.bits_past_eof == 0
        
        
        # Read less than the whole block
        n2 = bitstream.NBits(length=4)
        b = bitstream.BoundedBlock(n2, 8)
        b.read(r)
            
        assert n2.value == 0x3
        assert n2.offset == (1, 7)
        assert n2.bits_past_eof == 0
        
        assert b.pad_value == 0x4
        assert b.offset == (1, 7)
        assert b.unused_bits == 4
        assert b.bits_past_eof == 0
        
        # Read more than the whole block
        n3 = bitstream.NBits(length=12)
        b = bitstream.BoundedBlock(n3, 8)
        b.read(r)
        
        assert n3.value == 0x56F
        assert n3.offset == (2, 7)
        assert n3.bits_past_eof == 4
        
        assert b.pad_value == 0
        assert b.offset == (2, 7)
        assert b.unused_bits == 0
        assert b.bits_past_eof == 0
    
    def test_read_past_end(self):
        # If the block extends past the end of the file, both the block and its
        # contents should have bits_past_eof set accordingly, in addition to
        # any bits beyond the end of the block.
        r = bitstream.BitstreamReader(BytesIO(b"\x12"))
        
        n = bitstream.NBits(length=24)
        b = bitstream.BoundedBlock(n, 16)
        b.read(r)
        
        assert n.value == 0x12FFFF
        assert n.bits_past_eof == 8 + 8
        
        assert b.pad_value == 0
        assert b.bits_past_eof == 8
    
    def test_write(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        
        # Write exactly the whole block
        n1 = bitstream.NBits(0x12, 8)
        b = bitstream.BoundedBlock(n1, 8, pad_value=0xAB)
        b.write(w)
        assert n1.offset == (0, 7)
        assert b.unused_bits == 0
        assert b.offset == (0, 7)
        
        # Write less than the whole block
        n2 = bitstream.NBits(0x3, 4)
        b = bitstream.BoundedBlock(n2, 8, pad_value=0xAB)
        b.write(w)
        assert n2.offset == (1, 7)
        assert b.unused_bits == 4
        assert b.offset == (1, 7)
        
        # Write more than the whole block
        n3 = bitstream.NBits(0x45FF, 16)
        b = bitstream.BoundedBlock(n3, 8, pad_value=0xAB)
        b.write(w)
        assert n3.offset == (2, 7)
        assert b.unused_bits == 0
        assert b.offset == (2, 7)
        
        assert f.getvalue() == b"\x12\x3B\x45"
    
    def test_write_zero_past_end_of_block_fails(self):
        w = bitstream.BitstreamWriter(BytesIO())
        
        n = bitstream.NBits(0, 16)
        b = bitstream.BoundedBlock(n, 8)
        
        with pytest.raises(ValueError):
            b.write(w)
