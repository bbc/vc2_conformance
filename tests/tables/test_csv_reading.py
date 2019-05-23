import pytest

from collections import namedtuple

from enum import IntEnum

from vc2_conformance.tables._csv_reading import (
    read_csv_without_comments,
    read_enum_from_csv,
    read_lookup_from_csv,
    to_list,
    to_enum_from_index,
    to_enum_from_name,
    to_dict_value,
)


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
