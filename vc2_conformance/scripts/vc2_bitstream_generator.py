"""
``vc2-bitstream-generator``
===========================

A command-line utility for generating arbitrary VC-2 bitstreams.

"""

import sys

import json

import traceback

from sentinels import Sentinel

from copy import deepcopy

from argparse import ArgumentParser

from vc2_conformance.state import State

from vc2_conformance._py2x_compat import string_types

from vc2_conformance.bitstream import (
    AUTO,
    BitstreamWriter,
    Serialiser,
    vc2_default_values_with_auto,
    autofill_picture_number,
    autofill_parse_offsets,
    autofill_parse_offsets_finalize,
    parse_sequence,
    UnusedTargetError,
)

from vc2_conformance.fixeddict import FixedDictKeyError

import vc2_data_tables as tables

from vc2_conformance import vc2_math


def remove_comments_from_json(obj):
    """
    Given a deserialised JSON value, remove all comments.
    
    In JSON objects, a comment is a value whose key is "#".
    
    In JSON arrays, a comment is a string value starting with "#".
    
    Mutates the object in-place and returns the modified object
    """
    if isinstance(obj, dict):
        for key in list(obj):
            if key == "#":
                del obj[key]
            else:
                remove_comments_from_json(obj[key])
    elif isinstance(obj, list):
        i = 0
        while i < len(obj):
            if isinstance(obj[i], string_types) and obj[i].startswith("#"):
                del obj[i]
            else:
                remove_comments_from_json(obj[i])
                i += 1
    return obj


class JSONEvalError(Exception):
    """
    An exception was thrown while executing the embedded Python code in a JSON
    dictionary.
    """

    def __init__(self, expression, path, exception):
        self.expression = expression
        self.path = path
        self.exception = exception

    def __str__(self):
        return "Evaluation of {!r} in {} failed: {}: {}".format(
            self.expression,
            "Sequence{}".format("".join("[{!r}]".format(key) for key in self.path)),
            type(self.exception).__name__,
            self.exception,
        )


def evaluate_strings_in_json(obj, globals={}, locals={}, path=()):
    """
    Evaluate all strings in a JSON deserialised value with the Python
    interpreter.
    
    Mutates values in place (where possible) and returns the evaluated result.
    
    Throws a :py:exc:`JSONEvalError` if evaluation fails.
    """
    if isinstance(obj, dict):
        for key in list(obj):
            obj[key] = evaluate_strings_in_json(
                obj[key], globals, locals, path + (key,)
            )
    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = evaluate_strings_in_json(obj[i], globals, locals, path + (i,))
    elif isinstance(obj, string_types):
        try:
            obj = eval(obj, globals, locals)
        except Exception as e:
            raise JSONEvalError(obj, path, e)
    return obj


def parse_args(*args, **kwargs):
    """
    Parse a set of command line arguments. Returns a :py:mod:`argparse`
    ``args`` object with the following fields:
    
    * specification (str): The filename of the bitstream specification to read.
    * bitstream (str): The filename of the bitstream to write.
    * verbose (int): The number of times the --verbose argument was given
    """
    parser = ArgumentParser(
        description="""
        Generate a VC-2 bitstream from a JSON specification.
    """
    )

    parser.add_argument(
        "specification",
        help="""
            The filename of the JSON bitstream specification.
        """,
    )

    parser.add_argument(
        "bitstream",
        help="""
            The filename to write the generated bitstream to.
        """,
    )

    parser.add_argument(
        "--verbose",
        "-v",
        default=0,
        action="count",
        help="""
            Show a full Python traceback on error.
        """,
    )

    args = parser.parse_args(*args, **kwargs)

    return args


def main(*args, **kwargs):
    args = parse_args(*args, **kwargs)

    try:
        with open(args.specification, "r") as f:
            specification = json.load(f)
    except ValueError as exc:
        sys.stderr.write("Invalid JSON: {}\n".format(exc))
        return 2
    except Exception as exc:
        sys.stderr.write("Could not open {}: {}\n".format(args.specification, exc,))
        return 1

    specification = remove_comments_from_json(specification)

    eval_globals = {"AUTO": AUTO}
    for name in tables.__all__:
        eval_globals[name] = getattr(tables, name)
    for name in vc2_math.__all__:
        eval_globals[name] = getattr(vc2_math, name)
    try:
        specification = evaluate_strings_in_json(specification, eval_globals)
    except JSONEvalError as exc:
        sys.stderr.write("Error in Python expression: {}\n".format(exc))
        return 3

    if not isinstance(specification, dict):
        sys.stderr.write(
            "Specification must contain a JSON object (got {})\n".format(
                type(specification).__name__,
            )
        )
        return 4

    if not (
        "data_units" in specification
        and len(specification["data_units"]) >= 1
        and specification["data_units"][-1].get("parse_info", {}).get("parse_code")
        == tables.ParseCodes.end_of_sequence
    ):
        sys.stderr.write("Specification must end with an 'end of sequence' data unit\n")
        return 5

    def show_traceback():
        if args.verbose > 0:
            traceback.print_exc()

    with open(args.bitstream, "wb") as f:
        writer = BitstreamWriter(f)

        try:
            autofill_picture_number(specification)
            (
                next_parse_offsets_to_autofill,
                previous_parse_offsets_to_autofill,
            ) = autofill_parse_offsets(specification)

            with Serialiser(writer, specification, vc2_default_values_with_auto) as ser:
                parse_sequence(ser, State())

            autofill_parse_offsets_finalize(
                writer,
                ser.context,
                next_parse_offsets_to_autofill,
                previous_parse_offsets_to_autofill,
            )
        except FixedDictKeyError as exc:
            show_traceback()
            sys.stderr.write(
                "The field {!r} is not allowed in {} (allowed fields: {})\n".format(
                    exc.args[0],
                    ser.describe_path(),
                    ", ".join(map(repr, exc.fixeddict_class.entry_objs)),
                )
            )
            return 6
        except UnusedTargetError as exc:
            show_traceback()
            sys.stderr.write("Unused field {}\n".format(exc.args[0]))
            return 7
        except Exception as exc:
            show_traceback()
            sys.stderr.write(
                "Unable to construct bitstream at {}: {}: {} (is a sequence or fragment header missing?)\n".format(
                    ser.describe_path(), type(exc).__name__, exc,
                )
            )
            return 8
        writer.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())
