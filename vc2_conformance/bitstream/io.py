"""
Low-level wrappers for file-like objects which facilitate bitwise read and
write operations of the kinds used by VC-2's bitstream format.

By contrast with the implementation defined by the VC-2 pseudo code:

* Writing is implemented, as well as reading
* More appropriate Python data types are returned
* During writing, bounds checking is performed.
"""

from bitarray import bitarray

from vc2_conformance.exceptions import OutOfRangeError

from vc2_conformance._string_formatters import Bytes

from vc2_conformance.exp_golomb import (
    exp_golomb_length,
    signed_exp_golomb_length,
)


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
        
        # The current byte index being read
        self._byte_offset = self._file.tell()
        
        # The byte currently being read (or None if at the EOF)
        self._current_byte = None
        
        # None, if not in a bounded block. Otherwise, the number of unused bits
        # remaining in the block. If negative, indicates the number of bits
        # read past the end of the block.
        self._bits_remaining = None
        
        # The number of bits read past the end-of-file. Reset on 'seek'.
        self._bits_past_eof = 0
        
        # Load-in the first byte
        self._read_byte()
    
    def _read_byte(self):
        """Internal method. Advance to the next byte. (A.2.2)"""
        byte = self._file.read(1)
        self._byte_offset += 1
        if len(byte) == 1:
            self._current_byte = bytearray(byte)[0]
            self._next_bit = 7
        else:
            self._current_byte = None
            self._next_bit = 7
    
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
        return (self._byte_offset - 1, self._next_bit)
    
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
        
        if self._bits_remaining is not None:
            raise Exception("Cannot seek while in a bounded block.")
        
        self._file.seek(bytes)
        self._byte_offset = self._file.tell()
        self._read_byte()
        self._next_bit = bits
        self._bits_past_eof = 0
    
    @property
    def bits_past_eof(self):
        """
        The number of bits read beyond the end of the file.
        """
        return self._bits_past_eof
    
    @property
    def bits_remaining(self):
        """
        The number of bits left in the current bounded block.
        
        None, if not in a bounded block. Otherwise, the number of unused bits
        remaining in the block. If negative, indicates the number of bits read
        past the end of the block.
        """
        return self._bits_remaining
    
    def bounded_block_begin(self, length):
        """
        Begin a bounded block of the specified length in bits.
        """
        if self._bits_remaining is not None:
            raise Exception("Cannot nest bounded blocks")
        self._bits_remaining = length
    
    def bounded_block_end(self):
        """
        Ends the current bounded block. Returns the number of unused bits
        remaining, but does not read them or seek past them.
        """
        if self._bits_remaining is None:
            raise Exception("Not in bounded block.")
        
        unused_bits = max(0, self._bits_remaining)
        self._bits_remaining = None
        
        return unused_bits
    
    def read_bit(self):
        """
        Read and return the next bit in the stream. (A.2.3) Reads '1' for
        values past the end of file.
        """
        # Don't read past the end of the current bounded block
        if self._bits_remaining is not None:
            self._bits_remaining -= 1
        
            # NB: Checked *after* decrement hence <= -1 not <= 0
            if self._bits_remaining <= -1:
                return 1
        
        # Read '1's past the EOF
        if self._current_byte is None:
            self._bits_past_eof += 1
            return 1
        
        bit = (self._current_byte >> self._next_bit) & 1
        
        self._next_bit -= 1
        if self._next_bit < 0:
            self._read_byte()
        
        return bit
    
    def read_nbits(self, bits):
        """
        Read an 'bits'-bit unsigned integer (like read_nbits (A.3.3)).
        """
        value = 0
        for i in range(bits):
            value <<= 1
            value |= self.read_bit()
        
        return value
    
    def read_bitarray(self, bits):
        """
        Read 'bits' bits returning the value as a
        :py:class:`bitarray.bitarray`.
        """
        return bitarray(self.read_bit() for _ in range(bits))
    
    def read_bytes(self, num_bytes):
        """
        Read a number of bytes returning a :py:class:`bytes` string.
        """
        return self.read_bitarray(num_bytes * 8).tobytes()
    
    def read_uint(self):
        """
        Read an unsigned exp-golomb code (like read_uint (A.4.3)) and return an
        integer.
        """
        value = 1
        while True:
            if self.read_bit():
                break
            else:
                value <<= 1
                value += self.read_bit()
        
        value -= 1
        
        return value
    
    def read_sint(self):
        """
        Signed version of :py:meth:`read_uint`` (like read_sint (A.4.4)).
        """
        value = self.read_uint()
        
        # Read sign bit
        if value != 0:
            if self.read_bit():
                value = -value
        
        return value


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
        
        # The current byte index being written
        self._byte_offset = self._file.tell()
        
        # The byte currently being write
        self._current_byte = 0
        
        # None, if not in a bounded block. Otherwise, the number of unused bits
        # remaining in the block. If negative, indicates the number of bits
        # read past the end of the block.
        self._bits_remaining = None
    
    def _write_byte(self):
        """Internal method. Write the current byte and start a new one. (A.2.2)"""
        self._file.write(bytearray([self._current_byte]))
        self._current_byte = 0
        self._next_bit = 7
        self._byte_offset += 1
    
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
        return (self._byte_offset, self._next_bit)
    
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
        
        if self._bits_remaining is not None:
            raise Exception("Cannot seek while in a bounded block.")
        
        self.flush()
        
        self._file.seek(bytes)
        self._byte_offset = self._file.tell()
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
    
    @property
    def bits_past_eof(self):
        """The number of bits written beyond the end of the file. Always 0."""
        return 0
    
    @property
    def bits_remaining(self):
        """
        The number of bits left in the current bounded block.
        
        None, if not in a bounded block. Otherwise, the number of unused bits
        remaining in the block. If negative, indicates the number of bits read
        past the end of the block.
        """
        return self._bits_remaining
    
    def bounded_block_begin(self, length):
        """
        Begin a bounded block of the specified length in bits.
        """
        if self._bits_remaining is not None:
            raise Exception("Cannot nest bounded blocks")
        self._bits_remaining = length
    
    def bounded_block_end(self):
        """
        Ends the current bounded block. Returns the number of unused bits
        remaining, but does not write them or seek past them.
        """
        if self._bits_remaining is None:
            raise Exception("Not in bounded block.")
        
        unused_bits = max(0, self._bits_remaining)
        self._bits_remaining = None
        
        return unused_bits
    
    def write_bit(self, value):
        """
        Write a bit into the bitstream. If in a bounded block, raises a
        :py:exc:`ValueError` if a '0' is written beyond the end of the block.
        """
        # Don't write past the end of the current bounded block
        if self._bits_remaining is not None:
            self._bits_remaining -= 1
        
            # NB: Checked *after* decrement hence <= -1 not <= 0
            if self._bits_remaining <= -1:
                if not value:
                    raise ValueError(
                        "Cannot write 0s past the end of a bounded block.")
                return
        
        # Clear the target bit
        self._current_byte &= ~(1 << self._next_bit)
        # Set new value
        if value:
            self._current_byte |= 1 << self._next_bit
        
        self._next_bit -= 1
        if self._next_bit < 0:
            self._write_byte()
    
    def write_nbits(self, bits, value):
        """
        Write an 'bits'-bit integer. The complement of read_nbits (A.3.3).
        
        Throws an :py:exc:`OutOfRangeError` if the value is too large to fit in
        the requested number of bits.
        """
        if value < 0 or value.bit_length() > bits:
            raise OutOfRangeError("0b{:b} is {} bits, not {}".format(
                value,
                value.bit_length(),
                bits,
            ))
        
        for i in range(bits-1, -1, -1):
            self.write_bit((value >> i) & 1)
    
    def write_bitarray(self, bits, value):
        """
        Write the 'bits' from the :py;class:`bitarray.bitarray` 'value'.
        
        Throws an :py:exc:`OutOfRangeError` if the value has the wrong length.
        """
        if len(value) != bits:
            raise OutOfRangeError("0b{} is {} bits, not {}".format(
                value.to01(),
                len(value),
                bits,
            ))
        
        for bit in value:
            self.write_bit(bit)
    
    def write_bytes(self, num_bytes, value):
        """
        Write the provided :py:class:`bytes` or :py:class:`bytearray` in a python
        bytestring.
        
        If the provided byte string is the wrong length an
        :py:exc:`OutOfRangeError` will be raised.
        """
        if len(value) != num_bytes:
            raise OutOfRangeError("{} is {} bytes, not {}".format(
                Bytes()(value),
                len(value),
                num_bytes,
            ))
        
        for byte in bytearray(value):
            self.write_nbits(8, byte)
    
    def write_uint(self, value):
        """
        Write an unsigned exp-golomb code.
        
        An :py:exc:`OutOfRangeError` will be raised if a negative value is
        provided.
        """
        if value < 0:
            raise OutOfRangeError("{} is negative, expected positive".format(value))
        
        value += 1
        
        for i in range(value.bit_length()-2, -1, -1):
            self.write_bit(0)
            self.write_bit((value >> i) & 1)
        
        self.write_bit(1)
    
    def write_sint(self, value):
        """
        Signed version of :py:meth:`write_uint``.
        """
        self.write_uint(abs(value))
        
        # Write sign bit
        if value != 0:
            self.write_bit(value < 0)
