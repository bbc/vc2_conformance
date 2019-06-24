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
    Serialiser,
    ParseInfo,
    Padding,
    AuxiliaryData,
    PictureHeader,
    FragmentHeader,
    vc2_default_values,
    parse_sequence,
    BitstreamWriter,
    UnusedTargetError,
)

from vc2_conformance.fixeddict import FixedDictKeyError

from vc2_conformance.tables import ParseCodes, PARSE_INFO_HEADER_BYTES

from vc2_conformance import tables, vc2_math


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
            obj[key] = evaluate_strings_in_json(obj[key], globals, locals, path + (key, ))
    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = evaluate_strings_in_json(obj[i], globals, locals, path + (i, ))
    elif isinstance(obj, string_types):
        try:
            obj = eval(obj, globals, locals)
        except Exception as e:
            raise JSONEvalError(obj, path, e)
    return obj


class NoAutomaticValueAvailableError(Exception):
    """
    Thrown when an 'AUTO' is encountered for a bitstream value where no
    automatic functionality exists.
    """


class EmptyParseInfoFound(Exception):
    """
    Thrown when a data unit is provided with an empty parse info definition.
    This may be used to terminate the bitstream prematurely (without an
    end-of-sequence)
    """


class SmartSerialiser(Serialiser):
    """
    A :py:class:`vc2_conformance.bitstream.Serialiser` with a number of
    additional features aimed at 1) supporting context dictionaries
    deserialised from JSON and 2) supporting more advanced 'default'/automatic
    value filling.
    """
    
    # A sentinel value indicating some smart 'automatic' value should be
    # chosen.
    AUTO = Sentinel("AUTO")
    
    
    def __init__(self, *args, **kwargs):
        super(SmartSerialiser, self).__init__(*args, **kwargs)
        
        # Use a local copy of the default values (since we'll be mutating
        # these)
        self.default_values = deepcopy(self.default_values)
        
        # Log of byte offsets of all parse_info blocks in the stream
        self._parse_info_offsets = []
        
        # Indices of ParseInfo blocks in which the next_parse_offset field
        # should be overwritten with the correct value after serialisation
        # finishes.
        self._next_parse_offset_values_to_update = []
        
        # The latest picture number to be used in the stream
        self._last_picture_number = -1
    
    def _get_context_value(self, target):
        value = super(SmartSerialiser, self)._get_context_value(target)
        
        # Stop if an empty parse info is encountered
        if target == "parse_info_prefix" and type(self.cur_context) == ParseInfo:
            if not self.cur_context:
                raise EmptyParseInfoFound()
        
        # Log parse_info block offsets
        if target == "parse_info_prefix" and type(self.cur_context) == ParseInfo:
            num_bytes, num_bits = self.io.tell()
            assert num_bits == 7
            self._parse_info_offsets.append(num_bytes)
        
        # Update the default value to be the current value
        context_type = type(self.cur_context)
        if context_type not in self.default_values:
            self.default_values[context_type] = {}
        self.default_values[context_type][target] = value
        
        if value is SmartSerialiser.AUTO:
            value = self._get_auto(target)
        
        # Log picture numbers
        if target == "picture_number" and type(self.cur_context) in (PictureHeader, FragmentHeader):
            self._last_picture_number = value
        
        return value
    
    def _get_auto(self, target):
        if target == "next_parse_offset" and type(self.cur_context) == ParseInfo:
            return self._get_auto_next_parse_offset()
        elif target == "previous_parse_offset" and type(self.cur_context) == ParseInfo:
            return self._get_auto_previous_parse_offset()
        elif target == "picture_number" and type(self.cur_context) in (PictureHeader, FragmentHeader):
            return self._get_auto_picture_number()
        else:
            raise NoAutomaticValueAvailableError(self.describe_path(target))
    
    def _get_auto_next_parse_offset(self):
        parse_code = self.context["_state"]["parse_code"]
        if parse_code == ParseCodes.end_of_sequence:
            # Special case: end of sequence always has a next parse offset of 0
            return 0
        elif parse_code in (ParseCodes.padding_data, ParseCodes.auxiliary_data):
            # Special case: padding and auxiliary data blocks lengths are
            # determined entirely from the next_parse_offset field. If set to
            # auto, we must look inside the context dictionary for these blocks
            # to determine the intended size.
            if parse_code == ParseCodes.padding_data:
                data_unit_field = "padding"
                data_unit_field_type = Padding
            elif parse_code == ParseCodes.auxiliary_data:
                data_unit_field = "auxiliary_data"
                data_unit_field_type = AuxiliaryData
            
            # Grab the aux/padding data in this data unit and calculate its
            # length directly
            data_unit_context = self._context_stack[-1]
            data_context = data_unit_context.get(data_unit_field, data_unit_field_type())
            aux_or_padding_data = data_context.get(
                "bytes",
                self.default_values.get(data_unit_field_type, b""),
            )
            
            return PARSE_INFO_HEADER_BYTES + len(aux_or_padding_data)
        else:
            # For simplicity of implementation the next parse offset is
            # initially set to an arbitrary value then later
            # overwritten with the correct value by
            # set_auto_next_parse_offset_values.
            self._next_parse_offset_values_to_update.append(len(self._parse_info_offsets) - 1)
            return 0
    
    def set_auto_next_parse_offset_values(self):
        """
        Call at the end of serialisation to go back and fill in all
        next_parse_offset fields which were set to AUTO.
        """
        end_num_bytes, end_num_bits = self.io.tell()
        
        for parse_info_index in self._next_parse_offset_values_to_update:
            if parse_info_index >= len(self._parse_info_offsets) - 1:
                next_parse_offset = end_num_bytes - self._parse_info_offsets[-1]
                if end_num_bits != 7:
                    next_parse_offset += 1
            else:
                next_parse_offset = (
                    self._parse_info_offsets[parse_info_index + 1] -
                    self._parse_info_offsets[parse_info_index]
                )
            
            self.io.seek(
                self._parse_info_offsets[parse_info_index] +
                4 +  # Skip past 32-bit parse info prefix
                1  # Skip past 8-bit parse code
            )
            self.io.write_uint_lit(4, next_parse_offset)
        
        self.io.seek(end_num_bytes, end_num_bits)
    
    def _get_auto_previous_parse_offset(self):
        if len(self._parse_info_offsets) < 2:
            return 0
        else:
            return self._parse_info_offsets[-1] - self._parse_info_offsets[-2]
    
    def _get_auto_picture_number(self):
        picture_number = self._last_picture_number
        
        # Increment unless we're mid-fragment
        if self.cur_context.get("fragment_slice_count", 0) == 0:
            picture_number = picture_number + 1
        
        picture_number &= 0xFFFFFFFF
        
        return picture_number
    
    def __exit__(self, exc_type, exc_value, traceback):
        super(SmartSerialiser, self).__exit__(exc_type, exc_value, traceback)
        self.set_auto_next_parse_offset_values()


vc2_default_values_with_auto = deepcopy(vc2_default_values)
"""
Like :py:data:`vc2_conformance.bitstreams.vc2_default_values` but with 'AUTO'
set as the default value for all fields which support it.
"""

vc2_default_values_with_auto[ParseInfo]["next_parse_offset"] = SmartSerialiser.AUTO
vc2_default_values_with_auto[ParseInfo]["previous_parse_offset"] = SmartSerialiser.AUTO
vc2_default_values_with_auto[PictureHeader]["picture_number"] = SmartSerialiser.AUTO
vc2_default_values_with_auto[FragmentHeader]["picture_number"] = SmartSerialiser.AUTO


def parse_args(*args, **kwargs):
    """
    Parse a set of command line arguments. Returns a :py:mod:`argparse`
    ``args`` object with the following fields:
    
    * specification (str): The filename of the bitstream specification to read.
    * bitstream (str): The filename of the bitstream to write.
    * verbose (int): The number of times the --verbose argument was given
    """
    parser = ArgumentParser(description="""
        Generate a VC-2 bitstream from a JSON specification.
    """)
    
    parser.add_argument("specification",
        help="""
            The filename of the JSON bitstream specification.
        """
    )
    
    parser.add_argument("bitstream",
        help="""
            The filename to write the generated bitstream to.
        """
    )
    
    parser.add_argument("--verbose", "-v", default=0, action="count",
        help="""
            Show a full Python traceback on error.
        """
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
        sys.stderr.write("Could not open {}: {}\n".format(
            args.specification,
            exc,
        ))
        return 1
    
    specification = remove_comments_from_json(specification)
        
    eval_globals = {"AUTO": SmartSerialiser.AUTO}
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
        sys.stderr.write("Specification must contain a JSON object (got {})\n".format(
            type(specification).__name__,
        ))
        return 4
    
    def show_traceback():
        if args.verbose > 0:
            traceback.print_exc()
    
    with open(args.bitstream, "wb") as f:
        w = BitstreamWriter(f)
        try:
            with SmartSerialiser(w, specification, vc2_default_values_with_auto) as ser:
                parse_sequence(ser, State())
        except EmptyParseInfoFound:
            show_traceback()
            sys.stderr.write("Empty 'parse info' specification at {} (missing end of sequence?)\n".format(
                ser.describe_path(),
            ))
            return 5
        except FixedDictKeyError as exc:
            show_traceback()
            sys.stderr.write("The field {!r} is not allowed in {} (allowed fields: {})\n".format(
                exc.args[0],
                ser.describe_path(),
                ", ".join(map(repr, exc.fixeddict_class.entry_objs))
            ))
            return 6
        except UnusedTargetError as exc:
            show_traceback()
            sys.stderr.write("Unused field {}\n".format(exc.args[0]))
            return 7
        except Exception as exc:
            show_traceback()
            sys.stderr.write("Unable to construct bitstream at {}: {}: {} (is a sequence or fragment header missing?)\n".format(
                ser.describe_path(),
                type(exc).__name__,
                exc,
            ))
            return 8
        w.flush()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
