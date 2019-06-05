# -*- coding: utf-8 -*-

"""
:py:mod:`vc2_conformance.tables._csv_reading`: Internal table reading routines
==============================================================================

These routines are used to load and parse constants and tables of values from
CSV files into :py:class:`~enum.IntEnum` enums and dictionary-based tables.
"""

import re
import os
import csv

from enum import IntEnum

from collections import OrderedDict, defaultdict

from vc2_conformance._constraint_table import (
    ValueSet,
    AnyValue,
)


__all__ = [
    "is_ditto",
    "read_enum_from_csv",
    "read_lookup_from_csv",
    "read_constraints_from_csv",
    "to_list",
    "to_enum_from_index",
    "to_enum_from_name",
    "to_dict_value",
]


QUOTE_CHARS = [
    '"',  # ASCII double quote
    "“",  # Unicode double opening quote
    "”",  # Unicode double closing quote
    "'",  # ASCII single quote
    "’",  # Unicode single opening quote
    "’",  # Unicode single closing quote
    "`",  # ASCII tick
]
"""
The various unicode characters which spreadsheet programs (unhelpfully) replace
quotes with.

NB: Under Python 2, these strings are intentionally non-unicode strings (and so
will be interpreted as raw bytes) while in Python 3 these will be ordinary
unicode strings.
"""


def is_ditto(string):
    """Test if a cell's value string just indicates 'ditto'"""
    # NB: To enable backward compatibility with Python 2 (and its messy
    # handling of Unicode), this function works as if the input is a byte
    # string and avoids text-handling routines.
    
    quotes_removed = string
    for quote_char in QUOTE_CHARS:
        # This technically isn't a robust way to perform byte-wise unicode
        # character substitutions but given this simple application of just
        # detecting unicode quotes inserted by spreadsheet packages this is
        # excusable
        quotes_removed = quotes_removed.replace(quote_char, "")
    
    return quotes_removed != string and len(quotes_removed.strip()) == 0

def csv_path(csv_filename):
    """
    Given a CSV filename in the ``vc2_conformance/tables/`` directory, returns
    a complete path to that file.
    """
    return os.path.join(os.path.dirname(__file__), csv_filename)


def read_csv_without_comments(csv_filename):
    """
    Given a CSV filename in the ``vc2_conformance/tables/`` directory, returns
    a list of dictionaries, one per row, containing the values in the CSV (as
    read by :py:class:`csv.DictReader`).
    """
    csv_filename = csv_path(csv_filename)
    
    # Find the first non-empty/comment row in the CSV
    with open(csv_filename) as f:
        for first_non_empty_row, cells in enumerate(csv.reader(f)):
            if any(cell.strip() != "" and not cell.strip().startswith("#")
                   for cell in cells):
                break
    
    with open(csv_filename) as f:
        # Skip empty/comment rows
        for _ in range(first_non_empty_row):
            f.readline()
        
        return list(csv.DictReader(f))


def read_enum_from_csv(csv_filename, enum_name):
    """
    Create a :py:class:`IntEnum` class from the values listed in a CSV file.
    
    The 'name' field will be used as enum value names and the (integer) 'index'
    column will be used for values. Names must be unique, valid Python identifiers.
    
    Parameters
    ==========
    csv_filename : str
        Filename of the CSV file to read (relative to the
        vc2_conformance/tables directory). Column headings will be read from
        the first row which isn't empty or contains only '#' prefixed values.
    enum_name : str
        The name of the :py:class:`IntEnum` class to be created.
    
    Returns
    =======
    :py:class:`IntEnum`
    """
    rows = read_csv_without_comments(csv_filename)
    
    enum_values = OrderedDict()
    for row in rows:
        # Skip rows without names/indices
        if (not row["index"].strip() or is_ditto(row["index"]) or
                not row["name"].strip() or is_ditto(row["name"])):
            continue
        
        index = int(row["index"].strip())
        name = str(row["name"].strip())
        
        enum_values[name] = index
    
    return IntEnum(enum_name, enum_values)


def read_lookup_from_csv(
    csv_filename,
    index_enum_type,
    namedtuple_type,
    type_conversions={},
):
    """
    Create a dictionary which looks up named tuples by :py:class:`IntEnum`
    enumerated indexes.
    
    Empty cells are treated as containing the same value as the previous row.
    Completely empty rows are ignored.
    
    Parameters
    ==========
    csv_filename : str
        Filename of the CSV file to read (relative to the
        vc2_conformance/tables directory). Column headings will be read from
        the first row which isn't empty or contains only '#' prefixed values.
    index_enum_type : :py:class:`enum.IntEnum`
        The :py:class:`enum.IntEnum` which enumerates all of the valid index
        values. The index for each row will be taken from the 'index' column.
    namedtuple_type : :py:class:`collections.namedtuple`
        A namedtuple type which will be populated with the values for each row
        in the CSV.
    type_conversions : {column_name: func(str) -> value, ...}
        An optional converter function which will be used to convert each
        column's values from strings into some other type.
    
    Returns
    =======
    :py:class:`collections.OrderedDict` : {index: row_tuple, ...}
    """
    rows = read_csv_without_comments(csv_filename)
    
    column_values = defaultdict(str)
    
    lookup = OrderedDict()
    for row in rows:
        # Skip completely empty/comment-only rows
        if all(not cell.strip() or cell.strip().startswith("#")
               for key, cell in row.items()
               if key is not None):
            continue
        
        # Get values for this row (falling back on previous ones if absent)
        for field in namedtuple_type._fields + ("index", ):
            if row[field].strip() and not is_ditto(row[field]):
                column_values[field] = row[field]
        
        index = index_enum_type(int(column_values["index"]))
        
        value = namedtuple_type(**{
            field: type_conversions.get(field, str)(column_values[field])
            for field in namedtuple_type._fields
        })
        
        lookup[index] = value
    
    return lookup


def read_constraints_from_csv(csv_filename):
    """
    Reads a table of constraints (see
    :py:mod:`vc2_conformance._constraint_table`) from a CSV file.
    
    The CSV file should be arranged with each row describing a particular value
    to be constrained and each column defining an allowed combination of
    values.
    
    Empty rows and rows containing only '#' prefixed values will be skipped.
    
    The first column will be treated as the keys being constrained, remaining
    columns should contain allowed combinations of values. Each of these values
    will be converted into a
    :py:class:`~vc2_conformance._constraint_table.ValueSet` as follows::
    
    * Values which contain integers will be converted to ``int``
    * Values which contain 'TRUE' or 'FALSE' will be converted to ``bool``
    * Values containing a pair of integers separated by a ``-`` will be treated
      as an incusive range.
    * Several comma-separated instances of the above will be combined into a
      single ValueSet.
    * The value 'any' will be substituted for
      :py:class:`~vc2_conformance._constraint_table.AnyValue`.
    * Empty cells will be converted into empty ValueSets.
    * Cells which contain only a pair of quotes (e.g. ``"``, i.e. ditto) will
      be assigned the same value as the column to their left.
    
    The read constraint table will be returned as a list of dictionaries (one
    per column) as expected by the functions in
    :py:mod:`vc2_conformance._constraint_table`.
    """
    out = []
    
    with open(csv_path(csv_filename)) as f:
        for row in csv.reader(f):
            # Skip empty lines
            if all(not cell.strip() or cell.strip().startswith("#")
                   for cell in row):
                continue
            
            # Add extra constraint sets as required
            for _ in range(len(out), len(row) - 1):
                out.append({})
            
            # Populate this row's values
            key = row[0]
            last_value = ValueSet()
            for i, column in enumerate(row[1:]):
                value = ValueSet()
                if is_ditto(column):
                    value += last_value
                elif column.strip().lower() == "any":
                    value = AnyValue()
                else:
                    for value_string in column.split(","):
                        values = [
                            True if s.strip().lower() == "true" else
                            False if s.strip().lower() == "false" else
                            int(s)
                            for s in value_string.partition("-")[::2]
                            if s
                        ]
                        if len(values) == 1:
                            value.add_value(values[0])
                        elif len(values) == 2:
                            value.add_range(values[0], values[1])
                out[i][key] = value
                last_value = value
    
    return out


def to_list(type_conversion):
    """
    Returns a function which takes a comma-separated string and returns a list
    of values converted by the supplied 'type_conversion' function.
    """
    def func(string):
        return [
            type_conversion(value)
            for value in filter(None, re.split(r"\s*,\s*", string))
        ]
    
    return func


def to_enum_from_index(enum_type):
    """
    Returns a function which maps strings containing enum value integers to
    their corresponding enum_type values.
    """
    def func(string):
        return enum_type(int(string))
    
    return func


def to_enum_from_name(enum_type):
    """
    Returns a function which maps strings containing enum value names to their
    corresponding enum_type values.
    """
    def func(string):
        return getattr(enum_type, string)
    
    return func

def to_dict_value(dictionary):
    """
    Returns a function which maps strings to their corresponding value in the
    supplied dictionary.
    """
    return dictionary.get


def read_quantisation_matrices_from_csv(csv_filename):
    """
    Read a table of preset quantisation matrices from a CSV.
    
    The CSV format is similar to (Table D.1) - (Table D.8).  The following
    columns will be present:
    
    * ``wavelet_index``: A wavelet transform index.
    * ``wavelet_index_ho``: A wavelet transform index.
    * ``dwt_depth_ho``: A horizontal-only transform index
    * ``level``: A transform level
    * ``orientations``: A comma-separated list of orientations (i.e. L, H, LL,
      HL, LH, HH)
    * Several columns named ``dwt_depth=n`` where ``n`` is an integer giving
      the dwt_depth the values in that column correspond to. The values in this
      column should be a comma-separated list of quantisation matrix values
      corresponding to the ``orientations`` specified for that row.
    
    Empty rows and rows containing only "#" prefixed cells are ignored. A cell
    which contains a ditto symbol (i.e. ``"``) will inherit the value of the
    cell above it.
    
    Parameters
    ==========
    csv_filename : str
        Filename of the CSV file to read (relative to the
        vc2_conformance/tables directory).
    
    Returns
    =======
    quantisation_matrices : {(wavelet_index, wavelet_index_ho, dwt_depth, dwt_depth_ho): {level: {orientation: value, ...}, ...}, ...}
        Where:
        
        * ``wavelet_index`` and ``wavelet_index_ho`` are :py:class:`WaveletFilters`
          values
        * ``dwt_depth`` and ``dwt_depth_ho`` are transform depths (integers)
        * ``level`` is the transform level (integer)
        * ``orientation`` is one of `"L"`, `"H"`, `"LL"``, `"HL"``, `"LH"`` or `"HH"``
    """
    rows = read_csv_without_comments(csv_filename)
    last_row = defaultdict(str)
    quantisation_matrices = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        # Skip completely empty/comment-only rows
        if all(not cell.strip() or cell.strip().startswith("#")
               for key, cell in row.items()
               if key is not None):
            continue
        
        # Back-fill row values with dittos
        for field in row:
            if is_ditto(row[field]):
                row[field] = last_row[field]
        last_row = row
        
        wavelet_index = int(row["wavelet_index"].strip())
        wavelet_index_ho = int(row["wavelet_index_ho"].strip())
        dwt_depth_ho = int(row["dwt_depth_ho"].strip())
        level = int(row["level"].strip())
        orientations = row["orientations"].split(",")
        
        for column_name in filter(
            lambda col: re.match(r"\s*dwt_depth\s*=\s*[0-9]+\s*", col),
            row,
        ):
            dwt_depth = int(column_name.partition("=")[2].strip())
            values = row[column_name].split(",")
            
            for orientation, value in zip(orientations, values):
                if value.strip():
                    quantisation_matrices[(
                        wavelet_index,
                        wavelet_index_ho,
                        dwt_depth,
                        dwt_depth_ho,
                    )][
                        level
                    ][
                        orientation.strip()
                    ] = int(value.strip())
    
    return quantisation_matrices
