"""
:py:class:`vc2_conformance.symbol_re`: Regular expressions for VC-2 sequences
=============================================================================

This module contains logic for checking sequences of abstract symbols conform
to a particular pattern as defined by a regular expression. In addition, it may
also be used to geneate sequences conforming to such patterns.

The intended usage of this module is to verify or generate sequences of VC-2
data units which conform to the restrictions imposed by the VC-2 standard or
level.

.. note::
    
    In the context of software development the term 'regular expression' is
    often used to refer to just the specific application of string pattern
    matching. This module instead refers to the generalised meaning of 'regular
    expressions' where a regular expressions may match patterns in any sequence
    of symbols.

Examples
--------

In the following pair of examples, :py:class:`~vc2_data_tables.ParseCodes` name
strings are used as symbols in sequences representing sequences of VC-2 data
units.

The example below shows how a :py:class:`Matcher` may be used to check that a
sequence of data units follows a predefined pattern.

    >>> from vc2_conformance.symbol_re import Matcher
    
    >>> # Checking the sequence of data units within a VC-2 sequence consist of
    >>> # alternating sequence_headers and HQ pictures eventually ending with
    >>> # an end-of-sequence marker.
    >>> m = Matcher("(sequence_header high_quality_picture)* end_of_sequence")
    >>> m.match_symbol("sequence_header")
    True
    >>> m.match_symbol("high_quality_picture")
    True
    >>> m.match_symbol("sequence_header")
    True
    >>> m.match_symbol("high_quality_picture")
    True
    >>> m.match_symbol("end_of_sequence")
    True
    >>> m.is_complete()
    True
    
    >>> # If the pattern does not match that specified in the pattern, this
    >>> # will be detected
    >>> m = Matcher("(sequence_header high_quality_picture)* end_of_sequence")
    >>> m.match_symbol("sequence_header")
    True
    >>> m.match_symbol("high_quality_picture")
    True
    >>> m.match_symbol("high_quality_picture")  # Not allowed!
    False
    >>> m.valid_next_symbols()
    {"sequence_header", "end_of_sequence"}
    >>> m.is_complete()
    False

The example below shows how we may use :py:func:`make_matching_sequence` to
fill-in additional data units in a sequence to make it conform to a particular
set of patterns.

    >>> from vc2_conformance.symbol_re import make_matching_sequence
    
    >>> # Suppose we want some sequence which contains two high_quality_picture
    >>> # data units but we don't really care about the rest...
    >>> desired_sequence = ["high_quality_picture", "high_quality_picture"]
    
    >>> # ...and we're required to match the following patterns...
    >>> required_patterns = [
    ...     # The VC-2 main specification simply requires that a sequence start
    ...     # with a sequence_header and end with an end-of-sequence
    ...     "sequence_header .* end_of_sequence $",
    ...     # A particular level may force the sequence to begin with a
    ...     # sequence header and aux data block followed by alternating
    ...     # sequence headers and pictures.
    ...     "sequence_header auxiliary_data (sequence_header high_quality_picture)+ end_of_sequence $",
    ... ]
    
    >>> # We can generate a suitable sequence like so:
    >>> for sym in make_matching_sequence(desired_sequence, *required_patterns):
    ...     print(sym)
    sequence_header
    auxiliary_data
    sequence_header
    high_quality_picture
    sequence_header
    high_quality_picture
    end_of_sequence

API
---

.. autoclass:: Matcher
    :members:

.. autodata:: WILDCARD

.. autodata:: END_OF_SEQUENCE

.. autoexc:: SymbolRegexSyntaxError

.. autofunction:: make_matching_sequence

.. autoexc:: ImpossibleSequenceError

Implementation overview
-----------------------

This module internally consists of two parts:

* A parser which parses the regular expression syntax described in the
  :py:class:`Matcher` docstring  into an Non-deterministic Finite-state
  Automaton (NFA).
* An NFA evaluator which uses the compiled NFA to test if a sequence of
  symbols match the pattern.

The regular expression syntax is first tokenized by :py:func:`tokenize_regex`
and then parsed using :py:func:`parse_regex` into an Abstract Syntax Tree
(AST). This is implemented as a simple 'recursive descent parser'. The
resultant AST is converted into an NFA by :py:func:`NFA.from_ast` using
Thompson's constructions.

Since this matching module will only be used with very simple regular
expressions and very short sequences (i.e. likely to be tens of symbols long),
the NFA is not further converted into a Deterministic Finite-state Automaton
(DFA) nor minimised. Instead, :py:class:`Matcher` uses the NFA-form of the
regular expression to match sequences directly.
"""


import re

from copy import deepcopy

from collections import defaultdict, namedtuple, deque


__all__ = [
    "Matcher",
    "SymbolRegexSyntaxError",
    "WILDCARD",
    "END_OF_SEQUENCE",
    "ImpossibleSequenceError",
    "make_matching_sequence",
]


class SymbolRegexSyntaxError(Exception):
    """
    Thrown when a regular expression string is provided which could not be
    parsed.
    """


TOKEN_REGEX = re.compile(
    r"(?P<string>[\w]+)|"
    r"(?P<wildcard>[.])|"
    r"(?P<end_of_sequence>[$])|"
    r"(?P<modifier>[?*+])|"
    r"(?P<bar>[|])|"
    r"(?P<parenthesis>[()])"
)
"""
A regular expression which matches a single token in the regular expression
syntax.
"""


def tokenize_regex(regex_string):
    """
    A generator which tokenizes a sequence regular expression specification
    into (token_type, token_value, offset) 3-tuples.
    
    Token types are:
    
    * ``"string"`` (value is the string)
    * ``"modifier"`` (value is one of ``?*+``)
    * ``"wildcard"`` (value is ``.``)
    * ``"end_of_sequence"`` (value is ``$``)
    * ``"bar"`` (value is ``|``)
    * ``"parenthesis"`` (value is one of ``()``)
    
    Throws a :py:exc:`SymbolRegexSyntaxError` if an invalid character is
    encountered.
    """
    # Remove newline characters which have special behaviour in Python re
    # library
    regex_string = regex_string.replace("\n", " ").replace("\r", " ")
    
    offset = 0
    while True:
        # Skip whitespace
        ws_match = re.match(r"^\s*", regex_string)
        regex_string = regex_string[ws_match.end():]
        offset += ws_match.end()
        
        # Special case: End of string
        if not regex_string:
            break
        
        # Process token
        t_match = TOKEN_REGEX.match(regex_string)
        if not t_match:
            raise SymbolRegexSyntaxError("Unexpected text at position {}".format(offset))
        [(token_type, token_value)] = [
            (t, v) for t, v in t_match.groupdict().items() if v is not None
        ]
        yield (token_type, token_value, offset)
        regex_string = regex_string[t_match.end():]
        offset += t_match.end()


Symbol = namedtuple("Symbol", "symbol")
"""AST node for a symbol."""

Star = namedtuple("Star", "expr")
"""AST node for a Kleene Star pattern (``*``)."""

Concatenation = namedtuple("Concatenation", "a,b")
"""AST node for a concatenation of two expressions."""

Union = namedtuple("Union", "a,b")
"""AST node for a union (``|``) of two expressions."""


WILDCARD = "."
"""A constant representing a wildcard match."""

END_OF_SEQUENCE = ""
"""A constant representing the end-of-sequence."""


def parse_expression(tokens):
    """
    A recursive-descent parser which parses an Abstract Syntax Tree (AST) from
    the regex specification.
    
    The parsed tokens will be removed from the provided token list. Tokens are
    consumed right-to-left making implementing tight binding of modifiers (i.e.
    '?', '*' and '+') easy.
    
    This function will return as soon as it runs out of tokens or reaches an
    unmatched opening parenthesis.
    
    Returns an AST node: one of :py:class:`Symbol`, :py:class:`Star`,
    :py:class:`Concatenation`, :py:class:`Union` or ``None``.
    """
    ast = None
    modifier = None
    
    while tokens and tokens[-1][0:2] != ("parenthesis", "("):
        # Special case: reached a modifier: just set a flag
        if tokens[-1][0] == "modifier":
            if modifier is not None:
                raise SymbolRegexSyntaxError("Multiple modifiers at position {}".format(tokens[-1][2]))
            modifier = tokens.pop(-1)[1]
            continue
        
        # Special case: reached a union
        if tokens[-1][0] == "bar":
            if modifier is not None:
                raise SymbolRegexSyntaxError("Modifier before '|' at position {}".format(tokens[-1][2]))
            tokens.pop(-1)
            ast = Union(parse_expression(tokens), ast)
            continue
        
        # Grab the next expression from the token list
        if tokens[-1][0:2] == ("parenthesis", ")"):
            tokens.pop(-1)
            next_ast = parse_expression(tokens)
            if not tokens:
                raise SymbolRegexSyntaxError("Unmatched parentheses")
            tokens.pop(-1)
        elif tokens[-1][0] == "string":
            next_ast = Symbol(tokens.pop(-1)[1])
        elif tokens[-1][0] == "wildcard":
            tokens.pop(-1)
            next_ast = Symbol(WILDCARD)
        elif tokens[-1][0] == "end_of_sequence":
            tokens.pop(-1)
            next_ast = Symbol(END_OF_SEQUENCE)
        
        # Apply the modifier (as required)
        if modifier == "*":
            next_ast = Star(next_ast)
        elif modifier == "+":
            next_ast = Concatenation(next_ast, Star(next_ast))
        elif modifier == "?":
            next_ast = Union(next_ast, None)
        modifier = None
        
        # Add the expression to the AST
        if ast is None:
            ast = next_ast
        else:
            ast = Concatenation(next_ast, ast)
    
    if modifier is not None:
        if tokens:
            raise SymbolRegexSyntaxError("Modifier before '(' at position {}".format(tokens[-1][2]))
        else:
            raise SymbolRegexSyntaxError("Modifier at start of expression")
    
    return ast


def parse_regex(regex_string):
    """
    Parse a sequence regular expression specification into an Abstract Syntax
    Tree (AST) consisting of None (empty), :py:class:`Symbol`, :py:class:`Star`
    :py:class:`Concatenation` and :py:class:`Union` objects.
    """
    tokens = list(tokenize_regex(regex_string))
    
    ast = parse_expression(tokens)
    if tokens:
        raise SymbolRegexSyntaxError("Unmatched parentheses")
    
    return ast


class NFANode(object):
    """
    A node (a.k.a.) state in a Non-deterministic Finite-state Automaton (NFA).
    
    Attributes
    ==========
    transitions : {symbol: set([:py:class:`NFANode`, ...]), ...}
        The transition rules from this node.
        
        Empty transitions are listed under the symbol ``None`` and are always
        bidirectional.
    """
    
    def __init__(self):
        self.transitions = defaultdict(set)
    
    def add_transition(self, dest_node, symbol=None):
        """
        Add a transition rule from this node to the specified destination.
        
        If no symbols is specified, a (bidirectional) empty transition between
        the two nodes will be added.
        """
        if symbol is None:
            # Empty transitions should be bidirectional
            self.transitions[symbol].add(dest_node)
            dest_node.transitions[symbol].add(self)
        else:
            self.transitions[symbol].add(dest_node)
    
    def equivalent_nodes(self):
        """
        Iterate over the set of :py:class:`NFANode` nodes connected to this one
        by only empty transitions (includes this node).
        """
        visited = set([self])
        to_visit = [self]
        while to_visit:
            node = to_visit.pop()
            yield node
            
            for other in node.transitions.get(None, []):
                if other not in visited:
                    to_visit.append(other)
                    visited.add(other)
    
    def follow(self, symbol):
        """
        Iterate over the :py:class:`NFANode`s reachable from this node
        following the given symbol.
        """
        visited = set()
        for node in self.equivalent_nodes():
            for neighbour in node.transitions.get(symbol, []):
                if neighbour not in visited:
                    yield neighbour
                    visited.add(neighbour)


class NFA(object):
    """
    A Non-deterministic Finite-state Automaton (NFA) with a labelled 'start'
    and 'final' state.
    """
    
    def __init__(self, start=None, final=None):
        self.start = start or NFANode()
        self.final = final or NFANode()
    
    @classmethod
    def from_ast(cls, ast):
        """
        Convert a regular expression AST node into a new :py:class:`NFA` object
        using Thompson's constructions.
        """
        if ast is None:
            node = NFANode()
            return cls(node, node)
        elif isinstance(ast, Symbol):
            nfa = cls()
            nfa.start.add_transition(nfa.final, ast.symbol)
            
            return nfa
        elif isinstance(ast, Concatenation):
            nfa_a = cls.from_ast(ast.a)
            nfa_b = cls.from_ast(ast.b)
            
            nfa_a.final.add_transition(nfa_b.start)
            
            return cls(nfa_a.start, nfa_b.final)
        elif isinstance(ast, Symbol):
            nfa = cls()
            nfa.start.add_transition(nfa.final, ast.symbol)
            return nfa
        elif isinstance(ast, Union):
            nfa = cls()
            
            nfa_a = cls.from_ast(ast.a)
            nfa_b = cls.from_ast(ast.b)
            
            nfa.start.add_transition(nfa_a.start)
            nfa.start.add_transition(nfa_b.start)
            
            nfa_a.final.add_transition(nfa.final)
            nfa_b.final.add_transition(nfa.final)
            
            return nfa
        elif isinstance(ast, Star):
            nfa = cls()
            
            sub_nfa = cls.from_ast(ast.expr)
            
            nfa.start.add_transition(nfa.final)
            nfa.start.add_transition(sub_nfa.start)
            
            sub_nfa.final.add_transition(sub_nfa.start)
            sub_nfa.final.add_transition(nfa.final)
            
            return nfa


class Matcher(object):
    """
    Test whether a sequence of symbols (alpha-numeric strings with underscores,
    e.g. ``"foo"`` or ``"bar_123"``) conforms to a pattern described by a
    regular expression.
    
    :py:meth:`match_symbol` should be called for each symbol in the sequence.
    If ``False`` is returned, the sequence does not match the specified regular
    expression. :py:meth:`valid_next_symbols` may be used to list what symbols
    *would* have been allowed at this stage of the sequence. Once the entire
    sequence has been passed to :py:meth:`match_symbol`, :py:meth:`is_complete`
    should be used to check that a complete pattern has been matched.
    
    Parameters
    ==========
    pattern : str
        The regular expression describing the pattern this :py:class:`Matcher`
        should match.
        
        Regular expressions may be specified with a syntax similar (but
        different to) that used by common string-matching regular expression
        libraries.
        
        * An alpha-numeric-with-underscore expression matches a single instance
          of the specified symbol. For example ``foo_123`` will match the
          symbol ``"foo_123"``.
        * A dot (``.``) will match any (singular) symbol.
        * A dollar (``$``) will match only at the end of the sequence.
        * Two expressions (separated by any amount of whitespace) will match
          the first expression followed by the second. For example ``. foo``
          will match a sequence ``"anything"``, ``"foo"``.
        * Two expressions separated by a bar (``|``) will match either the
          first expression or the second expression.
        * A question mark (``?``) suffix to an expression will match zero or
          one instances of that expression. For example ``foo?`` will match an
          empty sequence or a single ``"foo"``.
        * An asterisk (``*``) suffix to an expression will match zero or more
          instances of that expression. For example ``foo*`` will match an
          empty sequence, a sequence of a single ``"foo"`` symbol or a sequence
          of many ``"foo"`` symbols.
        * A plus (``+``) suffix to an expression will match one or more
          instances of that expression. For example ``foo+`` will match a
          sequence of a single ``"foo"`` symbol or a sequence of many ``"foo"``
          symbols.
        * Parentheses (``(`` and ``)``) may be used to group expressions
          together into a single logical expression.
        
        The expression suffixes bind tightly to their left-hand expression.
        Beyond this, consider operator precedence undefined: be explicit to
        help readability!
    """
    
    def __init__(self, pattern):
        # This object explicitly executes the NFA of the provided regular
        # expression. The 'cur_states' set holds the set of states we've
        # reached in the NFA.
        self.nfa = NFA.from_ast(parse_regex(pattern))
        self.cur_states = set([self.nfa.start])
    
    def match_symbol(self, symbol):
        """
        Attempt to match the next symbol in the sequence.
        
        Returns True if the symbol matched and False otherwise.
        """
        new_states = set()
        for nfa in self.cur_states:
            new_states.update(nfa.follow(symbol))
            new_states.update(nfa.follow(WILDCARD))
        
        if not new_states:
            return False
        
        self.cur_states = new_states
        return True
    
    def is_complete(self):
        """
        Is it valid for the sequence to terminate at this point?
        """
        for nfa in self.cur_states:
            # Is final state in NFA
            if self.nfa.final in list(nfa.equivalent_nodes()):
                return True
            # ...or is explicit end-of-sequence marker
            if list(nfa.follow(END_OF_SEQUENCE)):
                return True
        
        return False
    
    def valid_next_symbols(self):
        """
        Return the :py:class:`set` of valid next symbols in the sequence.
        
        If a wildcard is allowed, :py:data:`WILDCARD` will be returned as one
        of the symbols in addition to any concretely allowed symbols.
        
        If it is valid for the sequence to end at this point,
        :py:data:`END_OF_SEQUENCE` will be in the returned set.
        """
        valid_symbols = set()
        for nfa in self.cur_states:
            for equivalent_nfa in nfa.equivalent_nodes():
                for symbol in equivalent_nfa.transitions:
                    if symbol is not None:
                        valid_symbols.add(symbol)
        
        # If we're allowed to end the string here, also include
        # END_OF_SEQUENCE.
        if self.is_complete():
            valid_symbols.add(END_OF_SEQUENCE)
        
        return valid_symbols


class ImpossibleSequenceError(Exception):
    """
    Thrown whne :py:func:`make_matching_sequence` is unable to find a suitable
    sequence of symbols.
    """
    pass


def make_matching_sequence(initial_sequence, *patterns, **kwargs):
    """
    Given a sequence of symbols, returns a new sequence based on this which
    matches the supplied set of patterns. The new sequence will be a copy of
    the supplied sequence with additional symbols inserted where necessary.
    
    Find the shortest sequence of symbols which is matched by the
    supplied set of regular expressions.
    
    Parameters
    ==========
    initial_sequence : [symbol, ...]
        The minimal set of entries which must be included in the sequence, in
        the order they are required to appear.
    patterns : str
        A series of regular expression specificeations (as accepted by
        :py:class:`Matcher`) which the generated sequence must simultaneously
        satisfy.
    depth_limit : int
        Keyword-only argument specifying the maximum number of non-target data
        units to try including before giving up. Defaults to 4.
    symbol_priority : [symbol, ...]
        Keyword-only argument. If supplied, orders possible symbols from most
        to least preferable. Though this function will always return a sequence
        of the shortest possible length, where several equal-length sequences
        are possible, this argument may be used to influence which is returned.
        Where some candidate symbols do not appear in the list they will be
        treated as being at the end of the list (i.e. lowest priority) in
        alphabetical order.  If this argument is not supplied (or is empty),
        'wildcard' entries will be filled with the :py:data:`WILDCARD` sentinel
        rather than a concrete symbol.
    
    Returns
    =======
    matching_sequence : [symbol, ...]
        A sequence of symbols which satisfies all of the supplied patterns.
        This will contain a superset of the sequence in ``initial_sequence``
        where additional symbols may have been inserted.
    
    Raises
    ======
    ImpossibleSequenceError
        Thrown if no sequence of symbols could be found which matches all of
        the supplied patterns.
    """
    # NB: Python 2.x doesn't directly support keyword-only oarguments
    depth_limit = kwargs.pop("depth_limit", 3)
    symbol_priority = kwargs.pop("symbol_priority", [])
    if kwargs:
        raise TypeError("find_minimal_sequence() got unuexpected keyword argument(s) {}".format(
            ", ".join(map(repr, kwargs)),
        ))
    
    # Perform a breadth-first search of the pattern space
    
    # Queue of candidates to try
    #     (symbols_so_far, symbols_remaining, matchers, this_depth_limit)
    # Where:
    # * symbols_so_far is the symbols of the generated sequence so far
    # * symbols_remaining is the list of symbols from initial_sequence still to
    #   included
    # * matchers is a list of Matcher objects which have matched the
    #   symbols_so_far
    # * this_depth_limit is an integer giving the number of search levels
    #   remaining before giving up.
    initial_matchers = [Matcher(pattern) for pattern in patterns]
    queue = deque([
        ([], initial_sequence, initial_matchers, depth_limit),
    ])
    
    while queue:
        (
            symbols_so_far,
            symbols_remaining,
            matchers,
            this_depth_limit,
        ) = queue.popleft()
        
        # Try and match the next required symbool
        if len(symbols_remaining) == 0:
            if all(m.is_complete() for m in matchers):
                # No more symbols to match and found a suitable matching
                # sequence! We're done.
                return symbols_so_far
        else:
            if all(
                symbols_remaining[0] in m.valid_next_symbols() or
                WILDCARD in m.valid_next_symbols()
                for m in matchers
            ):
                # The next symbol is matched by all matchers, move on!
                new_matchers = deepcopy(matchers)
                for m in new_matchers:
                    m.match_symbol(symbols_remaining[0])
                queue.append((
                    symbols_so_far + [symbols_remaining[0]],
                    symbols_remaining[1:],
                    new_matchers,
                    depth_limit,  # NB: Reset depth limit when a match is found
                ))
                continue
        
        # If we reach this point the current symbol in the provided sequence
        # was not matched by all of the matchers. We must now try to inserting
        # some other symbol into the sequence and see if it lets us get any
        # further.
        
        if this_depth_limit <= 0:
            # Depth limit reached, give up on this branch of the search
            continue
        
        # Find the set of candidate symbols which would be accepted by all of
        # the matchers
        candidate_next_symbols = set([WILDCARD])
        for matcher in matchers:
            symbols = matcher.valid_next_symbols()
            symbols.discard(END_OF_SEQUENCE)
            if WILDCARD in symbols and WILDCARD in candidate_next_symbols:
                candidate_next_symbols.update(symbols)
            elif WILDCARD in candidate_next_symbols:
                candidate_next_symbols = symbols
            elif WILDCARD in symbols:
                pass
            else:
                candidate_next_symbols.intersection_update(symbols)
        
        if len(candidate_next_symbols) == 0:
            # Reached a dead-end (no symbol fits all patterns), give up on this
            # branch of the search
            continue
        
        # Descend the search into each of the potential next steps. We try
        # candidates in the order indicated by the symbol_priority argument.
        if WILDCARD in candidate_next_symbols and len(symbol_priority) > 0:
            # Substitute wildcard for concrete symbols if possible
            candidate_next_symbols.remove(WILDCARD)
            candidate_next_symbols.update(symbol_priority)
        candidate_symbols = sorted(
            candidate_next_symbols,
            key=lambda sym: (
                (symbol_priority.index(sym), None)
                if sym in symbol_priority else
                (len(symbol_priority), sym)
            )
        )
        for candidate_symbol in candidate_symbols:
            new_matchers = deepcopy(matchers)
            for m in new_matchers:
                m.match_symbol(candidate_symbol)
            queue.append((
                symbols_so_far + [candidate_symbol],
                symbols_remaining,
                new_matchers,
                this_depth_limit - 1,
            ))
            continue
    
    raise ImpossibleSequenceError()
