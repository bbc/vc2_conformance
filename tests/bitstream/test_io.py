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


