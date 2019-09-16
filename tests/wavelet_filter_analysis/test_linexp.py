import pytest

from vc2_conformance.wavelet_filter_analysis.linexp import LinExp

from fractions import Fraction

from collections import OrderedDict

from itertools import permutations

import operator


class TestLinExp(object):
    
    def test_constructor_default(self):
        assert LinExp()._coeffs == {}
    
    @pytest.mark.parametrize("value", [0, 0.0, Fraction(0)])
    def test_constructor_zero(self, value):
        assert LinExp(value)._coeffs == {}
    
    @pytest.mark.parametrize("value", [123, 1.23, Fraction(1, 10)])
    def test_constructor_number(self, value):
        assert LinExp(value)._coeffs == {None: value}
    
    @pytest.mark.parametrize("symbol", ["a", (1, 2, 3)])
    def test_constructor_symbol(self, symbol):
        assert LinExp(symbol)._coeffs == {symbol: 1}
    
    def test_constructor_dictionary(self):
        # Zero coefficients should be removed
        assert LinExp({
            "a": 100,
            "b": 200,
            "c": 0,
            None: 123
        })._coeffs == {
            "a": 100,
            "b": 200,
            None: 123,
        }
    
    def test_constructor_linexp(self):
        v1 = LinExp({"a": 1, "b": 2})
        
        v2 = LinExp(v1)
        
        # Should pass through original object without creating a new value
        assert v1 is v2
    
    @pytest.mark.parametrize("value,exp_symbols", [
        (0, set([])),
        (123, set([None])),
        ({"a": 123}, set(["a"])),
        ({"a": 123, "b": 321, None: 111}, set(["a", "b", None])),
    ])
    def test_symbols(self, value, exp_symbols):
        assert set(LinExp(value).symbols()) == exp_symbols
    
    @pytest.mark.parametrize("value,exp_items", [
        (0, set([])),
        (123, set([(None, 123)])),
        ({"a": 123}, set([("a", 123)])),
        ({"a": 123, "b": 321, None: 111}, set([("a", 123), ("b", 321), (None, 111)])),
    ])
    def test_iter(self, value, exp_items):
        assert set(iter(LinExp(value))) == exp_items
    
    def test_getitem(self):
        v = LinExp({"a": 123, "b": 321, None: 111})
        
        assert v["a"] == 123
        assert v["b"] == 321
        assert v[None] == 111
        assert v["xxx"] == 0
    
    def test_contains(self):
        v = LinExp({"a": 123, "b": 321, None: 111})
        
        assert ("a" in v) is True
        assert ("b" in v) is True
        assert (None in v) is True
        assert ("xxx" in v) is False
    
    @pytest.mark.parametrize("value,exp_is_constant", [
        (0, True),
        (123, True),
        ({None: 123}, True),
        ({"a": 123}, False),
        ({"a": 123, None: 321}, False),
    ])
    def test_is_constant(self, value, exp_is_constant):
        assert LinExp(value).is_constant is exp_is_constant
    
    @pytest.mark.parametrize("value,exp_is_symbol", [
        (0, False),
        (123, False),
        ({None: 1}, False),
        ({None: 123}, False),
        ({"a": 1}, True),
        ({"a": 123}, False),
        ({"a": 1, None: 321}, False),
    ])
    def test_is_symbol(self, value, exp_is_symbol):
        assert LinExp(value).is_symbol is exp_is_symbol
    
    def test_symbol(self):
        assert LinExp((1, 2, 3)).symbol == (1, 2, 3)
        
        with pytest.raises(TypeError):
            LinExp({(1, 2, 3): 2}).symbol
    
    @pytest.mark.parametrize("value,exp_value", [
        (0, 0),
        (123, 123),
    ])
    def test_constant(self, value, exp_value):
        assert LinExp(value).constant == exp_value
    
    @pytest.mark.parametrize("value", [
        {"a": 123},
        {"a": 123, None: 321},
    ])
    def test_constant_when_not_constant(self, value):
        with pytest.raises(TypeError):
            LinExp(value).constant
    
    def test_number_type_casts(self):
        v = LinExp(1.5)
        
        assert isinstance(complex(v), complex)
        assert complex(v) == 1.5+0j
        
        assert isinstance(float(v), float)
        assert float(v) == 1.5
        
        assert isinstance(int(v), int)
        assert int(v) == 1
    
    @pytest.mark.parametrize("value,exp_bool", [
        (0, False),
        ({None: 123}, True),
        ({"a": 123}, True),
        ({"a": 123, None: 321}, True),
    ])
    def test_bool(self, value, exp_bool):
        assert bool(LinExp(value)) is exp_bool
    
    @pytest.mark.parametrize("value,exp_strs", [
        # Constants
        (0, ["LinExp(0)"]),
        (123, ["LinExp(123)"]),
        (Fraction(1, 10), ["LinExp(Fraction(1, 10))"]),
        # Symbols with weight 1
        ("a", ["LinExp('a')"]),
        # Anything else
        ({"a": 123}, ["LinExp({'a': 123})"]),
        (
            {"a": 123, "b": 321},
            [
                "LinExp({'a': 123, 'b': 321})",
                "LinExp({'b': 321, 'a': 123})",
            ],
        ),
    ])
    def test_repr(self, value, exp_strs):
        assert repr(LinExp(value)) in exp_strs
    
    @pytest.mark.parametrize("value,exp_strs", [
        # Constants
        (0, ["0"]),
        (123, ["123"]),
        (Fraction(1, 10), ["1/10"]),
        # Symbol with weight 1
        ("a", ["a"]),
        # Weighted symbol
        ({"a": 123}, ["123*a"]),
        # Orderable symbols
        (
            {"a": 123, "c": Fraction(1, 10), "b": 321},
            [
                "123*a + 321*b + (1/10)*c",
            ],
        ),
        (
            {"a": 123, None: 42, "c": Fraction(1, 10), "b": 321},
            [
                "123*a + 321*b + (1/10)*c + 42",
            ],
        ),
        # Unorderable symbols
        (
            {"a": 123, "b": 321, (1, 2, 3): Fraction(1, 10)},
            list(
                " + ".join(parts)
                for parts in permutations([
                    "123*a",
                    "321*b",
                    "(1/10)*(1, 2, 3)",
                ])
            )
        ),
        (
            {"a": 123, None: 42, "b": 321, (1, 2, 3): Fraction(1, 10)},
            list(
                "{} + 42".format(" + ".join(parts))
                for parts in permutations([
                    "123*a",
                    "321*b",
                    "(1/10)*(1, 2, 3)",
                ])
            )
        ),
    ])
    def test_str(self, value, exp_strs):
        assert str(LinExp(value)) in exp_strs
    
    def test_hash(self):
        # Hashses should be order insensitive
        assert hash(LinExp(OrderedDict([
            ("a", 123),
            ("b", 321),
            ("c", 111),
        ]))) == hash(LinExp(OrderedDict([
            ("c", 111),
            ("b", 321),
            ("a", 123),
        ])))
        
        # Hashes of LinExp constants should match the raw constant
        assert hash(LinExp(123)) == hash(123)
        assert hash(LinExp(Fraction(1, 3))) == hash(Fraction(1, 3))
        
        # Hashes of symbols should match the raw symbols
        assert hash(LinExp("a")) == hash("a")
        
        # Hashes should produce different values for different contents... Note
        # that this test is not strictly guaranteed to pass in theory, though
        # it practice it is almost certain to do so. Should it start failing,
        # think very hard!!
        assert hash(LinExp({"a": 123, "b": 321})) != hash(LinExp({"a": 123}))
    
    def test_eq_constants(self):
        assert LinExp(123) == LinExp(123)
        assert LinExp(123) == 123
        assert 123 == LinExp(123)
        
        assert LinExp(123) != LinExp(321)
        assert LinExp(123) != 321
        assert 321 != LinExp(123)
        
    def test_eq_expressions(self):
        assert LinExp({"a": 123}) == LinExp({"a": 123})
        assert LinExp({"a": 123}) != LinExp({"b": 123})
        assert LinExp({"a": 123}) != LinExp({"a": 321})
    
    def test_lt_constants(self):
        assert LinExp(1) < LinExp(2)
        assert not (LinExp(1) < LinExp(1))
        assert not (LinExp(2) < LinExp(1))
        
        assert 1 < LinExp(2)
        assert not (1 < LinExp(1))
        assert not (2 < LinExp(1))
        
        assert LinExp(1) < 2
        assert not (LinExp(1) < 1)
        assert not (LinExp(2) < 1)
        
    def test_lt_free_symbols_cancel(self):
        assert LinExp({"a": 123, None: 1}) < LinExp({"a": 123, None: 2})
        assert not (LinExp({"a": 123, None: 1}) < LinExp({"a": 123, None: 1}))
        assert not (LinExp({"a": 123, None: 2}) < LinExp({"a": 123, None: 1}))
        
    def test_lt_free_symbols_dont_cancel(self):
        with pytest.raises(TypeError):
            LinExp({"a": 1}) < LinExp({"a": 2})
        with pytest.raises(TypeError):
            123 < LinExp({"a": 2})
        with pytest.raises(TypeError):
            LinExp({"a": 1}) < 123
    
    @pytest.mark.parametrize("a,b,exp_result", [
        # Constants
        (LinExp(10), LinExp(3), LinExp(7)),
        (LinExp(10), 3, LinExp(7)),
        (10, LinExp(3), LinExp(7)),
        # Symbols should be summed too
        (
            LinExp({"a": 10, "b": 100, None: 1000}),
            LinExp({"a": 7, "b": 70, None: 700}),
            LinExp({"a": 3, "b": 30, None: 300}),
        ),
        # Both sides may differ in which symbols they have
        (
            LinExp({"a": 10, "b": 100, None: 10000}),
            LinExp({"b": 70, "c": 700, None: 7000}),
            LinExp({"a": 10, "b": 30, "c": -700, None: 3000}),
        ),
        # One side cannot be cast (due to non-hashable type)
        (123, ["fail"], NotImplemented),
        (["fail"], 123, NotImplemented),
    ])
    def test_pairwise_operator(self, a, b, exp_result):
        assert LinExp._pairwise_operator(a, b, operator.sub) == exp_result
    
    def test_add(self):
        assert (
            LinExp({"a": 10, "b": 20}) + LinExp({"b": 30, "c": 40}) ==
            LinExp({"a": 10, "b": 50, "c": 40})
        )
        # radd
        assert (
            10 + LinExp({"a": 20, "b": 30}) ==
            LinExp({None: 10, "a": 20, "b": 30})
        )
    
    def test_sub(self):
        assert (
            LinExp({"a": 10, "b": 20}) - LinExp({"b": 30, "c": 40}) ==
            LinExp({"a": 10, "b": -10, "c": -40})
        )
        # rsub
        assert (
            10 - LinExp({"a": 20, "b": 30}) ==
            LinExp({None: 10, "a": -20, "b": -30})
        )
    
    @pytest.mark.parametrize("a,b,exp_result", [
        # Both sides constant
        (LinExp(2), LinExp(3), LinExp(6)),
        (LinExp(2), 3, LinExp(6)),
        (2, LinExp(3), LinExp(6)),
        # One side constant
        (LinExp({"a": 10, None: 100}), LinExp(3), LinExp({"a": 30, None: 300})),
        (LinExp({"a": 10, None: 100}), 3, LinExp({"a": 30, None: 300})),
        (LinExp(3), LinExp({"a": 10, None: 100}), LinExp({"a": 30, None: 300})),
        (3, LinExp({"a": 10, None: 100}), LinExp({"a": 30, None: 300})),
        # One side cannot be cast (due to non-hashable type)
        (123, ["fail"], NotImplemented),
        (["fail"], 123, NotImplemented),
        # Neither side is constant
        (LinExp({"a": 10, None: 100}), LinExp({"a": 10, None: 100}), NotImplemented),
    ])
    def test_mul_operator(self, a, b, exp_result):
        assert LinExp._mul_operator(a, b) == exp_result
    
    def test_mul(self):
        assert LinExp({"a": 10, None: 100}) * LinExp(3) == LinExp({"a": 30, None: 300})
        # rmul
        assert 3 * LinExp({"a": 10, None: 100}) == LinExp({"a": 30, None: 300})
    
    @pytest.mark.parametrize("a,b,exp_result", [
        # Both sides constant
        (LinExp(2), LinExp(3), LinExp(Fraction(2, 3))),
        (LinExp(2), 3, LinExp(Fraction(2, 3))),
        (2, LinExp(3), LinExp(Fraction(2, 3))),
        # RHS is a constant
        (LinExp({"a": 2}), LinExp(3), LinExp({"a": Fraction(2, 3)})),
        (
            LinExp({None: 1, "a": 2, "b": 3}),
            LinExp(3),
            LinExp({
                None: Fraction(1, 3),
                "a": Fraction(2, 3),
                "b": 1,
            })
        ),
        # LHS and RHS are multiples of eachother
        (
            LinExp({None: 1, "a": 2, "b": 3}),
            LinExp({None: -10, "a": -20, "b": -30}),
            LinExp(Fraction(-1, 10)),
        ),
        # LHS is zero
        (
            LinExp(0),
            LinExp({None: -10, "a": -20, "b": -30}),
            LinExp(0),
        ),
        # LHS and RHS are not multiples of eachother
        (
            LinExp({None: 2, "a": 2, "b": 3}),
            LinExp({None: -10, "a": -20, "b": -30}),
            NotImplemented,
        ),
        # Different symbols on each side
        (LinExp(3), LinExp({"a": 2}), NotImplemented),
        (LinExp({"a": 10, None: 100}), LinExp({"b": 10, None: 100}), NotImplemented),
        # One side cannot be cast (due to non-hashable type)
        (123, ["fail"], NotImplemented),
        (["fail"], 123, NotImplemented),
    ])
    def test_div_operator(self, a, b, exp_result):
        assert LinExp._div_operator(a, b) == exp_result
    
    def test_div_operator_div_by_zero(self):
        with pytest.raises(ZeroDivisionError):
            LinExp._div_operator(LinExp(123), LinExp(0))
        with pytest.raises(ZeroDivisionError):
            LinExp._div_operator(LinExp({"a": 123}), LinExp(0))
    
    def test_div(self):
        assert LinExp({"a": 10, None: 100}) / LinExp(2) == LinExp({"a": 5, None: 50})
        # rrealdiv/rdiv
        assert 0 / LinExp({"a": 10, None: 100}) == LinExp(0)
    
    
    @pytest.mark.parametrize("a,b,exp_result", [
        # Both sides constant
        (LinExp(2), LinExp(3), LinExp(8)),
        (2, LinExp(3), LinExp(8)),
        (LinExp(2), 3, LinExp(8)),
        # Either side contains a symbol
        (LinExp("a"), LinExp(3), NotImplemented),
        (LinExp(3), LinExp("a"), NotImplemented),
        # One side cannot be cast (due to non-hashable type)
        (123, ["fail"], NotImplemented),
        (["fail"], 123, NotImplemented),
    ])
    def test_pow_operator(self, a, b, exp_result):
        assert LinExp._pow_operator(a, b) == exp_result
    
    def test_pow(self):
        assert LinExp(2)**LinExp(3) == LinExp(8)
        
        # Modulo never supported
        with pytest.raises(TypeError):
            LinExp(2)**LinExp(3)%5
        
        # rpow
        assert 2**LinExp(3) == LinExp(8)
    
    def test_neg(self):
        assert -LinExp() == LinExp()
        assert -LinExp(3) == LinExp(-3)
        assert -LinExp({"a": 1, "b": -2}) == LinExp({"a": -1, "b": 2})
    
    def test_pos(self):
        assert +LinExp() == LinExp()
        assert +LinExp(3) == LinExp(3)
        assert +LinExp({"a": 1, "b": -2}) == LinExp({"a": 1, "b": -2})
    
    @pytest.mark.parametrize("before,substitutions,exp_after", [
        # Do nothing to nothing
        (LinExp(), {}, LinExp()),
        # Do something to nothing
        (LinExp(), {"a": "b"}, LinExp()),
        # Do nothing to something
        (LinExp({"a": 123}), {}, LinExp({"a": 123})),
        # Zero out a value
        (LinExp({"a": 123, "b": 321}), {"a": 0}, LinExp({"b": 321})),
        # Replace symbol with number
        (LinExp({"a": 10, "b": 100}), {"a": 5}, LinExp({"b": 100, None: 50})),
        # Replace symbol with expression
        (
            LinExp({"a": 10, "b": 100}),
            {"a": LinExp({"b": 20, "c": 30})},
            LinExp({"b": 100 + (20*10), "c": 30*10})
        ),
        # Replace symbol with symbol
        (LinExp({"a": 10, "b": 100}), {"a": "c"}, LinExp({"c": 10, "b": 100})),
        # Replace symbol with existing symbol
        (LinExp({"a": 10, "b": 100, "c": 1000}), {"a": "c"}, LinExp({"c": 1010, "b": 100})),
        # Replace several symbols with same (existing) symbol
        (
            LinExp({"a": 10, "b": 100, "c": 1000}),
            {"a": "c", "b": "c"},
            LinExp({"c": 1110})
        ),
        # Swap symbols (ensure simultaneous replacement)
        (
            LinExp({"a": 10, "b": 20}),
            {"a": "b", "b": "a"},
            LinExp({"a": 20, "b": 10})
        ),
        # 'Overwrite' symbol (again, ensuring simultaneous action of different
        # mutations)
        (
            LinExp({"a": 10, "b": 20}),
            {"a": "b", "b": 0},
            LinExp({"b": 10})
        ),
    ])
    def test_subs(self, before, substitutions, exp_after):
        assert before.subs(substitutions) == exp_after
    
    def test_integration(self):
        # A simple test showing most of the moving parts used in a way they
        # might be in a video filter...
        
        a = LinExp("a")
        b = LinExp("b")
        
        ab = a + b
        assert str(ab) == "a + b"
        
        ab3 = 3 * ab
        assert str(ab3) == "3*a + 3*b"
        
        ab2 = ab3 * Fraction(2, 3)
        assert str(ab2) == "2*a + 2*b"
        
        b2_1 = 2*b - 1
        assert str(b2_1) == "2*b + -1"
        
        a2_1 = ab2 - b2_1
        assert str(a2_1) == "2*a + 1"
        
        a_05 = a2_1 / 2
        assert str(a_05) == "a + 1/2"
        
        two_and_a_half = a_05.subs({"a": 2})
        assert str(two_and_a_half) == "5/2"
        
        three = (3*a_05) / a_05
        assert str(three) == "3"
