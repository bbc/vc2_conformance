import pytest

from io import BytesIO
from enum import Enum

from vc2_conformance import bitstream


class TestConcatenation(object):
    
    def test_validate(self):
        # Empty is OK
        c = bitstream.Concatenation()
        assert c.value == tuple()
        
        # OK
        u1 = bitstream.UInt()
        u2 = bitstream.UInt()
        u3 = bitstream.UInt()
        c = bitstream.Concatenation(u1, u2, u3)
        assert c.value == (u1, u2, u3)
        
        # OK
        c.value = (u3, u2,u1)
        assert c.value == (u3, u2,u1)
        
        # Not OK
        with pytest.raises(ValueError):
            bitstream.Concatenation(123)  # Not a BitstreamValue
        
        # Not OK
        with pytest.raises(ValueError):
            c.value = u1  # Not an iterable
        with pytest.raises(ValueError):
            c.value = 123  # Not an iterable/BitstreamValue
        with pytest.raises(ValueError):
            c.value = tuple([123])  # Not a BitstreamValue
        assert c.value == (u3, u2,u1)
    
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
    
    def test_str(self):
        u1 = bitstream.UInt(10)
        u2 = bitstream.UInt(20)
        
        assert str(bitstream.Concatenation(u1, u2)) == "10 20"


class TestLabelledConcatenation(object):
    
    def test_indexing(self):
        u1 = bitstream.UInt()
        u2 = bitstream.UInt()
        u3 = bitstream.UInt()
        l = bitstream.LabelledConcatenation("foo", None, "bar", ("u1", u1), None, u2, ("u3", u3))
        
        # Numerical indexing
        assert l[0] == u1
        assert l[1] == u2
        assert l[2] == u3
        assert l[:] == (u1, u2, u3)
        
        # Named indexing
        assert l["u1"] == u1
        assert l["u3"] == u3
        
        # Missing items
        with pytest.raises(IndexError):
            l[4]
        with pytest.raises(KeyError):
            l["u2"]
        with pytest.raises(KeyError):
            l["bar"]
    
    def test_bitstream_functions(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        r = bitstream.BitstreamReader(BytesIO())
        
        u1 = bitstream.UInt()
        u2 = bitstream.UInt()
        u3 = bitstream.UInt()
        l = bitstream.LabelledConcatenation("foo", None, "bar", ("u1", u1), None, u2, ("u3", u3))
        
        l.read(r)
        
        assert l.length == 3
        assert l.bits_past_eof == 3
        
        u1.value = 1
        u2.value = 2
        u3.value = 3
        
        l.write(w)
        
        # 1     2   3     <excess>
        # 0b001_011_00001_00000
        # 0x2____C____2____0___
        w.flush()
        assert f.getvalue() == b"\x2C\x20"
    
    def test_str_labels_and_indents(self):
        u1 = bitstream.UInt(10)
        u2 = bitstream.UInt(20)
        u3 = bitstream.UInt(30)
        u4 = bitstream.UInt(40)
        u5 = bitstream.UInt(50)
        u6 = bitstream.UInt(60)
        u7 = bitstream.UInt(70)
        u8 = bitstream.UInt(80)
        l = bitstream.LabelledConcatenation(
            "Title 1",
            ("U1", u1),
            u2,
            "Subheading 1",
            ("U3", u3),
            u4,
            None,
            None,
            None,
            None,
            "Title 2",
            ("U5", u5),
            u6,
            None,
            ("U7", u7),
            u8,
        )
        
        assert str(l) == (
            "Title 1\n"
            "  U1: 10\n"
            "  20\n"
            "  Subheading 1\n"
            "    U3: 30\n"
            "    40\n"
            "Title 2\n"
            "  U5: 50\n"
            "  60\n"
            "U7: 70\n"
            "80"
        )
    
    def test_str_hidden_entries(self):
        u = bitstream.UInt(10)
        m = bitstream.Maybe(u, True)
        l = bitstream.LabelledConcatenation("Title", ("maybe", m), m)
        
        assert str(l) == "Title\n  maybe: 10\n  10"
        
        # Omit entries entirely whose values print as empty strings
        m.flag = False
        assert str(l) == "Title"

    def test_str_multi_line_entries(self):
        u1 = bitstream.UInt(10)
        u2 = bitstream.UInt(20)
        u3 = bitstream.UInt(30)
        inner = bitstream.LabelledConcatenation("Inner", ("First", u2), ("Second", u3))
        l = bitstream.LabelledConcatenation("Title", ("First", u1), ("Second", inner))
        
        assert str(l) == (
            "Title\n"
            "  First: 10\n"
            "  Second:\n"
            "    Inner\n"
            "      First: 20\n"
            "      Second: 30"
        )

    def test_str_self_labelling(self):
        u1 = bitstream.UInt(10)
        u2 = bitstream.UInt(20)
        inner = bitstream.LabelledConcatenation("Inner:", ("First", u1), ("Second", u2))
        l = bitstream.LabelledConcatenation("Title", ("Inner", inner))
        
        assert str(l) == (
            "Title\n"
            "  Inner:\n"
            "    First: 10\n"
            "    Second: 20"
        )
