"""
:py:mod:`vc2_conformance.io`: (A) VC-2 Data Coding Definitions
==============================================================
"""

from vc2_conformance.metadata import ref_pseudocode

from vc2_conformance.decoder.exceptions import UnexpectedEndOfStream


@ref_pseudocode(deviation="inferred_implementation")
def init_io(state, f):
    """
    (A.2.1) Initialise the io-related variables in state.
    
    This function should be called to initialise the IO-related parts of the
    state dictionary to their initial state as specified by (A.2.1):
    
        ... a decoder is deemed to maintain a copy of the current byte,
        state[current_byte], and an index to the next bit (in the byte) to be
        read, state[next_bit] ...
    
    Parameters
    ----------
    state : :py:class:`~vc2_conformance.state.State`
        The state dictionary to be initialised.
    f : file-like object
        The file to read the bitstream from.
    """
    state["_file"] = f
    read_byte(state)


@ref_pseudocode(deviation="inferred_implementation")
def read_byte(state):
    """
    (A.2.2) Load the next byte in the stream into the global state, ready for
    the bits to be read.
    
    By convention, when the end-of-file is reached, ``state["current_byte"]``
    is set to ``None``. This condition must be checked before every read
    operation.
    """
    # Step 1.
    state["next_bit"] = 7
    
    # Step 2.
    byte = state["_file"].read(1)
    if len(byte) == 1:
        state["current_byte"] = bytearray(byte)[0]  # Convert byte to int
    else:
        # End of file
        state["current_byte"] = None


@ref_pseudocode
def read_bit(state):
    """(A.2.3)"""
    ## Begin not in spec
    # From (A.2.1):
    #
    #     ... a decoder is deemed  to maintain a copy of the current byte,
    #     state[current_byte] ...
    #
    # As such, if there is no 'current_byte' when we come to read, we've
    # reached a situation not defined by the specification.
    if state["current_byte"] is None:
        raise UnexpectedEndOfStream()
    ## End not in spec
    
    bit = (state["current_byte"] >> state["next_bit"])&1
    state["next_bit"] -= 1
    if state["next_bit"] < 0:
        state["next_bit"] = 7
        read_byte(state)
    return bit


@ref_pseudocode
def byte_align(state):
    """(A.2.4)"""
    # NB: No check for end-of-stream is required here. If we're at the end of
    # the stream, we'll be on a byte boundary so this is a no-op. If we're not
    # at the end of the stream, we can always read until the end of the current
    # byte, even if it is the last in the stream.
    if state["next_bit"] != 7:
        read_byte(state)


@ref_pseudocode
def read_bool(state):
    """(A.3.2)"""
    if read_bit(state) == 1:
        return True
    else:
        return False

@ref_pseudocode
def read_nbits(state, n):
    """(A.3.3)"""
    val = 0
    for i in range(0, n):
        val <<= 1
        val += read_bit(state)
    return val

@ref_pseudocode
def read_uint_lit(state, n):
    """(A.3.4)"""
    return read_nbits(state, 8*n)


@ref_pseudocode
def read_bitb(state):
    """(A.4.2)"""
    if state["bits_left"] == 0:
        return 1
    else:
        state["bits_left"] -= 1
        return read_bit(state)


@ref_pseudocode
def read_boolb(state):
    """(A.4.2)"""
    if read_bitb(state) == 1:
        return True
    else:
        return False


@ref_pseudocode
def flush_inputb(state):
    """(A.4.2)"""
    while state["bits_left"] > 0:
        read_bit(state)
        state["bits_left"] -= 1


@ref_pseudocode
def read_uint(state):
    """(A.4.3)"""
    value = 1
    while read_bit(state) == 0:
        value <<= 1
        if read_bit(state) == 1:
            value += 1
    value -= 1
    return value


@ref_pseudocode
def read_uintb(state):
    """(A.4.3)"""
    value = 1
    while read_bitb(state) == 0:
        value <<= 1
        if read_bitb(state):
            value += 1
    value -= 1
    return value


@ref_pseudocode
def read_sint(state):
    """(A.4.4)"""
    value = read_uint(state)
    if value != 0:
        if read_bit(state) == 1:
            value = -value
    return value


@ref_pseudocode
def read_sintb(state):
    """(A.4.4)"""
    value = read_uintb(state)
    if value != 0:
        if read_bitb(state) == 1:
            value = -value
    return value
