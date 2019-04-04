"""
Bitstream interfaces implementing low-level primitive types.

The primitive types are used as the basis of all other values and translate
between bit-encoding and Python datatypes. By default these primitives express
their values using an appropriate Python primitive data type (e.g. bool or int)
and to represent them in ``str()`` representations using their native string
formatting. This can be overridden, for example to allow :py:class:`Enum`
values to be used or hexidecimal representations to be shown.
"""

from vc2_conformance.bitstream import BitstreamValue, ensure_bitstream_value

from vc2_conformance.bitstream._integer_io import (
    read_bits,
    write_bits,
    exp_golomb_length,
    read_exp_golomb,
    write_signed_exp_golomb,
    signed_exp_golomb_length,
    read_signed_exp_golomb,
    write_exp_golomb,
)


__all__ = [
    "PrimitiveValue",
    "Bool",
    "NBits",
    "ByteAlign",
    "UInt",
    "SInt",
]


class PrimitiveValue(BitstreamValue):
    """
    Base class for primitive datatypes.
    """
    
    def __init__(self, value,
                 formatter=str,
                 cast_to_primitive=None,
                 cast_from_primitive=None,
                 get_value_name=None,
                 enum=None):
        r"""
        Parameters
        ==========
        value
            The initial value for the bitstream entry.
        formatter : function(value) -> string
            When the underlying primitive value is being converted to a string,
            this function will be used to perform the conversion.
            
            For example, it might be used to format the value as a hexidecimal
            number (see, for example, :py:class:`Hex`).
        cast_to_primitive : None or function(value) -> primitive
            If a function is provided, this function will be used to cast any
            new value assigned to :py:attr:`PrimitiveValue.value` into a
            primitive type (e.g. a bool or integer) suitable for encoding in
            the bitstream. If the function raises a :py:exc:`ValueError`, or if
            this argument is None, no conversion will take place and the
            user-provided value will be used as-is.
            
            This argument may be used to allow users to assign :py:class:`Enum`
            values. In this case, cast_to_primitive argument might be a lambda
            function ``lambda v: MyEnum(v).value``. This function will convert
            any provided ``MyEnum`` value into its corresponding value, or
            raise a :py:exc:`ValueError` if the value is not a valid ``MyEnum``
            value (in which case that value will be kept as-is).
        cast_from_primitive : None or function(primitive) -> value
            If a function is provided, when a user accesses the
            :py:attr:`PrimitiveValue.value` property, the underlying primitive
            value will first be casted as defined by this function. If a
            :py:exc:`ValueError` is thrown, or this argument is None, the
            original value will be returned.
            
            Continuing the example given for ``cast_to_primitive`` of allowing
            :py:class:`Enum` values to be passed as
            :py:attr:`PrimitiveValue.value`\ s, ``cast_from_primitive`` can be
            used to make :py:attr:`PrimitiveValue.value` read as an
            enumeration value when possible, or just the primitive otherwise.
            In this case, providing the ``MyEnum`` class will suffice since
            when called with a primitive value it will 'return' an enumeration
            value. If the primitive value is not a member of the enumeration,
            the constructor will instead throw a :py:exc:`ValueError` and the
            primitive value will be exposed directly.
        get_value_name : None or function(primitive) -> str
            If a function is provided, it will be used when generating a
            ``str()`` representation of this value to produce a human-friendly
            representation of the primitive value. If this function returns a
            value, it will be displayed alongside the ``formatter`` formatted
            primtive value (which will be shown in brackets). If a
            :py:exc:`ValueError` is raised, or this function is not provided
            only the primitive value will be shown.
            
            Continuing the example of ``cast_to_primitive`` and
            ``cast_from_primitive``, this argument might be set to a lambda
            function: ``lambda p: MyEnum(p).name``. This function will return
            the human-friendly enumeration name if possible or raise a
            :py:exc:`ValueError` when values outside of the enumeration have
            been used causing only the primitive value to be displayed.
        enum : None or :py:class:`Enum`
            A convenience argument which, if set to a :py:class:`Enum`
            subclass, sets ``cast_to_primitive``, ``cast_from_primitive`` and
            ``get_value_name`` as described in the examples above.
            
            If both this argument and any of the cast_to_primitive,
            cast_from_primitive and get_value_name arguments are given
            simultaneously, 'enum' will be overridden.
        """
        super(PrimitiveValue, self).__init__()
        
        self._formatter = formatter
        
        if enum is not None:
            cast_to_primitive = cast_to_primitive or (lambda v: enum(v).value)
            cast_from_primitive = cast_from_primitive or enum
            get_value_name = get_value_name or (lambda p: enum(p).name)
        
        self._cast_to_primitive = cast_to_primitive
        self._cast_from_primitive = cast_from_primitive
        self._get_value_name = get_value_name
        
        # Set the value via its property to ensure value conversion takes
        # place.
        self.value = value
    
    @property
    def value(self):
        if self._cast_from_primitive is not None:
            try:
                return self._cast_from_primitive(self._value)
            except ValueError:
                return self._value
        else:
            return self._value
    
    @value.setter
    def value(self, value):
        if self._cast_to_primitive is not None:
            try:
                value = self._cast_to_primitive(value)
            except ValueError:
                pass
        
        self._value = value
        self._offset = None
        self._bits_past_eof = None
        
        self._changed()
    
    def __str__(self):
        if self.bits_past_eof:
            primitive_str = "{}*".format(self._formatter(self._value))
        else:
            primitive_str = self._formatter(self._value)
        
        if self._get_value_name is not None:
            try:
                return "{} ({})".format(
                    self._get_value_name(self._value),
                    primitive_str,
                )
            except ValueError:
                return primitive_str
        else:
            return primitive_str



class Bool(PrimitiveValue):
    """A boolean value, as per read_bool (A.3.2)"""
    
    def __init__(self, value=False, *args, **kwargs):
        super(Bool, self).__init__(value, *args, **kwargs)
    
    @property
    def length(self):
        return 1
    
    def read(self, reader):
        self._offset = reader.tell()
        bit = reader.read_bit()
        self._value = bool(bit) if bit is not None else True
        self._bits_past_eof = int(bit is None)
        self._changed()
    
    def write(self, writer):
        self._offset = writer.tell()
        self._bits_past_eof = 1 - writer.write_bit(self.value)


class NBits(PrimitiveValue):
    """A fixed-width unsigned integer, as per read_nbits (A.3.3)"""
    
    def __init__(self, value=0, length=0, *args, **kwargs):
        """
        length : int or :py:class:`BitstreamValue`
            The length of this value (in bits). May be an constant or a
            :py:class:`BitstreamValue`.
        """
        self._length_bitstream_value = ensure_bitstream_value(length)
        self._length_bitstream_value._notify_on_change(self)
        
        super(NBits, self).__init__(value, *args, **kwargs)
    
    def _dependency_changed(self, _):
        self._changed()
    
    @property
    def length(self):
        return self._length_bitstream_value.value
    
    @property
    def length_bitstream_value(self):
        return self._length_bitstream_value
    
    def read(self, reader):
        self._offset = reader.tell()
        
        self._value, self._bits_past_eof = read_bits(reader, self.length)
        self._changed()
    
    def write(self, writer):
        self._offset = writer.tell()

        if self._value < 0 or self._value.bit_length() > self.length:
            raise ValueError("{}-bit NBits cannot represent {}".format(
                self.length, self._value
            ))

        self._bits_past_eof = write_bits(writer, self.length, self._value)

class ByteAlign(PrimitiveValue):
    """
    Align to the next whole-byte boundary, as per byte_align (A.2.4).
    
    The :py:attr:`value` field holds the bits to use when padding. The
    least-significant bits will be used.
    
    The :py:attr:`length` field is read-only for this type and is None unless
    this value has been serialised or deserialised.
    """
    
    def __init__(self, value=0):
        self._length = None
        super(ByteAlign, self).__init__(value)
    
    @property
    def length(self):
        return self._length
    
    def read(self, reader):
        self._offset = reader.tell()
        
        # Advance to next byte, if required
        if self.offset[1] != 7:
            self._length = self.offset[1] + 1
        else:
            self._length = 0
        
        self._value, self._bits_past_eof = read_bits(reader, self.length)
        self._changed()
    
    def write(self, writer):
        self._offset = writer.tell()
        
        # Advance to next byte, if required
        if self.offset[1] != 7:
            self._length = self.offset[1] + 1
        else:
            self._length = 0
        
        self._bits_past_eof = write_bits(writer, self._length, self._value)
        
        # NB: Writing may change this value
        self._changed()
    
    def __str__(self):
        if self.length:
            bits = self.value
            bits &= (1 << self.length) - 1
            return "<padding 0b{:0{}b}>".format(bits, self.length)
        else:
            return ""


class UInt(PrimitiveValue):
    """
    A variable length (modified exp-Golomb) unsigned integer, as per read_uint
    (A.4.3)
    """
    
    def __init__(self, value=0, *args, **kwargs):
        super(UInt, self).__init__(value, *args, **kwargs)
    
    @property
    def length(self):
        return exp_golomb_length(self._value)
    
    def read(self, reader):
        self._offset = reader.tell()
        self._value, self._bits_past_eof = read_exp_golomb(reader)
        self._changed()
    
    def write(self, writer):
        self._offset = writer.tell()
        
        if self._value < 0:
            raise ValueError(
                "UInt cannot represent negative value {}".format(self._value))
        
        self._bits_past_eof = write_exp_golomb(writer, self._value)

class SInt(PrimitiveValue):
    """
    A variable length (modified exp-Golomb) signed integer, as per read_sint
    (A.4.4)
    """
    
    def __init__(self, value=0, *args, **kwargs):
        super(SInt, self).__init__(value, *args, **kwargs)
    
    @property
    def length(self):
        return signed_exp_golomb_length(self._value)
    
    def read(self, reader):
        self._offset = reader.tell()
        self._value, self._bits_past_eof = read_signed_exp_golomb(reader)
        self._changed()
    
    def write(self, writer):
        self._offset = writer.tell()
        self._bits_past_eof = write_signed_exp_golomb(writer, self._value)
