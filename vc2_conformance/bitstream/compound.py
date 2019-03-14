"""
General-purpose compound BitstreamValue types.
"""

from vc2_conformance.bitstream import BitstreamValue

from vc2_conformance.bitstream._util import indent, concat_strings

from collections import Iterable

__all__ = [
    "Concatenation",
    "Maybe",
    "BoundedBlock",
    "LabelledConcatenation",
]


class Concatenation(BitstreamValue):
    r"""
    Composite value. A concatenation of a fixed set of
    :py:class:`BitstreamValue`\ s.
    
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
                "All concatenation components must be BitstreamValues.")
    
    @property
    def length(self):
        if any(v.length is None for v in self._value):
            return None
        else:
            return sum(v.length for v in self._value)
    
    @property
    def bits_past_eof(self):
        if any(v.bits_past_eof is None for v in self._value):
            return None
        else:
            return sum(v.bits_past_eof for v in self._value)
    
    def read(self, reader):
        self._offset = reader.tell()
        for v in self._value:
            v.read(reader)
    
    def write(self, writer):
        self._offset = writer.tell()
        for v in self._value:
            v.write(writer)
    
    def __getitem__(self, key):
        """Shorthand for ``concatenation.value[key]``"""
        return self._value[key]
    
    def __repr__(self):
        return "<{} {}>".format(
            self.__class__.__name__,
            " ".join(repr(v) for v in self._value)
        )
    
    def __str__(self):
        return concat_strings([str(v) for v in self.value])


class Maybe(BitstreamValue):
    r"""
    Composite value. An 'maybe' type for bitstream values which may sometimes
    be omitted.
    
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
    
    def __init__(self, value, flag_fn):
        """
        Parameters
        ==========
        value_value : :py:class:`BitstreamValue`
            The value which may (or may not) be included in the bitstream.
            Stored as :py:attr:`Maybe.value`.
        flag_fn : callable
            This function will be called with no arguments and should return
            True if :py:attr:`Maybe.value` is to be included in the bitstream
            and False otherwise.
            
            This function will generally be a simple computation based on a
            previously read or written :py:class:`BitstreamValue`. For example,
            it may be a lambda function which returns the
            :py:class:`BitstreamValue.value` of a :py:class:`Bool`.
        """
        self.flag_fn = flag_fn
        
        super(Maybe, self).__init__(value, length=None)
    
    def _validate(self, value, length):
        if not isinstance(value, BitstreamValue):
            raise ValueError(
                "Maybe.value must be BitstreamValues.")
    
    
    @property
    def flag(self):
        """
        True if :py:attr:`Maybe.value` should be included in the bitstream,
        False otherwise.
        """
        return bool(self.flag_fn())
    
    @property
    def length(self):
        if self.flag:
            return self.value.length
        else:
            return 0
    
    @property
    def bits_past_eof(self):
        if self.flag:
            return self.value.bits_past_eof
        else:
            return 0
    
    def read(self, reader):
        """
        Read the flag and maybe the value from the bitstream. If value is not
        present in the bitstream, :py:attr:`Option.value` will not be altered
        and should be considered undefined.
        """
        self._offset = reader.tell()
        
        if self.flag:
            self.value.read(reader)
    
    def write(self, writer):
        """
        Write the flag and maybe the value into the bitstream. If the flag
        indicates the value is to be omitted, the value in
        :py:attr:`Option.value` will not be touched and its state should be
        considered undefined.
        """
        self._offset = writer.tell()
        
        if self.flag:
            self.value.write(writer)
    
    def __repr__(self):
        return "<{} {!r} flag={}>".format(
            self.__class__.__name__,
            self.value,
            self.flag,
        )
    
    def __str__(self):
        if self.flag:
            return str(self.value)
        else:
            return ""


class BoundedBlock(BitstreamValue):
    """
    Composite value. A fixed-size bounded data-block as described in (A.4.2) which
    contains a :py:class:`BitstreamValue`.
    
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
    
    def __init__(self, value, length, pad_value=0):
        # NB: Set first so that repr will work later if the validator fails on
        # the main constructor.
        self._pad_value = pad_value
        
        super(BoundedBlock, self).__init__(value, length)
    
    def _validate(self, value, length):
        if not isinstance(value, BitstreamValue):
            raise ValueError(
                "BoundedBlock.value must be a BitstreamValue.")
    
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
        When this block was last serialised/deserialised, the number of unused
        bits left in the block. None otherwise.
        """
        if self.value.length is None:
            return None
        else:
            return max(0, self.length - self.value.length)
    
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
        
        self.value.read(bounded_reader)
        
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
        
        self.value.write(bounded_writer)
        
        self._bits_past_eof = bounded_writer.bits_past_eof
        
        # Write padding bits, as required
        for i in range(bounded_writer.bits_remaining-1, -1, -1):
            self._bits_past_eof += 1 - writer.write_bit((self._pad_value >> i) & 1)
    
    def __repr__(self):
        return "<{} value={!r} length={!r} pad_value={!r} unused_bits={!r}>".format(
            self.__class__.__name__,
            self.value,
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
        
        return concat_strings([str(self.value), padding])


class LabelledConcatenation(Concatenation):
    """
    Like :py:class:`Concatenation` except with labelled entries.
    
    In terms of its bitstream formatting/behaviour, this is identical to
    Concatenation. The principle difference are:
    
    * The ability to look-up values by name (not just index), e.g.
      ``concat["foo"]``
    * A richer str() representation with headings and labels.
    """
    
    def __init__(self, *names_values):
        """
        Parameters
        ==========
        names_values : (str, :py:class:`BitstreamValue`) or :py:class:`BitstreamValue` or str or None
            A series of entries to include in this concatenation.

            * If a (str, :py:class:`BitstreamValue`) tuple, this gives a value
              and its corresponding label string (which must be unique).
            
            * If just a :py:class:`BitstreamValue`, this gives a value to include
              without a label.
            
            * If a string, this specifies a heading to include in the ``str()``
              representation. Also increases the indent level for all following
              values in the string.
            
            * If None, reduces the indentation level for all following levels in
              the ``str`` representation..
        """
        self._names_values = names_values
        
        super(LabelledConcatenation, self).__init__(
            *self._names_values_to_values(names_values))
    
    def _names_values_to_values(self, names_values):
        """
        Internal method. Extract just the list of :py:class:`BitstreamValue`
        from a names and values list.
        """
        return tuple(
            nv if isinstance(nv, BitstreamValue) else nv[1]
            for nv in names_values
            if nv is not None and not isinstance(nv, str)
        )
    
    @property
    def value(self):
        """The values in the concatenation (see constructor arguments)."""
        return self._names_values
    
    @value.setter
    def value(self, names_values):
        value = self._names_values_to_values(values)
        self._validate(value, self.length)
        
        self._value = value
        self._names_values = _names_values
    
    def __getitem__(self, key):
        r"""
        Get a :py:class:`BitstreamValue` by either index or name.
        
        If an (numerical) index is given, this will be looked up according to
        the order the :py:class:`BitstreamValue`\ s appear in the bitstream. If
        a (string) name is given, the value with the specified name will be
        returned.
        """
        if isinstance(key, str):
            # Get by name
            for nv in self._names_values:
                if nv is None:
                    continue  # An empty line
                elif isinstance(nv, str):
                    continue  # A heading
                elif isinstance(nv, BitstreamValue):
                    continue  # An unlabelled value
                else:
                    name, value = nv
                    if name == key:
                        return value
            raise KeyError(key)
        else:
            # Get by index
            return self._value[key]
    
    def __repr__(self):
        return "<{} {}>".format(
            self.__class__.__name__,
            " ".join(
                (
                    repr(nv)
                    if isinstance(nv, BitstreamValue) else
                    "{}={!r}".format(nv[0], nv[1])
                )
                for nv in self._names_values
                if nv is not None and not isinstance(nv, str)
            )
        )
    
    def __str__(self):
        body = []
        
        space = "  "
        
        indent_level = 0
        for nv in self._names_values:
            if nv is None:
                indent_level = max(0, indent_level - 1)
            elif isinstance(nv, str):
                body.append(indent(nv, space*indent_level))
                indent_level += 1
            elif isinstance(nv, BitstreamValue):
                string = str(nv)
                if string:
                    body.append(indent(string, space*indent_level))
            else:
                name, value = nv
                string = str(value)
                if string:
                    string = "{}: {}".format(name, string)
                    body.append(indent(string, space*indent_level))
        
        return "\n".join(body)
