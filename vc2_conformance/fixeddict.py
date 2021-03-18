r"""
The :py:mod:`vc2_conformance.fixeddict` module provides the
:py:func:`fixeddict` function for creating new :py:class:`dict` subclasses
which permit only certain keys to be used.  These new types may be used like
ordinary Python dictionaries but add three main features:

* Explicitness -- The VC-2 pseudocode creates and uses many dictionaries
  (called 'maps' in the specification) in place of struct-like objects.
  :py:mod:`fixeddicts <vc2_conformance.fixeddict>` provide a way to give these
  clear names.
* Avoidance of typos -- Misspelt key names will result in a
  :py:exc:`FixedDictKeyError`.
* Better pretty printing -- See more below...


Tutorial
--------

Using :py:func:`fixeddict`, dictionary-like types with well defined fields can
be described like so::

    >>> from vc2_conformance.fixeddict import fixeddict

    >>> FrameSize = fixeddict(
    ...     "FrameSize",
    ...     "custom_dimensions_flag",
    ...     "frame_width",
    ...     "frame_height",
    ... )

This produces a 'dict' subclass called ``FrameSize`` with all of the usual
dictionary behaviour but which only allows the specified keys to be used::

    >>> f = FrameSize()
    >>> f["custom_dimensions_flag"] = True
    >>> f["frame_width"] = 1920
    >>> f["frame_height"] = 1080

    >>> f["frame_width"]
    1920

    >>> f["not_in_fixeddict"] = 123
    Traceback (most recent call last):
      ...
    FixedDictKeyError: 'not_in_fixeddict'


To improve readability when producing string representations of VC-2 data
structures, the generated dictionary types have a 'pretty' string
representation.

    >>> print(f)
    FrameSize:
      custom_dimensions_flag: True
      frame_width: 1920
      frame_height: 1080

To further improve the readability of this output, custom string formatting
functions may be provided for each entry in the dictionary. To define these,
:py:class:`Entry` instances must be used in place of key name strings like
so::

    >>> from vc2_conformance.string_formatters import Hex
    >>> from vc2_data_tables import ParseCodes  # An IntEnum
    >>> ParseInfo = fixeddict(
    ...     "ParseInfo",
    ...     Entry("parse_info_prefix", formatter=Hex(8)),
    ...     Entry("parse_code", enum=ParseCodes, formatter=Hex(2)),
    ...     Entry("next_parse_offset"),
    ...     Entry("previous_parse_offset"),

    >>> pi = ParseInfo(
    ...     parse_info_prefix=0x42424344,
    ...     parse_code=0x10,
    ...     next_parse_offset=0,
    ...     previous_parse_offset=0,
    ... )
    >>> str(pi)
    ParseInfo:
       parse_info_prefix: 0x42424344
       parse_code: end_of_sequence (0x10)
       next_parse_offset: 0
       previous_parse_offset: 0

See the :py:mod:`vc2_conformance.string_formatters` module for a set of useful
string formatting functions.

Finally, documentation can optionally be added in the form of ``help`` and
``help_type`` arguments which will combined into the generated type's
docstring::

    >>> ParseInfo = fixeddict(
    ...     "ParseInfo",
    ...     Entry("parse_info_prefix", formatter=Hex(8), help_type="int", help="Always 0x42424344"),
    ...     Entry("parse_code", enum=ParseCodes, formatter=Hex(2), help_type="int"),
    ...     Entry("next_parse_offset", help_type="int"),
    ...     Entry("previous_parse_offset", help_type="int"),
    ...     help="A deserialised parse info block.",
    ... )

    >>> print(ParseInfo.__doc__)
    A deserialised parse info block.
    <BLANKLINE>
    Parameters
    ==========
    parse_info_prefix : int
        Always 0x42424344
    parse_code : int
    next_parse_offset : int
    previous_parse_offset : int


API
---

.. autofunction:: fixeddict

.. autoclass:: Entry

.. autoexception:: FixedDictKeyError

"""

import sys

from collections import OrderedDict

from textwrap import dedent

from vc2_conformance.string_utils import indent


__all__ = [
    "fixeddict",
    "Entry",
    "FixedDictKeyError",
]


class Entry(object):
    """
    Defines advanced properties of of an entry in a :py:func:`fixeddict`
    dictionary.

    All constructor arguments, except name, are keyword-only.

    Parameters
    ==========
    name : str
        The name of this entry in the dictionary.
    formatter : function(value) -> string
        A function which takes a value and returns a string representation
        to use when printing this value as a string. Defaults to 'str'.
    friendly_formatter : function(value) -> string
        If provided, when converting this value to a string, this function
        will be used to generate a 'friendly' name for this value. This
        will be followed by the actual value in brackets. If this function
        returns None, only the actual value will be shown (without
        brackets).
    enum : :py:class:`~enum.Enum`
        A convenience interface which is equivalent to the following
        ``formatter`` argument::

            def enum_formatter(value):
                try:
                    return str(MyEnum(value).value)
                except ValueError:
                    return str(value)

        And the following ``friendly_formatter`` argument::

            def friendly_enum_formatter(value):
                try:
                    return MyEnum(value).name
                except ValueError:
                    return None

        If ``formatter`` or ``friendly_formatter`` are provided in addition
        to ``enum``, they will override the functions implicitly defined by
        ``enum``.
    help : str
        Optional documentation string.
    help_type : str
        Optional string describing the type of the entry.
    """

    def __init__(self, name, **kwargs):
        self.name = name

        if "enum" in kwargs:
            enum_type = kwargs.pop("enum")

            def enum_formatter(value):
                try:
                    return str(enum_type(value).value)
                except ValueError:
                    return str(value)

            kwargs.setdefault("formatter", enum_formatter)

            def friendly_enum_formatter(value):
                try:
                    return enum_type(value).name
                except ValueError:
                    return None

            kwargs.setdefault("friendly_formatter", friendly_enum_formatter)

        self.formatter = kwargs.pop("formatter", str)
        self.friendly_formatter = kwargs.pop("friendly_formatter", None)

        self.help = kwargs.pop("help", None)
        if self.help is not None:
            self.help = dedent(self.help).strip()

        self.help_type = kwargs.pop("help_type", None)
        if self.help_type is not None:
            self.help_type = dedent(self.help_type).strip()

        if kwargs:
            raise TypeError(
                "unexpected keyword arguments: {} for {}".format(
                    ", ".join(kwargs.keys()), self.__class__.__name__
                )
            )

    def to_string(self, value):
        """
        Convert a value to a string according to the specification in this
        :py:class:`Entry`.
        """
        value_string = self.formatter(value)

        if self.friendly_formatter is not None:
            friendly_string = self.friendly_formatter(value)
            if friendly_string is not None:
                value_string = "{} ({})".format(friendly_string, value_string)

        return value_string


class FixedDictKeyError(KeyError):
    """
    A :py:exc:`KeyError` which also includes information about which fixeddict
    dictionary it was produced by.

    Attributes
    ==========
    key
        The key which was accessed.
    fixeddict_class
        The :py:mod:`~vc2_conformance.fixeddict` type of the dictionary used.
    """

    def __init__(self, key, fixeddict_class):
        super(FixedDictKeyError, self).__init__(key)
        self.key = key
        self.fixeddict_class = fixeddict_class

    def __str__(self):
        return "{!r} not allowed in {}".format(self.key, self.fixeddict_class.__name__)


def fixeddict(name, *entries, **kwargs):
    """
    Create a fixed-entry dictionary.

    A fixed-entry dictionary is a :py:class:`dict` subclass which permits only
    a preset list of key names.

    The first argument is the name of the created class, the remaining
    arguments may be strings or :py:class:`Entry` instances describing the
    allowed entries in the dictionary.

    Example usage:

        >>> ExampleDict = fixeddict(
        ...     "ExampleDict",
        ...     "attr",
        ...     Entry("attr_with_default"),
        ... )

    Instances of the dictionary can be created like an ordinary dictionary::

        >>> d = ExampleDict(attr=10, attr_with_default=20)
        >>> d["attr"]
        10
        >>> d["attr_with_default"]
        20

    The string format of generated dictionaries includes certain
    pretty-printing behaviour (see :py:class:`Entry`) and will also omit any
    entries whose name is prefixed with an underscore (``_``).

    The class itself will have a static (and read-only) attribute
    ``entry_objs`` which is a :py;class:`collections.OrderedDict` mapping from
    entry name to :py:class:`Entry` object in the dictionary.

    The keyword-only argument, 'module' may be provided which overrides the
    ``__module__`` value of the returned fixeddict type. (By default the module
    name is inferred using runtime stack inspection, if possible). This must be
    set correctly for this type to be picklable.

    The keyword-only argument 'help' may be used to set the docstring of the
    returned class. This will automatically be appended with the list of
    entries allowed (and their help strings).
    """
    # Extract keyword-only arguments
    module = kwargs.pop("module", None)
    help = kwargs.pop("help", None)
    assert not kwargs, "Got unexpected keyword arguments: {}".format(", ".join(kwargs))

    if help is not None:
        help = dedent(help).strip()

    # Collect the list of Entry instances defined for this class
    # {name: Entry, ...}
    entry_objs = OrderedDict(
        (entry.name, entry)
        for entry in (arg if isinstance(arg, Entry) else Entry(arg) for arg in entries)
    )

    # Create all of the methods which will be added to the class
    __dict__ = {}

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)

        # Check for invalid names
        for name in self.keys():
            if name not in entry_objs:
                raise FixedDictKeyError(name, self.__class__)

    __dict__["__init__"] = __init__

    __dict__["help"] = help
    __dict__["__doc__"] = "{}\n\nParameters\n==========\n{}\n".format(
        help if help is not None else "A :py:mod:`~vc2_conformance.fixeddict`.",
        "\n".join(
            "{}{}{}".format(
                entry.name,
                (" : " + entry.help_type if entry.help_type is not None else ""),
                (("\n" + indent(entry.help, "    ")) if entry.help is not None else ""),
            )
            for entry in entry_objs.values()
        ),
    )

    def __setitem__(self, key, value):
        if key in entry_objs:
            return dict.__setitem__(self, key, value)
        else:
            raise FixedDictKeyError(key, self.__class__)

    __dict__["__setitem__"] = __setitem__

    def setdefault(self, key, value):
        if key in entry_objs:
            return dict.setdefault(self, key, value)
        else:
            raise FixedDictKeyError(key, self.__class__)

    __dict__["setdefault"] = setdefault

    def update(self, E=None, **F):
        # Using the naming convention defined by 'help(dict.setdefault)'
        if E is not None:
            if hasattr(E, "keys"):
                for k in E:
                    self[k] = E[k]
            else:
                for k, v in E:
                    self[k] = v
        for k in F:
            self[k] = F[k]

    __dict__["update"] = update

    def __repr__(self):
        return "{}({{{}}})".format(
            self.__class__.__name__,
            ", ".join(
                "{!r}: {!r}".format(name, self[name])
                for name, entry_obj in entry_objs.items()
                if name in self
            ),
        )

    __dict__["__repr__"] = __repr__

    def __str__(self):
        if len(self) == 0:
            return self.__class__.__name__
        else:
            return "{}:\n{}".format(
                self.__class__.__name__,
                "\n".join(
                    indent("{}: {}".format(name, entry_obj.to_string(self[name])))
                    for name, entry_obj in entry_objs.items()
                    if name in self and not name.startswith("_")
                ),
            )

    __dict__["__str__"] = __str__

    def copy(self):
        return self.__class__(self)

    __dict__["copy"] = copy

    # Support pickling/unpickling (part 1).
    #
    # Dictionaries have their own magic behaviour by default under pickle so we
    # must explicitly tell pickle how to handle this type.
    def __getstate__(self):
        return dict(self)

    __dict__["__getstate__"] = __getstate__

    def __setstate__(self, state):
        self.update(state)

    __dict__["__setstate__"] = __setstate__

    def __reduce__(self):
        return (
            type(self),
            (),
            self.__getstate__(),
        )

    __dict__["__reduce__"] = __reduce__

    cls = type(name, (dict,), __dict__)

    setattr(cls, "entry_objs", entry_objs)

    # Support pickling/unpickling (part 2)
    #
    # Setting the __module__ class attributes tells pickle where to find this
    # type when unpickling.
    if module is None:
        # Detect the module of the caller by inspecting the stack. This is a
        # bit gross, and won't work under all Python interpreters, but is what
        # enum.Enum also has to do and if its good enough for the stdlib, its
        # good enough for this...
        try:
            module = sys._getframe(1).f_globals["__name__"]
        except (AttributeError, ValueError, KeyError):
            pass
    if module is not None:
        setattr(cls, "__module__", module)

    return cls
