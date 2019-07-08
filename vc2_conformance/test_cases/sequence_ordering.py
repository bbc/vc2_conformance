"""
:py:mod:`vc2_conformance.test_cases.sequence_ordering`: Generate valid sequence orderings
=========================================================================================

This module contains a utility for generating minimal sequences which conform
to a specified set of :py:mod:`~vc2_conformance._symbol_re` regular
expressions.

For example, if a test sequence containing (at least) a padding data unit is
required while meeting the sequence restrictions imposed by VC-2,
:py:func:`find_minimal_sequence` may be used::

    >>> from vc2_conformance.tables import ParseCodes
    >>> from vc2_conformance.test_cases.sequence_ordering import find_minimal_sequence
    
    >>> pattern = "sequence_header .* end_of_sequence"
    >>> find_minimal_sequence([ParseCodes.padding_data], pattern)
    [<ParseCodes.sequence_header: 0>, <ParseCodes.padding_data: 48>, <ParseCodes.end_of_sequence: 16>]
"""

from copy import deepcopy

from collections import deque

from vc2_conformance.tables import ParseCodes

from vc2_conformance._symbol_re import Matcher, WILDCARD, END_OF_SEQUENCE


class ImpossibleSequenceError(Exception):
    """
    Thrown whne :py:func:`find_minimal_sequence` is unable to find a suitable
    sequence of data units.
    """
    pass


def find_minimal_sequence(data_units, *patterns, **kwargs):
    """
    Find the shortest sequence of data unit types (i.e.
    :py:class:`vc2_conformance.tables.ParseCodes`) which is matched by the
    supplied set of regular expressions.
    
    Parameters
    ==========
    data_units : [:py:class:`vc2_conformance.tables.ParseCodes`, ...]
        The minimal set of entries which must be included in the sequence, in
        the order they are required to appear.
    patterns : str
        A series of :py:mod:`~vc2_conformance._symbol_re` regular expression
        specificeations whose symbols are the names given for the various parse
        codes defined in :py:class:`vc2_conformance.tables.ParseCodes`.
    depth_limit : int
        Keyword-only argument specifying the maximum number of non-target data
        units to try including before giving up. Defaults to 4.
    
    Returns
    =======
    data_units : [:py:class:`vc2_conformance.tables.ParseCodes`, ...]
        A sequence of data unit types which would be matched by the specified
        patterns.
    
    Raises
    ======
    ImpossibleSequenceError
        Thrown if no sequence of data units could be found which includes the
        required all of the data units while matching all of the supplied
        patterns.
    """
    # NB: Python 2.x doesn't directly support keyword-only oarguments
    depth_limit = kwargs.pop("depth_limit", 3)
    if kwargs:
        raise TypeError("find_minimal_sequence() got unuexpected keyword argument(s) {}".format(
            ", ".join(map(repr, kwargs)),
        ))
    
    data_units = [ParseCodes(c) for c in data_units]
    
    matchers = [Matcher(pattern) for pattern in patterns]
    
    # Perform a breadth-first search of the pattern space
    
    # Queue of candidates to try
    #     (data_units_so_far, data_units_remaining, matchers, this_depth_limit)
    # Where:
    # * data_units_so_far is the list of generated sequence so far
    # * data_units_remaining is the list of data units still to include
    # * matchers is a list of Matcher objects which have matched the
    #   data_units_so_far
    # * this_depth_limit is an integer giving the number of search levels
    #   remaining before giving up.
    queue = deque([
        ([], data_units, matchers, depth_limit),
    ])
    
    while queue:
        (
            data_units_so_far,
            data_units_remaining,
            matchers,
            this_depth_limit,
        ) = queue.popleft()
        
        # Try and match the next required symbool
        if len(data_units_remaining) == 0:
            if all(m.is_complete() for m in matchers):
                # Found a suitable matching sequence!
                return data_units_so_far
        else:
            if all(
                data_units_remaining[0].name in m.valid_next_symbols() or
                WILDCARD in m.valid_next_symbols()
                for m in matchers
            ):
                # The next data unit required has been matched by all matchers
                new_matchers = deepcopy(matchers)
                for m in new_matchers:
                    m.match_symbol(data_units_remaining[0].name)
                queue.append((
                    data_units_so_far + [data_units_remaining[0]],
                    data_units_remaining[1:],
                    new_matchers,
                    depth_limit,  # NB: Reset depth limit when a match is found
                ))
                continue
        
        # If we reach this point, no matching symbol was found above.
        
        if this_depth_limit <= 0:
            # Depth limit reached, give up on this branch of the search
            continue
        
        # Continue searching with any allowed symbol next
        valid_next_symbols = set([WILDCARD])
        for matcher in matchers:
            symbols = matcher.valid_next_symbols()
            symbols.discard(END_OF_SEQUENCE)
            if WILDCARD not in symbols:
                if WILDCARD in valid_next_symbols:
                    valid_next_symbols = symbols
                else:
                    valid_next_symbols.intersection_update(symbols)
        
        if len(valid_next_symbols) == 0:
            # Reached a dead-end (no symbol fits all patterns), give up on this
            # branch of the search
            continue
        
        # Descend the search into each of the potential next steps (NB:
        # sorted to ensure deterministic oucomes)
        if WILDCARD in valid_next_symbols:
            possible_data_units = sorted(ParseCodes)
        else:
            possible_data_units = sorted(
                getattr(ParseCodes, name) for name in valid_next_symbols
            )
        for candidate_data_unit in possible_data_units:
            new_matchers = deepcopy(matchers)
            for m in new_matchers:
                m.match_symbol(candidate_data_unit.name)
            queue.append((
                data_units_so_far + [candidate_data_unit],
                data_units_remaining,
                new_matchers,
                this_depth_limit - 1,
            ))
            continue
    
    raise ImpossibleSequenceError()
