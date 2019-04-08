import pytest

from enum import Enum

from vc2_conformance.structured_dict import structured_dict, Value


class TestValue(object):
    
    def test_no_args(self):
        v = Value()
        assert v.has_default is False
        assert v.formatter is str
        assert v.friendly_formatter is None
    
    def test_with_default(self):
        v = Value(default="foo")
        assert v.has_default is True
        assert v.default == "foo"
        assert v.formatter is str
        assert v.friendly_formatter is None
    
    def test_with_default_factory(self):
        v = Value(default_factory=list)
        assert v.has_default is True
        assert v.default_factory is list
        assert v.formatter is str
        assert v.friendly_formatter is None
    
    def test_with_formatter(self):
        v = Value(formatter=hex)
        assert v.has_default is False
        assert v.formatter is hex
        assert v.friendly_formatter is None
    
    def test_with_friendly_formatter(self):
        v = Value(friendly_formatter=hex)
        assert v.has_default is False
        assert v.formatter is str
        assert v.friendly_formatter is hex
    
    def test_enum(self):
        class MyEnum(Enum):
            a = 1
            b = 2
            c = 3
        
        v = Value(enum=MyEnum)
        assert v.has_default is False
        assert v.formatter is str
        
        assert v.friendly_formatter(1) == "a"
        assert v.friendly_formatter(2) == "b"
        assert v.friendly_formatter(3) == "c"
        assert v.friendly_formatter(MyEnum.a) == "a"
        assert v.friendly_formatter(MyEnum.b) == "b"
        assert v.friendly_formatter(MyEnum.c) == "c"
        assert v.friendly_formatter(0) is None
        assert v.friendly_formatter("foo") is None
    
    def test_get_default(self):
        v = Value(default=123)
        assert v.get_default() == 123
        
        v = Value(default_factory=list)
        d1 = v.get_default()
        assert d1 == []
        d2 = v.get_default()
        assert d2 == []
        assert d1 is not d2
    
    def test_to_string(self):
        v = Value()
        assert v.to_string({}, 123) == "123"
        assert v.to_string({}, "abc") == "abc"
        
        v = Value(formatter=bin)
        assert v.to_string({}, 0b1010) == "0b1010"
        
        v = Value(friendly_formatter=str.upper)
        assert v.to_string({}, "foo") == "FOO (foo)"
        
        v = Value(formatter=str.lower, friendly_formatter=str.upper)
        assert v.to_string({}, "Foo") == "FOO (foo)"
        
        v = Value(formatter=lambda d,v: "{} in {}".format(v, d), formatter_pass_dict=True)
        assert v.to_string({"a": "Foo"}, "Foo") == "Foo in {'a': 'Foo'}"
        
        v = Value(friendly_formatter=lambda d,v: "{} in {}".format(v, d),
                  friendly_formatter_pass_dict=True)
        assert v.to_string({"a": "Foo"}, "Foo") == "Foo in {'a': 'Foo'} (Foo)"


@structured_dict
class MyStructuredDict(object):
    """
    A structured dict for test purposes.
    """
    # With default
    name = Value(default="Anon")
    
    # Without default, also has a formatter
    age = Value(friendly_formatter=lambda d, v: "{} (one of {} entries)".format(v, len(d)),
                friendly_formatter_pass_dict=True,
                formatter=hex)
    
    # Hidden value (and with factory)
    _hidden = Value(default_factory=list)
    
    # Not a Value
    other = "not a value"
    
    # Methods
    def hello(self):
        return "Hello, {}".format(self.name)
    
    # Static methods
    @staticmethod
    def random():
        return 4  # Chosen by fair dice roll


class TestStructuredDict(object):
    
    def test_constructors(self):
        # Check defaults work
        d = MyStructuredDict()
        assert d.name == "Anon"
        assert hasattr(d, "age") is False
        assert d._hidden == []
        
        # Check can override defaults with kwargs
        d = MyStructuredDict(name="Foo", age=123, _hidden=[1, 2, 3])
        assert d.name == "Foo"
        assert d.age == 123
        assert d._hidden == [1, 2, 3]
        
        # Can initialise with dict
        d = MyStructuredDict({"name": "Foo", "age": 123})
        assert d.name == "Foo"
        assert d.age == 123
        
        # Can initialise with pairs
        d = MyStructuredDict([("name", "Foo"), ("age", 123)])
        assert d.name == "Foo"
        assert d.age == 123
        
        # Kwargs take precidence
        d = MyStructuredDict([("name", "Foo"), ("age", 123)], age=321)
        assert d.name == "Foo"
        assert d.age == 321
        
        # Defaults don't apply when providing an iterable
        d = MyStructuredDict([])
        assert "name" not in d
        assert "age" not in d
        
        # Factory constructors work
        d1 = MyStructuredDict()
        d2 = MyStructuredDict()
        assert d1._hidden is not d2._hidden
    
    def test_non_value_items(self):
        assert MyStructuredDict.other == "not a value"
        assert MyStructuredDict.random() == 4
        
        d = MyStructuredDict(name="Foo")
        assert d.hello() == "Hello, Foo"
        d.other = "custom non-value"
        assert d.other == "custom non-value"
    
    def test_values_as_attrs(self):
        d = MyStructuredDict(name="Foo")
        
        assert d.name == "Foo"
        d.name = "Bar"
        assert d.name == "Bar"
        
        del d.name
        assert hasattr(d, "name") is False
        
        d.name = "Back!"
        assert d.name == "Back!"
    
    def test_values_as_attrs(self):
        d = MyStructuredDict(name="Foo")
        
        assert d["name"] == "Foo"
        d["name"] = "Bar"
        assert d["name"] == "Bar"
        assert "name" in d
        
        del d["name"]
        assert "name" not in d
        
        d["name"] = "Back!"
        assert d["name"] == "Back!"
    
    def test_cannot_create_or_delete_non_known_values(self):
        d = MyStructuredDict()
        
        with pytest.raises(KeyError):
            d["foo"] = "bar"
        
        with pytest.raises(KeyError):
            del d["foo"]
        
        with pytest.raises(AttributeError):
            d.foo = "bar"
        
        with pytest.raises(AttributeError):
            del d.foo
    
    def test_contains(self):
        d = MyStructuredDict()
        
        assert "name" in d
        assert "age" not in d
        
        # Exists as an attribute on the object, but not one of the known names
        assert "hello" not in d
        assert "other" not in d
        assert "random" not in d
    
    def test_clear(self):
        d = MyStructuredDict()
        assert "name" in d
        assert "age" not in d
        
        d.clear()
        assert "name" not in d
        assert "age" not in d
    
    def test_iteration_and_len(self):
        d = MyStructuredDict()
        
        assert len(d) == 2
        assert bool(d) is True
        assert list(d) == ["name", "_hidden"]
        assert list(d.keys()) == ["name", "_hidden"]
        assert list(d.values()) == ["Anon", []]
        assert list(d.items()) == [("name", "Anon"), ("_hidden", [])]
        
        d.age = 10
        assert len(d) == 3
        assert bool(d) is True
        assert list(d) == ["name", "age", "_hidden"]
        assert list(d.keys()) == ["name", "age", "_hidden"]
        assert list(d.values()) == ["Anon", 10, []]
        assert list(d.items()) == [("name", "Anon"), ("age", 10), ("_hidden", [])]
        
        d.clear()
        assert len(d) == 0
        assert bool(d) is False
        assert list(d) == []
        assert list(d.keys()) == []
        assert list(d.values()) == []
        assert list(d.items()) == []
    
    def test_repr(self):
        # Make sure the __str__ formatter isn't taking this on...
        assert repr(MyStructuredDict()).startswith("<")
    
    def test_str(self):
        d = MyStructuredDict()

        # Should print only values which are set
        assert str(d) == (
            "MyStructuredDict:\n"
            "  name: Anon"
        )

        # Should use formatters
        d.age = 32
        assert str(d) == (
            "MyStructuredDict:\n"
            "  name: Anon\n"
            "  age: 32 (one of 3 entries) (0x20)"
        )
        
        # Should handle multi-line values
        d.name = "foo\nbar\nbaz"
        assert str(d) == (
            "MyStructuredDict:\n"
            "  name: foo\n"
            "  bar\n"
            "  baz\n"
            "  age: 32 (one of 3 entries) (0x20)"
        )

        # Should work if we delete all values
        d.clear()
        assert str(d) == "MyStructuredDict"
    
    def test_copy(self):
        d1 = MyStructuredDict(age=100)
        del d1.name
        
        d2 = d1.copy()
        assert isinstance(d2, MyStructuredDict)
        assert d2 is not d1
        assert "name" not in d2
        assert d2.age == 100
        
        d2.age = 10
        assert d2.age == 10
        assert d1.age == 100  # Unchanged
    
    def test_get(self):
        d = MyStructuredDict()
        
        assert d.get("name") == "Anon"
        assert d.get("name", "foo") == "Anon"
        assert d.get("age") is None
        assert d.get("age", 123) == 123
    
    def test_setdefault(self):
        d = MyStructuredDict()
        
        assert d.setdefault("name") == "Anon"
        assert d.setdefault("name", "foo") == "Anon"
        
        assert d.setdefault("age") is None
        assert d.age is None
        del d.age
        
        assert d.setdefault("age", 123) == 123
        assert d.age == 123
        del d.age
    
    def test_pop(self):
        d = MyStructuredDict()
        
        assert d.pop("name") == "Anon"
        assert "name" not in d
        
        with pytest.raises(KeyError):
            d.pop("name")
        
        assert d.pop("name", "nope") == "nope"
        
        with pytest.raises(TypeError):
            assert d.pop("name", "nope", "unexpected arg")
    
    def test_popitem(self):
        d = MyStructuredDict(name="Foo", age=123)
        
        assert d.popitem() == ("name", "Foo")
        assert "name" not in d
        assert d.popitem() == ("age", 123)
        assert "age" not in d
        assert d.popitem() == ("_hidden", [])
        assert "_hidden" not in d
        
        with pytest.raises(KeyError):
            d.popitem()
    
    def test_update(self):
        # Using dict
        d = MyStructuredDict(age=123)
        d.update({"name": "Foo"})
        assert d.name == "Foo"
        assert d.age == 123
        
        # Using list of tuples
        d = MyStructuredDict(age=123)
        d.update([("name", "Foo")])
        assert d.name == "Foo"
        assert d.age == 123
        
        # Using kwargs
        d = MyStructuredDict(age=123)
        d.update(name="Foo")
        assert d.name == "Foo"
        assert d.age == 123
        
        # Kwargs take precidence (but work in addition, not instead of
        # argument.
        d = MyStructuredDict(age=123)
        d.update({"name": "Bar", "age": 0}, name="Foo")
        assert d.name == "Foo"
        assert d.age == 0
    
    def test_asdict(self):
        d = MyStructuredDict()
        assert d.asdict() == {"name": "Anon", "_hidden": []}
    
    def test_missing(self):
        # Normally, just throw a key error
        d = MyStructuredDict()
        with pytest.raises(KeyError):
            d["unknown"]
        
        # When __missing__ is defined, use that
        @structured_dict
        class SDWithMissing(object):
            foo = Value()
            
            def __missing__(self, key):
                return "Missing {}".format(key)
        
        d = SDWithMissing(foo="bar")
        assert d["foo"] == "bar"
        assert d["unknown"] == "Missing unknown"
