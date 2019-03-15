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
    
    This class does not contain any useful implementation and instead simply
    defines the required API.
    """
    
    def __init__(self):
        self._offset = None
        self._bits_past_eof = None
    
    @property
    def value(self):
        """The value repersented by this object in a native Python type."""
        raise NotImplementedError()
    
    @property
    def length(self):
        """The number of bits used to represent this value in the bitstream."""
        raise NotImplementedError()
    
    @property
    def offset(self):
        """
        If this value has been seriallised/deseriallised, this will contain the
        offset into the stream where the first bit was read/written as a
        (bytes, bits) tuple (see :py:meth:`BitstreamReader.tell`). None
        otherwise.
        
        This value is set to None whenever :py:attr:`value` is chagned.
        """
        return self._offset
    
    @property
    def bits_past_eof(self):
        """
        If this value has been seriallised/deseriallised from a bitstream but
        all or part of the value was located past the end of the file (or past
        the end of a :py:class:`BoundedBlock`), gives the number of bits beyond
        the end which were read/written. Set to None otherwise.
        
        This value is set to None whenever :py:attr:`value` is chagned.
        """
        return self._bits_past_eof
    
    def read(self, reader):
        """
        Read and deserialise this value from the next bits read by the provided
        :py:class:`BitstreamReader`.
        
        Sets the :py:attr:`offset` and :py:attr:`bits_past_eof` parameters.
        """
        raise NotImplementedError()
    
    def write(self, writer):
        """
        Serialise and write this value to the provided
        :py:class:`BitstreamWriter`.
        
        Sets the :py:attr:`offset` and :py:attr:`bits_past_eof` parameters.
        """
        raise NotImplementedError()
    
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
            return "{}*".format(str(self.value))
        else:
            return str(self.value)

