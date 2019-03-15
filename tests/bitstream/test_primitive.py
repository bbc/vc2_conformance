import pytest

from io import BytesIO
from enum import Enum

from vc2_conformance import bitstream
from vc2_conformance.bitstream.formatters import Hex


class TestPrimitiveValueBaseclass(object):
    
    def test_value(self):
        p = bitstream.PrimitiveValue(123, 32)
        
        # Argument value should pass through
        assert p.value == 123
        
        # Should be able to override
        p.value = 100
        assert p.value == 100
        p.value = -100
        assert p.value == -100
        
        # Casting should work (sample functions store all positive numbers as
        # 10x their input value....)
        def cast_to_primitive(v):
            if v >= 0:
                return v * 10
            else:
                raise ValueError()
        
        def cast_from_primitive(v):
            if v >= 0:
                return v // 10
            else:
                raise ValueError()
        
        p = bitstream.PrimitiveValue(
            123, 32,
            cast_to_primitive=cast_to_primitive,
            cast_from_primitive=cast_from_primitive)
        
        # The initial value should have been converted
        assert p._value == 1230
        
        # The exposed value should be un-converted, however
        assert p.value == 123
        
        # Writing a +ve number directly should also be rescaled
        p.value = 321
        assert p._value == 3210
        assert p.value == 321
        
        # Writing a -ve number (which is not modified) should work as expected
        # with the value not beeing modified internally
        p.value = -321
        assert p._value == -321
        assert p.value == -321
    
    def test_length(self):
        p = bitstream.PrimitiveValue(0, 32)
        
        # Value is set from constructor
        assert p.length == 32
        
        # Can be changed
        p.length = 0
        assert p.length == 0
        
        # Validation should prevent invalid lengths
        with pytest.raises(ValueError):
            p.length = -1
        assert p.length == 0
        
        # And in the constructor too
        with pytest.raises(ValueError):
            bitstream.PrimitiveValue(0, -1)
    
    def test_str(self):
        p = bitstream.PrimitiveValue(0, 32)
        
        assert str(p) == "0"
        
        # Default formatting...
        p.value = 123
        assert str(p) == "123"
        
        # Past EOF should be marked
        p._bits_past_eof = 1
        assert str(p) == "123*"
        
        # Override primitive formatting
        p = bitstream.PrimitiveValue(0x1234, 32, formatter=Hex(8))
        assert str(p) == "0x00001234"
        
        # Past EOF should be marked
        p._bits_past_eof = 1
        assert str(p) == "0x00001234*"
        
        # Add name
        def get_value_name(v):
            if v == 0:
                return "zero"
            else:
                raise ValueError()
        
        p = bitstream.PrimitiveValue(0, 32,
                                     formatter=Hex(8),
                                     get_value_name=get_value_name)
        p.value = 0
        assert str(p) == "zero (0x00000000)"
        
        # Past EOF should be marked
        p._bits_past_eof = 1
        assert str(p) == "zero (0x00000000*)"
        p._bits_past_eof = None
        
        # Unnamed values should also work
        p.value = 0x1234
        assert str(p) == "0x00001234"
        
        p._bits_past_eof = 1
        assert str(p) == "0x00001234*"
    
    def test_enum(self):
        class ABC(Enum):
            a = 1
            b = 2
            c = 3
        
        # Check can pass enum values as arguments
        p = bitstream.PrimitiveValue(ABC.a, 32, enum=ABC)
        assert p.value is ABC.a
        assert p._value == 1
        
        # ...and non-enum arguments with enum equivalents
        p = bitstream.PrimitiveValue(1, 32, enum=ABC)
        assert p.value is ABC.a
        assert p._value == 1
        
        # ...and values not in the enum
        p = bitstream.PrimitiveValue(0, 32, enum=ABC)
        assert p.value == 0
        assert p._value == 0
        
        # Pass in enum type
        p.value = ABC.b
        assert p.value is ABC.b
        assert p._value == 2
        
        # Pass in integer with enum equivalent
        p.value = 3
        assert p.value is ABC.c
        assert p._value == 3
        
        # Pass in out-of-range value
        p.value = 4
        assert p.value == 4
        assert p._value == 4
        
        # String of enum value
        p.value = 1
        assert str(p) == "a (1)"
        
        # String of non-enum value
        p.value = 0
        assert str(p) == "0"


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
            assert b.bits_past_eof == 0
        
        assert f.getvalue() == b"\xAA"
    
    def test_write_past_eof(self):
        w = bitstream.BitstreamWriter(BytesIO(b""))
        bb = bitstream.BoundedBlock(bitstream.Bool(True), length=0)
        bb.write(w)
        
        assert bb.value.offset == (0, 7)
        assert bb.value.bits_past_eof == 1


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
        assert n.bits_past_eof == 0
        
        n.value = 0x5
        n.write(w)
        assert n.offset == (0, 3)
        assert n.bits_past_eof == 0
        
        assert f.getvalue() == b"\xA5"
    
    def test_write_past_eof(self):
        w = bitstream.BitstreamWriter(BytesIO(b""))
        
        bb = bitstream.BoundedBlock(bitstream.NBits(0xFF, length=8), length=0)
        bb.write(w)
        assert bb.value.offset == (0, 7)
        assert bb.value.bits_past_eof == 8
        
        bb = bitstream.BoundedBlock(bitstream.NBits(0xFF, length=8), length=4)
        bb.write(w)
        assert bb.value.offset == (0, 7)
        assert bb.value.bits_past_eof == 4


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
        assert b.bits_past_eof == 0

        w.flush()
        assert f.getvalue() == b""
        
        w.write_bit(0)
        
        b.write(w)
        assert b.offset == (0, 6)
        assert b.length == 7
        assert b.value == 0xFA
        assert b.bits_past_eof == 0
        
        assert f.getvalue() == b"\x7A"
    
    def test_write_past_eof(self):
        w = bitstream.BitstreamWriter(BytesIO(b""))
        w.seek(0, 6)
        
        bb = bitstream.BoundedBlock(bitstream.ByteAlign(0xFF), length=4)
        bb.write(w)
        assert bb.value.offset == (0, 6)
        assert bb.value.bits_past_eof == 3
    
    def test_str(self):
        r = bitstream.BitstreamReader(BytesIO(b"\x0F"))
        
        # By default should be 'invisible'
        b = bitstream.ByteAlign()
        b.read(r)
        assert str(b) == ""
        
        # Should become visible when needed
        r.seek(0, 6)
        b.read(r)
        assert str(b) == "<padding 0b0001111>"
        
        # Should change length as required
        r.seek(0, 4)
        b.read(r)
        assert str(b) == "<padding 0b01111>"


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
        assert u.bits_past_eof == 0
        assert f.getvalue() == b"\x80"
        
        u.value = 1
        u.write(w)
        w.flush()
        assert u.offset == (0, 6)
        assert u.bits_past_eof == 0
        assert f.getvalue() == b"\x90"
    
    def test_write_past_eof(self):
        w = bitstream.BitstreamWriter(BytesIO(b""))
        w.seek(0, 6)
        
        # The even-bit falls off the end
        bb = bitstream.BoundedBlock(bitstream.UInt(15), length=8)
        bb.write(w)
        assert bb.value.bits_past_eof == 1
        
        # The whole string falls off the end
        bb = bitstream.BoundedBlock(bitstream.UInt(0), length=0)
        bb.write(w)
        assert bb.value.bits_past_eof == 1
        
        # The odd-bit falls falls off the end
        bb = bitstream.BoundedBlock(bitstream.UInt(16), length=7)
        bb.write(w)
        assert bb.value.bits_past_eof == 2
    
    
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
        assert s.bits_past_eof == 0
        assert f.getvalue() == b"\x80"
        
        s.value = 1
        s.write(w)
        w.flush()
        assert s.offset == (0, 6)
        assert s.bits_past_eof == 0
        assert f.getvalue() == b"\x90"
        
        s.value = -1
        s.write(w)
        w.flush()
        assert s.offset == (0, 2)
        assert s.bits_past_eof == 0
        assert f.getvalue() == b"\x91\x80"
    
    def test_write_past_eof(self):
        w = bitstream.BitstreamWriter(BytesIO(b""))
        w.seek(0, 6)
        
        # The whole string falls off the end
        bb = bitstream.BoundedBlock(bitstream.SInt(0), length=0)
        bb.write(w)
        assert bb.value.bits_past_eof == 1
        
        # The even-bit and sign fall off the end
        bb = bitstream.BoundedBlock(bitstream.SInt(-15), length=8)
        bb.write(w)
        assert bb.value.bits_past_eof == 2
        
        # The odd-bit and sign fall off the end
        bb = bitstream.BoundedBlock(bitstream.SInt(-16), length=7)
        bb.write(w)
        assert bb.value.bits_past_eof == 3
        
        # The sign falls off the end
        bb = bitstream.BoundedBlock(bitstream.SInt(-7), length=7)
        bb.write(w)
        assert bb.value.bits_past_eof == 1
    
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
