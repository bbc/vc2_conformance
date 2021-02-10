r"""
The :py:mod:`vc2_conformance.constraint_table` module describes a constraint
system which is used to describe restrictions imposed by VC-2 levels. See
:py:data:`vc2_conformance.level_constraints.LEVEL_CONSTRAINTS` for the actual
level constraints table.

Tutorial
--------

Constraint tables enumerate allowed combinations of values as a list of
dictionaries containing :py:class:`ValueSet` objects. Each dictionary describes
a valid combination of values. In the contrived running example below we'll
define valid food-color combinations (rather than VC-2 codec options)::

    >>> real_foods = [
    ...     {"type": ValueSet("tomato"), "color": ValueSet("red")},
    ...     {"type": ValueSet("apple"), "color": ValueSet("red", "green")},
    ...     {"type": ValueSet("beetroot"), "color": ValueSet("purple")},
    ... ]

We can check dictionaries of values against this permitted list of
combinations using :py:func:`is_allowed_combination`::

    >>> # Allowed combinations
    >>> is_allowed_combination(real_foods, {"type": "tomato", "color": "red"})
    True
    >>> is_allowed_combination(real_foods, {"type": "apple", "color": "red"})
    True
    >>> is_allowed_combination(real_foods, {"type": "apple", "color": "green"})
    True

    >>> # Purple apples? I don't think so...
    >>> is_allowed_combination(real_foods, {"type": "apple", "color": "purple"})
    False

But we don't have to check a complete set of values. For example, we can check if a
particular color is valid for any foodstuff::

    >>> is_allowed_combination(real_foods, {"color": "red"})
    True
    >>> is_allowed_combination(real_foods, {"color": "yellow"})
    False

This behaviour allows us to detect the first non-constraint-satisfying value
when values are obtained sequentially (as they are for a VC-2 bitstream). The
bitstream validator (:py:mod:`vc2_conformance.decoder`) uses this functionality
to check bitstream values conform to the constraints imposed by a specified
VC-2 level.

Given an incomplete set of values, we can use :py:func:`allowed_values_for` to
discover what values are permissible for values we've not yet assigned. For
example:

    >>> # If we have an apple, what colors can it be?
    >>> allowed_values_for(real_foods, "color", {"type": "apple"})
    ValueSet('red', 'green')

    >>> # If we have something red, what might it be?
    >>> allowed_values_for(real_foods, "type", {"color": "red"})
    ValueSet('apple', 'tomato')

This functionality is used by the test case generators and encoder
(:py:mod:`vc2_conformance.test_cases` and :py:mod:`vc2_conformance.encoder`) to
discover combinations of bitstream features which satisfy particular level
requirements.


:py:class:`ValueSet`
--------------------

.. autoclass:: ValueSet
    :members:
    :special-members: __init__, __contains__, __eq__, __add__, __iter__, __str__

.. autoclass:: AnyValue


Constraint tables
-----------------

A 'constraint table' is defined as a list of 'allowed combination' dictionaries.

An 'allowed combination' dictionary defines a :py:class:`ValueSet` for every
permitted key.

For example, the following is a constraint table containing three allowed
combination dictionaries::

    >>> real_foods = [
    ...     {"type": ValueSet("tomato"), "color": ValueSet("red")},
    ...     {"type": ValueSet("apple"), "color": ValueSet("red", "green")},
    ...     {"type": ValueSet("beetroot"), "color": ValueSet("purple")},
    ... ]

A set of values satisfies a constraint table if there is at least one allowed
combination dictionary which contains the specified combination of values. For
example, the following two dictionaries satisfy the constraint table::

    {"type": "apple", "color": "red"}

    {"color": "red"}

The first satisfies the constraint table because the combination of values
given appears in the second entry of the constraint table.

The second satisfies the constraint table because, even though it does not
define a value for every key, the key it does define is included in both the
first and second entries.

Meanwhile, the following dictionaries do *not* satisfy the constraint table::

    {"type": "apple", "color": "purple"}

    {"type": "beetroot", "color": "purple", "pickleable": True}

The first of these contains values which, in isolation, would be permitted by
the second and third entries of the table but which are not present together in
any table entries. Consequently, this value does not satisfy the table.

The second contains a 'pickleable' key which is not present in any of the
allowed combinations in constraint table and so does not satisfy the table.

The functions below may be used to interrogate a constraint table.

.. autofunction:: filter_constraint_table

.. autofunction:: is_allowed_combination

.. autofunction:: allowed_values_for


CSV format
----------

A Constraint table can be read from CSV files using the following function:

.. autofunction:: read_constraints_from_csv

"""

import csv

from vc2_data_tables.csv_readers import open_utf8, is_ditto


__all__ = [
    "ValueSet",
    "AnyValue",
    "filter_constraint_table",
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
        Create a :py:class:`ValueSet` containing the specified set of values::

            >>> no_values = ValueSet()
            >>> 100 in no_values
            False

            >>> single_value = ValueSet(100)
            >>> 100 in single_value
            True
            >>> 200 in single_value
            False

            >>> range_of_values = ValueSet((10, 20))
            >>> 9 in range_of_values
            False
            >>> 10 in range_of_values
            True
            >>> 11 in range_of_values
            True
            >>> 20 in range_of_values  # NB: Range is inclusive
            True
            >>> 21 in range_of_values
            False

            >>> many_values = ValueSet(100, 200, (300, 400))
            >>> 100 in many_values
            True
            >>> 200 in many_values
            True
            >>> 300 in many_values
            True
            >>> 350 in many_values
            True
            >>> 500 in many_values
            False

            >>> non_numeric = ValueSet("foo", "bar", "baz")
            >>> "foo" in non_numeric
            True
            >>> "nope" in non_numeric
            False

        Parameters
        ==========
        *values_and_ranges : value, or (lower_value, upper_value)
            Sets the initial set of values and (inclusive) ranges to be matched
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
        Test if a value is a member of this set. For example::

            >>> value_set = ValueSet(1, 2, 3)
            >>> 1 in value_set
            True
            >>> 100 in value_set
            False
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

    def __hash__(self):
        # Warning: This null-hash function is provided only to allow ValueSets
        # to be used as part of dictionary keys in non-performance sensitive
        # settings.
        return hash(0)

    def __eq__(self, other):
        return (
            not isinstance(other, AnyValue)
            and self._values == other._values
            and self._ranges == other._ranges
        )

    def __ne__(self, other):
        """Required under Python 2.x"""
        return not self.__eq__(other)

    def __add__(self, other):
        """
        Combine two :py:class:`ValueSet` objects into a single object
        containing the union of both of their values.

        For example::

            >>> a = ValueSet(123)
            >>> b = ValueSet((10, 20))
            >>> a + b
            ValueSet(123, (10, 20))
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
        value set in no particular order.
        """
        for value in self._values:
            yield value
        for range in self._ranges:
            yield range

    def iter_values(self):
        """
        Iterate over the values (including the enumerated values of ranges) in
        this value set in no particular order.
        """
        for value in self._values:
            yield value
        for low, high in self._ranges:
            for value in range(low, high + 1):
                yield value

    def __repr__(self):
        return "{}({})".format(
            type(self).__name__,
            ", ".join(map(repr, self)),
        )

    def __str__(self):
        """
        Produce a human-readable description of the permitted values.

        For example::

            >>> print(ValueSet())
            {<no values>}
            >>> print(ValueSet(1, 2, 3, (10, 20)))
            {1, 2, 3, 10-20}
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

    def add_value(self, value):
        pass

    def add_range(self, lower_bound, upper_bound):
        pass

    def __contains__(self, value):
        return True

    def is_disjoint(self, other):
        if isinstance(other, AnyValue):
            return False
        else:
            return other.is_disjoint(self)

    def __hash__(self):
        return hash(0)

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


def filter_constraint_table(constraint_table, values):
    """
    Return the subset of ``constraint_table`` entries which match all of the
    values in ``values``. That is, with the entries whose constraints are not
    met by the provided values removed.
    """
    return [
        allowed_combination
        for allowed_combination in constraint_table
        if all(
            key in allowed_combination and value in allowed_combination[key]
            for key, value in values.items()
        )
        or len(allowed_combination) == 0  # Special case: 'catch all' rule
    ]


def is_allowed_combination(constraint_table, values):
    """
    Check to see if the ``values`` dictionary holds an allowed combination of
    values according to the provided constraint table.

    .. note::

        A candidate containing only a subset of the keys listed in the
        constraint table is allowed if the fields it does define are a
        permitted combination.

    Parameters
    ==========
    constraint_table: [{key: :py:class:`ValueSet`, ...}, ...]
    values : {key: value}
    """
    return len(filter_constraint_table(constraint_table, values)) > 0


def allowed_values_for(constraint_table, key, values={}, any_value=AnyValue()):
    """
    Return a :py:class:`ValueSet` which matches all allowed values for the
    specified key, given the existing values defined in ``values``.

    Parameters
    ==========
    constraint_table : [{key: :py:class:`ValueSet`, ...}, ...]
    key : key
    values : {key: value, ...}
        Optional. The values already chosen. (Default: assume nothing chosen).
    any_value : :py:class:`ValueSet`
        Optional. If provided and :py:class:`AnyValue` is allowed, this value
        will be substituted instead. This may be useful when
        :py:class:`AnyValue` is being used as a short-hand for a more concrete
        set of values.
    """
    out = ValueSet()

    for allowed_combination in filter_constraint_table(constraint_table, values):
        out += allowed_combination.get(key, ValueSet())

    if isinstance(out, AnyValue):
        return any_value
    else:
        return out


def read_constraints_from_csv(csv_filename):
    r'''
    Reads a table of constraints from a CSV file.

    The CSV file should be arranged with each row describing a particular value
    to be constrained and each column defining an allowed combination of
    values.

    Empty rows and rows containing only '#' prefixed values will be skipped.

    The first column will be treated as the keys being constrained, remaining
    columns should contain allowed combinations of values. Each of these values
    will be converted into a :py:class:`ValueSet` as follows:

    * Values which contain integers will be converted to ``int``
    * Values which contain 'TRUE' or 'FALSE' will be converted to ``bool``
    * Values containing a pair of integers separated by a ``-`` will be treated
      as an incusive range.
    * Several comma-separated instances of the above will be combined into a
      single :py:class:`ValueSet`. (Cells containing comma-separated values
      will need to be enclosed in double quotes (``"``) in the CSV).
    * The value 'any' will be substituted for :py:class:`AnyValue`.
    * Empty cells will be converted into empty :py:class:`ValueSets <ValueSet>`.
    * Cells which contain only a pair of quotes (e.g. ``"``, i.e. ditto) will
      be assigned the same value as the column to their left. (This is encoded
      using four double quotes (``""""``) in CSV format).

    The read constraint table will be returned as a list of dictionaries (one
    per column) as expected by the functions in
    :py:mod:`vc2_conformance.constraint_table`.
    '''
    out = []

    with open_utf8(csv_filename) as f:
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
