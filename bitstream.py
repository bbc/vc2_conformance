"""
VC-2 bitstream manipulation utility library.

This module implements a library for reading, manipulating and creating VC-2
bit streams at a low-level. For example it might be used to generate
human-readable descriptions of a bitstream, introduce particular errors into a
bit stream or to produce bespoke bitstreams.

This module is *not* intended to be used as part of a reference decoder
implementation since its implementation and structure differs substantially
from the bitstream description in the standard and thus is more difficult to
directly verify.
"""

from contextlib import contextmanager

from collections import Iterable


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
        """
        # Clear the target bit
        self._current_byte &= ~(1 << self._next_bit)
        # Set new value
        self._current_byte |= int(bool(value)) << self._next_bit
        
        self._next_bit -= 1
        if self._next_bit < 0:
            self._write_byte()
    
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



class BitstreamValue(object):
    """
    The various subclasses of this class represent values which may be
    deserialised-from/seriallised-to a VC-2 bitstream (using :py:meth:`read`
    and :py:meth:`write` respectively).
    """
    
    def __init__(self, value=None, length=0):
        self._value = value
        self._length = length
        self._offset = None
        self._bits_past_eof = None
        
        # NB: This step is carried out last so that 'repr' will work for the
        # traceback.
        self._validate(value, length)
    
    @property
    def value(self):
        """The value repersented by this object in a native Python type."""
        return self._value
    
    @value.setter
    def value(self, value):
        self._validate(value, self.length)
        self._value = value
    
    @property
    def length(self):
        """The number of bits used to represent this value in the bitstream."""
        return self._length
    
    @length.setter
    def length(self, length):
        self._validate(self.value, length)
        self._length = length
    
    @property
    def offset(self):
        """
        If this value has been seriallised/deseriallised, this will contain the
        offset into the stream where the first bit was read/written as a
        (bytes, bits) tuple (see :py:meth:`BitstreamReader.tell`). None
        otherwise.
        """
        return self._offset
    
    @property
    def bits_past_eof(self):
        """
        If this value has been deseriallised from a bitstream but all or part of
        the value was located past the end of the file (or past the end of a
        :py:class:`BoundedBlock`), gives the number of bits beyond the end which
        were read. Set to None otherwise.
        """
        return self._bits_past_eof
    
    def _validate(self, value, length):
        """
        Internal method, to be overridden as required. Validate a candidate
        :py:attr:`value` and :py:attr:`length` field value combination. Raise a
        :py:exc:`ValueError` if invalid values have been provided.
        """
        if length < 0:
            raise ValueError(
                "Bitstream value lengths must always be non-negative")
    
    def __repr__(self):
        return "<{} value={!r} length={!r} offset={!r} bits_past_eof={!r}>".format(
            self.__class__.__name__,
            self.value,
            self.length,
            self.offset,
            self.bits_past_eof,
        )


class Bool(BitstreamValue):
    """A boolean value, as per read_bool (A.3.2)"""
    
    def __init__(self, value=False):
        super(Bool, self).__init__(value, 1)
    
    def read(self, reader):
        self._offset = reader.tell()
        bit = reader.read_bit()
        self._value = bool(bit) if bit is not None else True
        self._bits_past_eof = int(bit is None)
    
    def write(self, writer):
        self._offset = writer.tell()
        writer.write_bit(self.value)


class NBits(BitstreamValue):
    """A fixed-width unsigned integer, as per read_nbits (A.3.3)"""
    
    def __init__(self, value=0, length=0):
        super(NBits, self).__init__(value, length)
    
    def _validate(self, value, length):
        super(NBits, self)._validate(value, length)
        if value < 0 or value.bit_length() > length:
            raise ValueError(
                "NBits value must fit in {} bit(s) (got {})".format(
                    self.length, value))
    
    def read(self, reader):
        self._offset = reader.tell()
        
        self._value = 0
        self._bits_past_eof = 0
        for i in range(self.length):
            bit = reader.read_bit()
            self._value <<= 1
            self._value |= bit if bit is not None else 1
            self._bits_past_eof += int(bit is None)
    
    def write(self, writer):
        self._offset = writer.tell()

        for i in range(self.length-1, -1, -1):
            writer.write_bit((self.value >> i) & 1)

class ByteAlign(NBits):
    """
    Align to the next whole-byte boundary, as per byte_align (A.2.4).
    
    The :py:attr:`value` field holds the bits to when padding. The
    least-significant bits will be used.
    
    The :py:attr:`length` field is read-only for this type and is None unless
    this value has been serialised or deserialised.
    """
    
    def __init__(self, value=0):
        super(ByteAlign, self).__init__(value, None)
    
    def _validate(self, value, length):
        # Nothing to validate
        pass
    
    def read(self, reader):
        self._offset = reader.tell()
        
        # Advance to next byte, if required
        if self._offset[1] != 7:
            self._length = self.offset[1] + 1
            super(ByteAlign, self).read(reader)
        else:
            self._value = 0
            self._length = 0
            self._bits_past_eof = 0
    
    def write(self, writer):
        self._offset = writer.tell()
        
        # Advance to next byte, if required
        if self.offset[1] != 7:
            self.length = self.offset[1] + 1
            super(ByteAlign, self).write(writer)
        else:
            self.length = 0
            self._bits_past_eof = 0


class UInt(BitstreamValue):
    """
    A variable length (modified exp-Golomb) unsigned integer, as per read_uint
    (A.4.3)
    """
    
    def __init__(self, value=0):
        super(UInt, self).__init__(value, None)
    
    def _validate(self, value, length):
        if value < 0:
            raise ValueError(
                "UInt value must be non-negative (got {})".format(value))
    
    @property
    def length(self):
        return (((self.value + 1).bit_length() - 1) * 2) + 1
    
    def read(self, reader):
        self._offset = reader.tell()
        
        self._value = 1
        self._bits_past_eof = 0
        while True:
            bit = reader.read_bit()
            bit_value = bit if bit is not None else 1
            self._bits_past_eof += int(bit is None)
            
            if bit_value == 1:
                break
            else:
                self._value <<= 1
                
                bit = reader.read_bit()
                self._bits_past_eof += int(bit is None)
                self._value += bit if bit is not None else 1
        
        self._value -= 1
    
    def write(self, writer):
        self._offset = writer.tell()
        
        value = self.value + 1
        
        for i in range(value.bit_length()-2, -1, -1):
            writer.write_bit(0)
            writer.write_bit((value >> i) & 1)

        writer.write_bit(1)


class SInt(UInt):
    """
    A variable length (modified exp-Golomb) signed integer, as per read_sint
    (A.4.4)
    """
    
    def _validate(self, value, length):
        # Positive and negative values are allowed
        pass
    
    @property
    def length(self):
        orig_value = self.value
        self._value = abs(self.value)

        length = super(SInt, self).length
        
        # Account for sign bit
        if self.value != 0:
            length += 1
        
        self._value = orig_value
        
        return length
    
    def read(self, reader):
        super(SInt, self).read(reader)
        
        # Read sign bit
        if self.value != 0:
            bit = reader.read_bit()
            self._bits_past_eof += int(bit is None)
            if bit is None or bit == 1:
                self._value = -self.value
    
    def write(self, writer):
        orig_value = self.value
        self._value = abs(self.value)
        
        super(SInt, self).write(writer)
        
        # Write sign bit
        if self.value != 0:
            writer.write_bit(orig_value < 0)
        
        self._value = orig_value


class BoundedBlock(BitstreamValue):
    """
    Low-level construct. A bounded data-block as described in (A.4.2).
    
    The :py:math:`read` and :py:meth:`write` methods of this class should be
    used with ``with`` structures like so to get bounded readers/writers to
    pass to other values::
    
        uints = [UInt() for _ in range(100)]
        
        block = BoundedBlock(10)  # A 10-bit long bounded block

        # Reading from a bounded block
        with block.read(reader) as bounded_reader:
            for uint in uints:
                uint.read(bounded_reader)
        
        # Writing to a bounded block
        with block.write(writer) as bounded_writer:
            for uint in uints:
                uint.write(bounded_writer)
    
    Remaining bits will be flushed automatically when the ``with`` block exits.
    
    Any bits read beyond the end of the bounded block will be read as being
    beyond the 'end of file' (and should treated by the readers as 1s). This
    means that values read from past the end of the bounded block will be
    labelled as coming from the first bit after the end of the block and will
    have bits_past_eof set to their length.
    
    If any bits remain unread within the bounded block, these padding bits will
    be read when the ``with`` block ends and will be assigned to the
    :py:attr:`value` field and :py:attr:`unused_bits` will be set to the length
    of this padding field.
    
    When writing to a bounded block, all bits written past the end of the
    bounded block will be checked to ensure they're 1. A :py:exc:`ValueError`
    will be thrown otherwise. All writes past the end of the block will not
    advance the 'tell' value.
    """
    
    def __init__(self, length=0, value=0):
        # NB: Set first so that repr will work later if the validator fails on
        # the main constructor.
        self._unused_bits = None
        
        super(BoundedBlock, self).__init__(value, length)
    
    @property
    def unused_bits(self):
        """
        When this block was last serialised/deserialised, the number of unused
        bits left in the block. None otherwise.
        """
        return self._unused_bits
    
    class BoundedReader(object):
        """A wrapper around a :py:class:`BitstreamReader`."""
        
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
            raise NotImplementedError("Seek not supported in BoundedBlock")
    
    class BoundedWriter(object):
        """A wrapper around a :py:class:`BitstreamWriter`."""
        
        def __init__(self, writer, length):
            self._writer = writer
            self.bits_remaining = length
        
        def write_bit(self, value):
            if self.bits_remaining > 0:
                self.bits_remaining -= 1
                return self._writer.write_bit(value)
            else:
                if not value:
                    raise ValueError(
                        "Cannot write 0s past the end of a BoundedBlock.")
        
        def tell(self):
            return self._writer.tell()
        
        def seek(self, *args, **kwargs):
            raise NotImplementedError("Seek not supported in BoundedBlock")
        
        def flush(self):
            return self._writer.flush()
    
    
    @contextmanager
    def read(self, reader):
        """A context manager providing a bounded reader."""
        self._offset = reader.tell()
        
        bounded_reader = BoundedBlock.BoundedReader(reader, self.length)
        
        yield bounded_reader
        # NB: We intentionally don't flush the rest of the block if an
        # exception is raiesd (which is probably what you'd expect)
        
        self._unused_bits = bounded_reader.bits_remaining
        
        # Read any remaining bits in the block
        self._value = 0
        self._bits_past_eof = bounded_reader.bits_past_eof
        for i in range(bounded_reader.bits_remaining):
            bit = reader.read_bit()
            self._value <<= 1
            self._value |= bit if bit is not None else 1
            self._bits_past_eof += int(bit is None)
    
    @contextmanager
    def write(self, writer):
        """A context manager providing a bounded writer."""
        self._offset = writer.tell()
        
        bounded_writer = BoundedBlock.BoundedWriter(writer, self.length)
        
        yield bounded_writer
        # NB: We intentionally don't add the padding if an exception is raiesd
        # (which is probably what you'd expect)
        
        self._unused_bits = bounded_writer.bits_remaining
        
        # Write padding bits, as required
        for i in range(bounded_writer.bits_remaining-1, -1, -1):
            writer.write_bit((self.value >> i) & 1)
    
    def __repr__(self):
        return "<{} value={!r} length={!r} offset={!r} bits_past_eof={!r} unused_bits={!r}>".format(
            self.__class__.__name__,
            self.value,
            self.length,
            self.offset,
            self.bits_past_eof,
            self.unused_bits,
        )

class Concatenation(BitstreamValue):
    r"""
    A concatenation of a fixed set of :py:class:`BitstreamValue`\ s.
    
    The :py:attr:`value` should be an (ordered, preferably immutable) iterable
    of :py:class:`BitstreamValue` classes. These values will be
    serialised/deserialised one after the other.
    
    This may be used as the basis for defining composite structures of
    bitstream values. For example ``parse_parameters`` (11.2.1)``::
        
        major_version = UInt()
        minor_version = UInt()
        profile = UInt()
        level = UInt()
        
        parse_parameters = Concatenation(
            major_version, minor_version, profile, level)
    """
    
    def __init__(self, *values):
        super(Concatenation, self).__init__(values, length=None)
    
    def _validate(self, value, length):
        if not isinstance(value, Iterable):
            raise ValueError(
                "Concatenation expects an iterable of BitstreamValues.")
        if not all(isinstance(v, BitstreamValue) for v in value):
            raise ValueError(
                "All bitstream.Tuple components must be BitstreamValues.")
    
    @property
    def length(self):
        if any(v.length is None for v in self.value):
            return None
        else:
            return sum(v.length for v in self.value)
    
    @property
    def bits_past_eof(self):
        if any(v.bits_past_eof is None for v in self.value):
            return None
        else:
            return sum(v.bits_past_eof for v in self.value)
    
    def read(self, reader):
        self._offset = reader.tell()
        for v in self.value:
            v.read(reader)
    
    def write(self, writer):
        self._offset = writer.tell()
        for v in self.value:
            v.write(writer)
    
    def __getitem__(self, key):
        """Shorthand for ``concatenation.value[key]``"""
        return self.value[key]
    
    def __repr__(self):
        return "<{} {}>".format(
            self.__class__.__name__,
            " ".join(repr(v) for v in self.values)
        )

class Option(BitstreamValue):
    r"""
    An option type consisting of two :py:class:`BitstreamValue`\ s.
    
    The first value indicates whether the second value can be found in the
    bitstream or whether it is absent.
    
    This type may be used to describe the bitstream sequences such as
    ``scan_format`` (11.4.5) where a flag or index indicates if another value
    will follow immediately after or not::
    
        custom_scan_format_flag = Bool()
        source_sampling = UInt()
        
        scan_format = Option(custom_scan_format_flag, source_sampling)
    """
    
    def __init__(self, flag_value, value_value, inverted=False):
        """
        Parameters
        ==========
        flag_value : :py:class:`BitstreamValue`
            A value which appears first in the bitstream. If this value is
            truthy, ``value_value`` will follow in the bitstream. If
            ``flag_value`` is falsy, ``value_value`` will not appear in the
            bitstream. Stored as :py:attr:`Option.flag`.
        value_value : :py:class:`BitstreamValue`
            The value which may (or may not) be include in the bitstream.
            Stored as :py:attr:`Option.value`.
        inverted : bool
            If set to True, inverts the meaning of the flag_value (making
            truthy values omit the value and falsey values include it).
        """
        self._flag = flag_value
        self._inverted = inverted
        
        super(Option, self).__init__(value_value, length=None)
        self._validate_flag()
    
    def _validate(self, value, length):
        if not isinstance(value, BitstreamValue):
            raise ValueError(
                "Option values must be BitstreamValues.")
    
    def _validate_flag(self, flag):
        if not isinstance(flag, BitstreamValue):
            raise ValueError(
                "Option flags must be BitstreamValues.")
    
    @property
    def flag(self):
        """
        The flag :py:class:`BitstreamValue` which dictates whether the
        :py:attr:`Option.value` appears in the bitstream.
        """
        return self._flag
    
    @flag.setter
    def flag(self, flag)
        self._validate_flag(flag)
        self._flag = flag
    
    @property
    def inverted(self):
        """Should the meaning of the :py:attr:`Option.flag` be inverted?"""
        return self._inverted
    
    @inverted.setter
    def inverted(self, inverted):
        self._inverted = inverted
    
    @property
    def value_present(self):
        """
        True if :py:attr:`Option.value` is/will be included in the bitstream,
        False otherwise.
        """
        value_present = bool(self.flag.value)
        if self.inverted:
            value_present = not value_present
        
        return value_present
    
    @property
    def length(self):
        if self.value_present:
            if self.flag.length is None or self.value.length is None:
                return None
            else:
                return self.flag.length + self.value.length
        else:
            return self.flag.length
    
    @property
    def bits_past_eof(self):
        if self.value_present:
            if self.flag.bits_past_eof is None or self.value.bits_past_eof is None:
                return None
            else:
                return self.flag.bits_past_eof + self.value.bits_past_eof
        else:
            return self.flag.bits_past_eof
    
    def read(self, reader):
        """
        Read the flag and maybe the value from the bitstream. If value is not
        present in the bitstream, :py:attr:`Option.value` will not be altered
        and should be considered undefined.
        """
        self._offset = reader.tell()
        
        self.flag.read(reader)
        if self.value_present:
            self.value.read(reader)
    
    def write(self, writer):
        """
        Write the flag and maybe the value into the bitstream. If the flag
        indicates the value is to be omitted, the value in
        :py:attr:`Option.value` will not be touched and its state should be
        considered undefined.
        """
        self._offset = writer.tell()
        
        self.flag.write(writer)
        if self.value_present:
            self.value.write(writer)
