import pytest

from vc2_conformance import test_cases as tc


def test_test_case():
    t = tc.TestCase(1234)

    assert t.value == 1234

    t.case_name = "my_test_case"
    assert t.name == "my_test_case"
    assert repr(t) == "<TestCase my_test_case>"

    t.subcase_name = "100"
    assert t.name == "my_test_case[100]"
    assert repr(t) == "<TestCase my_test_case[100]>"

    assert t == tc.TestCase(1234, case_name="my_test_case", subcase_name="100")
    assert t != tc.TestCase(1235, case_name="my_test_case", subcase_name="100")
    assert t != tc.TestCase(1234, case_name="your_test_case", subcase_name="100")
    assert t != tc.TestCase(1234, case_name="my_test_case", subcase_name="101")
    assert t != tc.TestCase(
        1234, case_name="my_test_case", subcase_name="100", metadata={}
    )

    tm = tc.TestCase(1234, metadata=[1, 2, 3, 4])
    assert tm.metadata == [1, 2, 3, 4]


class TestNormaliseTestCaseGenerator(object):
    def test_returns_value(self):
        def foobar(a):
            return a + 1

        assert list(tc.normalise_test_case_generator(foobar, 100)) == [
            tc.TestCase(101, case_name="foobar"),
        ]

    def test_returns_test_case(self):
        def foobar(a):
            return tc.TestCase(a + 1, "plus_one")

        assert list(tc.normalise_test_case_generator(foobar, 100)) == [
            tc.TestCase(101, case_name="foobar", subcase_name="plus_one"),
        ]

    def test_returns_none(self):
        def foobar(a):
            return None

        assert list(tc.normalise_test_case_generator(foobar, 100)) == []

    def test_yields_value(self):
        def foobar(a):
            yield a + 1
            yield a + 2
            yield a + 3

        assert list(tc.normalise_test_case_generator(foobar, 100)) == [
            tc.TestCase(101, case_name="foobar", subcase_name="0"),
            tc.TestCase(102, case_name="foobar", subcase_name="1"),
            tc.TestCase(103, case_name="foobar", subcase_name="2"),
        ]

    def test_yields_testcase(self):
        def foobar(a):
            yield tc.TestCase(a + 1, "one")
            yield tc.TestCase(a + 2, "two")
            yield tc.TestCase(a + 3, "three")

        assert list(tc.normalise_test_case_generator(foobar, 100)) == [
            tc.TestCase(101, case_name="foobar", subcase_name="one"),
            tc.TestCase(102, case_name="foobar", subcase_name="two"),
            tc.TestCase(103, case_name="foobar", subcase_name="three"),
        ]

    def test_yields_none(self):
        def foobar(a):
            yield tc.TestCase(a + 1, "one")
            yield None
            yield tc.TestCase(a + 3, "three")

        assert list(tc.normalise_test_case_generator(foobar, 100)) == [
            tc.TestCase(101, case_name="foobar", subcase_name="one"),
            tc.TestCase(103, case_name="foobar", subcase_name="three"),
        ]


class TestRegistry(object):
    def test_empty(self):
        r = tc.Registry()
        assert list(r.generate_test_cases("foo", bar=1234)) == []
        assert list(r.iter_independent_generators("foo", bar=1234)) == []

    @pytest.fixture
    def registry_and_call_counts(self):
        registry = tc.Registry()

        call_counts = {
            "foo": 0,
            "bar": 0,
        }

        @registry.register_test_case_generator
        def foo(a):
            call_counts["foo"] += 1
            return a + 1

        @registry.register_test_case_generator
        def bar(a):
            call_counts["bar"] += 1
            yield a + 1
            yield a + 2
            yield a + 3

        return registry, call_counts

    @pytest.fixture
    def registry(self, registry_and_call_counts):
        return registry_and_call_counts[0]

    @pytest.fixture
    def call_counts(self, registry_and_call_counts):
        return registry_and_call_counts[1]

    def test_generate_test_cases(self, registry, call_counts):
        assert list(registry.generate_test_cases(100)) == [
            tc.TestCase(101, case_name="foo"),
            tc.TestCase(101, case_name="bar", subcase_name="0"),
            tc.TestCase(102, case_name="bar", subcase_name="1"),
            tc.TestCase(103, case_name="bar", subcase_name="2"),
        ]

        assert call_counts == {"foo": 1, "bar": 1}

    def test_iter_independent_generators(self, registry, call_counts):
        gens = list(registry.iter_independent_generators(100))
        assert len(gens) == 2
        assert call_counts == {"foo": 0, "bar": 0}

        assert list(gens[0]()) == [
            tc.TestCase(101, case_name="foo"),
        ]
        assert call_counts == {"foo": 1, "bar": 0}

        assert list(gens[1]()) == [
            tc.TestCase(101, case_name="bar", subcase_name="0"),
            tc.TestCase(102, case_name="bar", subcase_name="1"),
            tc.TestCase(103, case_name="bar", subcase_name="2"),
        ]
        assert call_counts == {"foo": 1, "bar": 1}

    def test_iter_registered_functions(self, registry, call_counts):
        funcs = list(registry.iter_registered_functions())
        assert len(funcs) == 2
        assert call_counts == {"foo": 0, "bar": 0}

        assert set(f.__name__ for f in funcs) == set(["foo", "bar"])
