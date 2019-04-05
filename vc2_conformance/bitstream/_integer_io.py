r"""
A series of functions which perform simple integer low-level IO operations such
as reading and writing fixed- and variable length integers from
:py:class:`BitstreamReader`\ s and :py:class:`BitstreamWriter`\ s.
"""

from bitarray import bitarray


class OutOfRangeError(ValueError):
    """
    An exception thrown whenever an out-of-range value is passed to a bitstream
    writing function.
    """


def read_bits(reader, bits):
    """
    Read 'bits' bits from a :py:class:`BitstreamReader`, like read_nbits
    (A.3.3) returning the value as a python integer.
    """
    value = 0
    for i in range(bits):
        bit = reader.read_bit()
        value <<= 1
        value |= bit if bit is not None else 1
    
    return value

def write_bits(writer, bits, value):
    """
    Write the 'bits' lowest-rder bits of 'value' into a
    :py:class:`BitstreamWriter`. The inverse of read_nbits
    (A.3.3).
    
    Throws an :py:exc:`OutOfRangeError` if the value is too large to fit in the
    requested number of bits.
    """
    if value < 0 or value.bit_length() > bits:
        raise OutOfRangeError(value)
    
    for i in range(bits-1, -1, -1):
        writer.write_bit((value >> i) & 1)

def read_bitarray(reader, bits):
    """
    Read 'bits' bits from a :py:class:`BitstreamReader` returning the value as
    a :py:class:`bitarray.bitarray`.
    """
    value = bitarray()
        
    for i in range(bits):
        bit = reader.read_bit()
        value.append(bit if bit is not None else 1)
    
    return value

def write_bitarray(writer, bits, value):
    """
    Write the 'bits' from the :py;class:`bitarray.bitarray` 'value' into a
    :py:class:`BitstreamWriter`.
    
    Throws an :py:exc:`OutOfRangeError` if the value has the wrong length.
    """
    if len(value) != bits:
        raise OutOfRangeError(value)
    
    for bit in value:
        writer.write_bit(bit)

def read_bytes(reader, num_bytes):
    """
    Read a number of bytes from a :py:class:`BitstreamReader`, returning a
    :py:class:`bytes` string.
    """
    return bytes(
        read_bits(reader, 8)
        for _ in range(num_bytes)
    )

def write_bytes(writer, num_bytes, value):
    """
    Write the provided :py:class:`bytes` or :py:class:`bytearray` in a python
    bytestring using a :py:class:`BitstreamWriter`.
    
    If the provided byte string is the wrong length an
    :py:exc:`OutOfRangeError` will be raised.
    """
    if len(value) != num_bytes:
        raise OutOfRangeError(value)
    
    for byte in bytearray(value):
        write_bits(writer, 8, byte)

def exp_golomb_length(value):
    """
    Return the length (in bits) of the unsigned exp-golomb representation of
    value.
    
    An :py:exc:`OutOfRangeError` will be raised if a negative value is
    provided.
    """
    if value < 0:
        raise OutOfRangeError(value)
    
    return (((value + 1).bit_length() - 1) * 2) + 1

def read_exp_golomb(reader):
    """
    Read an unsigned exp-golomb code from :py:class:`BitstreamReader`, like
    read_uint (A.4.3) and return an integer.
    """
    value = 1
    while True:
        bit = reader.read_bit()
        bit_value = bit if bit is not None else 1
        
        if bit_value == 1:
            break
        else:
            value <<= 1
            
            bit = reader.read_bit()
            value += bit if bit is not None else 1
    
    value -= 1
    
    return value


def write_exp_golomb(writer, value):
    """
    Write an unsigned exp-golomb code to a :py:class:`BitstreamWriter`, like
    read_uint (A.4.3) in reverse.
    
    An :py:exc:`OutOfRangeError` will be raised if a negative value is
    provided.
    """
    if value < 0:
        raise OutOfRangeError(value)
    
    value += 1
    
    for i in range(value.bit_length()-2, -1, -1):
        writer.write_bit(0)
        writer.write_bit((value >> i) & 1)

    writer.write_bit(1)


def signed_exp_golomb_length(value):
    """
    Return the length (in bits) of the signed exp-golomb representation of
    value.
    """
    length = exp_golomb_length(abs(value))
    if value != 0:
        length += 1
    return length


def read_signed_exp_golomb(reader):
    """
    Signed version of :py:class:`read_exp_golomb``, like read_sint (A.4.4).
    """
    value = read_exp_golomb(reader)
    
    # Read sign bit
    if value != 0:
        bit = reader.read_bit()
        if bit is None or bit == 1:
            value = -value
    
    return value


def write_signed_exp_golomb(writer, value):
    """
    Signed version of :py:class:`write_exp_golomb``, like read_sint (A.4.4) in
    reverse.
    """
    write_exp_golomb(writer, abs(value))
    
    # Write sign bit
    if value != 0:
        writer.write_bit(value < 0)


