"""
Bitstream interfaces implementing low-level primitive types.
"""

from vc2_conformance.bitstream import BitstreamValue


__all__ = [
    "Bool",
    "NBits",
    "ByteAlign",
    "UInt",
    "SInt",
]


class Bool(BitstreamValue):
    """A boolean value, as per read_bool (A.3.2)"""
    
    def __init__(self, value=False, formatter=str):
        super(Bool, self).__init__(value, 1, formatter)
    
    def read(self, reader):
        self._offset = reader.tell()
        bit = reader.read_bit()
        self._value = bool(bit) if bit is not None else True
        self._bits_past_eof = int(bit is None)
    
    def write(self, writer):
        self._offset = writer.tell()
        self._bits_past_eof = 1 - writer.write_bit(self.value)


class NBits(BitstreamValue):
    """A fixed-width unsigned integer, as per read_nbits (A.3.3)"""
    
    def __init__(self, value=0, length=0, formatter=str):
        super(NBits, self).__init__(value, length, formatter)
    
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

        self._bits_past_eof = 0
        for i in range(self.length-1, -1, -1):
            self._bits_past_eof += 1 - writer.write_bit((self.value >> i) & 1)

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
    
    @property
    def formatter(self):
        raise NotImplementedError("ByteAlign does not have a formatter.")
    
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
    
    def __str__(self):
        if self.length:
            bits = self.value
            bits &= (1 << self.length) - 1
            return "<padding 0b{:0{}b}>".format(bits, self.length)
        else:
            return ""


class UInt(BitstreamValue):
    """
    A variable length (modified exp-Golomb) unsigned integer, as per read_uint
    (A.4.3)
    """
    
    def __init__(self, value=0, formatter=str):
        super(UInt, self).__init__(value, None, formatter)
    
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
        
        self._bits_past_eof = 0
        for i in range(value.bit_length()-2, -1, -1):
            self._bits_past_eof += 1 - writer.write_bit(0)
            self._bits_past_eof += 1 - writer.write_bit((value >> i) & 1)

        self._bits_past_eof += 1 - writer.write_bit(1)


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
            self._bits_past_eof += 1 - writer.write_bit(orig_value < 0)
        
        self._value = orig_value
