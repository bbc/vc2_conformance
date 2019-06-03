"""
:py:mod:`vc2_conformance._constraint_table`
===========================================

Certain bitstream conformance rules are best expressed by enumerating valid
combinations of values -- e.g. restrictions imposed by VC-2's levels. This
module provides various tools for testing combinations of values against these
tables of constraints.

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

"""


__all__ = [
    "ValueSet",
    "AnyValue",
    "filter_allowed_values",
    "is_allowed_combination",
    "allowed_values_for",
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
        self._values = set(v for v in values_and_ranges if not isinstance(v, tuple))
        
        # A series of (lower_bound, upper_bound) tuples which give *incuslive*
        # ranges of values which are permitted.
        self._ranges = set(v for v in values_and_ranges if isinstance(v, tuple))
    
    def add_value(self, value):
        """
        Add a single value to the set.
        """
        self._values.add(value)
    
    def add_range(self, lower_bound, upper_bound):
        """
        Add the range of values between the two inclusive bounds to the set.
        """
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
    
    def __eq__(self, other):
        return (
            not isinstance(other, AnyValue) and
            self._values == other._values and
            self._ranges == other._ranges
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
    
    def __repr__(self):
        return "{}({})".format(
            type(self).__name__,
            ", ".join(map(repr, self)),
        )
    
    def __str__(self):
        """
        Produce a human-readable description of the permitted values.
        """
        values_and_ranges = sorted([(v, ) for v in self._values] + list(self._ranges))
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
    
    def __eq__(self, other):
        return isinstance(other, AnyValue)
    
    def __add__(self, other):
        return AnyValue()
    
    def __iter__(self):
        raise AttributeError("__iter__")
    
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
        combination for combination in allowed_values
        if all(
            key in combination and value in combination[key]
            for key, value in values.items()
        ) or len(combination) == 0  # Special case: 'catch all' rule
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


def allowed_values_for(allowed_values, key, values={}):
    """
    Return the :py:class:`ValueSet` which matches the allowable values which
    might be added to the specified key given the existing values in
    ``values``.
    """
    out = ValueSet()
    
    for allowed in filter_allowed_values(allowed_values, values):
        out += allowed.get(key, ValueSet())
    
    return out
