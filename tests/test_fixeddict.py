import pytest

from enum import IntEnum

from vc2_conformance.fixeddict import fixeddict, Entry, FixedDictKeyError


class TestEntry(object):
    
    def test_no_args(self):
        v = Entry("v")
        assert v.name == "v"
        assert v.formatter is str
        assert v.friendly_formatter is None
    
    def test_with_formatter(self):
        v = Entry("v", formatter=hex)
        assert v.formatter is hex
        assert v.friendly_formatter is None
    
    def test_with_friendly_formatter(self):
        v = Entry("v", friendly_formatter=hex)
        assert v.formatter is str
        assert v.friendly_formatter is hex
    
    def test_enum(self):
        class MyEnum(IntEnum):
            a = 1
            b = 2
            c = 3
        
        v = Entry("v", enum=MyEnum)
        
        assert v.to_string(1) == "a (1)"
        assert v.to_string(2) == "b (2)"
        assert v.to_string(3) == "c (3)"
        assert v.to_string(MyEnum.a) == "a (1)"
        assert v.to_string(MyEnum.b) == "b (2)"
        assert v.to_string(MyEnum.c) == "c (3)"
        assert v.to_string(0) == "0"
        assert v.to_string("foo") == "foo"
        
        # Check can override formatter/friendly_formatter
        v = Entry("v", enum=MyEnum, formatter=hex)
        assert v.to_string(MyEnum.a) == "a (0x1)"
        assert v.to_string(MyEnum.b) == "b (0x2)"
        assert v.to_string(MyEnum.c) == "c (0x3)"
        
        v = Entry("v", enum=MyEnum, friendly_formatter=repr)
        assert v.to_string(MyEnum.a) == "<MyEnum.a: 1> (1)"
        assert v.to_string(MyEnum.b) == "<MyEnum.b: 2> (2)"
        assert v.to_string(MyEnum.c) == "<MyEnum.c: 3> (3)"
    
    def test_to_string(self):
        v = Entry("v")
        assert v.to_string(123) == "123"
        assert v.to_string("abc") == "abc"
        
        v = Entry("v", formatter=bin)
        assert v.to_string(0b1010) == "0b1010"
        
        v = Entry("v", friendly_formatter=str.upper)
        assert v.to_string("foo") == "FOO (foo)"
        
        v = Entry("v", formatter=str.lower, friendly_formatter=str.upper)
        assert v.to_string("Foo") == "FOO (foo)"


MyFixedDict = fixeddict(
    "MyFixedDict",
    # No formatter
    Entry("name"),
    # With a formatter
    Entry("age", friendly_formatter=str, formatter=hex),
    # Hidden value
    Entry("_hidden"),
)

class TestFixedDict(object):
    
    def test_constructors(self):
        # Sanity check standard dictionary initialisation works
        
        # Check empty initialiser
        d = MyFixedDict()
        assert d == {}
        
        # Check can set values with kwargs
        d = MyFixedDict(name="Foo", age=123, _hidden=[1, 2, 3])
        assert d["name"] == "Foo"
        assert d["age"] == 123
        assert d["_hidden"] == [1, 2, 3]
        
        # Can initialise with dict
        d = MyFixedDict({"name": "Foo", "age": 123})
        assert d["name"] == "Foo"
        assert d["age"] == 123
    
    def test_values_as_items(self):
        d = MyFixedDict(name="Foo")
        
        assert d["name"] == "Foo"
        d["name"] = "Bar"
        assert d["name"] == "Bar"
        assert "name" in d
        
        del d["name"]
        assert "name" not in d
        
        d["name"] = "Back!"
        assert d["name"] == "Back!"
    
    def test_cannot_create_unknown_values(self):
        # Construction
        with pytest.raises(FixedDictKeyError, match=r"'foo' not allowed in MyFixedDict"):
            MyFixedDict(foo="bar")
        with pytest.raises(FixedDictKeyError, match=r"'foo' not allowed in MyFixedDict"):
            MyFixedDict([("foo", "bar")])
        
        d = MyFixedDict()
        
        # Assignment
        with pytest.raises(FixedDictKeyError, match=r"'foo' not allowed in MyFixedDict"):
            d["foo"] = "bar"
        
        # setdefault
        with pytest.raises(FixedDictKeyError, match=r"'foo' not allowed in MyFixedDict"):
            d.setdefault("foo", "bar")
        
        # update
        with pytest.raises(FixedDictKeyError, match=r"'foo' not allowed in MyFixedDict"):
            d.update(foo="bar")
        with pytest.raises(FixedDictKeyError, match=r"'foo' not allowed in MyFixedDict"):
            d.update({"foo": "bar"})
    
    def test_update(self):
        d = MyFixedDict({})
        assert d == {}
        d.update(name="bar")
        assert d == {"name": "bar"}
        d.update({"age": 123})
        assert d == {"name": "bar", "age": 123}
        
    def test_repr(self):
        # Should include hidden entries and be a valid constructor
        assert repr(MyFixedDict(name="Anon", _hidden=[])) == (
            "MyFixedDict({"
            "'name': 'Anon', "
            "'_hidden': []"
            "})"
        )
    
    def test_str(self):
        d = MyFixedDict(name="Anon", _hidden=[])

        # Should print only values which are set
        assert str(d) == (
            "MyFixedDict:\n"
            "  name: Anon"
        )

        # Should use formatters
        d["age"] = 32
        assert str(d) == (
            "MyFixedDict:\n"
            "  name: Anon\n"
            "  age: 32 (0x20)"
        )
        
        # Should handle multi-line values
        d["name"] = "foo\nbar\nbaz"
        assert str(d) == (
            "MyFixedDict:\n"
            "  name: foo\n"
            "  bar\n"
            "  baz\n"
            "  age: 32 (0x20)"
        )

        # Should work if we delete all values
        d.clear()
        assert str(d) == "MyFixedDict"
    
    def test_copy(self):
        d1 = MyFixedDict(name="Anon", age=100)
        del d1["name"]
        
        d2 = d1.copy()
        assert isinstance(d2, MyFixedDict)
        assert d2 is not d1
        assert "name" not in d2
        assert d2["age"] == 100
        
        d2["age"] = 10
        assert d2["age"] == 10
        assert d1["age"] == 100  # Unchanged
