import pytest

from mock import Mock

from mock_notification_target import MockNotificationTarget

from io import BytesIO

from vc2_conformance import bitstream


class TestWrappedValue(object):
    
    def test_validation(self):
        bitstream.WrappedValue()._validate(bitstream.UInt())
        with pytest.raises(ValueError):
            bitstream.WrappedValue()._validate(123)
    
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
        
        # Errors should be thrown if the inner value is empty
        w = bitstream.WrappedValue()
        with pytest.raises(bitstream.EmptyValueError):
            w.value
        with pytest.raises(bitstream.EmptyValueError):
            w[0]


class TestBoundedBlock(object):
    
    def test_invalid_lengths(self):
        b = bitstream.BoundedBlock(bitstream.UInt(), 8)
        
        assert b.length == 8
        
        b.length_bitstream_value.value = -2
        assert b.length == 0
        
        b.length_bitstream_value.exception = Exception()
        assert b.length == 0

    
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
        assert str(b) == "0 <padding 0b0001111>"
        
        b = bitstream.BoundedBlock(s, length=8, pad_value=0x0F)
        assert str(b) == "1 <padding 0b1111>"
        
        # Value the right length should have no padding
        s.value = 7
        assert str(b) == "7"
        
        # Value longer than supported should have no padding either
        w = bitstream.BitstreamWriter(BytesIO())
        b = bitstream.BoundedBlock(u, length=8, pad_value=0x0F)
        u.value = 15
        b.write(w)
        assert str(b) == "15*"
    
    def test_notifications(self):
        u = bitstream.UInt(0)
        l = bitstream.UInt(0)
        b = bitstream.BoundedBlock(u, length=l, pad_value=0x0F)

        notify = MockNotificationTarget()
        b._notify_on_change(notify)
        
        b.pad_value = 0
        assert notify.notification_count == 1
        
        l.value = 3
        assert notify.notification_count == 2
        
        u.value = 1
        assert notify.notification_count == 3
        
        r = bitstream.BitstreamReader(BytesIO())
        b.read(r)
        assert notify.notification_count == 4


class TestMaybe(object):
    
    def test_length(self):
        m = bitstream.Maybe(bitstream.UInt, True)
        assert m.length == 1
        
        m.value = 3
        assert m.length == 5
        
        m.flag_bitstream_value.value = False
        assert m.length == 0
    
    def test_flag(self):
        r = bitstream.BitstreamReader(BytesIO())
        
        m = bitstream.Maybe(lambda: bitstream.Array(bitstream.UInt, 2), True)
        
        # Reading past the EOF should propagate the bits-past-EOF count
        m.read(r)
        assert m.bits_past_eof == 2
        
        # Length should be calculated based on the internal value and value
        # accessors should work
        assert m.length == 2
        m.value[0].value = 3
        assert m.length == 6
        m[1].value = 3
        assert m.length == 10
        
        # Clearing the flag should remove the value
        m.flag_bitstream_value.value = False
        assert m.bits_past_eof == 0
        assert m.length == 0
        with pytest.raises(bitstream.EmptyValueError):
            m.value
        with pytest.raises(bitstream.EmptyValueError):
            m[0]
        
        # Setting the flag again produces a new values
        m.flag_bitstream_value.value = True
        assert m.length == 2
        assert m.bits_past_eof is None
        
        # Setting the flag to an exception-raising should be treated as 'False'
        m.flag_bitstream_value.exception = Exception()
        assert m.flag is False
        assert m.length == 0
    
    def test_read(self):
        r = bitstream.BitstreamReader(BytesIO(b"\x00"))
        m = bitstream.Maybe(bitstream.UInt, False)
        
        m.flag_bitstream_value.value = False
        m.read(r)
        assert r.tell() == (0, 7)
        assert m.offset == (0, 7)
        assert m.inner_value is None  # Value not read
        
        m.flag_bitstream_value.value = True
        m.read(r)
        assert m.inner_value.value == 15
        assert m.value == 15
        assert r.tell() == (1, 7)
        assert m.offset == (0, 7)
        assert m.inner_value.offset == (0, 7)  # Value was read
    
    def test_write(self):
        f = BytesIO()
        w = bitstream.BitstreamWriter(f)
        
        m = bitstream.Maybe(lambda: bitstream.UInt(15), False)
        
        m.write(w)
        w.flush()
        assert f.getvalue() == b""
        assert w.tell() == (0, 7)
        assert m.offset == (0, 7)
        assert m.inner_value is None
        
        m.flag_bitstream_value.value = True
        m.write(w)
        w.flush()
        assert f.getvalue() == b"\x00\x80"
        assert w.tell() == (1, 6)
        assert m.offset == (0, 7)
        assert m.inner_value.offset == (0, 7)  # Value was written
    
    def test_str(self):
        assert str(bitstream.Maybe(lambda: bitstream.UInt(10), False)) == ""
        assert str(bitstream.Maybe(lambda: bitstream.UInt(10), True)) == "10"
    
    def test_notifications(self):
        flag = bitstream.ConstantValue(False)
        m = bitstream.Maybe(bitstream.UInt, flag)

        notify = MockNotificationTarget()
        m._notify_on_change(notify)
        
        # Changing flag notifies
        flag.value = True
        assert notify.notification_count == 1
        
        # Changing the value notifies
        m.value = 123
        assert notify.notification_count == 2
        
        # Setting the flag to the same value results in no change
        flag.value = True
        assert m.value == 123
        assert notify.notification_count == 2
        
        # Changing the flag again notifies a change
        flag.value = False
        assert notify.notification_count == 3
        
        # Setting the flag to the same value doesn't notify a change
        flag.value = False
        assert notify.notification_count == 3
    
    def test_discarded_value_notifications(self):
        # Check that when an inner value is discarded its 'changed' event
        # no longer produces notifications on the Maybe
        
        flag = bitstream.ConstantValue(True)
        m = bitstream.Maybe(bitstream.UInt, flag)
        
        notify = MockNotificationTarget()
        m._notify_on_change(notify)
        
        value = m.inner_value
        value._changed()
        assert notify.notification_count == 1
        
        flag.value = False
        assert notify.notification_count == 2
        
        value._changed()
        assert notify.notification_count == 2
