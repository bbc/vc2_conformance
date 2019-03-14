"""
Base class definition for :py:class:`BitstreamValue`, the generic interface
implemented by all bitstream interfaces.
"""

__all__ = [
    "BitstreamValue",
]

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
    
    def __str__(self):
        """
        The string representation used for human-readable representations of a
        value. By convention values which contain any bits past the EOF (or end
        of a bounded block) are shown with an asterisk afterwards.
        """
        if self.bits_past_eof:
            return "{!r}*".format(self.value)
        else:
            return str(self.value)

