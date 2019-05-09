from io import BytesIO

from vc2_conformance import bitstream
from vc2_conformance import decoder

from vc2_conformance.state import State


def seriallise_to_bytes(context, func, state=None):
    """
    Seriallise the specified context with the given vc2 bitstream pseudocode
    function. Returns the seriallised bytes.
    """
    f = BytesIO()
    w = bitstream.BitstreamWriter(f)
    with bitstream.Serialiser(w, context) as ser:
        func(ser, State() if state is None else state)
    w.flush()
    return f.getvalue()


def bytes_to_state(bitstream):
    """Return a raedy-to-read state dictionary."""
    f = BytesIO(bitstream)
    state = State()
    decoder.init_io(state, f)
    return state
