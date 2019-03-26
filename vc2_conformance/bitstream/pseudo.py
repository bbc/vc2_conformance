r"""
Pseudo :py:class:`BitstreamValue` classes which don't represent values in the
bitstream but instead represent in-memory values or functions on existing
bitstream values.

These classes are not directly useful for defining bitstreams but may be useful
as control parameters for other bitstream components. For example, a
:py:class:`FunctionValue` may be used to provide a flag
for a :py:class:`Maybe` element which depends on some complex function of other
:py:class:`BitstreamValue`\ s.
"""

from vc2_conformance.bitstream import BitstreamValue


__all__ = [
    "PseudoValue",
    "ConstantValue",
    "ensure_bitstream_value",
    "FunctionValue",
]


class PseudoValue(BitstreamValue):
    """
    A :py:class:`BitstreamValue` with no serialised/deserialised form.
    """
    
    @property
    def length(self):
        return 0
    
    def read(self, reader):
        self._offset = reader.tell()
        self._bits_past_eof = 0
    
    def write(self, writer):
        self._offset = writer.tell()
        self._bits_past_eof = 0
    
    def __repr__(self):
        return "<{} value={}>".format(
            self.__class__.__name__,
            self.value,
        )


class ConstantValue(PseudoValue):
    """
    A :py:class:`BitstreamValue` which holds a constant value (or throws an
    exception on access) and which does not form part of the
    serialised/deserialised bitstream.
    
    Useful only in situations where a :py:class:`BitstreamValue` is required
    with a constant value.
    """
    
    def __init__(self, value=None, exception=None):
        self._value = value
        self._exception = exception
        super(ConstantValue, self).__init__()
    
    @property
    def value(self):
        if self._exception is None:
            return self._value
        else:
            raise self._exception
    
    @value.setter
    def value(self, value):
        self._value = value
        self._exception = None
        self._changed()
    
    @property
    def exception(self):
        return self._exception
    
    @exception.setter
    def exception(self, exception):
        self._value = None
        self._exception = exception
        self._changed()
    


def ensure_bitstream_value(value):
    """
    Ensure that the provided object is a :py:class:`BitstreamValue`, wrapping
    it in a :py:class:`ConstantValue` if it is not.
    """
    if isinstance(value, BitstreamValue):
        return value
    else:
        return ConstantValue(value)


class FunctionValue(PseudoValue):
    r"""
    A read-only :py:class:`BitstreamValue` whose value is a function of a
    number of other :py:class:`BitstreamValue`\ s.
    
    If the function raises an exception, that exception will be caught and
    raised whenever the value is accessed.
    
    Has no serialised/deserialised form (i.e. reads/writes 0 bits).
    """
    
    def __init__(self, fn, *arg_values):
        self._fn = fn
        self._arg_values = [ensure_bitstream_value(v) for v in arg_values]
        
        for value in self._arg_values:
            value._notify_on_change(self)
        
        super(FunctionValue, self).__init__()
        
        # Evaluate initial value/exception
        self._dependency_changed(None)
    
    @property
    def value(self):
        if self._exception is None:
            return self._value
        else:
            raise self._exception
    
    def _dependency_changed(self, _):
        try:
            self._value = self._fn(*self._arg_values)
            self._exception = None
        except Exception as e:
            self._value = None
            self._exception = e
        self._changed()
