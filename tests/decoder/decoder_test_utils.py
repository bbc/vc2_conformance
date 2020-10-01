from io import BytesIO

from vc2_conformance import bitstream
from vc2_conformance import decoder

from vc2_conformance.pseudocode.state import State


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


def populate_parse_offsets(sequence, state=None):
    """
    Given a complete :py:class:`vc2_conformance.bitstream.Sequence`, update all
    of the parse_info next_parse_offset and previous_parse_offset values to the
    correct value.
    """
    state = state.copy() if state is not None else State()
    w = bitstream.BitstreamWriter(BytesIO())

    # This function seriallises the provided sequence using a
    # MonitoredSerialiser to log the offsets at which the parse_info headers
    # are written.
    parse_info_offsets = []

    def capture_parse_info_offsets(serdes, target, value):
        if target == "parse_info_prefix":
            # NB: Offset reported is at the end of the parse_info_prefix so the
            # parse_info block started 32 bits earlier.
            next_byte, next_bit = w.tell()
            assert next_bit == 7
            parse_info_offsets.append(next_byte - 4)

    with bitstream.MonitoredSerialiser(
        capture_parse_info_offsets,
        w,
        sequence,
        bitstream.vc2_default_values,
    ) as serdes:
        bitstream.parse_sequence(serdes, state)

    # Retrospectively update the parse_info offsets in-place
    for i in range(len(sequence["data_units"])):
        if i == 0:
            sequence["data_units"][i]["parse_info"]["previous_parse_offset"] = 0
        else:
            sequence["data_units"][i]["parse_info"]["previous_parse_offset"] = (
                parse_info_offsets[i] - parse_info_offsets[i - 1]
            )

        if i == len(sequence["data_units"]) - 1:
            sequence["data_units"][i]["parse_info"]["next_parse_offset"] = 0
        else:
            sequence["data_units"][i]["parse_info"]["next_parse_offset"] = (
                parse_info_offsets[i + 1] - parse_info_offsets[i]
            )
