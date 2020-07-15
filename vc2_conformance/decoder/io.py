"""
The :py:mod:`vc2_conformance.io` module implements I/O functions for reading
bitstreams from file-like objects. The exposed functions implement the
interface specified in annex (A).


Initialisation
--------------

The :py:func:`init_io` function must be used to initialise a
:py:class:`~vc2_conformance.pseudocode.state.State` dictionary so that it is
ready to read a bitstream.

.. autofunction:: init_io


Determining stream position
---------------------------

The :py:func:`tell` function (below) is used by verification logic to report
and check offsets of values within a bitstream. For example, it may be used to
check ``next_parse_offset`` fields are correct (see
:py:func:`vc2_conformance.decoder.stream.parse_info`).

.. autofunction:: tell


Bitstream recording
-------------------

The VC-2 specification sometimes requires that the coded bitstream
representation of a particular set of repeated fields is consistent within a
bitstream (e.g. see
:py:func:`vc2_conformance.decoder.sequence_header.sequence_header`). To
facilitate this test, the :py:func:`record_bitstream_start` and
:py:func:`record_bitstream_finish` functions may be used to capture the
bitstream bytes read within part of the bitstream.

.. autofunction:: record_bitstream_start

.. autofunction:: record_bitstream_finish


"""

from vc2_conformance.pseudocode.metadata import ref_pseudocode

from vc2_conformance.decoder.exceptions import UnexpectedEndOfStream

__all__ = [
    "init_io",
    "record_bitstream_start",
    "record_bitstream_finish",
    "tell",
    "read_byte",
    "is_end_of_stream",
    "read_bit",
    "byte_align",
    "read_bool",
    "read_nbits",
    "read_uint_lit",
    "read_bitb",
    "read_boolb",
    "flush_inputb",
    "read_uint",
    "read_uintb",
    "read_sint",
    "read_sintb",
]


@ref_pseudocode(deviation="inferred_implementation")
def init_io(state, f):
    """
    (A.2.1) Initialise the I/O-related variables in state.

    This function should be called exactly once to initialise the I/O-related
    parts of the state dictionary to their initial state as specified by
    (A.2.1):

        ... a decoder is deemed to maintain a copy of the current byte,
        state[current_byte], and an index to the next bit (in the byte) to be
        read, state[next_bit] ...

    As well as initialising the state["current_byte"] and state["next_bit"]
    fields, this sets the (out-of-spec) state["_file"] entry to the provided
    file-like object.

    Parameters
    ----------
    state : :py:class:`~vc2_conformance.pseudocode.state.State`
        The state dictionary to be initialised.
    f : file-like object
        The file to read the bitstream from.
    """
    state["_file"] = f
    read_byte(state)


def record_bitstream_start(state):
    """
    Not part of spec; used for verifying that repeated sequence_headers are
    byte-for-byte identical (11.1).

    This function causes all future bytes read from the bitstream to be logged
    into state["_read_bytes"] until :py:func:`record_bitstream_finish` is
    called.

    Recordings must start byte aligned.
    """
    assert state["next_bit"] == 7, "Recordings must always be byte aligned"
    assert state.get("_recorded_bytes") is None, "Cannot nest recordings"
    state["_recorded_bytes"] = bytearray()


def record_bitstream_finish(state):
    """
    See :py:func:`record_bitstream_start`.

    Returns
    =======
    bytearray
        The bytes read since :py:func:`record_bitstream_start` was called. Any
        unread bits of the final byte will be set to zero.
    """
    recorded_bytes = state["_recorded_bytes"]
    del state["_recorded_bytes"]

    # Add whatever has been used of the current byte
    if state["next_bit"] != 7:
        recorded_bytes.append(
            state["current_byte"] & ~((1 << (state["next_bit"] + 1)) - 1)
        )

    return recorded_bytes


def tell(state):
    """
    Not part of spec; used to log bit offsets in the bitstream.

    Return a (byte, bit) tuple giving the offset of the next bit to be read in
    the stream.
    """
    return (
        state["_file"].tell() - (1 if state["current_byte"] is not None else 0),
        state["next_bit"],
    )


@ref_pseudocode(deviation="inferred_implementation")
def read_byte(state):
    """
    (A.2.2) Load the next byte in the stream into the global state, ready for
    the bits to be read.

    By convention, when the end-of-file is reached, ``state["current_byte"]``
    is set to ``None``. This condition must be checked before every read
    operation.
    """
    # Record the now used-up byte (see record_bitstream_start)
    if "_recorded_bytes" in state:
        state["_recorded_bytes"].append(state["current_byte"])

    # Step 1.
    state["next_bit"] = 7

    # Step 2.
    byte = state["_file"].read(1)
    if len(byte) == 1:
        state["current_byte"] = bytearray(byte)[0]  # Convert byte to int
    else:
        # End of file
        state["current_byte"] = None


@ref_pseudocode(deviation="inferred_implementation")
def is_end_of_stream(state):
    """
    (A.2.5) Determine if we have reached the end of the stream (i.e. the end of
    the file).
    """
    return state["current_byte"] is None


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

    bit = (state["current_byte"] >> state["next_bit"]) & 1
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
    for i in range(n):
        val <<= 1
        val += read_bit(state)
    return val


@ref_pseudocode
def read_uint_lit(state, n):
    """(A.3.4)"""
    return read_nbits(state, 8 * n)


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
