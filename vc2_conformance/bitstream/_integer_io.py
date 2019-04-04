r"""
A series of functions which perform simple integer low-level IO operations such
as reading and writing fixed- and variable length integers from
:py:class:`BitstreamReader`\ s and :py:class:`BitstreamWriter`\ s.
"""

def read_bits(reader, bits):
    """
    Read 'bits' bits from a :py:class:`BitstreamReader`, like read_nbits
    (A.3.3) and return a tuple (value, bits_past_eof).
    """
    value = 0
    bits_past_eof = 0
    for i in range(bits):
        bit = reader.read_bit()
        value <<= 1
        value |= bit if bit is not None else 1
        bits_past_eof += int(bit is None)
    
    return (value, bits_past_eof)

def write_bits(writer, bits, value):
    """
    Write the 'bits' lowest-rder bits of 'value' into a
    :py:class:`BitstreamWriter`. The inverse of read_nbits
    (A.3.3). Return 'bits_past_eof'.
    """
    bits_past_eof = 0
    for i in range(bits-1, -1, -1):
        bits_past_eof += 1 - writer.write_bit((value >> i) & 1)
    
    return bits_past_eof

def read_bytes(reader, num_bytes):
    """
    Read a number of bytes from a :py:class:`BitstreamReader`, returning a
    (:py:class:`bytes`, bits_past_eof) tuple.
    """
    values = []
    bits_past_eof = 0
    for _ in range(num_bytes):
        value, this_bits_past_eof = read_bits(reader, 8)
        values.append(value)
        bits_past_eof += this_bits_past_eof
    
    return (bytes(values), bits_past_eof)

def write_bytes(writer, num_bytes, value):
    """
    Write the provided :py:class:`bytes` or :py:class:`bytearray` in a python
    bytestring using a :py:class:`BitstreamWriter`, returning the number of
    bits written past the end-of-file.
    
    If the provided byte string is the wrong length it will be left-padded with
    null bytes or truncated, discarding left-most values. This behaviour is
    intended to be consistent with the behaviour of read_bits.
    """
    if num_bytes != 0:
        value = value[-num_bytes:].rjust(num_bytes, b"\x00")
    else:
        # Special case required because value[-0:] doesn't do the right
        # thing...
        value = b""
    return sum(
        write_bits(writer, 8, byte)
        for byte in bytearray(value)
    )

def exp_golomb_length(value):
    """
    Return the length (in bits) of the unsigned exp-golomb representation of
    value.
    """
    return (((value + 1).bit_length() - 1) * 2) + 1

def read_exp_golomb(reader):
    """
    Read an unsigned exp-golomb code from :py:class:`BitstreamReader`, like
    read_uint (A.4.3) and return a tuple (value, bits_past_eof).
    """
    value = 1
    bits_past_eof = 0
    while True:
        bit = reader.read_bit()
        bit_value = bit if bit is not None else 1
        bits_past_eof += int(bit is None)
        
        if bit_value == 1:
            break
        else:
            value <<= 1
            
            bit = reader.read_bit()
            bits_past_eof += int(bit is None)
            value += bit if bit is not None else 1
    
    value -= 1
    
    return (value, bits_past_eof)


def write_exp_golomb(writer, value):
    """
    Write an unsigned exp-golomb code to a :py:class:`BitstreamWriter`, like
    read_uint (A.4.3) in reverse. Return  bits_past_eof.
    """
    value += 1
    
    bits_past_eof = 0
    for i in range(value.bit_length()-2, -1, -1):
        bits_past_eof += 1 - writer.write_bit(0)
        bits_past_eof += 1 - writer.write_bit((value >> i) & 1)

    bits_past_eof += 1 - writer.write_bit(1)
    
    return bits_past_eof


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
    value, bits_past_eof = read_exp_golomb(reader)
    
    # Read sign bit
    if value != 0:
        bit = reader.read_bit()
        bits_past_eof += int(bit is None)
        if bit is None or bit == 1:
            value = -value
    
    return value, bits_past_eof


def write_signed_exp_golomb(writer, value):
    """
    Signed version of :py:class:`write_exp_golomb``, like read_sint (A.4.4) in
    reverse.
    """
    bits_past_eof = write_exp_golomb(writer, abs(value))
    
    # Write sign bit
    if value != 0:
        bits_past_eof += 1 - writer.write_bit(value < 0)
    
    return bits_past_eof


