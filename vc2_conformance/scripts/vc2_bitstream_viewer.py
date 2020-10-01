r"""
.. _vc2-bitstream-viewer:

``vc2-bitstream-viewer``
========================

A command-line utility for displaying VC-2 bitstreams in a human readable form.

The following tutorials give a higher-level introduction to this tool.
Complete usage information can be obtained by running ``vc2-bitstream-viewer
--help``.

.. warning::

    This program prioritises correctness over performance. Internally the
    pseudocode from the VC-2 specification is used to drive the bitstream
    parser. As a consequence this program is relatively slow, e.g. taking many
    seconds per HD frame.


Basic usage
-----------

In its simplest form, this command can be used to create a complete textual
representation of a VC-2 bitstream::

    $ vc2-bitstream-viewer path/to/bitstream.vc2
                                                      +- data_units:
                                                      | +- 0:
                                                      | | +- parse_info:
    000000000000:                                     | | | +- padding: 0b
    000000000000: 01000010010000100100001101000100    | | | +- parse_info_prefix: Correct (0x42424344)
    000000000032: 00010000                            | | | +- parse_code: end_of_sequence (0x10)
    000000000040: 00000000000000000000000000000000    | | | +- next_parse_offset: 0
    000000000072: 00000000000000000000000000000000    | | | +- previous_parse_offset: 0

In the printed output, each value read from the bitstream is shown on its own
line:

* The number at the start of the line is the offset (in bits) from the
  start of the file that that value begins.
* The next value is the value in the bitstream expressed as a binary number.
  If values are being read from the bounded block in the bitstream, a (``*``)
  indicates that any remaining bits in the value shown were read from beyond
  the end of the block (and read as '1').
* The final part of the line indicates the name and decoded value of the read
  data. Where possible, the names used match the names of variables in the VC-2
  pseudocode.

By default, every bit and every field in the bitstream will be visible,
including padding bits.


Displaying an area of interest
------------------------------

It is possible to restrict the output to only parts of the bitstream
surrounding a particular offset. For example, the ``--offset``/``-o`` argument
may be used to restrict display to only the parts of the bitstream surrounding
a particular bit offset::

    $ vc2-bitstream-viewer bitstream.vc2 --offset 40000

See the ``--context``/``-C``, ``--context-after``/``-A`` and
``--context-before``/``-B`` arguments to control the number of bits before and
after the supplied offset to be shown. Alternatively, you can also specify an
explicit range to display using the ``--from-offset``/``-f`` and
``--to-offset``/``-t``.

.. note::

    Though values before the specified bit offset will not be displayed, they
    must still be read and parsed by the bitstream viewer in order to correctly
    parse what comes later in the bitstream.


Filtering displayed values
--------------------------

It is possible to filter the displayed values according to the VC-2 pseudocode
function which read them. A common case might be to show only the parse_info
headers from a stream::

    $ vc2-bitstream-viewer bitstream.vc2 --show parse_info

Alternatively, you may wish to show everything in a bitstream except for the
transform coefficients (slice data)::

    $ vc2-bitstream-viewer bitstream.vc2 --hide slice

For this particular action, the convenience alias ``-S`` for ``--hide slice``
is also provided.

Showing VC-2 decoder state
--------------------------

As well as displaying a textual representation of the VC-2 bitstream, this tool
can also display (a subset of) the internal state of a VC-2 decoder based on
the pseudocode in the specification at different points during bitstream
processing. Use the ``--show-internal-state`` option to enable this. This may
be useful when debugging the encoding of transform data whose organisation
depends on various computed values earlier in the bitstream.


Malformed bitstream handling
----------------------------

The bitstream parser is as tolerant of malformed bitstreams as is practical and
will accept, and blindly tolerate values which are out-of-spec so long as they
do not lead to undefined behaviour. In the event that the parser encounters an
anomaly that prevents it preceding further, an error will be shown and parsing
will terminate.

By default, error messages show only limited information about the failure.
Adding the ``--verbose``/``-v`` option will cause additional details (such as
the next few bits in the bitstream and details of what was being parsed at the
time.

Arguments
---------

The complete set of arguments can be listed using ``--help``

.. program-output:: vc2-bitstream-viewer --help

"""  # noqa: E501

import os
import sys
import time
import inspect
import traceback

from bitarray import bitarray

from argparse import ArgumentParser

from textwrap import wrap

from vc2_conformance import __version__

from vc2_conformance.pseudocode.metadata import make_pseudocode_traceback

from vc2_conformance import bitstream

from vc2_conformance.pseudocode.state import State

from vc2_data_tables import PARSE_INFO_PREFIX

from vc2_conformance.string_utils import ellipsise_lossy
from vc2_conformance.string_formatters import Hex

from vc2_conformance.py2x_compat import (
    zip_longest,
    get_terminal_size,
)


DEFAULT_CONTEXT_BITS = 128
"""Number of bits either side of --offset to show by default."""

STATUS_LINE_UPDATE_INTERVAL = 0.2
"""Number of seconds between updates to the status line."""

OFFSET_DIGITS = 12
"""Number of digits to show in bit offsets"""

RAW_BITS_PER_LINE = 32
"""Number of binary digits to show per line in raw binary strings."""


def relative_int(string):
    """
    Given an integer of the form accepted by --to-offset, return a (relative,
    offset) pair. 'relative' will be True for relative offsets and False
    otherwise. 'offset' will be an int.
    """
    if not isinstance(string, str):
        raise ValueError(string)

    relative = string.startswith("+")
    offset = int(string)

    return (relative, offset)


def relative_to_abs_index(num, length):
    """
    Given a relative index (negative values are relative to the end of the
    length), return an absolute index.
    """
    if num >= 0:
        return num
    else:
        return length + num


# The filename of this module and the bitstream VC2 module (not the .pyc files)
_this_script_filename = inspect.getsourcefile(sys.modules[__name__])
_bitstream_vc2_filename = inspect.getsourcefile(bitstream.vc2)


def is_internal_error(tb):
    """
    Given a Python traceback, attempt to determine if the fault lies with a bug
    in this script (i.e. not an error produced by the VC-2 pseudo code
    encountering an unnacceptably out-of-range value).
    """
    is_internal = False

    stack_summary = traceback.extract_tb(tb)
    for frame_summary in stack_summary:
        filename = frame_summary[0]

        if filename == _this_script_filename:
            is_internal = True
        elif filename == _bitstream_vc2_filename:
            is_internal = False

    return is_internal


def _call(f, *args, **kwargs):
    """
    For use by the test suite. Calls function 'f' with the provided arguments.
    """
    return f(*args, **kwargs)


def most_recent_pseudocode_function(tb):
    """
    Given a Python traceback, return the function name/citation of the
    inner-most VC-2 pseudocode function to be executed.
    """
    ptb = make_pseudocode_traceback(traceback.extract_tb(tb))
    if ptb:
        return ptb[-1].citation
    else:
        return "<unknown>"


def format_path_summary(path):
    """
    Format a :py:mod:`serdes` path as a string.
    """
    return ": ".join(map(str, path))


def format_value_line(offset, raw_bits, label, label_filler="", truncated=False):
    """
    Format a line of output which displays a single value from the bitstream.

    Parameters
    ----------
    offset : int
        Bit offset into bitstream.
    raw_bits : :py:class:`bitarray.bitarray`
        The raw bits which encode this value.
    label : str
        The label which describes the value encoded by the raw_bits.
    label_filler : str
        If the raw_bits, when printed, spread onto multiple lines, the string
        to show in place of the label on these lines.
    truncated : bool
        If True, shows a '*' at the end of the raw_bits to indicate that
        truncation (e.g. at the end of a bounded block) has taken place.
    """
    raw_bits_suffix = "*" if truncated else ""
    raw_bits_lines = wrap(raw_bits.to01() + raw_bits_suffix, RAW_BITS_PER_LINE)

    if len(raw_bits_lines) == 0:
        raw_bits_lines = [""]

    out = []
    out.append(
        "{:0{}d}: {:<{}s}    {}".format(
            offset,
            OFFSET_DIGITS,
            raw_bits_lines[0],
            RAW_BITS_PER_LINE,
            label,
        )
    )

    for line in raw_bits_lines[1:]:
        out.append(
            "{}  {:<{}s}    {}".format(
                " " * OFFSET_DIGITS, line, RAW_BITS_PER_LINE, label_filler
            )
        )

    return "\n".join(out)


def format_header_line(label):
    """
    Format a line of output which displays only a header (indented to match the
    labels printed by :py:func:`format_value_line`.
    """
    return "{}{}".format(
        " " * (OFFSET_DIGITS + 2 + RAW_BITS_PER_LINE + 4),
        label,
    )


def format_omission_line(offset, num_bits):
    """
    Format a line of output which indicates a number of bits have been omitted
    from the bitstream.
    """
    return "{:0{}d}: {:<{}s}    ...".format(
        offset,
        OFFSET_DIGITS,
        "<{} bits omitted>".format(num_bits),
        RAW_BITS_PER_LINE,
    )


class BitstreamViewer(object):
    """
    Main commandline application logic.

    Construct an instance of this class then call :py:meth:`run` and, later,
    :py:meth:`close`.
    """

    def __init__(
        self,
        filename,
        from_offset=0,
        to_offset=-1,
        shown_pseudocode_names=[],
        hidden_pseudocode_names=[],
        show_internal_state=False,
        check_parse_info_prefix=True,
        show_status=True,
        verbose=0,
        num_trailing_bits_on_error=128,
    ):
        """
        Parameters
        ==========
        filename : str
            The filename of the bitstream.
        from_offset : int
            The bit offset at which to start reading from the bitstream. If
            negative, will be assumed to be an offset from the end of the file.
        to_offset : int
            The bit offset at which to stop reading the bitstream. If negative,
            will be assumed to be an offset from the end of the file.
        shown_pseudocode_names : [str, ...]
            A list of strings naming the bitstream pseudocode functions whose
            values should be shown in the printed output. If empty, all values
            are shown.
        hidden_pseudocode_names : [str, ...]
            A list of strings naming the bitstream pseudocode functions whose
            values should be omitted in the printed output.
        show_internal_state : bool
            If True, the internal state of the pseudocode functions will be
            printed before and after every data unit.
        check_parse_info_prefix : bool
            If True, validate parse_info prefix bytes and stop if they don't
            hold the expected value.
        show_status : bool
            If True, show a status line on stderr while reading parts of the
            bitstream which aren't being printed.
        verbose : int
            Error message verbosity level:

            0. Only show the error message.
            1. Show trailing bits in bitstream, bit offset and current
               target.
            2. Show traceback.
        num_trailing_bits_on_error : int
            When ``verbose`` is at least 1, controls the (maximum) number of
            bits in the bitstream to display after an error has ocurred.
        """
        self._filename = filename
        self._from_offset = from_offset
        self._to_offset = to_offset
        self._show_internal_state = show_internal_state
        self._check_parse_info_prefix = check_parse_info_prefix
        self._show_status = show_status
        self._verbose = verbose
        self._num_trailing_bits_on_error = num_trailing_bits_on_error

        # A set of fixeddict types which are to be shown or hidden (None if no
        # filter).
        self._shown_types = None
        self._hidden_types = None

        # Convert from pseudocode function names to sets of corresponding
        # fixeddict types for the above
        shown = set()
        for name in shown_pseudocode_names:
            shown.update(bitstream.pseudocode_function_to_fixeddicts_recursive[name])
        hidden = set()
        for name in hidden_pseudocode_names:
            hidden.update(bitstream.pseudocode_function_to_fixeddicts_recursive[name])
        if len(shown) > 0:
            self._shown_types = shown - hidden
        elif len(hidden) > 0:
            self._hidden_types = hidden

        # The file object for the bitstream
        self._file = None

        # The BitstreamReader reading the file
        self._reader = None

        # The MonitoredDeserialiser in use
        self._serdes = None

        # The internal State variable used by VC-2 pseudocode
        self._state = State()

        # Is the status line currently visible
        self._status_line_visible = False

        # The last time at which the status bar was updated
        self._status_line_updated = 0.0

        # The bitstream offset last time the monitor function was called
        self._last_tell = (0, 7)

        # The last bitstream offset at which the monitor function printed a
        # value
        self._last_displayed_tell = (0, 7)

        # The last serdes path displayed
        self._last_path = []

        # The last number of data units in the stream (only used when
        # show_internal_state is True)
        self._last_num_data_units = 0

    def _print_error(self, message):
        """
        Print an error message to stderr.
        """
        # Avoid interleaving with stdout (and make causality clearer)
        sys.stdout.flush()

        # The 'trailing bits' print out below may move the read position
        # so record it now.
        if self._reader is not None:
            offset = bitstream.to_bit_offset(*self._reader.tell())

        # Display the trailing bits from the bitstream
        if self._verbose >= 1:
            if self._reader is not None:
                self._reader.seek(*self._last_tell)
                bits = self._reader.try_read_bitarray(self._num_trailing_bits_on_error)
                if len(bits) > 0:
                    sys.stderr.write(
                        "{}\n".format(
                            format_value_line(
                                bitstream.to_bit_offset(*self._last_tell),
                                bitarray(bits),
                                "<next {} bits>".format(len(bits)),
                            )
                        )
                    )

        # Display the traceback
        if self._verbose >= 2:
            if sys.exc_info()[0] is not None:
                traceback.print_exc()

        # Display offset/target information
        prog = os.path.basename(sys.argv[0])
        if self._verbose >= 1:
            if self._reader is not None:
                sys.stderr.write(
                    "{}: offset: {}\n".format(
                        prog,
                        offset,
                    )
                )
            if self._serdes is not None:
                sys.stderr.write(
                    "{}: target: {}\n".format(
                        prog,
                        format_path_summary(self._serdes.path()),
                    )
                )

        # Display the message
        message = "{}: error: {}".format(prog, message)
        sys.stderr.write("{}\n".format(message))

    class _TerminateSuccess(Exception):
        """
        Thrown from the monitoring function to indicate a healty early
        termination of bitstream parsing.
        """

        pass

    class _TerminateError(Exception):
        """
        Thrown from the monitoring function to indicate a fatal error during
        bitstream parsing..
        """

        pass

    def _update_status_line(self, target):
        """
        Update the status line, if a sufficiently long time has ellpased (to
        avoid spending too long printing to the console).
        """
        now = time.time()
        if now - self._status_line_updated >= STATUS_LINE_UPDATE_INTERVAL:
            self._status_line_visible = True
            self._status_line_updated = now

            cur_offset = bitstream.to_bit_offset(*self._reader.tell())
            cur_path = format_path_summary(self._serdes.path(target))

            terminal_width = get_terminal_size()[0]
            line = "{:0{}d}: <{}>".format(
                cur_offset,
                OFFSET_DIGITS,
                ellipsise_lossy(cur_path, terminal_width - OFFSET_DIGITS - 4),
            )

            # Ensure stdout is fully displayed before printing the status line
            sys.stdout.flush()

            sys.stderr.write(
                (
                    "\033[2K"  # Clear to end of line
                    "\033[s"  # Save cursor position
                    "{}"
                    "\033[u"  # Restore cursor position
                ).format(line)
            )
            sys.stderr.flush()

    def _hide_status_line(self):
        """If the status line is visible, hide it."""
        if self._status_line_visible:
            self._status_line_visible = False

            # Ensure stdout is fully displayed before doing anything to the
            # status line.
            sys.stdout.flush()

            sys.stderr.write("\033[2K")  # Clear to end of line
            sys.stderr.flush()

    def _print_value(self, offset, raw_bits, target, value):
        """
        Print a value from the bitstream on stdout.

        Parameters
        ==========
        offset : int
            The bit offset at the start of the value in the bitstraem.
        raw_bits : bitarray
            The raw bits read from the bitstream for this value.
        target : str
            The target name of this value.
        value : any
            The deserialised value.
        """
        # Print new/changed path prefixes
        last_path = self._last_path
        this_path = self._serdes.path(target)
        self._last_path = this_path
        different = False
        for level, (last_path_element, this_path_element) in enumerate(
            zip_longest(last_path[:-1], this_path[:-1])
        ):
            different |= (
                last_path_element != this_path_element and this_path_element is not None
            )
            if different and this_path_element is not None:
                prefix = "| " * level
                print(format_header_line("{}+- {}:".format(prefix, this_path_element)))

        # Mark values read past the end of a bounded block
        past_end_of_bounded_block = (
            self._reader.bits_remaining is not None and self._reader.bits_remaining < 0
        )

        # Format value for display
        if hasattr(self._serdes.cur_context, "entry_objs"):
            formatter = self._serdes.cur_context.entry_objs[target].to_string
        else:
            formatter = str
        if self._serdes.cur_context[target] is not value:
            # This is a list target, use the formatter's inner formatter
            formatter = getattr(formatter, "formatter", str)

        value_prefix = "{}+- {}: ".format("| " * (len(this_path) - 1), this_path[-1])
        value_str = "{}{}".format(value_prefix, formatter(value))

        value_filler_str = "| " * (len(this_path))

        print(
            format_value_line(
                offset,
                raw_bits,
                value_str,
                value_filler_str,
                past_end_of_bounded_block,
            )
        )

    def _print_internal_state(self):
        """
        Display the current internal state of the VC-2 pseudocode functions.
        """
        if self._state:
            print("-" * (OFFSET_DIGITS + 2 + RAW_BITS_PER_LINE))
            print(str(self._state))
            print("-" * (OFFSET_DIGITS + 2 + RAW_BITS_PER_LINE))

    def _print_omitted_bits(self, tell):
        """
        Display the number of bits omitted since the last displayed value up
        until 'tell'.
        """
        offset = bitstream.to_bit_offset(*tell)
        last_displayed_offset = bitstream.to_bit_offset(*self._last_displayed_tell)
        num_bits = offset - last_displayed_offset

        print(format_omission_line(last_displayed_offset, num_bits))

    def __call__(self, serdes, target, value):
        """
        Called as the monitoring function of the the
        :py:class:`MonitoredDeserialiser`. Responsible for printing values from
        the bitstream and terminating once the region of interest has been
        parsed.
        """
        last_tell = self._last_tell
        this_tell = self._reader.tell()
        self._last_tell = this_tell

        if self._show_internal_state:
            # Only show at start of new data unit (NB: strictly speaking this
            # will display the state was it was after parsing the first field
            # of each data unit. Since this is a padding field, the state
            # should still be correct.
            num_data_units = sum(
                len(sequence["data_units"])
                for sequence in self._serdes.context["sequences"]
            )
            if self._last_num_data_units != num_data_units:
                self._last_num_data_units = num_data_units

                self._hide_status_line()
                self._print_internal_state()

        this_offset = bitstream.to_bit_offset(*this_tell)

        enable_display = False
        enable_display = (
            # Within the specified region (NB: we terminate once past it)
            (self._from_offset == 0 or this_offset > self._from_offset)
            and
            # Is the current context selected to be shown
            (
                self._hidden_types is None
                or self._serdes.cur_context.__class__ not in self._hidden_types
            )
            and (
                self._shown_types is None
                or self._serdes.cur_context.__class__ in self._shown_types
            )
        )

        if enable_display:
            self._hide_status_line()

            last_offset = bitstream.to_bit_offset(*last_tell)

            # Print message if we've skipped some bits
            if self._last_displayed_tell != last_tell:
                self._print_omitted_bits(last_tell)
            self._last_displayed_tell = this_tell

            # Re-read the bits within the value just read and display it
            self._reader.seek(*last_tell)
            raw_bits = self._reader.read_bitarray(this_offset - last_offset)
            self._print_value(last_offset, raw_bits, target, value)
        else:
            if self._show_status:
                self._update_status_line(target)

        # Stop if we've encountered an invalid parse_info prefix code
        if self._check_parse_info_prefix:
            # The test below relies on the only use of the target name
            # 'parse_info_prefix' being for the parse info prefix. (This should
            # be the case).
            if target == "parse_info_prefix" and value != PARSE_INFO_PREFIX:
                raise BitstreamViewer._TerminateError(
                    "invalid parse_info prefix ({})".format(Hex(8)(value))
                )

        # Stop when we've reached/passed the end of the region of interest
        if self._to_offset != 0 and this_offset >= self._to_offset:
            raise BitstreamViewer._TerminateSuccess()

        # Save memory by discarding previously deserialised data units
        current_data_unit = True
        for sequence in reversed(self._serdes.context["sequences"]):
            for i in reversed(range(len(sequence["data_units"]))):
                if not current_data_unit:
                    sequence["data_units"][i] = None
                current_data_unit = False

    def run(self):
        """
        Parse the bitstream. Returns 0 if the bitstream was read successfully
        or another integer otherwise.
        """
        # Open the file
        try:
            self._file = open(self._filename, "rb")
            self._reader = bitstream.BitstreamReader(self._file)
            filesize_bytes = os.path.getsize(self._filename)
        except Exception as e:
            # Catch-all exception handler excuse: Catching only file-related
            # exceptions is challenging, particularly in a backward-compatible
            # manner. However, none of the above are known to produce
            # exceptions *except* due to file-related issues.
            self._print_error(str(e))
            return 1

        # Resolve filesizes to absolute values
        filesize = filesize_bytes * 8
        self._from_offset = relative_to_abs_index(self._from_offset, filesize)
        self._to_offset = max(0, relative_to_abs_index(self._to_offset, filesize))

        return_code = 0
        error_message = None

        # Parse the bitstream. A MonitoredDeserialiser is used which calls
        # __call__ whenever a value is read. That method is responsible for
        # printing the bitstream to stdout and also deciding when to terminate
        # the read process, raising _TerminateSuccess and _TerminateError to
        # end parsing before the end of the file.
        try:
            self._serdes = bitstream.MonitoredDeserialiser(
                io=self._reader,
                monitor=self,
            )
            bitstream.parse_stream(self._serdes, self._state)
        except BitstreamViewer._TerminateSuccess:
            return_code = 0
            error_message = None
        except KeyboardInterrupt:
            return_code = 1
            error_message = None
        except BitstreamViewer._TerminateError as e:
            return_code = 2
            error_message = str(e)
        except EOFError:
            return_code = 3
            error_message = "reached the end of the file while parsing {}".format(
                most_recent_pseudocode_function(sys.exc_info()[2]),
            )
        except Exception:
            # Other exceptions may be raised during parsing (e.g. due to
            # invalid bitstream values), attempt to display these sensibly.
            exc_type, exc_value, exc_tb = sys.exc_info()
            if is_internal_error(exc_tb):
                # If the exception does not originate from the VC-2 pseudocode,
                # we've encountered an internal error in this program. This
                # should not happen, but if it does it should be made clear.
                return_code = 255
                error_message = (
                    "internal error in bitstream viewer: {}: {} "
                    "(probably a bug in this program)".format(
                        exc_type.__name__,
                        str(exc_value),
                    )
                )
            else:
                # General case: some error in the VC-2 pseudocode due to an
                # out-of-range value
                return_code = 4
                error_message = (
                    "{} failed to parse bitstream ({}: {}) "
                    "(missing sequence_header, fragment or earlier out of range value?)"
                ).format(
                    most_recent_pseudocode_function(exc_tb),
                    exc_type.__name__,
                    str(exc_value),
                )
        finally:
            self._hide_status_line()

        if self._last_displayed_tell != self._last_tell:
            self._print_omitted_bits(self._last_tell)

        if self._show_internal_state:
            self._print_internal_state()

        if error_message is not None:
            self._print_error(error_message)

        return return_code

    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None


def parse_args(*args, **kwargs):
    """
    Parse a set of command line arguments. Returns a :py:mod:`argparse`
    ``args`` object with the following fields:

    * bitstream (str): The filename of the bitstream to read
    * no_status (bool): True if the status line is to be hidden.
    * verbose (int): Verbosity level
    * show_internal_state (bool): True if the state of the VC-2 pseudo code
      should be shown during parsing.
    * ignore_parse_info_prefix (bool): True if the parse_info prefix code
      should not be checked for correctness.
    * num_trailing_bits (int): Number of unprocessed bits from the bitstream to
      display in verbose error messages.
    * from_offset (int): The number of bits after the start of file to reach
      before displaying output. If negative, relative to the EOF.
    * to_offset (int): The bit offset at which to stop printing. If negative,
      relative to the EOF.
    * show (list of str): List of VC-2 pseudocode function names whose
      bitstream values must be displayed in the output. If empty, show
      everything.
    * hide (list of str): List of VC-2 pseudocode function names whose
      bitstream values must be hidden in the output.
    """
    parser = ArgumentParser(
        description="""
        Display VC-2 bitstreams in a human-readable form.
    """
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s {}".format(__version__),
    )

    parser.add_argument(
        "bitstream",
        help="""
            The filename of the bitstream to read.
        """,
    )

    parser.add_argument(
        "--no-status",
        "--quiet",
        "-q",
        action="store_true",
        default=False,
        help="""
            Do not display a status line on stderr while reading the bitstream.
        """,
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="""
            Increase the verbosity of error messages. Used once: also show bitstream
            offset, bitstream target value and next --num-trailing-bits bits in
            the bitstream at the time of the error. Used twice: also show the
            Python stack trace for the error.
        """,
    )

    parser.add_argument(
        "--show-internal-state",
        "-i",
        action="store_true",
        default=False,
        help="""
            Print the internal state variable used by the VC-2 pseudo code
            after parsing each data unit. Parts of the pseudocode state not
            directly related to bitstream processing may or may not be included
            in this printout.
        """,
    )

    parser.add_argument(
        "--ignore-parse-info-prefix",
        "-p",
        action="store_true",
        default=False,
        help="""
            By default, parsing is halted if an invalid parse_info prefix is
            encountered. Giving this option supresses this check and allows
            parsing to continue.
        """,
    )

    parser.add_argument(
        "--num-trailing-bits",
        "-b",
        type=int,
        default=DEFAULT_CONTEXT_BITS,
        help="""
            When --verbose is used, this argument defines the number of
            bits to show from the bitstream after the point the error occurred.
            (Default: %(default)d).
        """,
    )

    ###########################################################################

    range_group = parser.add_argument_group(title="range options")

    range_group.add_argument(
        "--from-offset",
        "-f",
        type=int,
        metavar="BIT_OFFSET",
        help="""
            Don't display bitstream values until the specified bit offset. If
            negative, gives an offset from the end of the file. Default: 0.
        """,
    )

    range_group.add_argument(
        "--to-offset",
        "-t",
        metavar="BIT_OFFSET",
        type=relative_int,
        help="""
            Stop reading the bitstream at the specified bit offset. If prefixed
            with '+', the offset will be relative to the offset given to
            '--from-offset'. If negative, gives an offset from the end of the
            file. Default: the end of the file.
        """,
    )

    range_group.add_argument(
        "--offset",
        "-o",
        metavar="BIT_OFFSET",
        type=int,
        help="""
            Shows the parts of the bitstream surrounding the specified bit
            offset. (An alternative to manually setting '--from-offset' and
            '--to-offset' to values either-side of the chosen offset). If
            none of '--after-context', '--before-context' or '--context' are
            given, {} bits of context either side of this offset will be
            shown.
        """.format(
            DEFAULT_CONTEXT_BITS
        ),
    )

    range_group.add_argument(
        "--after-context",
        "-A",
        metavar="NUM_BITS",
        type=int,
        help="""
            Sets the number of bits after '--around-offset' to be shown.
        """,
    )
    range_group.add_argument(
        "--before-context",
        "-B",
        metavar="NUM_BITS",
        type=int,
        help="""
            Sets the number of bits before '--around-offset' to be shown.
        """,
    )
    range_group.add_argument(
        "--context",
        "-C",
        metavar="NUM_BITS",
        type=int,
        help="""
            Sets the number of bits before and after '--around-offset' to be
            shown.
        """,
    )

    ###########################################################################

    filter_group = parser.add_argument_group(title="filtering options")

    filter_group.add_argument(
        "--show",
        "-s",
        type=str,
        metavar="FUNCTION",
        default=[],
        action="append",
        help="""
            Display only parts of the bitstream which are processed by the
            specified pseudo-code function as described in the VC-2
            specification. By default all parts of the bitstream are displayed.
            May be used multiple times to show different parts of the
            bitstream. Supported function names: {}.
        """.format(
            ", ".join(sorted(bitstream.pseudocode_function_to_fixeddicts_recursive))
        ),
    )

    filter_group.add_argument(
        "--hide",
        "-H",
        type=str,
        metavar="FUNCTION",
        default=[],
        action="append",
        help="""
            Omit parts of the bitstream which are processed by the specified
            pseudo-code function as described in the VC-2 specification.
            Accepts the same values as --show.
        """,
    )

    filter_group.add_argument(
        "--hide-slice",
        "-S",
        action="append_const",
        const="slice",
        dest="hide",
        help="""
            Alias for '--hide slice'. Suppresses the printing of all transform
            coefficients, greatly reducing the quantity of output.
        """,
    )

    ###########################################################################

    args = parser.parse_args(*args, **kwargs)

    from_to_offset = args.from_offset is not None or args.to_offset is not None
    if from_to_offset and args.offset is not None:
        parser.error("--offset may not be used with --from-offset or --to-offset")

    # Convert the '--offset' argument into '--from-offset' and '--to-offset'
    # arguments.
    if args.offset is not None:
        # Make sure the --*-context arguments don't conflict
        if args.context is not None and (
            args.after_context is not None or args.before_context is not None
        ):
            parser.error(
                "--context may not be used at the same time as --after-context or --before-context"
            )

        before_context = after_context = None

        if args.context is not None:
            before_context = after_context = args.context
        if args.before_context is not None:
            before_context = args.before_context
        if args.after_context is not None:
            after_context = args.after_context

        if before_context is None and after_context is None:
            before_context = after_context = DEFAULT_CONTEXT_BITS
        elif before_context is None:
            before_context = 0
        elif after_context is None:
            after_context = 0

        if args.offset < 0:
            args.from_offset = args.offset - before_context
            args.to_offset = (False, min(-1, args.offset + after_context))
        else:
            args.from_offset = max(0, args.offset - before_context)
            args.to_offset = (False, args.offset + after_context)

        args.offset = None
        args.context = None
        args.before_context = None
        args.after_context = None

    # Make sure the --*-context arguments aren't used with --{from,to}-offset
    if args.after_context is not None:
        parser.error("--after-context may only be used with --offset")
    if args.before_context is not None:
        parser.error("--before-context may only be used with --offset")
    if args.context is not None:
        parser.error("--context may only be used with --offset")

    # Set defaults for '--{from,to}-offset'
    if args.from_offset is None:
        args.from_offset = 0
    if args.to_offset is None:
        args.to_offset = (False, -1)

    # Normalise '--to-offset' into just an integer
    relative, to_offset = args.to_offset
    if relative:
        args.to_offset = args.from_offset + to_offset
    else:
        args.to_offset = to_offset

    # Check show/hide only contain allowed values
    for name in args.show:
        if name not in bitstream.pseudocode_function_to_fixeddicts_recursive:
            parser.error(
                "--show includes unrecognised pseudocode function {!r}".format(name)
            )
    for name in args.hide:
        if name not in bitstream.pseudocode_function_to_fixeddicts_recursive:
            parser.error(
                "--hide includes unrecognised pseudocode function {!r}".format(name)
            )

    return args


def main(*args, **kwargs):
    args = parse_args(*args, **kwargs)

    viewer = BitstreamViewer(
        filename=args.bitstream,
        from_offset=args.from_offset,
        to_offset=args.to_offset,
        shown_pseudocode_names=args.show,
        hidden_pseudocode_names=args.hide,
        show_internal_state=args.show_internal_state,
        check_parse_info_prefix=not args.ignore_parse_info_prefix,
        show_status=not args.no_status,
        verbose=args.verbose,
        num_trailing_bits_on_error=args.num_trailing_bits,
    )
    try:
        return viewer.run()
    finally:
        viewer.close()


if __name__ == "__main__":
    sys.exit(main())
