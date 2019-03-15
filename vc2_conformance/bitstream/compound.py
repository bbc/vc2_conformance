"""
General-purpose compound BitstreamValue types.
"""

from vc2_conformance.bitstream import BitstreamValue

from vc2_conformance.bitstream._util import indent, concat_strings

from enum import Enum


__all__ = [
    "Concatenation",
    "LabelledConcatenation",
    "WrapperValue",
    "Maybe",
    "BoundedBlock",
]


class Concatenation(BitstreamValue):
    r"""
    Compound value. A concatenation of a tuple of :py:class:`BitstreamValue`\
    s.
    
    The contained :py:class:`BitstreamValue` objects can be accessed either
    using :py:attr:`value` (as usual) or by indexing into this object. That is,
    the following are equivalent::
    
        c = Concatenation(b1, b2, b3)
        asssert c.value[0] is b1
        asssert c.value[1] is b2
        asssert c.value[2] is b3
        
        c = Concatenation(b1, b2, b3)
        asssert c[0] is b1
        asssert c[1] is b2
        asssert c[2] is b3
    
    In practice, :py:class:`LabelledConcatenation` may be preferable to this
    basic class.
    """
    
    def __init__(self, *values):
        """
        Parameters
        ==========
        values : :py:class:`BitstreamValue`
            The bitstream values to be concatenated (in order).
        """
        self._value = values
        super(Concatenation, self).__init__()
        
        # NB: Validation is done last, so that internal members are populated
        # allowing __repr__ work (which may be printed in tracebacks).
        self._validate(self._value)
    
    def _validate(self, value):
        if not isinstance(value, tuple):
            raise ValueError(
                "Concatenation expects a tuple of BitstreamValues.")
        if not all(isinstance(v, BitstreamValue) for v in value):
            raise ValueError(
                "All concatenation components must be BitstreamValues.")
    
    @property
    def value(self):
        r"""
        A tuple of :py:class:`BitstreamValue`\ s contained by this
        :py:class:`Concatenation`.
        """
        return self._value
    
    @value.setter
    def value(self, value):
        self._validate(value)
        self._value = value
    
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
        value = self._names_values_to_values(names_values)
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


class WrapperValue(BitstreamValue):
    r"""
    A WrapperValue is a base class for implementing :py:class:`BitstreamValue`\
    s which wrap another, single :py:class:`BitstreamValue`.
    """
    
    def __init__(self, value):
        self._value = value
        super(WrapperValue, self).__init__()
        self._validate(self._value)
    
    def _validate(self, value):
        if not isinstance(value, BitstreamValue):
            raise ValueError(
                "{}.value must be a BitstreamValue.".format(
                    self.__class__.__name__))
    
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, value):
        self._validate(value)
        self._value = value




class Maybe(WrapperValue):
    r"""
    Compound value. An 'maybe' type for bitstream values which may sometimes
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
    
    def __init__(self, value, flag):
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
        super(Maybe, self).__init__(value)
    
    @property
    def flag(self):
        """
        The current visibility state of this value. If True, :py:attr:`value`
        will be included in the bitstream, if False it will be omitted.
        
        This value may be set with either a bool or a function (see the
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


class BoundedBlock(WrapperValue):
    """
    Compound value. A fixed-size bounded data-block as described in (A.4.2) which
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
        """
        Parameters
        ==========
        value : :py:class:`BoundedBlock`
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
        
        super(BoundedBlock, self).__init__(value)
    
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


