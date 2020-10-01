r"""
.. _vc2-bitstream-validator:

``vc2-bitstream-validator``
===========================

A command-line utility for validating VC-2 bitstreams' conformance with the
VC-2 specification and providing a reference decoding of the pictures within.

Usage
-----

This command should be passed a filename containing a candidate VC-2 bitstream.
For example, given a valid stream::

    $ vc2-bitstream-validator path/to/bitstream.vc2 --output decoded_picture_%d.raw
    No errors found in bitstream. Verify decoded pictures to confirm conformance.

Here the ``--output`` argument specifies the printf-style template for the
decoded picture filenames. The decoded pictures are written as raw files (see
:ref:`file-format`).

If a conformance error is detected, a detailed explanation of the problem is
displayed::

    $ vc2-bitstream-validator invalid.vc2
    Conformance error at bit offset 104
    ===================================

    Non-zero previous_parse_offset, 5789784, in the parse info at the start of
    a sequence (10.5.1).


    Details
    -------

    Was this parse info block copied from another stream without the
    previous_parse_offset being updated?

    Does this parse info block incorrectly include an offset into an adjacent
    sequence?


    Suggested bitstream viewer commands
    -----------------------------------

    To view the offending part of the bitstream:

        vc2-bitstream-viewer invalid.vc2 --offset 104


    Pseudocode traceback
    --------------------

    Most recent call last:

    * parse_stream (10.3)
      * parse_sequence (10.4.1)
        * parse_info (10.5.1)

    vc2-bitstream-validator: error: non-conformant bitstream (see above)

Errors include an explanation of the conformance problem (along with references
to the VC-2 standards documents) along with possible causes of the error.
Additionally, a sample invocation of :ref:`vc2-bitstream-viewer` is given which
may be used to display the contents of the bitstream at the offending position.
Finally, a stack trace for the VC-2 pseudocode functions involved in parsing
the stream at the point of failure is also printed.


Arguments
---------

The complete set of arguments can be listed using ``--help``

.. program-output:: vc2-bitstream-validator --help

"""

import os
import sys
import traceback

from argparse import ArgumentParser

from textwrap import dedent

from vc2_conformance.pseudocode.metadata import make_pseudocode_traceback

from vc2_conformance import __version__

from vc2_conformance.py2x_compat import quote

from vc2_conformance.string_utils import wrap_paragraphs

from vc2_conformance.file_format import write

from vc2_conformance.pseudocode.state import State

from vc2_conformance.decoder import (
    init_io,
    parse_stream,
    ConformanceError,
    tell,
)

from vc2_conformance.bitstream import to_bit_offset

from vc2_conformance.py2x_compat import get_terminal_size


def format_pseudocode_traceback(tb):
    """
    Given a :py:func:`traceback.extract_tb` generated traceback description,
    return a string describing the current stack of VC-2 pseudocode functions
    being called.
    """
    ptb = make_pseudocode_traceback(tb)

    return "\n".join(
        "{}* {}".format("  " * num, pdf.citation) for num, pdf in enumerate(ptb)
    )


class BitstreamValidator(object):
    def __init__(self, filename, show_status, verbose, output_filename):
        """
        Parameters
        ==========
        filename : str
            The bitstream filename to read from.
        show_status : bool
            If True, show a status line indicating progress during validation.
        verbose : int
            If >=1, show Python stack traces on failure.
        output_filename : str
            A filename pattern for output bitstream files. Should contain a
            printf-style format string (e.g. "picture_%d.raw").
        """
        self._filename = filename
        self._show_status = show_status
        self._verbose = verbose
        self._output_filename = output_filename

        # The index to use in the filename of the next decoded picture
        self._next_picture_index = 0

        # Is the status line currently visible
        self._status_line_visible = False

    def run(self):
        try:
            self._file = open(self._filename, "rb")
            self._filesize_bytes = os.path.getsize(self._filename)
        except Exception as e:
            # Catch-all exception handler excuse: Catching only file-related
            # exceptions is challenging, particularly in a backward-compatible
            # manner. However, none of the above are known to produce
            # exceptions *except* due to file-related issues.
            self._print_error(str(e))
            return 1

        self._state = State(_output_picture_callback=self._output_picture)
        init_io(self._state, self._file)

        if self._show_status:
            self._update_status_line("Starting bitstream validation...")

        try:
            parse_stream(self._state)
            self._hide_status_line()
            if tell(self._state) == (0, 7):
                sys.stdout.flush()
                sys.stderr.write("Warning: 0 bytes read, bitstream is empty.\n")
            print(
                "No errors found in bitstream. Verify decoded pictures to confirm conformance."
            )
            return 0
        except ConformanceError as e:
            # Bitstream failed validation
            exc_type, exc_value, exc_tb = sys.exc_info()
            self._hide_status_line()
            self._print_conformance_error(e, traceback.extract_tb(exc_tb))
            self._print_error("non-conformant bitstream (see above)")
            return 2
        except Exception as e:
            # Internal error (shouldn't happen(!))
            self._hide_status_line()
            self._print_error(
                "internal error in bitstream validator: {}: {} "
                "(probably a bug in this program)".format(
                    type(e).__name__,
                    str(e),
                )
            )
            return 3

    def _output_picture(self, picture, video_parameters, picture_coding_mode):
        filename = self._output_filename % (self._next_picture_index,)
        self._next_picture_index += 1

        write(
            picture,
            video_parameters,
            picture_coding_mode,
            filename,
        )

        if self._show_status:
            self._update_status_line("Decoded picture written to {}".format(filename))

    def _update_status_line(self, message):
        """
        Display/update the status line indicating the progress of the decoding
        process.
        """
        self._status_line_visible = True

        percent = int(
            round((tell(self._state)[0] * 100.0) / (self._filesize_bytes or 1))
        )

        line = "[{:3d}%] {}".format(percent, message)

        # Ensure stdout is fully displayed before doing anything to the status
        # line.
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

    def _print_conformance_error(self, exception, tb):
        """
        Display detailed information from a ConformanceError on stdout.
        """
        terminal_width = get_terminal_size()[0]

        summary, _, details = wrap_paragraphs(exception.explain()).partition("\n")

        offending_offset = exception.offending_offset()
        if offending_offset is None:
            offending_offset = to_bit_offset(*tell(self._state))

        title = "Conformance error at bit offset {}".format(offending_offset)

        bitstream_viewer_hint = (
            dedent(exception.bitstream_viewer_hint())
            .strip()
            .format(
                cmd="vc2-bitstream-viewer",
                file=quote(self._filename),
                offset=offending_offset,
            )
        )

        out = ""

        out += title + "\n"
        out += ("=" * len(title)) + "\n"
        out += "\n"
        out += wrap_paragraphs(summary, terminal_width) + "\n"
        out += "\n"
        out += "\n"
        out += "Details\n"
        out += "-------\n"
        out += "\n"
        out += wrap_paragraphs(details, terminal_width) + "\n"
        out += "\n"
        out += "\n"
        out += "Suggested bitstream viewer commands\n"
        out += "-----------------------------------\n"
        out += "\n"
        out += bitstream_viewer_hint + "\n"
        out += "\n"
        out += "\n"
        out += "Pseudocode traceback\n"
        out += "--------------------\n"
        out += "\n"
        out += "Most recent call last:\n"
        out += "\n"
        out += format_pseudocode_traceback(tb) + "\n"

        print(out)

    def _print_error(self, message):
        """
        Print an error message to stderr.
        """
        # Avoid interleaving with stdout (and make causality clearer)
        sys.stdout.flush()

        # Display the traceback
        if self._verbose >= 1:
            if sys.exc_info()[0] is not None:
                traceback.print_exc()

        # Display the message
        prog = os.path.basename(sys.argv[0])
        message = "{}: error: {}".format(prog, message)
        sys.stderr.write("{}\n".format(message))


def parse_args(*args, **kwargs):
    """
    Parse a set of command line arguments. Returns a :py:mod:`argparse`
    ``args`` object with the following fields:

    * bitstream (str): The filename of the bitstream to read
    * no_status (bool): True if the status line is to be hidden.
    * verbose (int): The verbosity level.
    * output (str): The output picture filename pattern.
    """
    parser = ArgumentParser(
        description="""
        Validate a bitstream's conformance with the VC-2 specifications.
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
            The filename of the bitstream to validate.
        """,
    )

    parser.add_argument(
        "--no-status",
        "--quiet",
        "-q",
        action="store_true",
        default=False,
        help="""
            Do not display a status line on stderr while validating the
            bitstream.
        """,
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="""
            Show full Python stack-traces on failure.
        """,
    )

    parser.add_argument(
        "--output",
        "-o",
        default="picture_%d.raw",
        help="""
            The filename pattern for decoded picture data and metadata. The
            supplied pattern should a 'printf' style template with (e.g.) '%%d'
            where an index will be substituted. The first decoded picture will
            be assigned index '0', the second '1' and so on -- i.e. these
            indices are unrelated to the picture number. The file extension
            supplied will be stripped and two files will be written for each
            decoded picture: a '.raw' planar image file and a '.json' JSON
            metadata file. (Default: %(default)s).
        """,
    )

    args = parser.parse_args(*args, **kwargs)

    try:
        args.output % (0,)
    except TypeError as e:
        parser.error("--output is not a valid printf template: {}".format(e))

    return args


def main(*args, **kwargs):
    args = parse_args(*args, **kwargs)

    validator = BitstreamValidator(
        filename=args.bitstream,
        show_status=not args.no_status,
        verbose=args.verbose,
        output_filename=args.output,
    )
    return validator.run()


if __name__ == "__main__":
    sys.exit(main())
