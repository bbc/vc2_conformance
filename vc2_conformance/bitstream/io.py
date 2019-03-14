"""
Low-level wrappers for file-like objects which facilitate bitwise read and
write operations.
"""

__all__ = [
    "BitstreamReader",
    "BitstreamWriter",
]


class BitstreamReader(object):
    """
    An open file which may be read one bit at a time.
    """
    
    def __init__(self, file):
        """
        Parameters
        ==========
        file : A Python 'file' object in binary-read mode.
        """
        self._file = file
        
        # The index of the next bit to read
        self._next_bit = 7
        
        # The byte currently being read (or None if at the EOF)
        self._current_byte = None
        
        # Load-in the first byte
        self._read_byte()
    
    def _read_byte(self):
        """Internal method. Advance to the next byte. (A.2.2)"""
        byte = self._file.read(1)
        if len(byte) == 1:
            self._current_byte = bytearray(byte)[0]
            self._next_bit = 7
        else:
            self._current_byte = None
            self._next_bit = 7
    
    def read_bit(self):
        """
        Read and return the next bit in the stream. (A.2.3)
        
        Returns
        =======
        An integer 0 or 1. If the end-of-file has been reached, None is
        returned instead.
        """
        if self._current_byte is None:
            return None
        
        bit = (self._current_byte >> self._next_bit) & 1
        
        self._next_bit -= 1
        if self._next_bit < 0:
            self._read_byte()
        
        return bit
    
    def tell(self):
        """
        Report the current bit-position within the stream.
        
        Returns
        =======
        (bytes, bits)
            ``bytes`` is the offset of the current byte from the start of the
            stream. ``bits`` is the offset in the current byte (starting at 7
            (MSB) and advancing towards 0 (LSB) as bits are read).
        """
        if self._current_byte is not None:
            return (self._file.tell() - 1, self._next_bit)
        else:
            return (self._file.tell(), self._next_bit)
    
    def seek(self, bytes, bits=7):
        """
        Seek to a specific (absolute) position in the file.
        
        Parameters
        ==========
        bytes : int
            The byte-offset from the start of the file.
        bits : int
            The bit offset into the specified byte to start reading from.
        """
        assert 0 <= bits <= 7
        
        self._file.seek(bytes)
        self._read_byte()
        self._next_bit = bits


class BitstreamWriter(object):
    """
    An open file which may be written one bit at a time.
    """
    
    def __init__(self, file):
        """
        Parameters
        ==========
        file : A Python 'file' object in binary-write mode.
        """
        self._file = file
        
        # The index of the next bit to write
        self._next_bit = 7
        
        # The byte currently being write
        self._current_byte = 0
    
    def _write_byte(self):
        """Internal method. Write the current byte and start a new one. (A.2.2)"""
        self._file.write(bytearray([self._current_byte]))
        self._current_byte = 0
        self._next_bit = 7
    
    def write_bit(self, value):
        """
        Write a bit into the bitstream. (Opposite of A.2.3)
        
        Parameters
        ==========
        value :
            A truthy value (for 1) or a falsy value (for 0).
        
        Returns
        =======
        length : int
            Returns 1 if the value was written, 0 if the bit was not written
            (e.g. if trying to write past the end of the file)
        """
        # Clear the target bit
        self._current_byte &= ~(1 << self._next_bit)
        # Set new value
        self._current_byte |= int(bool(value)) << self._next_bit
        
        self._next_bit -= 1
        if self._next_bit < 0:
            self._write_byte()
        
        # Assume we always suceeed (the return value is only ever '0' for
        # BoundedBlock's BoundedWriter wrapper for this class).
        return 1
    
    def tell(self):
        """
        Report the current bit-position within the stream.
        
        Returns
        =======
        (bytes, bits)
            ``bytes`` is the offset of the current byte from the start of the
            stream. ``bits`` is the offset in the current byte (starting at 7
            (MSB) and advancing towards 0 (LSB) as bits are written).
        """
        return (self._file.tell(), self._next_bit)
    
    def seek(self, bytes, bits=7):
        """
        Seek to a specific (absolute) position in the file. Seeking to a given
        byte will overwrite any bits already set in that byte to 0.
        
        Parameters
        ==========
        bytes : int
            The byte-offset from the start of the file.
        bits : int
            The bit offset into the specified byte to start writing to.
        """
        assert 0 <= bits <= 7
        
        self._file.seek(bytes)
        self._current_byte = 0
        self._next_bit = bits
    
    def flush(self):
        """
        Ensure all bytes are committed to the file.
        """
        # Write the current byte to the file (if any bits have been written
        # into it). Note that we don't use write_bit() since this write is
        # writing a partially complete byte and so we don't wish to move on yet
        # (the user may later write some more bits to this byte).
        if self._next_bit != 7:
            self._file.write(bytearray([self._current_byte]))
            self._file.seek(-1, 1)  # Seek backward 1 byte
        
        self._file.flush()



