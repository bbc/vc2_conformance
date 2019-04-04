import pytest

from mock import Mock

from io import BytesIO
from enum import Enum

from vc2_conformance import bitstream

from mock_notification_target import MockNotificationTarget


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
        
        # Not OK
        with pytest.raises(ValueError):
            bitstream.Concatenation(123)  # Not a BitstreamValue
    
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
    
    def test_notify(self):
        n1 = bitstream.NBits(length=5)
        n2 = bitstream.NBits(length=5)
        
        c = bitstream.Concatenation(n1, n2)
        
        notify = MockNotificationTarget()
        c._notify_on_change(notify)
        
        assert notify.notification_count == 0
        
        n1.value = 1
        assert notify.notification_count == 1
        
        n2.value = 1
        assert notify.notification_count == 2
        
        # Reading the whole thing should result in just one notification
        r = bitstream.BitstreamReader(BytesIO())
        c.read(r)
        assert notify.notification_count == 3
    
    def test_str(self):
        u1 = bitstream.UInt(10)
        u2 = bitstream.UInt(20)
        
        assert str(bitstream.Concatenation(u1, u2)) == "(10, 20)"


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
        m = bitstream.Maybe(lambda: bitstream.UInt(10), True)
        l = bitstream.LabelledConcatenation("Title", ("maybe", m), m)
        
        assert str(l) == "Title\n  maybe: 10\n  10"
        
        # Omit entries entirely whose values print as empty strings
        m.flag_bitstream_value.value = False
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
    
    def test_notify(self):
        
        n1 = bitstream.NBits(length=5)
        n2 = bitstream.NBits(length=5)
        
        l = bitstream.LabelledConcatenation(("n1", n1), n2)
        
        notify = MockNotificationTarget()
        l._notify_on_change(notify)
        
        assert notify.notification_count == 0
        
        n1.value = 1
        assert notify.notification_count == 1
        
        n2.value = 1
        assert notify.notification_count == 2


class TestArray(object):
    
    def test_adjust_length(self):
        a = bitstream.Array(bitstream.UInt, 4)
        for i, v in enumerate(a.value):
            v.value = i
        
        # Changing the length should adjust the values stored
        a.num_values_bitstream_value.value = 4
        assert [v.value for v in a.value] == [0, 1, 2, 3]
        
        # Truncate
        a.num_values_bitstream_value.value = 3
        assert [v.value for v in a.value] == [0, 1, 2]
        
        # Extend
        a.num_values_bitstream_value.value = 5
        assert [v.value for v in a.value] == [0, 1, 2, 0, 0]
        
        # Setting to invalid value sets length to 0
        a.num_values_bitstream_value.value = "wut"
        assert a.num_values == 0
        assert a.value == tuple()
    
    def test_pass_index(self):
        a = bitstream.Array(bitstream.UInt, num_values=4, pass_index=False)
        assert [v.value for v in a.value] == [0, 0, 0, 0]
        
        a = bitstream.Array(bitstream.UInt, num_values=4, pass_index=True)
        assert [v.value for v in a.value] == [0, 1, 2, 3]
        
        a.pass_index = False
        a.num_values_bitstream_value.value = 8
        assert [v.value for v in a.value] == [0, 1, 2, 3, 0, 0, 0, 0]
        
        a.pass_index = True
        a.num_values_bitstream_value.value = 10
        assert [v.value for v in a.value] == [0, 1, 2, 3, 0, 0, 0, 0, 8, 9]
    
    def test_length(self):
        a = bitstream.Array(lambda: bitstream.NBits(length=8), num_values=4)
        
        assert a.length == 4 * 8
        
        a.num_values_bitstream_value.value = 0
        assert a.length == 0
        
        a.num_values_bitstream_value.value = 10
        assert a.length == 10 * 8
    
    def test_read_and_bits_past_eof(self):
        r = bitstream.BitstreamReader(BytesIO(b"\x00\x01\x02"))
        
        a = bitstream.Array(lambda: bitstream.NBits(length=8))
        
        a.num_values_bitstream_value.value = 4
        a.read(r)
        
        assert a[0].value == 0
        assert a[1].value == 1
        assert a[2].value == 2
        assert a[3].value == 0xFF
        
        assert a.bits_past_eof == 8
        
        a.num_values_bitstream_value.value = 3
        assert a.bits_past_eof == 0
    
    def test_write(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        
        a = bitstream.Array(lambda: bitstream.NBits(length=8), num_values=4)
        
        a[0].value = 1
        a[1].value = 2
        a[2].value = 3
        a[3].value = 4
        
        a.num_values_bitstream_value.value = 3
        a.write(w)
        
        assert f.getvalue() == b"\x01\x02\x03"
    
    def test_str(self):
        a = bitstream.Array(lambda: bitstream.NBits(length=8), num_values=4)
        
        a[0].value = 1
        a[1].value = 2
        a[2].value = 3
        a[3].value = 4
        
        assert str(a) == "1 2 3 4"
        
        a.num_values_bitstream_value.value = 5
        assert str(a) == "1 2 3 4 0"
    
    def test_discarded_value_notifications(self):
        # Check that when an inner value is discarded its 'changed' event
        # no longer produces notifications on the Maybe
        length = bitstream.ConstantValue(4)
        a = bitstream.Array(bitstream.UInt, length)
        
        notify = MockNotificationTarget()
        a._notify_on_change(notify)
        
        values = a.value
        for v in values:
            v._changed()
        assert notify.notification_count == 4
        
        # Discarded value notifications shouldn't come through (only those of
        # the retained values)
        length.value = 2
        assert notify.notification_count == 5
        
        for v in values:
            v._changed()
        assert notify.notification_count == 7


class TestRectangularArray(object):
    
    def test_num_values_et_al(self):
        s = bitstream.RectangularArray(bitstream.UInt)
        
        assert s.num_values == 0
        
        s.height_bitstream_value.value = 2
        assert s.num_values == 0
        
        s.width_bitstream_value.value = 3
        assert s.num_values == 6
        
        # Invalid values should be treated as zero
        s.height_bitstream_value.value = "wut"
        assert s.height == 0
        assert s.num_values == 0
        
        s.height_bitstream_value.value = 2
        assert s.num_values == 6
        
        s.width_bitstream_value.value = "wut"
        assert s.width == 0
        assert s.num_values == 0
    
    def test_length(self):
        s = bitstream.RectangularArray(lambda: bitstream.NBits(length=8))
        
        assert s.length == 0
        s.height_bitstream_value.value = 2
        s.width_bitstream_value.value = 3
        assert s.length == 8 * (2 * 3)
    
    def test_read(self):
        r = bitstream.BitstreamReader(BytesIO(b"\x01\x02\x03\x04\x05"))
        
        s = bitstream.RectangularArray(lambda: bitstream.NBits(length=8), 3, 2)
        s.read(r)
        
        assert [v.value for v in s.value] == [1, 2, 3, 4, 5, 0xFF]
        assert s.bits_past_eof == 8
    
    def test_write(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        
        s = bitstream.RectangularArray(lambda n: bitstream.NBits(n, 8), 3, 2, True)
        s.write(w)
        
        assert f.getvalue() == b"\x00\x01\x02\x03\x04\x05"
        assert s.bits_past_eof == 0
    
    def test_indexing(self):
        s = bitstream.RectangularArray(bitstream.UInt, 2, 3)
        
        assert s[0] is s[0, 0]
        assert s[1] is s[0, 1]
        assert s[2] is s[0, 2]
        assert s[3] is s[1, 0]
        assert s[4] is s[1, 1]
        assert s[5] is s[1, 2]
        
        with pytest.raises(IndexError):
            s[-1, 0]
        with pytest.raises(IndexError):
            s[0, -1]
        with pytest.raises(IndexError):
            s[2, 0]
        with pytest.raises(IndexError):
            s[0, 3]
    
    def test_str(self):
        s = bitstream.RectangularArray(lambda n: bitstream.NBits(n, 8), 3, 4, True)
        
        assert str(s) == (
            "0  1   2   3\n"
            "4  5   6   7\n"
            "8  9  10  11"
        )
    
    def test_str_multiline(self):
        s = bitstream.RectangularArray(
            lambda: bitstream.LabelledConcatenation("foo", None, "bar"),
            2, 3
        )
        
        assert str(s) == (
            "(y=0, x=0):\n"
            "  foo\n"
            "  bar\n"
            "(y=0, x=1):\n"
            "  foo\n"
            "  bar\n"
            "(y=0, x=2):\n"
            "  foo\n"
            "  bar\n"
            "(y=1, x=0):\n"
            "  foo\n"
            "  bar\n"
            "(y=1, x=1):\n"
            "  foo\n"
            "  bar\n"
            "(y=1, x=2):\n"
            "  foo\n"
            "  bar"
        )


class TestSubbandArray(object):
    
    def test_num_values_et_al(self):
        s = bitstream.SubbandArray(bitstream.UInt)
        
        assert s.num_values == 1
        
        s.dwt_depth_ho_bitstream_value.value = 2
        assert s.num_values == 3
        
        s.dwt_depth_bitstream_value.value = 2
        assert s.num_values == 9
        
        # Invalid values should be treated as zeros
        s.dwt_depth_bitstream_value.value = "wut"
        assert s.dwt_depth == 0
        assert s.num_values == 3
        
        s.dwt_depth_ho_bitstream_value.value = "lol"
        assert s.dwt_depth_ho == 0
        assert s.num_values == 1
    
    def test_length(self):
        s = bitstream.SubbandArray(lambda: bitstream.NBits(length=8))
        
        assert s.length == 8
        s.dwt_depth_ho_bitstream_value.value = 2
        s.dwt_depth_bitstream_value.value = 3
        assert s.length == 8 * (1 + 2 + (3*3))
    
    def test_read(self):
        r = bitstream.BitstreamReader(BytesIO(b"\x01\x02\x03\x04"))
        
        s = bitstream.SubbandArray(lambda: bitstream.NBits(length=8), 1, 1)
        s.read(r)
        
        assert [v.value for v in s.value] == [1, 2, 3, 4, 0xFF]
        assert s.bits_past_eof == 8
    
    def test_write(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        
        s = bitstream.SubbandArray(lambda n: bitstream.NBits(n, 8), 1, 1, True)
        s.write(w)
        
        assert f.getvalue() == b"\x00\x01\x02\x03\x04"
        assert s.bits_past_eof == 0
    
    def test_indexing_dc_only(self):
        s = bitstream.SubbandArray(bitstream.UInt)
        
        assert s[0] is s[0, "DC"]
        
        with pytest.raises(KeyError):
            s[0, "L"]
        
        with pytest.raises(KeyError):
            s[0, "LL"]
        
        with pytest.raises(KeyError):
            s[1, "DC"]
    
    def test_indexing_ho(self):
        s = bitstream.SubbandArray(bitstream.UInt, dwt_depth=3,dwt_depth_ho=2)
        
        assert s[0] is s[0, "L"]
        with pytest.raises(KeyError):
            s[0, "DC"]
        with pytest.raises(KeyError):
            s[0, "LL"]
        
        assert s[1] is s[1, "H"]
        with pytest.raises(KeyError):
            s[1, "HL"]
        with pytest.raises(KeyError):
            s[1, "LH"]
        with pytest.raises(KeyError):
            s[1, "HH"]
        
        assert s[2] is s[2, "H"]
        with pytest.raises(KeyError):
            s[2, "HL"]
        with pytest.raises(KeyError):
            s[2, "LH"]
        with pytest.raises(KeyError):
            s[2, "HH"]
        
        assert s[3] is s[3, "HL"]
        assert s[4] is s[3, "LH"]
        assert s[5] is s[3, "HH"]
        with pytest.raises(KeyError):
            s[3, "H"]
        with pytest.raises(KeyError):
            s[4, "H"]
        with pytest.raises(KeyError):
            s[5, "H"]
        
        assert s[6] is s[4, "HL"]
        assert s[7] is s[4, "LH"]
        assert s[8] is s[4, "HH"]
        
        assert s[9] is s[5, "HL"]
        assert s[10] is s[5, "LH"]
        assert s[11] is s[5, "HH"]
        
        with pytest.raises(KeyError):
            s[6, "HL"]
        with pytest.raises(KeyError):
            s[6, "LH"]
        with pytest.raises(KeyError):
            s[6, "HH"]
    
    def test_indexing_2d(self):
        s = bitstream.SubbandArray(bitstream.UInt, dwt_depth=3,dwt_depth_ho=0)
        
        assert s[0] is s[0, "LL"]
        with pytest.raises(KeyError):
            s[0, "DC"]
        with pytest.raises(KeyError):
            s[0, "L"]
        
        assert s[1] is s[1, "HL"]
        assert s[2] is s[1, "LH"]
        assert s[3] is s[1, "HH"]
        with pytest.raises(KeyError):
            s[1, "H"]
        with pytest.raises(KeyError):
            s[2, "H"]
        with pytest.raises(KeyError):
            s[3, "H"]
        
        assert s[4] is s[2, "HL"]
        assert s[5] is s[2, "LH"]
        assert s[6] is s[2, "HH"]
        
        assert s[7] is s[3, "HL"]
        assert s[8] is s[3, "LH"]
        assert s[9] is s[3, "HH"]
        
        with pytest.raises(KeyError):
            s[4, "HL"]
        with pytest.raises(KeyError):
            s[4, "LH"]
        with pytest.raises(KeyError):
            s[4, "HH"]
    
    def test_str(self):
        s = bitstream.SubbandArray(bitstream.UInt, dwt_depth=3,dwt_depth_ho=2)
        for i in range(s.num_values):
            s[i].value = i + 1
        
        assert str(s) == (
            "Level 0: L: 1\n"
            "Level 1: H: 2\n"
            "Level 2: H: 3\n"
            "Level 3: HL: 4, LH: 5, HH: 6\n"
            "Level 4: HL: 7, LH: 8, HH: 9\n"
            "Level 5: HL: 10, LH: 11, HH: 12"
        )
        
        s.dwt_depth_ho_bitstream_value.value = 0
        assert str(s) == (
            "Level 0: LL: 1\n"
            "Level 1: HL: 2, LH: 3, HH: 4\n"
            "Level 2: HL: 5, LH: 6, HH: 7\n"
            "Level 3: HL: 8, LH: 9, HH: 10"
        )
        
        s.dwt_depth_bitstream_value.value = 0
        assert str(s) == "Level 0: DC: 1"
    
    def test_str_multiline(self):
        s = bitstream.SubbandArray(
            lambda: bitstream.LabelledConcatenation("foo", None, "bar"),
            dwt_depth=1,
            dwt_depth_ho=1,
        )
        
        assert str(s) == (
            "Level 0:\n"
            "  L:\n"
            "    foo\n"
            "    bar\n"
            "Level 1:\n"
            "  H:\n"
            "    foo\n"
            "    bar\n"
            "Level 2:\n"
            "  HL:\n"
            "    foo\n"
            "    bar\n"
            "  LH:\n"
            "    foo\n"
            "    bar\n"
            "  HH:\n"
            "    foo\n"
            "    bar"
        )
    
    def test_index_to_subband(self):
        # DC only
        assert bitstream.SubbandArray.index_to_subband(0, 0, 0) == (0, "DC")
        with pytest.raises(ValueError):
            bitstream.SubbandArray.index_to_subband(1, 0, 0)
        
        # 2D only
        assert bitstream.SubbandArray.index_to_subband(0, 2, 0) == (0, "LL")
        assert bitstream.SubbandArray.index_to_subband(1, 2, 0) == (1, "HL")
        assert bitstream.SubbandArray.index_to_subband(2, 2, 0) == (1, "LH")
        assert bitstream.SubbandArray.index_to_subband(3, 2, 0) == (1, "HH")
        assert bitstream.SubbandArray.index_to_subband(4, 2, 0) == (2, "HL")
        assert bitstream.SubbandArray.index_to_subband(5, 2, 0) == (2, "LH")
        assert bitstream.SubbandArray.index_to_subband(6, 2, 0) == (2, "HH")
        with pytest.raises(ValueError):
            bitstream.SubbandArray.index_to_subband(7, 2, 0)
        
        # Horizontal and 2D
        assert bitstream.SubbandArray.index_to_subband(0, 2, 3) == (0, "L")
        assert bitstream.SubbandArray.index_to_subband(1, 2, 3) == (1, "H")
        assert bitstream.SubbandArray.index_to_subband(2, 2, 3) == (2, "H")
        assert bitstream.SubbandArray.index_to_subband(3, 2, 3) == (3, "H")
        assert bitstream.SubbandArray.index_to_subband(4, 2, 3) == (4, "HL")
        assert bitstream.SubbandArray.index_to_subband(5, 2, 3) == (4, "LH")
        assert bitstream.SubbandArray.index_to_subband(6, 2, 3) == (4, "HH")
        assert bitstream.SubbandArray.index_to_subband(7, 2, 3) == (5, "HL")
        assert bitstream.SubbandArray.index_to_subband(8, 2, 3) == (5, "LH")
        assert bitstream.SubbandArray.index_to_subband(9, 2, 3) == (5, "HH")
        with pytest.raises(ValueError):
            bitstream.SubbandArray.index_to_subband(10, 2, 0)
    
    def test_subband_to_index(self):
        # DC only
        assert bitstream.SubbandArray.index_to_subband(0, 0, 0) == (0, "DC")
        with pytest.raises(ValueError):
            bitstream.SubbandArray.index_to_subband(1, 0, 0)
        
        # 2D only
        assert bitstream.SubbandArray.index_to_subband(0, 2, 0) == (0, "LL")
        assert bitstream.SubbandArray.index_to_subband(1, 2, 0) == (1, "HL")
        assert bitstream.SubbandArray.index_to_subband(2, 2, 0) == (1, "LH")
        assert bitstream.SubbandArray.index_to_subband(3, 2, 0) == (1, "HH")
        assert bitstream.SubbandArray.index_to_subband(4, 2, 0) == (2, "HL")
        assert bitstream.SubbandArray.index_to_subband(5, 2, 0) == (2, "LH")
        assert bitstream.SubbandArray.index_to_subband(6, 2, 0) == (2, "HH")
        with pytest.raises(ValueError):
            bitstream.SubbandArray.index_to_subband(7, 2, 0)
        
        # Horizontal and 2D
        assert bitstream.SubbandArray.index_to_subband(0, 2, 3) == (0, "L")
        assert bitstream.SubbandArray.index_to_subband(1, 2, 3) == (1, "H")
        assert bitstream.SubbandArray.index_to_subband(2, 2, 3) == (2, "H")
        assert bitstream.SubbandArray.index_to_subband(3, 2, 3) == (3, "H")
        assert bitstream.SubbandArray.index_to_subband(4, 2, 3) == (4, "HL")
        assert bitstream.SubbandArray.index_to_subband(5, 2, 3) == (4, "LH")
        assert bitstream.SubbandArray.index_to_subband(6, 2, 3) == (4, "HH")
        assert bitstream.SubbandArray.index_to_subband(7, 2, 3) == (5, "HL")
        assert bitstream.SubbandArray.index_to_subband(8, 2, 3) == (5, "LH")
        assert bitstream.SubbandArray.index_to_subband(9, 2, 3) == (5, "HH")
        with pytest.raises(ValueError):
            bitstream.SubbandArray.index_to_subband(10, 2, 0)
