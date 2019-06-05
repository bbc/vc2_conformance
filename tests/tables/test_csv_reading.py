# -*- coding: utf-8 -*-

import pytest

from collections import namedtuple

from enum import IntEnum

from vc2_conformance._constraint_table import allowed_values_for, ValueSet, AnyValue

from vc2_conformance.tables._csv_reading import (
    is_ditto,
    read_csv_without_comments,
    read_enum_from_csv,
    read_lookup_from_csv,
    read_constraints_from_csv,
    read_quantisation_matrices_from_csv,
    to_list,
    to_enum_from_index,
    to_enum_from_name,
    to_dict_value,
)


def test_is_ditto():
    # NB: This is intentionally not marked as a unicode string so in Python 2.7
    # this will be interpreted as bytes -- as these characters will be if read
    # from a CSV file.
    quote_characters_and_spaces = ' " “ ” \' ’ ’ ` '
    assert is_ditto(quote_characters_and_spaces) is True
    assert is_ditto("") is False
    assert is_ditto(" ") is False
    assert is_ditto(" foo ") is False


def test_read_csv_without_comments():
    lines = read_csv_without_comments("test_table.csv")
    assert [l["index"] for l in lines] == ["1", "2", "", "", "3"]


def test_read_enum_from_csv():
    Test = read_enum_from_csv("test_table.csv", "Test")
    
    assert Test.__name__ == "Test"
    
    assert len(Test) == 3
    assert Test.one == 1
    assert Test.two == 2
    assert Test.three == 3


class TestReadLookupFromCSV(object):
    
    @pytest.fixture
    def Test(self):
        return read_enum_from_csv("test_table.csv", "Test")
    
    def test_simple(self, Test):
        TestTuple = namedtuple("TestTuple", "value0,value1")
        
        lookup = read_lookup_from_csv("test_table.csv", Test, TestTuple)
        
        assert lookup == {
            Test.one: TestTuple("1 (one)", "100"),
            Test.two: TestTuple("2 (two)", "200"),
            Test.three: TestTuple("3 (three)", "300"),
        }
    
    def test_type_conversion(self, Test):
        TestTuple = namedtuple("TestTuple", "value1,value2")
        
        lookup = read_lookup_from_csv(
            "test_table.csv",
            Test, TestTuple,
            type_conversions={"value1": int},
        )
        
        assert lookup == {
            Test.one: TestTuple(100, "sequence_header"),
            Test.two: TestTuple(200, "padding_data"),
            Test.three: TestTuple(300, "end_of_sequence"),
        }
    
    def test_keeping_value_from_last_row_when_absent(self, Test):
        TestTuple = namedtuple("TestTuple", "value3")
        
        lookup = read_lookup_from_csv("test_table.csv", Test, TestTuple)
        
        assert lookup == {
            Test.one: TestTuple(""),
            Test.two: TestTuple("Something"),
            Test.three: TestTuple("Something"),
        }


def test_read_constraints_from_csv():
    constraints = read_constraints_from_csv("test_constraints.csv")
    
    # Every column included (incl. empty column!)
    assert len(constraints) == 4
    
    # All columns should have all row names
    assert all(set(c) == set(["foo", "bar", "baz", "quo", "qux"])
               for c in constraints)
    
    # Plain integers in 'foo'
    assert constraints[0]["foo"] == ValueSet(1)
    assert constraints[1]["foo"] == ValueSet(2)
    assert constraints[2]["foo"] == ValueSet()  # Empty
    assert constraints[3]["foo"] == ValueSet(3)
    
    # Multiple integers in 'bar'
    assert constraints[0]["bar"] == ValueSet(10, 100)
    assert constraints[1]["bar"] == ValueSet(20, 200)
    assert constraints[2]["bar"] == ValueSet()  # Empty
    assert constraints[3]["bar"] == ValueSet(30, 300)
    
    # 'Ditto' used in 'baz'
    assert constraints[0]["baz"] == ValueSet(12)
    assert constraints[1]["baz"] == ValueSet(12)  # Ditto'd
    assert constraints[2]["baz"] == ValueSet()  # Empty
    assert constraints[3]["baz"] == ValueSet(3)
    
    # 'any', ranges and empty values used in 'quo'
    assert constraints[0]["quo"] == AnyValue()
    assert constraints[1]["quo"] == ValueSet((2, 200), (300, 3000))
    assert constraints[2]["quo"] == ValueSet()  # Empty
    assert constraints[3]["quo"] == ValueSet()
    
    # Booleans in 'qux'
    assert constraints[0]["qux"] == ValueSet(False)
    assert constraints[1]["qux"] == ValueSet(True)
    assert constraints[2]["qux"] == ValueSet()  # Empty
    assert constraints[3]["qux"] == ValueSet(True, False)


@pytest.mark.parametrize("string,exp_list", [
    ("", []),
    ("foo,bar ,baz, qux , quo,", ["foo", "bar", "baz", "qux", "quo"]),
])
def test_to_list(string, exp_list):
    assert to_list(str)(string) == exp_list



class MyEnum(IntEnum):
    foo = 123
    bar = 321

@pytest.mark.parametrize("string,exp_value", [
    ("123", MyEnum.foo),
    ("321", MyEnum.bar),
])
def test_to_enum_from_index(string, exp_value):
    assert to_enum_from_index(MyEnum)(string) is exp_value

@pytest.mark.parametrize("string,exp_value", [
    ("foo", MyEnum.foo),
    ("bar", MyEnum.bar),
])
def test_to_enum_from_name(string, exp_value):
    assert to_enum_from_name(MyEnum)(string) is exp_value


@pytest.mark.parametrize("string,exp_value", [
    ("foo", 123),
    ("bar", 321),
])
def test_to_dict_value(string, exp_value):
    assert to_dict_value({"foo": 123, "bar": 321})(string) == exp_value


def test_read_qauntisation_matrices_from_csv():
    qm = read_quantisation_matrices_from_csv("test_quantisation_matrices.csv")
    
    assert qm == {
        (1, 2, 1, 3): {
            0: {"LL": 11},
            1: {"HL": 211, "LH": 212, "HH": 213},
        },
        (1, 2, 2, 3): {
            0: {"LL": 12},
            1: {"HL": 221, "LH": 222, "HH": 223},
        },
        (3, 4, 1, 5): {
            0: {"L": 3},
        },
        (3, 4, 2, 5): {
            1: {"H": 4},
        },
    }
