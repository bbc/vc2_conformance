"""
General purpose wrappers :py:class:`BitstreamValue` which modify the bitstream
format of the contained value, for example by constraining it to a fixed-length
block.
"""

from vc2_conformance.bitstream import BitstreamValue, ensure_bitstream_value

from vc2_conformance.bitstream.primitive import read_bits, write_bits

from vc2_conformance.bitstream._util import concat_strings

from vc2_conformance.bitstream._safe_get import (
    safe_get_non_negative_integer_value,
    safe_get_bool,
)


__all__ = [
    "EmptyValueError",
    "WrappedValue",
    "Maybe",
    "BoundedBlock",
]


class EmptyValueError(Exception):
    """
    Error thrown when attempting to access the value within a
    :py:class:`WrappedValue` which is empty.
    
    Typically, thrown when accessing a :py:class:`Maybe` whose
    :py:attr:`Maybe.flag` is False.
    """


class WrappedValue(BitstreamValue):
    r"""
    A WrappedValue is a base class for implementing :py:class:`BitstreamValue`\
    s which wrap another, single :py:class:`BitstreamValue`.
    
    Implements validation that the wrapped value is a
    :py:class:`BitstreamValue` along with pass-throughs for the
    :py:attr:`value` property and indexing operator.
    """
    
    def __init__(self, inner_value=None):
        self._inner_value = inner_value
        super(WrappedValue, self).__init__()
    
    def _validate(self, inner_value):
        if not isinstance(inner_value, BitstreamValue):
            raise ValueError(
                "{}.inner_value must be a BitstreamValue.".format(
                    self.__class__.__name__))
    
    @property
    def inner_value(self):
        """The :py:class:`BitstreamValue` being wrapped."""
        return self._inner_value
    
    @property
    def value(self):
        """
        The value of the wrapped :py:class:`BitstreamValue`. Equivallent to
        ``wrapper.inner_value.value``.
        """
        if self._inner_value is not None:
            return self._inner_value.value
        else:
            raise EmptyValueError()
    
    @value.setter
    def value(self, value):
        if self._inner_value is not None:
            self._inner_value.value = value
        else:
            raise EmptyValueError()
    
    def __getitem__(self, key):
        """
        Shorthand for ``wrapper.inner_value[key]``.
        """
        if self._inner_value is not None:
            return self._inner_value[key]
        else:
            raise EmptyValueError()
    
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
        length : int or :py:class:`BitstreamValue`
            If an int, the length of the block in bits.
            
            If a :py:class:`BitstreamValue`, this value should specify the
            length of the block in bits.
        """
        self._length_bitstream_value = ensure_bitstream_value(length)
        self._pad_value = pad_value
        
        super(BoundedBlock, self).__init__(inner_value)
        
        self._validate(self._inner_value)
        
        self._inner_value._notify_on_change(self)
        self._length_bitstream_value._notify_on_change(self)
    
    def _dependency_changed(self, _):
        self._changed()
    
    @property
    def length(self):
        """
        The length of the bounded block (in bits). See also
        :py:attr:`length_bitstream_value`.
        """
        return safe_get_non_negative_integer_value(self._length_bitstream_value)
    
    @property
    def length_bitstream_value(self):
        """
        The :py:class:`BitstreamValue` which defines the :py:attr:`length` of
        this block.
        """
        return self._length_bitstream_value
    
    @property
    def pad_value(self):
        """The bit pattern to use to fill any unused space in the block."""
        return self._pad_value
    
    @pad_value.setter
    def pad_value(self, pad_value):
        self._pad_value = pad_value
        self._changed()
    
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
        with self._coalesce_change_notifications():
            self._offset = reader.tell()
            
            bounded_reader = BoundedBlock.BoundedReader(reader, self.length)
            self.inner_value.read(bounded_reader)
            
            # Read any remaining bits in the block
            self._pad_value, self._bits_past_eof = read_bits(reader, bounded_reader.bits_remaining)
            self._bits_past_eof += bounded_reader.bits_past_eof
            
            # Force a notification since the padding value will have changed
            # (as well as the inner value)
            self._changed()
    
    def write(self, writer):
        """A context manager providing a bounded writer."""
        self._offset = writer.tell()
        
        bounded_writer = BoundedBlock.BoundedWriter(writer, self.length)
        
        self.inner_value.write(bounded_writer)
        
        self._bits_past_eof = write_bits(writer, bounded_writer.bits_remaining, self._pad_value)
        self._bits_past_eof += bounded_writer.bits_past_eof
    
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
    
    ::
    
        custom_scan_format_flag = Bool()
        
        scan_format = Concatenation(
            custom_scan_format_flag,
            Maybe(UInt, custom_scan_format_flag),
        )
    """
    
    def __init__(self, value_constructor, flag):
        """
        Parameters
        ==========
        value_constructor : function() -> :py:class:`BitstreamValue`
            A function taking no arguments and returning a new
            :py:class:`BitstreamValue` to be held in this :py:class:`Maybe`.
            Called to construct a new value whenever the flag becomes 'True'.
        flag : bool or :py:class:`BitstreamValue`
            If a bool, specifies whether the wrapped value is present in the
            bitstream or not. (Not particularly useful).
            
            If a :py:class:`BitstreamValue`, the this value will be used to
            determine if this :py:class:`Maybe` should hold a value or not.
            
            When this value is False, the :py:attr:`inner_value` will be
            discarded (and set to None) and accessing :py:attr:`value` will
            produce a :py:exc`ValueError`.
            
            When this value is True, if no :py:attr:`inner_value` exists yet,
            one will be created using ``value_constructor``. Otherwise, the
            existing value will be retained.
            
            The :py:class:`BitstreamValue` provided for the flag is not
            read/written when this :py:class:`Maybe` is
            serialised/deserialised. You should ensure it appears at an earlier
            point in the bitstream.
        """
        self._value_constructor = value_constructor
        
        self._flag_bitstream_value = ensure_bitstream_value(flag)
        self.flag_bitstream_value._notify_on_change(self)
        
        super(Maybe, self).__init__()
        
        # Trigger a change to create the initial value, if the flag is True.
        self._dependency_changed(self.flag_bitstream_value)
    
    def _dependency_changed(self, bitstream_value):
        if bitstream_value is self.flag_bitstream_value:
            # Create/remove an inner value if the flag has changed
            if self.flag:
                if self.inner_value is None:
                    inner_value = self._value_constructor()
                    self._validate(inner_value)
                    self._inner_value = inner_value
                    self._inner_value._notify_on_change(self)
                    self._changed()
            else:
                if self.inner_value is not None:
                    self._inner_value._cancel_notify_on_change(self)
                    self._inner_value = None
                    self._changed()
        else:
            self._changed()
    
    @property
    def flag(self):
        """
        The current visibility state of this value. See also
        :py:attr:`flag_bitstream_value`.
        """
        return safe_get_bool(self._flag_bitstream_value)
    
    @property
    def flag_bitstream_value(self):
        """
        The :py:class:`BitstreamValue` which determines if this
        :py:class:`Maybe` appears in the bitstream or not.
        """
        return self._flag_bitstream_value
    
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
        return "<{} {!r} flag={!r}>".format(
            self.__class__.__name__,
            self.inner_value,
            self.flag_bitstream_value,
        )
    
    def __str__(self):
        if self.flag:
            return str(self.inner_value)
        else:
            return ""


