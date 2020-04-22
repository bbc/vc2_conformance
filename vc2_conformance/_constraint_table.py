"""
:py:mod:`vc2_conformance._constraint_table`
===========================================

Certain bitstream conformance rules are best expressed by enumerating valid
combinations of values -- e.g. restrictions imposed by VC-2's levels. This
module provides various tools for testing combinations of values against these
tables of constraints.

Tutorial
--------

Constraint tables enumerate allowed combinations of values as a list of
dictionaries containing :py;class:`ValueSet` objects.  are described using as a
list of dictionaries defining acceptable combinations. Take for eaxmple the
following example::

    >>> real_foods = [
    ...     {"type": ValueSet("tomato"), "color": ValueSet("red")},
    ...     {"type": ValueSet("apple"), "color": ValueSet("red", "green")},
    ...     {"type": ValueSet("beetroot"), "color": ValueSet("purple")},
    ... ]

We can check dictionaries of values against this permitted list of
combinations using :py:func:`is_allowed_combination`::

    >>> is_allowed_combination(real_foods, {"type": "tomato", "color": "red"})
    True
    >>> is_allowed_combination(real_foods, {"type": "apple", "color": "red"})
    True
    >>> is_allowed_combination(real_foods, {"type": "apple", "color": "green"})
    True
    >>> is_allowed_combination(real_foods, {"type": "apple", "color": "purple"})
    False

We can also check subsets of values, for example::

    >>> is_allowed_combination(real_foods, {"type": "apple"})
    True
    >>> is_allowed_combination(real_foods, {"color": "purple"})
    True
    >>> is_allowed_combination(real_foods, {"color": "yellow"})
    False

This behaviour means that if properties are being read incrementally we can
detect the first value to leave the allowed range. We can also use
:py:func:`allowed_values_for` to determine acceptable values for a particular
field given the current rules. For example::

    >>> allowed_values_for(real_foods, "color")
    ValueSet('red', 'green', 'purple')
    >>> allowed_values_for(real_foods, "color", {"type": "apple"})
    ValueSet('red', 'green')
    >>> allowed_values_for(real_foods, "type", {"color": "red"})
    ValueSet('apple', 'tomato')


API
---

.. autoclass:: ValueSet

.. autoclass:: AnyValue

.. autofunction:: filter_allowed_values

.. autofunction:: is_allowed_combination

.. autofunction:: allowed_values_for


Reading from CSV
----------------

A Constraint table can be read from CSV files using the following function:

.. autofunction:: read_constraints_from_csv

"""

import csv

from vc2_data_tables.csv_readers import is_ditto


__all__ = [
    "ValueSet",
    "AnyValue",
    "filter_allowed_values",
    "is_allowed_combination",
    "allowed_values_for",
    "read_constraints_from_csv",
]


class ValueSet(object):
    """
    Represents a set of allowed values. May consist of anything from a single
    value, a range of values or a combination of several of these.
    """

    def __init__(self, *values_and_ranges):
        """
        Parameters
        ==========
        *values_and_ranges : value, or (lower_value, upper_value)
            Sets the initial set of values and ranges to be matched
        """

        # Individual values explicitly included in this value set
        self._values = set()

        # A series of (lower_bound, upper_bound) tuples which give *incuslive*
        # ranges of values which are permitted.
        self._ranges = set()

        for value_or_range in values_and_ranges:
            if isinstance(value_or_range, tuple):
                self.add_range(*value_or_range)
            else:
                self.add_value(value_or_range)

    def add_value(self, value):
        """
        Add a single value to the set.
        """
        # Don't add duplicates
        if value not in self:
            self._values.add(value)

    def add_range(self, lower_bound, upper_bound):
        """
        Add the range of values between the two inclusive bounds to the set.
        """
        # Remove any single values which are encompassed by this new range
        for value in list(self._values):
            if lower_bound <= value <= upper_bound:
                self._values.remove(value)

        # Combine this range with any existing ranges where possible
        ranges_to_remove = []
        for other_lower_bound, other_upper_bound in self._ranges:
            if lower_bound <= other_upper_bound and other_lower_bound <= upper_bound:
                ranges_to_remove.append((other_lower_bound, other_upper_bound))
                lower_bound = min(lower_bound, other_lower_bound)
                upper_bound = max(upper_bound, other_upper_bound)
        for lower_upper in ranges_to_remove:
            self._ranges.remove(lower_upper)

        self._ranges.add((lower_bound, upper_bound))

    def __contains__(self, value):
        """
        Test if a value is a member of this set.
        """
        if value in self._values:
            return True

        for lower_bound, upper_bound in self._ranges:
            if lower_bound <= value <= upper_bound:
                return True

        return False

    def is_disjoint(self, other):
        """
        Test if this :py:class:`ValueSet` is disjoint from another -- i.e. they
        share no common values.
        """
        if isinstance(other, AnyValue):
            # Special case: only the empty ValueSet is disjoint from the
            # AnyValue value set.
            if self._values or self._ranges:
                return False
            else:
                return True
        else:
            # Check for values which overlap
            for a, b in [(self, other), (other, self)]:
                for value in a._values:
                    if value in b:
                        return False

            # Check for ranges which overlap
            for a, b in [(self, other), (other, self)]:
                for start, end in a._ranges:
                    if start in b:
                        return False
                    if end in b:
                        return False

            return True

    def __eq__(self, other):
        return (
            not isinstance(other, AnyValue)
            and self._values == other._values
            and self._ranges == other._ranges
        )

    def __add__(self, other):
        """
        Combine two :py:class:`ValueSet` objects into a single object
        containing the union of both of their values.
        """
        if isinstance(other, AnyValue):
            return AnyValue()
        else:
            out = type(self)()

            for value in self._values:
                out.add_value(value)
            for value in other._values:
                out.add_value(value)

            for lower, upper in self._ranges:
                out.add_range(lower, upper)
            for lower, upper in other._ranges:
                out.add_range(lower, upper)

            return out

    def __iter__(self):
        """
        Iterate over the values and (lower_bound, upper_bound) tuples in this
        value set.
        """
        for value in self._values:
            yield value
        for range in self._ranges:
            yield range

    def iter_values(self):
        """
        Iterate over the values (including the enumerated values of ranges) in
        this value set.
        """
        for value in self._values:
            yield value
        for low, high in self._ranges:
            for value in range(low, high + 1):
                yield value

    def __repr__(self):
        return "{}({})".format(type(self).__name__, ", ".join(map(repr, self)),)

    def __str__(self):
        """
        Produce a human-readable description of the permitted values.
        """
        values_and_ranges = sorted([(v,) for v in self._values] + list(self._ranges))
        if len(values_and_ranges) == 0:
            return "{<no values>}"
        else:
            return "{{{}}}".format(
                ", ".join(
                    repr(value[0]) if len(value) == 1 else "{!r}-{!r}".format(*value)
                    for value in values_and_ranges
                )
            )


class AnyValue(ValueSet):
    """
    Like :py:class:`ValueSet` but represents a 'wildcard' set of values which
    contains all possible values.
    """

    def __init__(self):
        pass

    def add_value(self):
        raise AttributeError("add_value")

    def add_range(self):
        raise AttributeError("add_range")

    def __contains__(self, value):
        return True

    def is_disjoint(self, other):
        if isinstance(other, AnyValue):
            return False
        else:
            return other.is_disjoint(self)

    def __eq__(self, other):
        return isinstance(other, AnyValue)

    def __add__(self, other):
        return AnyValue()

    def __iter__(self):
        raise AttributeError("__iter__")

    def iter_values(self):
        raise AttributeError("iter_values")

    def __repr__(self):
        return "{}()".format(type(self).__name__)

    def __str__(self):
        return "{<any value>}"


def filter_allowed_values(allowed_values, values):
    """
    Return the subset of ``allowed_values`` entries which match all of the
    values in ``values``.
    """
    return [
        combination
        for combination in allowed_values
        if all(
            key in combination and value in combination[key]
            for key, value in values.items()
        )
        or len(combination) == 0  # Special case: 'catch all' rule
    ]


def is_allowed_combination(allowed_values, values):
    """
    Check to see if the candidate dictionary holds a permissible collection of
    values according to the provided constraint table. A valid candidate may
    only contain a subset of the fields defined by the constraints in the
    constraint table.

    Parameters
    ==========
    allowed_values: [{key: :py:class:`ValueSet`, ...}, ...]
    values : {key: value}
    """
    return len(filter_allowed_values(allowed_values, values)) > 0


def allowed_values_for(allowed_values, key, values={}, any_value=AnyValue()):
    """
    Return the :py:class:`ValueSet` which matches the allowable values which
    might be added to the specified key given the existing values in
    ``values``.

    Parameters
    ==========
    allowed_values : [{key: :py:class:`ValueSet`, ...}, ...]
    key : key
    values : {key: value, ...}
        Optional. The values already chosen. (Default: assume nothing chosen).
    any_value : :py:class:`ValueSet`
        Optional. If :py:class:`AnyValue` is allowed, this will be substituted
        instead. This may be useful when :py:class:`AnyValue` is actually just
        short-hand for a more concrete set of values.
    """
    out = ValueSet()

    for allowed in filter_allowed_values(allowed_values, values):
        out += allowed.get(key, ValueSet())

    if isinstance(out, AnyValue):
        return any_value
    else:
        return out


def read_constraints_from_csv(csv_filename):
    r"""
    Reads a table of constraints from a CSV file.

    The CSV file should be arranged with each row describing a particular value
    to be constrained and each column defining an allowed combination of
    values.

    Empty rows and rows containing only '#' prefixed values will be skipped.

    The first column will be treated as the keys being constrained, remaining
    columns should contain allowed combinations of values. Each of these values
    will be converted into a :py:class:`ValueSet` as follows::

    * Values which contain integers will be converted to ``int``
    * Values which contain 'TRUE' or 'FALSE' will be converted to ``bool``
    * Values containing a pair of integers separated by a ``-`` will be treated
      as an incusive range.
    * Several comma-separated instances of the above will be combined into a
      single :py:class:`ValueSet`.
    * The value 'any' will be substituted for :py:class:`AnyValue`.
    * Empty cells will be converted into empty :py:class:`ValueSet`\ s.
    * Cells which contain only a pair of quotes (e.g. ``"``, i.e. ditto) will
      be assigned the same value as the column to their left.

    The read constraint table will be returned as a list of dictionaries (one
    per column) as expected by the functions in
    :py:mod:`vc2_conformance._constraint_table`.
    """
    out = []

    with open(csv_filename) as f:
        for row in csv.reader(f):
            # Skip empty lines
            if all(not cell.strip() or cell.strip().startswith("#") for cell in row):
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
                            True
                            if s.strip().lower() == "true"
                            else False
                            if s.strip().lower() == "false"
                            else int(s)
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
