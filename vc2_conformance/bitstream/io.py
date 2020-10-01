"""
The :py:mod:`vc2_conformance.bitstream.io` module contains low-level wrappers
for file-like objects which facilitate bitwise read and write operations of the
kinds used by VC-2's bitstream format.

The :py:class:`BitstreamReader` and :py:class:`BitstreamWriter` classes provide
equivalent methods for the various ``read_*`` pseudocode functions defined in
the VC-2 specification, along with a few additional utility methods.

.. note::

    These methods are designed to be 'safe' meaning that if out-of-range values
    are provided an error will be produced (rather than an unexpected value
    being written/read).

.. autoclass:: BitstreamReader
    :members:

.. autoclass:: BitstreamWriter
    :members:

The following utility functions are also provided for converting between
offsets given as ``(bytes, bits)`` pairs and offsets given in bytes.

.. autofunction:: to_bit_offset

.. autofunction:: from_bit_offset

"""

from bitarray import bitarray

from vc2_conformance.string_formatters import Bytes

from vc2_conformance.bitstream.exceptions import OutOfRangeError


__all__ = [
    "to_bit_offset",
    "from_bit_offset",
    "BitstreamReader",
    "BitstreamWriter",
]


def to_bit_offset(bytes, bits=7):
    """
    Convert from a (bytes, bits) tuple (as used by
    :py:meth:`BitstreamReader.tell` and :py:meth:`BitstreamWriter.tell`) into a
    total number of bits.
    """
    return (bytes * 8) + (7 - bits)


def from_bit_offset(total_bits):
    """
    Convert from a bit offset into a (bytes, bits) tuple (as used by
    :py:meth:`BitstreamReader.tell` and :py:meth:`BitstreamWriter.tell`).
    """
    bytes = total_bits // 8
    bits = total_bits % 8

    return (bytes, 7 - bits)


class BitstreamReader(object):
    """
    An open file which may be read one bit at a time.

    When the end-of-file is encountered, reads will result in a
    :py:exc:`EOFError`.
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

    def is_end_of_stream(self):
        """Check if we've reached the EOF. (A.2.5)"""
        return self._current_byte is None

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

        # Special case: in a bounded block
        if self._bits_remaining is not None:
            new_offset = to_bit_offset(bytes, bits)
            cur_offset = to_bit_offset(*self.tell())
            delta = new_offset - cur_offset

            # Special case: If the seek attemts to move past the end of the
            # bounded block, this is not possible so fail
            if delta > 0 and self._bits_remaining - delta < 0:
                raise Exception("Cannot seek() past end of bounded block.")

            if self._bits_remaining <= 0 and delta == 0:
                # We're past the end but not moving, don't change the count
                pass
            elif self._bits_remaining < 0 and delta < 0:
                # We're currently past the end of the bounded block and the
                # seek moves us back before the block, reset the bits remaining
                # accordingly
                self._bits_remaining = -delta
            else:
                # We're moving, adjust the remaining bit count accordingly
                self._bits_remaining -= delta

        self._file.seek(bytes)
        self._byte_offset = self._file.tell()
        self._read_byte()
        self._next_bit = bits

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

        if self._current_byte is None:
            raise EOFError()

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

    def read_uint_lit(self, num_bytes):
        """
        Read a 'num-bytes' long integer (like read_uint_lit (A.3.4)).
        """
        return self.read_nbits(num_bytes * 8)

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
        Signed version of :py:meth:`read_uint` (like read_sint (A.4.4)).
        """
        value = self.read_uint()

        # Read sign bit
        if value != 0:
            if self.read_bit():
                value = -value

        return value

    def try_read_bitarray(self, bits):
        """
        Attempt to read the next 'bits' bits from the bitstream file, leaving
        any bounded blocks we might be in if necessary). May read fewer bits if
        the end-of-file is encountered (but will not throw a :py:exc:`EOFError`
        like other methods of this class).

        Intended for the display of error messages (i.e. as the final use of a
        :py:class:`BitstreamReader` instance) only since this method may (or
        may not) exit the current bounded block as a side effect.
        """
        out = bitarray()

        try:
            for _ in range(bits):
                if self.bits_remaining is not None and self.bits_remaining <= 0:
                    self.bounded_block_end()
                out.append(self.read_bit())
        except EOFError:
            pass

        return out


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

    def is_end_of_stream(self):
        """
        Always True. (A.2.5)

        .. note::

            Strictly speaking this should return False when seeking to an
            earlier part of the stream however this behaviour is not
            implemented here for simplicity's sake.
        """
        return True

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

        # Special case: in a bounded block
        if self._bits_remaining is not None:
            new_offset = to_bit_offset(bytes, bits)
            cur_offset = to_bit_offset(*self.tell())
            delta = new_offset - cur_offset

            # Special case: If the seek attemts to move past the end of the
            # bounded block, this is not possible so fail
            if delta > 0 and self._bits_remaining - delta < 0:
                raise Exception("Cannot seek() past end of bounded block.")

            if self._bits_remaining <= 0 and delta == 0:
                # We're past the end but not moving, don't change the count
                pass
            elif self._bits_remaining < 0 and delta < 0:
                # We're currently past the end of the bounded block and the
                # seek moves us back before the block, reset the bits remaining
                # accordingly
                self._bits_remaining = -delta
            else:
                # We're moving, adjust the remaining bit count accordingly
                self._bits_remaining -= delta

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
                    raise ValueError("Cannot write 0s past the end of a bounded block.")
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
            raise OutOfRangeError(
                "0b{:b} is {} bits, not {}".format(
                    value,
                    value.bit_length(),
                    bits,
                )
            )

        for i in range(bits - 1, -1, -1):
            self.write_bit((value >> i) & 1)

    def write_uint_lit(self, num_bytes, value):
        """
        Write a 'num-bytes' long integer. The complement of read_uint_lit (A.3.4).

        Throws an :py:exc:`OutOfRangeError` if the value is too large to fit in
        the requested number of bytes.
        """
        self.write_nbits(num_bytes * 8, value)

    def write_bitarray(self, bits, value):
        """
        Write the 'bits' from the :py;class:`bitarray.bitarray` 'value'.

        Throws an :py:exc:`OutOfRangeError` if the value is longer than 'bits'.
        The value will be right-hand zero-padded to the required length.
        """
        if len(value) > bits:
            raise OutOfRangeError(
                "0b{} is {} bits, not {}".format(
                    value.to01(),
                    len(value),
                    bits,
                )
            )

        for bit in value:
            self.write_bit(bit)

        # Zero-pad
        for _ in range(len(value), bits):
            self.write_bit(0)

    def write_bytes(self, num_bytes, value):
        """
        Write the provided :py:class:`bytes` or :py:class:`bytearray` in a python
        bytestring.

        If the provided byte string is too long an :py:exc:`OutOfRangeError`
        will be raised. If it is too short, it will be right-hand zero-padded.
        """
        if len(value) > num_bytes:
            raise OutOfRangeError(
                "{} is {} bytes, not {}".format(
                    Bytes()(value),
                    len(value),
                    num_bytes,
                )
            )

        for byte in bytearray(value):
            self.write_nbits(8, byte)

        # Zero-pad
        for _ in range(len(value), num_bytes):
            self.write_nbits(8, 0)

    def write_uint(self, value):
        """
        Write an unsigned exp-golomb code.

        An :py:exc:`OutOfRangeError` will be raised if a negative value is
        provided.
        """
        if value < 0:
            raise OutOfRangeError("{} is negative, expected positive".format(value))

        value += 1

        for i in range(value.bit_length() - 2, -1, -1):
            self.write_bit(0)
            self.write_bit((value >> i) & 1)

        self.write_bit(1)

    def write_sint(self, value):
        """
        Signed version of :py:meth:`write_uint`.
        """
        self.write_uint(abs(value))

        # Write sign bit
        if value != 0:
            self.write_bit(value < 0)
