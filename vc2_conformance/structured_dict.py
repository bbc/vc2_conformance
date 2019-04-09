"""
In the VC-2 specification, dictionary-like objects (e.g. 'state') are widely
encountered. These dictionaries have all of the usual dictionary semantics
*but* the complete set of entries is well defined by the specification. As
such, these dictionaries are much more like simple classes/structs.

Using the :py:func:`structured_dict` decorator and :py:class:`Value` object,
dictionary-like types with well defined fields can be described like so::

    >>> @structured_dict
    ... class FrameSize(object):
    ...     custom_dimensiions_flag = Value(default=False)
    ...     frame_width = Value()
    ...     frame_height = Value()

In a manner similar to Python 3 :py:module:`dataclasses` and the
'attrs' library, classes defined in this way are imbued with automatically
generated constructors and string representations. For example::

    >>> fs = FrameSize(custom_dimensiions_flag=True,
    ...                frame_width=1920,
    ...                frame_height=1080)
    >>> str(fs)
    FrameSize:
      custom_dimensiions_flag: True
      frame_width: 1920
      frame_height: 1080

In addition, this type behaves both like a class and a dictionary::

    >>> fs.frame_width
    1920
    >>> fs["frame_width"]
    1920

The :py:class:`Value` class *must* be used to define *all* members of a
structured dictionary. The :py:class:`Value` controls several properties about
how that entry in the dictionary is displayed, intialised and used. In the
simplest case, the 'default' value may be used to specify default values to
use when a structured dictionary is initialised without specifying a value::

    >>> @structured_dict
    ... class ExampleDefaults(object):
    ...     foo = Value(default=123)
    ...     bar = Value(default="hello")
    >>> ed = ExampleDefaults()
    >>> str(ed)
    ExampleDefaults:
      foo: 123
      bar: "hello"

If an entry is not assigned a default value and then not assigned a value
during construction, this value will behave as if missing from the dictionary
or class::

    >>> fs = FrameSize()
    >>> str(fs)
    FrameSize:
        custom_dimensiions_flag: False
    >>> fs["frame_width"]
    Traceback (most recent call last):
      ...
    KeyError: 'frame_width'
    >>> fs.frame_height
    Traceback (most recent call last):
      ...
    AttributeError: 'FrameSize' object has no attribute 'frame_height'

Assigning values, however, results in those entries becoming available again::

    >>> fs.custom_dimensiions_flag = True
    >>> fs.frame_width = 1920
    >>> fs["frame_height"] = 1080
    >>> str(fs)
    FrameSize:
      custom_dimensiions_flag: True
      frame_width: 1920
      frame_height: 1080

Attepmting to add keys which have not been defined in advance is not allowed::

    >>> fs["foo"] = 123
    Traceback (most recent call last):
      ...
    KeyError: 'foo'
    >>> fs["bar"] = 123
    Traceback (most recent call last):
      ...
    AttributeError: 'FrameSize' object has no attribute 'bar'

Entries can control how they are displayed by specifying custom string
formatter functions. For example::

    >>> from vc2_conformance.string_utils import Hex, Bin
    >>> @structured_dict
    ... class ExampleFormatters(object):
    ...     decimal = Value()
    ...     hexidecimal = Value(formatter=Hex(4))
    ...     binary = Value(formatter=Bin(4))
    >>> ef = ExampleFormatters(decimal=123, hexidecimal=0xABC, binary=0b101)
    >>> str(ef)
    ExampleFormatters:
      decimal: 123
      hexidecimal: 0x0ABC
      binary: 0x0101

For values which may hold :py:class:`enum.Enum` types, the ``enum`` shorthand
can be used to cause the string representation of the dictionary to include
both the enumeration name and underlying value, when the value held is a valid
enumeration value, and just the underlying value otherwise. For example::

    >>> from enum import IntEnum
    >>> class ParseCodes(Enum):
    ...     sequence_header = 0x00
    ...     end_of_sequence = 0x10
    ...     auxiliary_data = 0x20
    ...     padding_data = 0x30
    ...     low_delay_picture = 0xC8
    ...     high_quality_picture = 0xE8
    ...     low_delay_picture_fragment = 0xCC
    ...     high_quality_picture_fragment = 0xEC
    
    >>> @structured_dict
    ... class ParseInfo(object):
    ...     parse_info_prefix = Value(default=0x42424344, formatter=Hex(8))
    ...     parse_code = Value(default=ParseCodes.end_of_sequence,
    ...                        enum=ParseCodes,
    ...                        formatter=Hex(2)),
    ...     next_parse_offset = Value(default=0)
    ...     previous_parse_offset = Value(default=0)
    
    >>> pi = ParseInfo()
    >>> str(pi)
    ParseInfo:
       parse_info_prefix: 0x42424344
       parse_code: end_of_sequence (0x10)
       next_parse_offset: 0
       previous_parse_offset: 0
    
    >>> # Change to an int and the string representation still shows the name
    >>> pi.parse_code = 0x30
    >>> str(pi)
    ParseInfo:
       parse_info_prefix: 0x42424344
       parse_code: padding_data (0x30)
       next_parse_offset: 0
       previous_parse_offset: 0
    
    >>> # Change to an out-of-range value and just the value is shown
    >>> pi.parse_code = 0xFF
    >>> str(pi)
    ParseInfo:
       parse_info_prefix: 0x42424344
       parse_code: 0xFF
       next_parse_offset: 0
       previous_parse_offset: 0
"""

from collections import OrderedDict

from itertools import chain

from vc2_conformance._string_utils import indent


__all__ = [
    "structured_dict",
    "Value",
]


class Value(object):
    """
    Defines the behaviour of a value in a structured dictionary (a class
    decorated with :py:func:`structured_dict`.
    """
    
    _counter = 0
    """
    Used to assign an ascending index to every :py:class:`Value` instance to
    enable ordering values by when they were defined.
    """
    
    def __init__(self, **kwargs):
        """
        All arguments are keyword-only.
        
        Parameters
        ==========
        default
            The default value to assign to this entry. If not given, this entry
            will initially not exist.
        default_factory : function() -> value
            A function to call to generate new instances of a default value.
            Useful if a default value is a list, for example, and a new list
            should be made for every structured dict instance. Must not be used
            at the same time as 'default' argument.
        formatter : function(value) -> string
            A function which takes a value and returns a string representation
            to use when printing this value as a string. Defaults to 'str'.
        formatter_pass_dict : bool
            If specified, a bool which, if True, causes the dictionary to be
            passed as first argument to the formatter function.
        friendly_formatter: function(value) -> string
            If provided, when converting this value to a string, this function
            will be used to generate a 'friendly' name for this value. This
            will be followed by the actual value in brackets. If this function
            returns None, only the actual value will be shown (without
            brackets).
        friendly_formatter_pass_dict : bool
            If specified, a bool which, if True, causes the dictionary to be
            passed as first argument to the friendly_formatter function.
        enum : :py:class:`Enum`
            A convenience interface which is equivalent to the following
            ``friendly_formatter`` argument::
            
                def friendly_enum_formatter(value):
                    try:
                        return enum(value).name
                    except ValueError:
                        return None
        """
        self._index = Value._counter
        Value._counter += 1
        
        self.has_default = "default" in kwargs or "default_factory" in kwargs
        self.default = kwargs.pop("default", None)
        self.default_factory = kwargs.pop("default_factory", None)
        
        if "enum" in kwargs:
            enum_type = kwargs.pop("enum")
            
            def friendly_enum_formatter(value):
                try:
                    return enum_type(value).name
                except ValueError:
                    return None
            
            kwargs["friendly_formatter"] = friendly_enum_formatter
        
        self.formatter = kwargs.pop("formatter", str)
        self.formatter_pass_dict = kwargs.pop("formatter_pass_dict", False)
        self.friendly_formatter = kwargs.pop("friendly_formatter", None)
        self.friendly_formatter_pass_dict = kwargs.pop("friendly_formatter_pass_dict", False)
        
        if kwargs:
            raise TypeError("unexpected keyword arguments: {}".format(
                ", ".join(kwargs.keys())))
    
    def get_default(self):
        """Return the default value of this object."""
        if self.default_factory:
            return self.default_factory()
        else:
            return self.default
    
    def to_string(self, dictionary, value):
        """
        Convert a value to a string according to the specification in this
        :py:class:`Value`.
        """
        if self.formatter_pass_dict:
            value_string = self.formatter(dictionary, value)
        else:
            value_string = self.formatter(value)
        
        if self.friendly_formatter is not None:
            if self.friendly_formatter_pass_dict:
                friendly_string = self.friendly_formatter(dictionary, value)
            else:
                friendly_string = self.friendly_formatter(value)
            if friendly_string is not None:
                value_string = "{} ({})".format(friendly_string, value_string)
        
        return value_string


def structured_dict(cls):
    """
    Class decorator which turns the specified class into a structured
    dictionary.
    
    The decorated class should have a series of :py:class:`Value` attributes,
    e.g.::
        
        >>> @structured_dict
        ... class MyStructuredDict(object):
        ...     attr1 = Value(default=123, formatter=hex)
        ...     attr2 = Value()
    
    .. warning::
    
        Any attributes (and methods) which are not :py:class:`Value` will be
        retained as attributes but will not form part of the dictionary
        (meaning, e.g., that they can't be set via the constructor or be
        accessed like a dictionary). Having such attributes is almost certainly
        a mistake.
        
        The decorated class should limit itself to being little more than a
        struct/dict type object. You should avoid adding complicated methods or
        inheritance.
    
    Decorated instances are given a constructor which takes initial values for
    all entries by keyword, and uses the default values specified if not
    provided::
        
        >>> d = MyStructuredDict(attr1=10, attr2=20)
        >>> d.attr1
        10
        >>> d.attr2
        20
        
        >>> d = MyStructuredDict(attr2=321)
        >>> d.attr1
        123
        >>> d.attr2
        321
    
    Instances can also be constructed by passing in an existing dictionary::
    
        >>> d = MyStructuredDict({"attr1": 100, "attr2": 200})
        >>> str(d)
        MyStructuredDict:
          attr1: 100
          attr2: 200
    
    Unlike when keyword arguments are used, if an existing dictionary is
    provided as an argument, default values for any missing values are **not**
    provided::
        
        >>> d = MyStructuredDict({})
        >>> str(d)
        MyStructuredDict
    
    Any values which are neither given a default value nor a keyword value
    during construction will not be present in the instance. For example::
    
        >>> d = MyStructuredDict()
        >>> d.attr1
        123
        >>> d.attr2
        Traceback (most recent call last):
          ...
        AttributeError: 'MyStructuredDict' object has no attribute 'attr2'
    
    Values can be read, set and deleted like ordinary object attributes::
    
        >>> d = MyStructuredDict()
        >>> d.attr1 = 1234
        >>> d.attr1
        1234
        >>> del d.attr1
        >>> d.attr1
        Traceback (most recent call last):
          ...
        AttributeError: 'MyStructuredDict' object has no attribute 'attr1'
    
    Attempting to get, set or delete any value which was not defined by the
    class results in an :py:exc:`AttributeError`::
    
        >>> d = MyStructuredDict()
        >>> d.foo = 123
        Traceback (most recent call last):
          ...
        AttributeError: 'MyStructuredDict' object has no attribute 'foo'
    
    Instances also implement all of the interfaces of :py:class:`dict`::
    
        >>> d = MyStructuredDict()
        
        >>> # Access values like a dict
        >>> d["attr1"]
        123
        >>> "attr2" in d
        False
        
        >>> # Iterate like a dict
        >>> list(d)
        ["attr1"]
        >>> list(d.keys())
        ["attr1"]
        >>> list(d.values())
        [123]
        >>> list(d.items())
        [("attr1", 123)]
        
        >>> # Length information
        >>> len(d)
        1
        >>> bool(d)
        True
    
    For advanced uses, a :py:meth:`dict.__missing__`  method may be provided,
    as in :py:class:`dict` subclasses, which is called in cases where an
    unrecognised key is used to access the dictionary.
    
    When printed as a string, structured dictionaries use the formatting
    options specified in the :py:class:`Value` instances::
    
        >>> d = MyStructuredDict(attr1=0x123, attr2=200)
        >>> str(d)
        MyStructuredDict:
          attr1: 0x123
          attr2: 200
    
    The ``asdict`` method can be used to return a :py:class:`dict` containing
    the same values as a structured dict, if required::
        
        >>> d = MyStructuredDict(attr1=100, attr2=200)
        >>> d.asdict()
        {"attr1": 100, "attr2": 200}
    
    As a final detail, any :py:class:`Value` attribute whose name is prefixed
    with an underscore (``_``) will be omitted from the string representation.
    """
    # Collect the list of Value instances defined for this class
    # {name: Value, ...}
    value_objs = OrderedDict(sorted(
        (
            (name, value)
            for name, value in vars(cls).items()
            if isinstance(value, Value)
        ),
        key=lambda nv: nv[1]._index,
    ))
    
    # Create all of the methods which will be added to the class
    methods = {}
    
    def __init__(self, iterable=None, **kwargs):
        if iterable is not None:
            # Convert iterable which may be a dict or may be an iterable of (name,
            # value) pairs into an iterator of (name, value) pairs.
            if hasattr(iterable, "items"):
                iterable = iterable.items()
        else:
            # Only populate default values if no iterable is provided
            iterable = (
                (name, value_obj.get_default())
                for name, value_obj in value_objs.items()
                if value_obj.has_default and name not in kwargs
            )
        
        for name, value in chain(iterable, kwargs.items()):
            if name in value_objs:
                setattr(self, name, value)
            else:
                raise TypeError("unexpected keyword argument '{}'".format(
                    name))
    
    methods["__init__"] = __init__
    
    def __setattr__(self, name, value):
        value_obj = value_objs.get(name)
        if value_obj is None and not hasattr(self, name):
            raise AttributeError("'{}' object has no attribute '{}'".format(
                self.__class__.__name__,
                name))
        else:
            super(cls, self).__setattr__(name, value)
    
    methods["__setattr__"] = __setattr__
    
    def __getitem__(self, key):
        if key in value_objs and hasattr(self, key):
            return getattr(self, key)
        elif hasattr(self, "__missing__"):
            return self.__missing__(key)
        else:
            raise KeyError(key)
    
    methods["__getitem__"] = __getitem__
    
    def __setitem__(self, key, value):
        if key in value_objs:
            return setattr(self, key, value)
        else:
            raise KeyError(key)
    
    methods["__setitem__"] = __setitem__
    
    def __delitem__(self, key):
        if key in value_objs:
            return delattr(self, key)
        else:
            raise KeyError(key)
    
    methods["__delitem__"] = __delitem__
    
    def __contains__(self, key):
        return key in value_objs and hasattr(self, key)
    
    methods["__contains__"] = __contains__
    
    def __iter__(self):
        for name in value_objs:
            if name in self:
                yield name
    
    methods["__iter__"] = __iter__
    methods["keys"] = __iter__
    
    def __len__(self):
        count = 0
        for name in value_objs:
            if name in self:
                count += 1
        return count
    
    methods["__len__"] = __len__
    
    def __nonzero__(self):
        for name in value_objs:
            if name in self:
                return True
        return False
    
    methods["__nonzero__"] = __nonzero__
    
    def __str__(self):
        if len(self) == 0:
            return self.__class__.__name__
        else:
            return "{}:\n{}".format(
                self.__class__.__name__,
                "\n".join(
                    indent("{}: {}".format(
                        name, value_obj.to_string(self, self[name])
                    ))
                    for name, value_obj in value_objs.items()
                    if name in self and not name.startswith("_")
                )
            )
    
    methods["__str__"] = __str__
    
    def clear(self):
        for name in value_objs:
            if name in self:
                del self[name]
    
    methods["clear"] = clear
    
    def copy(self):
        return self.__class__(self)
    
    methods["copy"] = copy
    
    def items(self):
        for name in value_objs:
            if name in self:
                yield (name, self[name])
    
    methods["items"] = items
    
    def values(self):
        for name in value_objs:
            if name in self:
                yield self[name]
    
    methods["values"] = values
    
    def get(self, key, default=None):
        if key in self:
            return self[key]
        else:
            return default
    
    methods["get"] = get
    
    def setdefault(self, key, default=None):
        if key in self:
            return self[key]
        else:
            self[key] = default
            return default
    
    methods["setdefault"] = setdefault
    
    def pop(self, key, *default):
        if len(default) > 1:
            raise TypeError()
        
        if key in self:
            value = self[key]
            del self[key]
            return value
        elif default:
            return default[0]
        else:
            raise KeyError(key)
    
    methods["pop"] = pop
    
    def popitem(self):
        for name in value_objs:
            if name in self:
                value = self[name]
                del self[name]
                return (name, value)
        raise KeyError()
    
    methods["popitem"] = popitem
    
    def update(self, iterable=None, **kwargs):
        if iterable is None:
            pass
        elif hasattr(iterable, "keys"):
            for name in iterable:
                self[name] = iterable[name]
        else:
            for (name, value) in iterable:
                self[name] = value
        
        for name, value in kwargs.items():
            self[name] = value
    
    methods["update"] = update
    
    def asdict(self):
        return {
            name: self[name]
            for name in value_objs
            if name in self
        }
    
    methods["asdict"] = asdict
    
    # Check none of the Value names conflict with methods we're about to add
    for name in value_objs:
        if name in methods:
            raise TypeError(
                "structured_dict classes cannot the name '{}'".format(name))
    
    # Remove the 'Value' attributes from the class so that they don't get
    # picked up when getting attributes of instances of the class.
    for name in value_objs:
        delattr(cls, name)
    
    # Add the new methods
    for name, method in methods.items():
        setattr(cls, name, method)
    
    return cls
