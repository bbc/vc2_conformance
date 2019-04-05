import pytest

from io import BytesIO

from vc2_conformance.bitstream import (
    BitstreamReader,
    BitstreamWriter,
    BoundedWriter,
)

from vc2_conformance.bitstream._integer_io import (
    read_bits,
    write_bits,
    read_bytes,
    write_bytes,
    exp_golomb_length,
    read_exp_golomb,
    write_signed_exp_golomb,
    signed_exp_golomb_length,
    read_signed_exp_golomb,
    write_exp_golomb,
)


class TestReadBits(object):
    
    def test_read_nothing(self):
        r = BitstreamReader(BytesIO())
        assert read_bits(r, 0) == 0
        assert r.tell() == (0, 7)
    
    def test_read_bytes_msb_first(self):
        r = BitstreamReader(BytesIO(b"\xA0\x50"))
        assert read_bits(r, 12) == 0xA05
        assert r.tell() == (1, 3)
    
    def test_read_past_eof(self):
        r = BitstreamReader(BytesIO(b"\xA0"))
        assert read_bits(r, 12) == 0xA0F
        assert r.tell() == (1, 7)


class TestWriteBits(object):
    
    @pytest.fixture
    def f(self):
        return BytesIO()
    
    @pytest.fixture
    def w(self, f):
        return BitstreamWriter(f)
    
    def test_write_nothing(self, w):
        write_bits(w, 0, 0x123)
        assert w.tell() == (0, 7)
    
    def test_write_only_lowest_order_bits(self, f, w):
        write_bits(w, 12, 0xABCD)
        assert w.tell() == (1, 3)
        w.flush()
        assert f.getvalue() == b"\xBC\xD0"
    
    def test_write_zeros_above_msb(self, f, w):
        write_bits(w, 16, 0xABC)
        assert w.tell() == (2, 7)
        w.flush()
        assert f.getvalue() == b"\x0A\xBC"
    
    def test_write_past_eof(self, f, w):
        bw = BoundedWriter(w, 8)
        write_bits(bw, 12, 0xABF)
        assert w.tell() == (1, 7)
        w.flush()
        assert f.getvalue() == b"\xAB"

class TestReadBytes(object):
    
    def test_read_nothing(self):
        r = BitstreamReader(BytesIO())
        assert read_bytes(r, 0) == b""
        assert r.tell() == (0, 7)
    
    def test_read_bytes_msb_first(self):
        r = BitstreamReader(BytesIO(b"\xDE\xAD\xBE\xEF"))
        assert read_bytes(r, 2) == b"\xDE\xAD"
        assert r.tell() == (2, 7)
    
    def test_unaligned(self):
        r = BitstreamReader(BytesIO(b"\xDE\xAD\xBE\xEF"))
        r.seek(0, 3)
        assert read_bytes(r, 2) == b"\xEA\xDB"
        assert r.tell() == (2, 3)
    
    def test_read_past_eof(self):
        r = BitstreamReader(BytesIO(b"\xDE"))
        assert read_bytes(r, 2) == b"\xDE\xFF"
        assert r.tell() == (1, 7)


class TestWriteBytes(object):
    
    @pytest.fixture
    def f(self):
        return BytesIO()
    
    @pytest.fixture
    def w(self, f):
        return BitstreamWriter(f)
    
    def test_write_nothing(self, w):
        write_bytes(w, 0, b"foo")
        assert w.tell() == (0, 7)
    
    def test_write_truncate(self, f, w):
        # Takes the right-most bytes
        write_bytes(w, 1, b"\xAB\xCD")
        assert w.tell() == (1, 7)
        assert f.getvalue() == b"\xCD"
    
    def test_write_extend(self, f, w):
        # Left-pads with null bytes
        write_bytes(w, 2, b"\xAB")
        assert w.tell() == (2, 7)
        assert f.getvalue() == b"\x00\xAB"
    
    def test_write_aligned(self, f, w):
        write_bytes(w, 2, b"\xAB\xCD")
        assert w.tell() == (2, 7)
        assert f.getvalue() == b"\xAB\xCD"
    
    def test_write_unaligned(self, f, w):
        w.seek(0, 3)
        write_bytes(w, 2, b"\xAB\xCD")
        assert w.tell() == (2, 3)
        w.flush()
        assert f.getvalue() == b"\x0A\xBC\xD0"
    
    def test_write_past_eof(self, f, w):
        bw = BoundedWriter(w, 8)
        write_bytes(bw, 2, b"\xAB\xFF")
        assert w.tell() == (1, 7)
        w.flush()
        assert f.getvalue() == b"\xAB"


@pytest.mark.parametrize("value,length", [
    # Low numbers
    (0, 1),
    (1, 3),
    (2, 3),
    (3, 5),
    (4, 5),
    (5, 5),
    (6, 5),
    (7, 7),
    (8, 7),
    # Very large numbers
    ((1<<100) - 2, (99*2) + 1),
    ((1<<100) - 1, (100*2) + 1),
])
def test_exp_golomb_length(value, length):
    assert exp_golomb_length(value) == length


class TestReadExpGolomb(object):
    
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
        r = BitstreamReader(BytesIO(encoded))
        assert read_exp_golomb(r) == exp_value
        assert r.tell() == exp_tell
    
    
    def test_read_past_eof(self):
        # Odd bit falls off end
        r = BitstreamReader(BytesIO(b"\x00"))
        r.seek(0, 7)
        assert read_exp_golomb(r) == 15
        
        # Even bit falls off end
        r = BitstreamReader(BytesIO(b"\x00"))
        r.seek(0, 6)
        assert read_exp_golomb(r) == 16
        
        # Whole string falls off end
        r = BitstreamReader(BytesIO(b"\x00"))
        r.seek(1, 7)
        assert read_exp_golomb(r) == 0


class TestWriteExpGolomb(object):
    
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
        w = BitstreamWriter(f)
        write_exp_golomb(w, value)
        assert w.tell() == exp_tell
        w.flush()
        assert f.getvalue() == encoded
    
    
    def test_write_past_eof(self):
        f = BytesIO()
        w = BitstreamWriter(f)
        
        # Odd bit falls off end
        bw = BoundedWriter(w, 8)
        write_exp_golomb(bw, 15)
        
        # Even bit falls off end
        bw = BoundedWriter(w, 7)
        write_exp_golomb(bw, 16)
        
        # Whole string falls off end
        bw = BoundedWriter(w, 0)
        write_exp_golomb(bw, 0)


@pytest.mark.parametrize("value,length", [
    # Zero
    (0, 1),
    # Low numbers (+ve)
    (1, 4),
    (2, 4),
    (3, 6),
    (4, 6),
    (5, 6),
    (6, 6),
    (7, 8),
    (8, 8),
    # Low numbers (-ve)
    (-1, 4),
    (-2, 4),
    (-3, 6),
    (-4, 6),
    (-5, 6),
    (-6, 6),
    (-7, 8),
    (-8, 8),
    # Very large numbers
    ((1<<100) - 2, (99*2) + 2),
    ((1<<100) - 1, (100*2) + 2),
    (-((1<<100) - 2), (99*2) + 2),
    (-((1<<100) - 1), (100*2) + 2),
])
def test_signed_exp_golomb_length(value, length):
    assert signed_exp_golomb_length(value) == length


class TestReadSignedExpGolomb(object):
    
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
        r = BitstreamReader(BytesIO(encoded))
        assert read_signed_exp_golomb(r) == exp_value
        assert r.tell() == exp_tell
    
    
    def test_read_past_eof(self):
        # Sign bit falls off end
        r = BitstreamReader(BytesIO(b"\x01"))
        r.seek(0, 6)
        assert read_signed_exp_golomb(r) == -7
        
        # Odd bit falls off end
        r = BitstreamReader(BytesIO(b"\x00"))
        r.seek(0, 7)
        assert read_signed_exp_golomb(r) == -15
        
        # Even bit falls off end
        r = BitstreamReader(BytesIO(b"\x00"))
        r.seek(0, 6)
        assert read_signed_exp_golomb(r) == -16
        
        # Whole string falls off end
        r = BitstreamReader(BytesIO(b"\x00"))
        r.seek(1, 7)
        assert read_signed_exp_golomb(r) == 0


class TestWriteSignedExpGolomb(object):
    
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
        w = BitstreamWriter(f)
        write_signed_exp_golomb(w, value)
        assert w.tell() == exp_tell
        w.flush()
        assert f.getvalue() == encoded
    
    def test_write_past_eof(self):
        f = BytesIO()
        w = BitstreamWriter(f)
        
        # Sign bit falls off end
        bw = BoundedWriter(w, 9)
        write_signed_exp_golomb(bw, -15)
        
        # Odd bit falls off end
        bw = BoundedWriter(w, 8)
        write_signed_exp_golomb(bw, -15)
        
        # Even bit falls off end
        bw = BoundedWriter(w, 7)
        write_signed_exp_golomb(bw, -16)
        
        # Whole string falls off end
        bw = BoundedWriter(w, 0)
        write_signed_exp_golomb(bw, 0)
