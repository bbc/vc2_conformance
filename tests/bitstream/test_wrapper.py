import pytest

from io import BytesIO

from vc2_conformance import bitstream


class TestWrappedValue(object):
    
    def test_validation(self):
        # Should prevent construction with wrong type
        with pytest.raises(ValueError):
            bitstream.WrappedValue(123)
        
        # Should prevent changing to wrong type
        u = bitstream.UInt()
        w = bitstream.WrappedValue(u)
        with pytest.raises(ValueError):
            w.inner_value = 123
        assert w.inner_value is u
        
    
    def test_value_passthrough(self):
        u1 = bitstream.UInt()
        u2 = bitstream.UInt()
        c = bitstream.Concatenation(u1, u2)
        
        # The 'value' property should forward to the inner_value's value
        w = bitstream.WrappedValue(u1)
        w.value == 0
        w = bitstream.WrappedValue(c)
        w.value == (u1, u2)
        
        # The indexing operator should also be forwarded
        w = bitstream.WrappedValue(c)
        assert w[0] is u1
        assert w[1] is u2


class TestBoundedBlock(object):
    
    @pytest.mark.parametrize("length,expected", [
        # As literals
        (0, 0),
        (32, 32),
        # As functions
        (lambda: 0, 0),
        (lambda: 32, 32),
    ])
    def test_length(self, length, expected):
        u = bitstream.UInt()
        
        # Test constructor
        b = bitstream.BoundedBlock(u, length)
        assert b.length == expected
        
        # Test property
        b = bitstream.BoundedBlock(u, 0)
        b.length = length
        assert b.length == expected
    
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
    
    def test_write_past_end(self):
        # If the block extends past the end of the file, both the block and its
        # contents should have bits_past_eof set accordingly, in addition to
        # any bits beyond the end of the block.
        w = bitstream.BitstreamWriter(BytesIO())
        
        # NB: To simulate a file which hits an EOF while writing we use another
        # nested BoundedBlock. This is not a construct likely to appear in VC-2
        # any time soon.
        n = bitstream.NBits(0x12FFFF, length=24)
        b = bitstream.BoundedBlock(n, 16, pad_value=-1)
        bb = bitstream.BoundedBlock(b, length=8)
        bb.write(w)
        
        assert n.bits_past_eof == 8 + 8
        assert b.bits_past_eof == 8
        assert bb.bits_past_eof == 0
    
    def test_write_zero_past_end_of_block_fails(self):
        w = bitstream.BitstreamWriter(BytesIO())
        
        n = bitstream.NBits(0, 16)
        b = bitstream.BoundedBlock(n, 8)
        
        with pytest.raises(ValueError):
            b.write(w)
    
    def test_str(self):
        u = bitstream.UInt(0)
        s = bitstream.SInt(1)
        b = bitstream.BoundedBlock(u, length=8, pad_value=0x0F)
        
        b.inner_value = u
        assert str(b) == "0 <padding 0b0001111>"
        b.inner_value = s
        assert str(b) == "1 <padding 0b1111>"
        
        # Value the right length should have no padding
        s.value = 7
        b.inner_value = s
        assert str(b) == "7"
        
        # Value longer than supported should have no padding either
        w = bitstream.BitstreamWriter(BytesIO())
        u.value = 15
        b.inner_value = u
        b.write(w)
        assert str(b) == "15*"


class TestMaybe(object):
    
    @pytest.mark.parametrize("flag_value,expected", [
        # Should take values or functions
        (True, True),
        (False, False),
        (lambda: True, True),
        (lambda: False, False),
        # Should cast non-bool values
        (1234, True),
        (None, False),
        (lambda: 1234, True),
        (lambda: None, False),
    ])
    def test_flag(self, flag_value, expected):
        value = bitstream.UInt()
        
        # Try via constructor
        m = bitstream.Maybe(value, flag_value)
        assert bool(m.flag) is expected
        
        # Try via property
        m = bitstream.Maybe(value, not expected)
        m.flag = flag_value
        assert bool(m.flag) is expected
    
    def test_length(self):
        value = bitstream.UInt()
        
        m = bitstream.Maybe(value, True)
        
        value.value = 3
        
        assert m.length == 5
        
        m.flag = False
        assert m.length == 0
    
    def test_bits_past_eof(self):
        r = bitstream.BitstreamReader(BytesIO())
        
        value = bitstream.UInt()
        
        m = bitstream.Maybe(value, False)
        
        value.read(r)
        
        m.flag = True
        assert m.bits_past_eof == 1
        
        m.flag = False
        assert m.bits_past_eof == 0
    
    def test_read(self):
        r = bitstream.BitstreamReader(BytesIO(b"\x00"))
        
        value = bitstream.UInt()
        
        m = bitstream.Maybe(value, False)
        
        m.flag = False
        m.read(r)
        assert r.tell() == (0, 7)
        assert m.offset == (0, 7)
        assert value.offset is None  # Value not read
        
        m.flag = True
        m.read(r)
        assert value.value == 15
        assert r.tell() == (1, 7)
        assert m.offset == (0, 7)
        assert value.offset == (0, 7)  # Value was read
    
    def test_write(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        
        value = bitstream.UInt(15)
        
        m = bitstream.Maybe(value, False)
        
        m.flag = False
        m.write(w)
        w.flush()
        assert f.getvalue() == b""
        assert w.tell() == (0, 7)
        assert m.offset == (0, 7)
        assert value.offset is None  # Value not written
        
        m.flag = True
        m.write(w)
        w.flush()
        assert f.getvalue() == b"\x00\x80"
        assert w.tell() == (1, 6)
        assert m.offset == (0, 7)
        assert value.offset == (0, 7)  # Value was written
    
    def test_str(self):
        u = bitstream.UInt(10)
        assert str(bitstream.Maybe(u, False)) == ""
        assert str(bitstream.Maybe(u, True)) == "10"
