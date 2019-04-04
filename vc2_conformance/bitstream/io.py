"""
Low-level wrappers for file-like objects which facilitate bitwise read and
write operations.
"""

__all__ = [
    "BitstreamReader",
    "BitstreamWriter",
    "BoundedReader",
    "BoundedWriter",
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
        
        self.flush()
        
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


class BoundedReader(object):
    """
    A wrapper around a :py:class:`BitstreamReader` which implements bounded
    reading whereby bits past the end of the defined block are read as '1'.
    
    Attributes
    ----------
    bits_remaining : int
        The number of bits left to be read in this block.
    bits_past_eof : int
        The number of bits read past the EOF.
    """
    
    def __init__(self, reader, length):
        self._reader = reader
        self.bits_remaining = length
        self.bits_past_eof = 0
    
    def read_bit(self):
        if self.bits_remaining > 0:
            bit = self._reader.read_bit()
            
            self.bits_remaining -= 1
            if bit is None:
                self.bits_past_eof += 1
            
            return bit
        else:
            return None
    
    def tell(self):
        return self._reader.tell()
    
    def seek(self, *args, **kwargs):
        raise NotImplementedError("Seek not supported in BoundedReader")


class BoundedWriter(object):
    """
    A wrapper around a :py:class:`BitstreamWriter` which implements bounded
    writing whereby bits past the end of the defined block are checked to
    ensure that they are '1'.
    
    Attributes
    ----------
    bits_remaining : int
        The number of bits left to be written in this block.
    bits_past_eof : int
        The number of bits written past the EOF.
    """
    
    def __init__(self, writer, length):
        self._writer = writer
        self.bits_remaining = length
        self.bits_past_eof = 0
    
    def write_bit(self, value):
        if self.bits_remaining > 0:
            self.bits_remaining -= 1
            length = self._writer.write_bit(value)
            self.bits_past_eof += 1 - length
            return length
        else:
            if not value:
                raise ValueError(
                    "Cannot write 0s past the end of a BoundedWriter.")
            return 0
    
    def tell(self):
        return self._writer.tell()
    
    def seek(self, *args, **kwargs):
        raise NotImplementedError("Seek not supported in BoundedWriter")
    
    def flush(self):
        return self._writer.flush()
