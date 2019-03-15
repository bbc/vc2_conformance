"""
General purpose wrappers :py:class:`BitstreamValue` which modify the bitstream
format of the contained value, for example by constraining it to a fixed-length
block.
"""

from vc2_conformance.bitstream import BitstreamValue

from vc2_conformance.bitstream._util import concat_strings


__all__ = [
    "WrappedValue",
    "Maybe",
    "BoundedBlock",
]


class WrappedValue(BitstreamValue):
    r"""
    A WrappedValue is a base class for implementing :py:class:`BitstreamValue`\
    s which wrap another, single :py:class:`BitstreamValue`.
    
    Implements validation that the wrapped value is a
    :py:class:`BitstreamValue` along with pass-throughs for the
    :py:attr:`value` property and indexing operator.
    """
    
    def __init__(self, inner_value):
        self._inner_value = inner_value
        super(WrappedValue, self).__init__()
        self._validate(self._inner_value)
    
    def _validate(self, inner_value):
        if not isinstance(inner_value, BitstreamValue):
            raise ValueError(
                "{}.inner_value must be a BitstreamValue.".format(
                    self.__class__.__name__))
    
    @property
    def inner_value(self):
        """The :py:class:`BitstreamValue` being wrapped."""
        return self._inner_value
    
    @inner_value.setter
    def inner_value(self, inner_value):
        self._validate(inner_value)
        self._inner_value = inner_value
    
    @property
    def value(self):
        """
        The value of the wrapped :py:class:`BitstreamValue`. Equivallent to
        ``wrapper.inner_value.value``.
        """
        return self._inner_value.value
    
    @value.setter
    def value(self, value):
        self._inner_value.value = value
    
    def __getitem__(self, key):
        """
        Shorthand for ``wrapper.inner_value[key]``.
        """
        return self._inner_value[key]
    
    def __repr__(self):
        return "<{} value={!r}>".format(
            self.__class__.__name__,
            self.inner_value,
        )


class BoundedBlock(WrappedValue):
    """
    :py:class:`BitstreamValue` wrapper. A fixed-size bounded data-block as
    described in (A.4.2) which contains a :py:class:`BitstreamValue`.
    
    When reading the contained value, any bits beyond the bounding size will be
    read as if past the end of the file (and treated as '1'). Likewise when
    writing, any bits beyond the bounding size will not be written (but will be
    checked to ensure they're '1' otherwise a :py:exc:`ValueError` is thrown).
    
    If any excess bits are left after reading/writing the contents, the least
    significant bits from the Python integer :py:attr:`pad_value` will be
    read-from/written-to the remaining space and :py:attr:`unused_bits` will be
    updated accordingly.
    
    An example use for this block might be to represent a represent a set of
    transform values in the bitstream. For example, the following contrived
    example shows a series of signed variable-length integers contained in a
    one byte block::
    
        coeffs = Concatenation(SInt(), SInt(), SInt(), SInt())
        coeffs_block = BoundedBlock(coeffs, 8)
    """
    
    def __init__(self, inner_value, length, pad_value=0):
        """
        Parameters
        ==========
        inner_value : :py:class:`BoundedBlock`
            The value to enclose in the bounded block.
        length : int or function() -> int
            If an int, the length of the block in bits.
            
            If a function, this function will be called with no arguments and
            should return an int giving the length of the block in bits.
            
            In general, this argument will be a lambda function which
            calculates the length using a previously read or written
            :py:class:`BitstreamValue`.
            
        """
        # NB: Set first so that repr will work later if the validator fails on
        # the main constructor.
        self._pad_value = pad_value
        self.length = length
        
        super(BoundedBlock, self).__init__(inner_value)
    
    @property
    def length(self):
        """
        The length of the bounded block.
        
        If set, may be set to an integer or a function (see ``length`` argument
        of constructor), but will always read as an int.
        """
        return self._length()
    
    @length.setter
    def length(self, length):
        if callable(length):
            self._length = length
        else:
            self._length = lambda: length
    
    @property
    def pad_value(self):
        """The bit pattern to use to fill any unused space in the block."""
        return self._pad_value
    
    @pad_value.setter
    def pad_value(self, pad_value):
        self._pad_value = pad_value
    
    @property
    def unused_bits(self):
        """
        The number of unused bits left in the block. None if the length of the
        wrapped value is unknown.
        """
        if self.inner_value.length is None:
            return None
        else:
            return max(0, self.length - self.inner_value.length)
    
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
                        "Cannot write 0s past the end of a BoundedBlock.")
                return 0
        
        def tell(self):
            return self._writer.tell()
        
        def seek(self, *args, **kwargs):
            raise NotImplementedError("Seek not supported in BoundedBlock")
        
        def flush(self):
            return self._writer.flush()
    
    
    def read(self, reader):
        """A context manager providing a bounded reader."""
        self._offset = reader.tell()
        
        bounded_reader = BoundedBlock.BoundedReader(reader, self.length)
        
        self.inner_value.read(bounded_reader)
        
        # Read any remaining bits in the block
        self._pad_value = 0
        self._bits_past_eof = bounded_reader.bits_past_eof
        for i in range(bounded_reader.bits_remaining):
            bit = reader.read_bit()
            self._pad_value <<= 1
            self._pad_value |= bit if bit is not None else 1
            self._bits_past_eof += int(bit is None)
    
    def write(self, writer):
        """A context manager providing a bounded writer."""
        self._offset = writer.tell()
        
        bounded_writer = BoundedBlock.BoundedWriter(writer, self.length)
        
        self.inner_value.write(bounded_writer)
        
        self._bits_past_eof = bounded_writer.bits_past_eof
        
        # Write padding bits, as required
        for i in range(bounded_writer.bits_remaining-1, -1, -1):
            self._bits_past_eof += 1 - writer.write_bit((self._pad_value >> i) & 1)
    
    def __repr__(self):
        return "<{} value={!r} length={!r} pad_value={!r} unused_bits={!r}>".format(
            self.__class__.__name__,
            self.inner_value,
            self.length,
            self.pad_value,
            self.unused_bits,
        )

    def __str__(self):
        padding = ""
        if self.unused_bits:
            bits = self.pad_value
            bits &= (1 << self.unused_bits) - 1
            padding = "<padding 0b{:0{}b}>".format(bits, self.unused_bits)
        
        return concat_strings([str(self.inner_value), padding])


class Maybe(WrappedValue):
    r"""
    :py:class:`BitstreamValue` wrapper. An 'maybe' type for bitstream values
    which may sometimes be omitted.
    
    This type may be used to describe the bitstream sequences such as
    ``scan_format`` (11.4.5) where a flag or index is used to control whether
    or not a value is omitted or included.
    
        custom_scan_format_flag = Bool()
        source_sampling = UInt()
        
        scan_format = Concatenation(
            custom_scan_format_flag,
            Maybe(
                source_sampling,
                lambda: custom_scan_format_flag.value,
            ),
        )
    """
    
    def __init__(self, inner_value, flag):
        """
        Parameters
        ==========
        value_value : :py:class:`BitstreamValue`
            The value which may (or may not) be included in the bitstream.
            Stored as :py:attr:`Maybe.value`.
        flag : bool or function() -> bool
            If a bool, specifies whether the wrapped value is present in the
            bitstream or not.
            
            If a function, the function will be called with no arguments and
            return a bool with the meaning above.
            
            In general, this argument will be a simple lambda function which
            fetches a previously read or written :py:class:`BitstreamValue` to
            determine the flag value.
        """
        self.flag = flag
        super(Maybe, self).__init__(inner_value)
    
    @property
    def flag(self):
        """
        The current visibility state of this value. If True,
        :py:attr:`inner_value` will be included in the bitstream, if False it
        will be omitted.
        
        This property may be set with either a bool or a function (see the
        constructor ``flag`` argument) but always reads as a bool.
        """
        return bool(self._flag())
    
    @flag.setter
    def flag(self, flag):
        if callable(flag):
            self._flag = flag
        else:
            self._flag = (lambda: flag)
    
    @property
    def length(self):
        if self.flag:
            return self.inner_value.length
        else:
            return 0
    
    @property
    def bits_past_eof(self):
        if self.flag:
            return self.inner_value.bits_past_eof
        else:
            return 0
    
    def read(self, reader):
        """
        Read the flag and maybe the value from the bitstream. If value is not
        present in the bitstream, :py:attr:`Maybe.inner_value` will not be
        altered and should be considered undefined.
        """
        self._offset = reader.tell()
        
        if self.flag:
            self.inner_value.read(reader)
    
    def write(self, writer):
        """
        Write the flag and maybe the value into the bitstream. If the flag
        indicates the value is to be omitted, the value in
        :py:attr:`Maybe.inner_value` will not be touched and its state should
        be considered undefined.
        """
        self._offset = writer.tell()
        
        if self.flag:
            self.inner_value.write(writer)
    
    def __repr__(self):
        return "<{} {!r} flag={}>".format(
            self.__class__.__name__,
            self.inner_value,
            self.flag,
        )
    
    def __str__(self):
        if self.flag:
            return str(self.inner_value)
        else:
            return ""


