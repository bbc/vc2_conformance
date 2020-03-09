import pytest

from vc2_conformance.symbol_re import (
    tokenize_regex,
    parse_regex,
    SymbolRegexSyntaxError,
    Symbol,
    Star,
    Concatenation,
    Union,
    NFANode,
    Matcher,
    make_matching_sequence,
    ImpossibleSequenceError,
)


class TestTokenize(object):
    
    @pytest.mark.parametrize("string,exp_tokens", [
        ("", []),
        ("foo", [("string", "foo", 0)]),
        (".", [("wildcard", ".", 0)]),
        ("$", [("end_of_sequence", "$", 0)]),
        ("?", [("modifier", "?", 0)]),
        ("*", [("modifier", "*", 0)]),
        ("+", [("modifier", "+", 0)]),
        ("|", [("bar", "|", 0)]),
        ("(", [("parenthesis", "(", 0)]),
        (")", [("parenthesis", ")", 0)]),
    ])
    def test_types(self, string, exp_tokens):
        assert list(tokenize_regex(string)) == exp_tokens
        
        # Check whitespace insensitivity
        assert list(tokenize_regex(" \n " + string)) == [(t, v, o+3) for (t, v, o) in exp_tokens]
        assert list(tokenize_regex(string + " \n ")) == exp_tokens
        assert list(tokenize_regex(" \n " + string + " \n ")) == [(t, v, o+3) for (t, v, o) in exp_tokens]
    
    @pytest.mark.parametrize("string", ["-", "<", "["])
    @pytest.mark.parametrize("formatter", ["{}", " \n {}", "{} \n ", " \n {} \n "])
    def test_invalid(self, string, formatter):
        with pytest.raises(SymbolRegexSyntaxError):
            list(tokenize_regex(formatter.format(string)))
    
    def test_multiple_tokens(self):
        assert list(tokenize_regex("(foo|bar)? baz")) == [
            ("parenthesis", "(", 0),
            ("string", "foo", 1),
            ("bar", "|", 4),
            ("string", "bar", 5),
            ("parenthesis", ")", 8),
            ("modifier", "?", 9),
            ("string", "baz", 11),
        ]


class TestParseRegex(object):
    
    def test_empty(self):
        assert parse_regex(" ") is None
    
    def test_symbol(self):
        assert parse_regex(" foo ") == Symbol("foo")
    
    def test_wildcard(self):
        assert parse_regex(" . ") == Symbol(".")
    
    def test_concatenation(self):
        assert parse_regex(" foo bar ") == Concatenation(
            Symbol("foo"),
            Symbol("bar"),
        )
        
        assert parse_regex(" foo bar baz ") == Concatenation(
            Symbol("foo"),
            Concatenation(
                Symbol("bar"),
                Symbol("baz"),
            ),
        )
    
    def test_union(self):
        assert parse_regex(" foo | ") == Union(
            Symbol("foo"),
            None,
        )
        
        assert parse_regex(" foo | bar ") == Union(
            Symbol("foo"),
            Symbol("bar"),
        )
        
        assert parse_regex(" foo | bar | baz ") == Union(
            Union(
                Symbol("foo"),
                Symbol("bar"),
            ),
            Symbol("baz"),
        )
    
    def test_star(self):
        assert parse_regex(" foo * ") == Star(Symbol("foo"))
    
    def test_plus(self):
        assert parse_regex(" foo + ") == Concatenation(
            Symbol("foo"),
            Star(Symbol("foo")),
        )
    
    def test_query(self):
        assert parse_regex(" foo ? ") == Union(Symbol("foo"), None)
    
    def test_parentheses(self):
        assert parse_regex(" (foo) (bar baz) * (qux quo)") == Concatenation(
            Symbol("foo"),
            Concatenation(
                Star(
                    Concatenation(
                        Symbol("bar"),
                        Symbol("baz"),
                    ),
                ),
                Concatenation(
                    Symbol("qux"),
                    Symbol("quo"),
                ),
            ),
        )
    
    def test_multiple_modifiers(self):
        with pytest.raises(SymbolRegexSyntaxError,
                           match=r"Multiple modifiers at position 4"):
            parse_regex("foo ? *")
    
    def test_modifier_before_union(self):
        with pytest.raises(SymbolRegexSyntaxError,
                           match=r"Modifier before '\|' at position 2"):
            parse_regex("a | ? b")
    
    def test_modifier_before_parenthesis(self):
        with pytest.raises(SymbolRegexSyntaxError,
                           match=r"Modifier before '\(' at position 1"):
            parse_regex(" ( ? foo ) ")
    
    def test_modifier_at_start_of_expression(self):
        with pytest.raises(SymbolRegexSyntaxError,
                           match=r"Modifier at start of expression"):
            parse_regex(" ? foo ")
    
    def test_unmatched_closing_parentheses(self):
        with pytest.raises(SymbolRegexSyntaxError,
                           match=r"Unmatched parentheses"):
            parse_regex(" ( foo ) )")
    
    def test_unmatched_opening_parentheses(self):
        with pytest.raises(SymbolRegexSyntaxError,
                           match=r"Unmatched parentheses"):
            parse_regex(" ( ( foo )")


class TestNFANode(object):
    
    def test_add_transition_symbol(self):
        a = NFANode()
        b = NFANode()
        
        a.add_transition(b, "foo")
        b.add_transition(a, "bar")
        a.add_transition(a, "baz")
        
        assert a.transitions["foo"] == set([b])
        assert b.transitions["bar"] == set([a])
        assert a.transitions["baz"] == set([a])
    
    def test_add_transition_empty(self):
        a = NFANode()
        b = NFANode()
        
        a.add_transition(b)
        
        assert a.transitions[None] == set([b])
        assert b.transitions[None] == set([a])
    
    def test_equivalent_nodes_chain(self):
        a = NFANode()
        b = NFANode()
        c = NFANode()
        
        a.add_transition(b)
        b.add_transition(c)
        c.add_transition(a)
        
        out = list(a.equivalent_nodes())
        assert len(out) == 3
        assert set(out) == set([a, b, c])
    
    def test_equivalent_nodes_deduplicate(self):
        a = NFANode()
        b = NFANode()
        c = NFANode()
        
        a.add_transition(b)
        a.add_transition(c)
        b.add_transition(c)
        c.add_transition(a)
        
        out = list(a.equivalent_nodes())
        assert len(out) == 3
        assert set(out) == set([a, b, c])
    
    def test_follow(self):
        a = NFANode()
        b = NFANode()
        c = NFANode()
        
        a.add_transition(b)
        
        a.add_transition(c, "foo")
        b.add_transition(c, "bar")
        
        a.add_transition(c, "baz")
        b.add_transition(c, "baz")
        
        assert list(a.follow("foo")) == [c]
        assert list(a.follow("bar")) == [c]
        assert list(a.follow("baz")) == [c]


class TestMatcher(object):
    
    @pytest.mark.parametrize("regex,sequence", [
        # Empty
        ("", ""),
        # Symbol
        ("a", ["a"]),
        # End of sequence
        ("$", [""]),
        # Wildcard
        (".", ["a"]),
        (".", ["b"]),
        # Concat
        ("a b c", ["a", "b", "c"]),
        ("a b c $", ["a", "b", "c"]),
        # Query
        ("a?", []),
        ("a?", ["a"]),
        # Union
        ("a|b|c", ["a"]),
        ("a|b|c", ["b"]),
        ("a|b|c", ["c"]),
        # Star (with complex subexpression)
        ("x((a a)|(b b))*x", ["x", "x"]),
        ("x((a a)|(b b))*x", ["x", "a", "a", "x"]),
        ("x((a a)|(b b))*x", ["x", "b", "b", "x"]),
        ("x((a a)|(b b))*x", ["x", "a", "a", "b", "b", "a", "a", "x"]),
        # Plus
        ("x(a)+x", ["x", "a", "x"]),
        ("x(a)+x", ["x", "a", "a", "a", "a", "x"]),
    ])
    def test_complete_matches(self, regex, sequence):
        m = Matcher(regex)
        for symbol in sequence:
            assert m.match_symbol(symbol) is True
        assert m.is_complete() is True
    
    def test_incomplete_match(self):
        m = Matcher("foo bar+")
        
        assert not m.is_complete()
        assert m.match_symbol("foo")
        assert not m.is_complete()
        assert m.match_symbol("bar")
        assert m.is_complete()
        assert m.match_symbol("bar")
        assert m.is_complete()
    
    @pytest.mark.parametrize("regex,sequence", [
        # Symbol
        ("a", ["x"]),
        # End of sequence
        ("$", ["x"]),
        # Wildcard
        (".", ["x", "x"]),
        # Concat
        ("a b c", ["a", "b", "c", "x"]),
        # Query
        ("a?", ["x"]),
        ("a?", ["a", "x"]),
        # Union
        ("a|b|c", ["d"]),
        # Star
        ("a*", ["x"]),
        ("a*", ["a", "x"]),
        ("a*", ["a", "a", "x"]),
        # Plus
        ("a+", ["x"]),
        ("a+", ["a", "x"]),
        ("a+", ["a", "a", "x"]),
    ])
    def test_non_match(self, regex, sequence):
        m = Matcher(regex)
        for i, symbol in enumerate(sequence):
            if i == len(sequence) - 1:
                assert m.match_symbol(symbol) is False
            else:
                assert m.match_symbol(symbol) is True
    
    @pytest.mark.parametrize("regex,next_symbols", [
        # Symbol
        ("foo", set(["foo"])),
        # End of sequence
        ("$", set([""])),
        # Wildcard
        (".", set(["."])),
        # Concat
        ("foo bar", set(["foo"])),
        # Query
        ("foo?", set(["foo", ""])),
        # Union
        ("foo | bar | ", set(["foo", "bar", ""])),
        ("foo | bar | $", set(["foo", "bar", ""])),
        ("foo | bar | .", set(["foo", "bar", "."])),
        ("foo | bar | . | $", set(["foo", "bar", ".", ""])),
        # Star
        ("foo*", set(["foo", ""])),
        # Plus
        ("foo+", set(["foo"])),
    ])
    def test_valid_next_symbols(self, regex, next_symbols):
        m = Matcher(regex)
        assert m.valid_next_symbols() == next_symbols


class TestMakeMatchingSequence(object):

    def test_empty_no_patterns(self):
        assert make_matching_sequence([]) == []

    def test_arbitrary_no_patterns(self):
        # When no patterns are supplied, any sequence should match
        assert make_matching_sequence(["a", "b", "c"]) == ["a", "b", "c"]

    @pytest.mark.parametrize("patterns", [
        # Single patterns which would allow an empty sequence
        [""],
        [".*"],
        ["$"],
        [".*$"],
        # Multiple patterns at once which would allow an empty sequence
        ["", ".*", "$", ".*$"],
    ])
    def test_patterns_allow_empty_sequence(self, patterns):
        assert make_matching_sequence([], *patterns) == []

    @pytest.mark.parametrize("patterns", [
        ["a b c$"],
        ["...$"],
        [".*"],
        [
            "a . . $",
            ". b . $",
            ". . c $",
        ],
    ])
    def test_fully_matched_pattern(self, patterns):
        # Patterns which match the test sequence exactly
        assert make_matching_sequence(["a", "b", "c"], *patterns) == ["a", "b", "c"]

    @pytest.mark.parametrize("patterns", [
        # Only one option
        ["a b$"],
        # Two options, one shorter
        ["a a? b$"],
        # All patterns together enforce the solution
        [
            "a .*",
            ".* b",
            ". .",
        ],
        # Wildcard options first
        [
            ". .",
            ".* b",
            "a .*",
        ],
        # End-of-sequence required
        [
            "a .* $",
            ".* b $",
            ". . $",
        ],
    ])
    def test_find_shortest_possible_filler_values(self, patterns):
        assert make_matching_sequence([], *patterns) == ["a", "b"]

    def test_fill_in_wildcard_value_if_empty_symbol_priority(self):
        assert make_matching_sequence([], "a . c") == ["a", ".", "c"]
    
    def test_prefer_wildcard_value_if_empty_symbol_priority(self):
        assert make_matching_sequence([], "a . c", "a (.|b) c") == ["a", ".", "c"]
    
    def test_prefer_highest_symbol_priority_over_wildcard(self):
        assert make_matching_sequence(
            [],
            "a . c",
            symbol_priority=["X", "a", "c"],
        ) == ["a", "X", "c"]
    
    def test_symbol_priority(self):
        assert make_matching_sequence(
            [],
            "(a|b|c) . .",
            ". (d|e|f) .",
            ". . (g|h|i)",
            symbol_priority=[
                "b",
                "a",
                "c",
                "e",
                "d",
                "f",
                # NB: G, H and I not specified so should be alphabetically
                # ordered
            ],
        ) == ["b", "e", "g"]

    def test_mixture_of_matched_and_fillled_in_values(self):
        assert make_matching_sequence(["b"], "a .* c") == ["a", "b", "c"]

    @pytest.mark.parametrize("symbols,patterns,works", [
        # When no requirements given, should work up to (but not past) the depth limit
        ([], ["a b c"], True),
        ([], ["a b c d"], False),
        # Depth limit should reset when a symbol is matched
        (
            ["X"],
            ["a b c X d e f"],
            True,
        ),
        (
            ["X"],
            ["a b c d X e f g"],
            False,
        ),
        # Depth limit should be reset even when wildcard matching is included
        (
            ["X"],
            ["a b c X d e f", ".*"],
            True,
        ),
        (
            ["X"],
            ["a b c d X e f g", ".*"],
            False,
        ),
    ])
    def test_search_depth_limit(self, symbols, patterns, works):
        if works:
            make_matching_sequence(symbols, *patterns, depth_limit=3)
        else:
            with pytest.raises(ImpossibleSequenceError):
                make_matching_sequence(symbols, *patterns, depth_limit=3)

    @pytest.mark.parametrize("patterns", [
        # Pattern shorter than sequence
        ["a"],
        ["c"],
        ["a b b"],
        # Pattern does not match sequence
        ["a b c c"],
        ["a X X c"],
        # One pattern doesn't match sequence
        [".*", "c"],
    ])
    def test_sequence_not_allowed_by_patterns(self, patterns):
        with pytest.raises(ImpossibleSequenceError):
            make_matching_sequence(["a", "b", "b", "c"], *patterns, depth_limit=3)
