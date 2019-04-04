import pytest

from io import BytesIO

from vc2_conformance import bitstream


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
                ((1, 7), None, 3, 1),
                ((1, 7), None, 2, 2),
                ((1, 7), None, 1, 3),
                ((1, 7), None, 0, 4),
                # Past end of bounded block
                ((1, 7), None, 0, 4),
                ((1, 7), None, 0, 4),
                ((1, 7), None, 0, 4),
                ((1, 7), None, 0, 4),
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
                ((1, 7), 1, False, 1, 3, 1),
                ((1, 7), 1, False, 1, 2, 2),
                ((1, 7), 1, False, 1, 1, 3),
                ((1, 7), 1, False, 1, 0, 4),
                # Past bounded block end
                ((1, 7), 1, False, 1, 0, 4),
                ((1, 7), 0, True, 1, 0, 4),
            ]:
        assert bw.tell() == exp_tell
        if exp_error:
            with pytest.raises(ValueError):
                bw.write_bit(bit)
            bits_past_eof = 1 - bw.write_bit(1)
        else:
            bits_past_eof = 1 - bw.write_bit(bit)
        assert bits_past_eof == exp_bits_past_eof
        assert bw.bits_remaining == exp_bw_bits_remaining
        assert bw.bits_past_eof == exp_bw_bits_past_eof
