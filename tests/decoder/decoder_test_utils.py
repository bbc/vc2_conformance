from io import BytesIO

from vc2_conformance import bitstream
from vc2_conformance import decoder

from vc2_conformance.state import State


def serialise_to_bytes(context, state=None, *args):
    """
    serialise the specified context dictionary. Returns the serialised bytes.
    """
    # Auto-determine the serialisation function to use based on the context
    # type
    func_name = bitstream.fixeddict_to_pseudocode_function[type(context)]
    func = getattr(bitstream, func_name)
    
    f = BytesIO()
    w = bitstream.BitstreamWriter(f)
    with bitstream.Serialiser(w, context, bitstream.vc2_default_values) as ser:
        func(ser, State() if state is None else state, *args)
    w.flush()
    return f.getvalue()


def bytes_to_state(bitstream):
    """Return a raedy-to-read state dictionary."""
    f = BytesIO(bitstream)
    state = State()
    decoder.init_io(state, f)
    return state
