"""
:py:class:`vc2_conformance._symbol_re`: Regular expressions for VC-2 sequences
==============================================================================

This module contains logic for checking that a series of abstract symbols
conform to a particular pattern as defined by a regular expression.

The intended usage of this module is to verify whether a sequence of data units
appearing within a VC-2 sequence conform to the restrictions imposed by the
VC-2 standard and current level.

.. note::
    
    In the context of software development the term 'regular expressions' is
    often used to refer to just the specific application of string pattern
    matching. This module instead refers to the generalised meaning of 'regular
    expressions' where a regular expressions may match patterns in any sequence
    of symbols.

Usage
-----

The :py:class:`Matcher` object is used to compare a sequence of symbols
(represented as Python strings containing only alpha-numeric characters and
underscores) against a predefined pattern given as a regular expression.

For the application of checking VC-2 sequence contents,
:py:class:`~vc2_conformance.tables.ParseCodes` name strings may be used as
symbols. For example::

    >>> from vc2_conformance._symbol_re import Matcher
    
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


:py:class:`Matcher` API
-----------------------

.. autoclass:: Matcher
    :members:

.. autodata:: WILDCARD

.. autodata:: END_OF_SEQUENCE

.. autoexc:: SymbolRegexSyntaxError


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

from collections import defaultdict, namedtuple


__all__ = [
    "Matcher",
    "SymbolRegexSyntaxError",
    "WILDCARD",
    "END_OF_SEQUENCE",
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
        
        If a wildcard is allowed, :py:data:`WILDCARD` will be returned.
        
        If it is valid for the sequence to end at this point,
        :py:data:`END_OF_SEQUENCE` will be in the returned set.
        """
        valid_symbols = set()
        for nfa in self.cur_states:
            for equivalent_nfa in nfa.equivalent_nodes():
                for symbol in equivalent_nfa.transitions:
                    if symbol is not None:
                        valid_symbols.add(symbol)
        
        # If a wildcard is available, simplify to just that
        if WILDCARD in valid_symbols:
            valid_symbols = set([WILDCARD])
        
        # If we're allowed to end the string here, also include
        # END_OF_SEQUENCE.
        if self.is_complete():
            valid_symbols.add(END_OF_SEQUENCE)
        
        return valid_symbols
