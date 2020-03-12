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


class TestNormaliseTestCaseGenerator(object):

    def test_returns_value(self):
        @tc.normalise_test_case_generator
        def foobar(a):
            return a + 1
        
        assert list(foobar(100)) == [
            tc.TestCase(101, case_name="foobar"),
        ]

    def test_returns_test_case(self):
        @tc.normalise_test_case_generator
        def foobar(a):
            return tc.TestCase(a + 1, "plus_one")
        
        assert list(foobar(100)) == [
            tc.TestCase(101, case_name="foobar", subcase_name="plus_one"),
        ]

    def test_yields_value(self):
        @tc.normalise_test_case_generator
        def foobar(a):
            yield a + 1
            yield a + 2
            yield a + 3
        
        assert list(foobar(100)) == [
            tc.TestCase(101, case_name="foobar", subcase_name="0"),
            tc.TestCase(102, case_name="foobar", subcase_name="1"),
            tc.TestCase(103, case_name="foobar", subcase_name="2"),
        ]

    def test_yields_testcase(self):
        @tc.normalise_test_case_generator
        def foobar(a):
            yield tc.TestCase(a + 1, "one")
            yield tc.TestCase(a + 2, "two")
            yield tc.TestCase(a + 3, "three")
        
        assert list(foobar(100)) == [
            tc.TestCase(101, case_name="foobar", subcase_name="one"),
            tc.TestCase(102, case_name="foobar", subcase_name="two"),
            tc.TestCase(103, case_name="foobar", subcase_name="three"),
        ]


class TestRegistry(object):
    
    def test_empty(self):
        r = tc.Registry()
        assert list(r.generate_test_cases("foo", bar=1234)) == []
    
    def test_normalised_output(self):
        r = tc.Registry()
        
        @r.register_test_case_generator
        def foo(a):
            return a + 1
        
        @r.register_test_case_generator
        def bar(a):
            yield a + 1
            yield a + 2
            yield a + 3
        
        assert list(r.generate_test_cases(100)) == [
            tc.TestCase(101, case_name="foo"),
            tc.TestCase(101, case_name="bar", subcase_name="0"),
            tc.TestCase(102, case_name="bar", subcase_name="1"),
            tc.TestCase(103, case_name="bar", subcase_name="2"),
        ]
