import pytest

from vc2_conformance import bitstream

from vc2_conformance.decoder import BadParseCode, NoQuantisationMatrixAvailable

from vc2_conformance.test_cases import registry


class TestForceXFail(object):
    
    def test_wraps_sequence_in_xfail(self):
        def f(foo, bar):
            return bitstream.Sequence(data_units=[
                foo,
                bar,
            ])
        
        fx = registry.force_xfail(f, BadParseCode)
        
        assert fx(123, bar=321) == registry.XFail(
            bitstream.Sequence(data_units=[123, 321]),
            BadParseCode,
        )
    
    def test_leaves_xfail_intact(self):
        def f(foo, bar):
            return registry.XFail(bitstream.Sequence(data_units=[
                foo,
                bar,
            ]), NoQuantisationMatrixAvailable)
        
        fx = registry.force_xfail(f, BadParseCode)
        
        assert fx(123, bar=321) == registry.XFail(
            bitstream.Sequence(data_units=[123, 321]),
            NoQuantisationMatrixAvailable,
        )
    
    def test_leaves_none_intact(self):
        def f(foo, bar):
            return None
        
        fx = registry.force_xfail(f, BadParseCode)
        
        assert fx(123, bar=321) is None


@pytest.mark.parametrize("spec,exp", [
    # Empty specification
    ([], [{}]),
    # Single parameter
    (
        ("foo", [1, 2, 3]),
        [
            {"foo": 1},
            {"foo": 2},
            {"foo": 3},
        ],
    ),
    (
        ("foo,", [(1, ), (2, ), (3, )]),
        [
            {"foo": 1},
            {"foo": 2},
            {"foo": 3},
        ],
    ),
    # Multiple parameters (no product)
    (
        ("foo, bar", [(1, "one"), (2, "two"), (3, "three")]),
        [
            {"foo": 1, "bar": "one"},
            {"foo": 2, "bar": "two"},
            {"foo": 3, "bar": "three"},
        ],
    ),
    # Product of parameters
    (
        [("foo", [1, 2, 3]), ("bar", [True, False])],
        [
            {"foo": 1, "bar": True},
            {"foo": 1, "bar": False},
            {"foo": 2, "bar": True},
            {"foo": 2, "bar": False},
            {"foo": 3, "bar": True},
            {"foo": 3, "bar": False},
        ],
    ),
    # Product of parameters with a non-product multiple parameter
    (
        [("foo", [1, 2, 3]), ("bar,baz", [(True, "a"), (False, "b")])],
        [
            {"foo": 1, "bar": True, "baz": "a"},
            {"foo": 1, "bar": False, "baz": "b"},
            {"foo": 2, "bar": True, "baz": "a"},
            {"foo": 2, "bar": False, "baz": "b"},
            {"foo": 3, "bar": True, "baz": "a"},
            {"foo": 3, "bar": False, "baz": "b"},
        ],
    ),
])
def test_expand_parameters(spec, exp):
    assert registry.expand_parameters(spec) == exp


class TestTestCaseRegistry(object):
    
    def test_group_stack(self):
        r = registry.TestCaseRegistry()
        
        class MyException(Exception):
            pass
        
        with pytest.raises(MyException):
            with r.test_group("g1"):
                with r.test_group("g2"):
                    assert r._group_stack == ["g1", "g2"]
                assert r._group_stack == ["g1"]
                raise MyException()
        assert r._group_stack == []
    
    def test_test_case_as_function(self):
        r = registry.TestCaseRegistry()
        
        def f(foo):
            """Help!"""
            return bitstream.Sequence(data_units=foo)
        
        r.test_case(f, xfail=BadParseCode, parameters=("foo", [[], [123]]))
        
        assert len(r.test_cases) == 2
        
        names = list(r.test_cases)
        assert names == ["f[foo=[]]", "f[foo=[123]]"]
        
        retvals = [f() for f in r.test_cases.values()]
        assert retvals == [
            registry.XFail(bitstream.Sequence(data_units=[]), BadParseCode),
            registry.XFail(bitstream.Sequence(data_units=[123]), BadParseCode),
        ]
        
        docs = [f.__doc__ for f in r.test_cases.values()]
        assert docs == ["Help!", "Help!"]
    
    def test_test_case_as_decorator_with_arguments(self):
        r = registry.TestCaseRegistry()
        
        @r.test_case(xfail=BadParseCode, parameters=("foo", [[], [123]]))
        def f(foo):
            """Help!"""
            return bitstream.Sequence(data_units=foo)
        
        assert len(r.test_cases) == 2
        
        names = list(r.test_cases)
        assert names == ["f[foo=[]]", "f[foo=[123]]"]
        
        retvals = [f() for f in r.test_cases.values()]
        assert retvals == [
            registry.XFail(bitstream.Sequence(data_units=[]), BadParseCode),
            registry.XFail(bitstream.Sequence(data_units=[123]), BadParseCode),
        ]
        
        docs = [f.__doc__ for f in r.test_cases.values()]
        assert docs == ["Help!", "Help!"]
    
    def test_test_case_as_decorator_without_arguments(self):
        r = registry.TestCaseRegistry()
        
        @r.test_case
        def f():
            """Help!"""
            return bitstream.Sequence()
        
        assert len(r.test_cases) == 1
        
        names = list(r.test_cases)
        assert names == ["f"]
        
        retvals = [f() for f in r.test_cases.values()]
        assert retvals == [bitstream.Sequence()]
        
        docs = [f.__doc__ for f in r.test_cases.values()]
        assert docs == ["Help!"]
    
    def test_test_case_unknown_kwargs(self):
        r = registry.TestCaseRegistry()
        
        with pytest.raises(TypeError):
            @r.test_case(foo="bar")
            def f():
                """Help!"""
                return bitstream.Sequence()
        
        assert len(r.test_cases) == 0
    
    def test_test_case_naming(self):
        r = registry.TestCaseRegistry()
        
        # No group and no parameters
        @r.test_case
        def foo():
            return None
        
        # Inside groups
        with r.test_group("outer"):
            @r.test_case
            def bar():
                return None
            
            with r.test_group("inner"):
                @r.test_case
                def baz():
                    return None
        
        # With one parameter
        @r.test_case(parameters=("foo", [1, 2, 3]))
        def qux(foo):
            return None
        
        # With several parameters
        @r.test_case(parameters=("foo, bar", [(1, "one"), (2, "two"), (3, "three")]))
        def quo(foo, bar):
            return None
        
        names = list(r.test_cases)
        assert names == [
            "foo",
            "outer:bar",
            "outer:inner:baz",
            "qux[foo=1]",
            "qux[foo=2]",
            "qux[foo=3]",
            "quo[foo=1, bar='one']",
            "quo[foo=2, bar='two']",
            "quo[foo=3, bar='three']",
        ]
