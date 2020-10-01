import pytest

from mock import Mock

from io import BytesIO

from bitarray import bitarray

from vc2_conformance.bitstream import (
    BitstreamReader,
    BitstreamWriter,
)

from vc2_conformance.fixeddict import fixeddict, Entry

from vc2_conformance.bitstream import exceptions

from vc2_conformance.bitstream.serdes import (
    SerDes,
    Serialiser,
    Deserialiser,
    MonitoredSerialiser,
    MonitoredDeserialiser,
    context_type,
)


@pytest.fixture
def f():
    return BytesIO()


@pytest.fixture
def r(f):
    return BitstreamReader(f)


@pytest.fixture
def w(f):
    return BitstreamWriter(f)


class TestSerDes(object):
    def test_constructor(self, r):
        # Auto-create context
        serdes = SerDes(r)
        assert serdes.io is r
        assert serdes.cur_context == {}

        # Use context if provided
        context = {}
        serdes = SerDes(r, context)
        assert serdes.io is r
        assert serdes.cur_context is context

    def test_declare_list(self):
        context = {
            "empty_list": [],
            "populated_list": [1, 2, 3],
            "non_list_1": 123,
            "non_list_2": 321,
        }
        serdes = SerDes(None, context)

        # Declaring something not in the context should work
        serdes.declare_list("non_existant_list")
        assert serdes.cur_context["non_existant_list"] == []
        assert serdes._cur_context_indices["non_existant_list"] == 0

        # Declaring something already a list should work (including already
        # populated lists.
        serdes.declare_list("empty_list")
        assert serdes.cur_context["empty_list"] == []
        assert serdes._cur_context_indices["empty_list"] == 0

        serdes.declare_list("populated_list")
        assert serdes.cur_context["populated_list"] == [1, 2, 3]
        assert serdes._cur_context_indices["populated_list"] == 0

        # Declaring something already declared or used should fail
        serdes._set_context_value("non_list_1", 123)
        with pytest.raises(
            exceptions.ReusedTargetError, match=r"dict\['non_existant_list'\]"
        ):
            serdes.declare_list("non_existant_list")
        with pytest.raises(exceptions.ReusedTargetError, match=r"dict\['empty_list'\]"):
            serdes.declare_list("empty_list")
        with pytest.raises(
            exceptions.ReusedTargetError, match=r"dict\['populated_list'\]"
        ):
            serdes.declare_list("populated_list")
        with pytest.raises(exceptions.ReusedTargetError, match=r"dict\['non_list_1'\]"):
            serdes.declare_list("non_list_1")

        # Declaring something as a list which hasn't been used but which hasn't
        # got a list type in it should fail
        with pytest.raises(
            exceptions.ListTargetContainsNonListError, match=r"dict\['non_list_2'\]"
        ):
            serdes.declare_list("non_list_2")

    def test_set_context_value(self):
        context = {
            "non_list_1": 123,
            "empty_list": [],
            "populated_list": [1, 2, 3],
        }
        serdes = SerDes(None, context)
        serdes.declare_list("empty_list")
        serdes.declare_list("populated_list")

        # Should be able to over-write something already there (the first time)
        serdes._set_context_value("non_list_1", 1234)
        assert serdes.cur_context["non_list_1"] == 1234
        assert serdes._cur_context_indices["non_list_1"] is True

        # Should be able to set a non-existant value
        serdes._set_context_value("non_list_2", 4321)
        assert serdes.cur_context["non_list_2"] == 4321
        assert serdes._cur_context_indices["non_list_2"] is True

        # Should be able to add to an empty list
        serdes._set_context_value("empty_list", 10)
        serdes._set_context_value("empty_list", 20)
        serdes._set_context_value("empty_list", 30)
        assert serdes.cur_context["empty_list"] == [10, 20, 30]
        assert serdes._cur_context_indices["empty_list"] == 3

        # Should be able to overwrite in a non-empty list
        serdes._set_context_value("populated_list", 100)
        assert serdes.cur_context["populated_list"] == [100, 2, 3]
        assert serdes._cur_context_indices["populated_list"] == 1

        # Should be able to write past end of non-empty list to add new items
        serdes._set_context_value("populated_list", 200)
        serdes._set_context_value("populated_list", 300)
        serdes._set_context_value("populated_list", 400)
        assert serdes.cur_context["populated_list"] == [100, 200, 300, 400]
        assert serdes._cur_context_indices["populated_list"] == 4

        # Shouldn't be able to re-set already set non-list property
        with pytest.raises(exceptions.ReusedTargetError, match=r"dict\['non_list_1'\]"):
            serdes._set_context_value("non_list_1", 0)

    def test_get_context_value(self):
        context = {
            "non_list": 123,
            "empty_list": [],
            "populated_list": [1, 2, 3],
        }
        serdes = SerDes(None, context)
        serdes.declare_list("empty_list")
        serdes.declare_list("populated_list")

        # Should be able to get non-list values (first time...)
        assert serdes._get_context_value("non_list") == 123
        assert serdes._cur_context_indices["non_list"] is True

        # Should be able to get list items (from non-empty lists)
        assert serdes._get_context_value("populated_list") == 1
        assert serdes._get_context_value("populated_list") == 2
        assert serdes._get_context_value("populated_list") == 3
        assert serdes._cur_context_indices["populated_list"] == 3

        # Should fail to get values which have already been accessed
        with pytest.raises(exceptions.ReusedTargetError, match=r"dict\['non_list'\]"):
            serdes._get_context_value("non_list")

        # Should fail to get values beyond the end of a list
        with pytest.raises(
            exceptions.ListTargetExhaustedError, match=r"dict\['empty_list'\]"
        ):
            serdes._get_context_value("empty_list")
        with pytest.raises(
            exceptions.ListTargetExhaustedError, match=r"dict\['populated_list'\]"
        ):
            serdes._get_context_value("populated_list")

    def test_setdefault_context_value(self):
        context = {
            "non_list": 123,
            "empty_list": [],
            "populated_list": [1, 2, 3],
        }
        serdes = SerDes(None, context)
        serdes.declare_list("empty_list")
        serdes.declare_list("populated_list")

        # Should be able to get non-list values (first time...)
        assert serdes._setdefault_context_value("non_list", 321) == 123
        assert serdes._cur_context_indices["non_list"] is True

        # Should be able to get list values
        assert serdes._setdefault_context_value("populated_list", 321) == 1
        assert serdes._setdefault_context_value("populated_list", 321) == 2
        assert serdes._setdefault_context_value("populated_list", 321) == 3
        assert serdes._cur_context_indices["populated_list"] == 3

        # Getting from non-existing value should create them
        assert serdes._setdefault_context_value("new_target", 321) == 321
        assert serdes._cur_context_indices["new_target"] is True

        # Getting from non-existing list item should add them
        assert serdes._setdefault_context_value("empty_list", 100) == 100
        assert serdes._cur_context_indices["empty_list"] == 1
        assert serdes._setdefault_context_value("populated_list", 40) == 40
        assert serdes._cur_context_indices["populated_list"] == 4

        # Re-using a target should still fail
        with pytest.raises(exceptions.ReusedTargetError, match=r"dict\['non_list'\]"):
            assert serdes._setdefault_context_value("non_list", 321)
        with pytest.raises(exceptions.ReusedTargetError, match=r"dict\['new_target'\]"):
            assert serdes._setdefault_context_value("new_target", 321)

    @pytest.mark.parametrize(
        "tell,expected_length",
        [
            # Already byte aligned
            ((0, 7), 0),
            ((1, 7), 0),
            # Not aligned
            ((0, 6), 7),
            ((1, 5), 6),
            ((2, 0), 1),
        ],
    )
    def test_byte_align(self, w, tell, expected_length):
        value = bitarray("0" * expected_length)

        w.seek(*tell)
        serdes = SerDes(w)
        serdes.bitarray = Mock(return_value=value)

        serdes.byte_align("foo")
        serdes.bitarray.assert_called_with("foo", expected_length)

    def test_bounded_block_unused_bits(self, w):
        serdes = SerDes(w)
        serdes.bitarray = Mock()

        # Open the block
        serdes.bounded_block_begin(123)

        # Correct length
        assert serdes.io.bits_remaining == 123

        # Close the block
        serdes.bitarray.return_value = bitarray("0" * 123)
        serdes.bounded_block_end("foo")

        serdes.bitarray.assert_called_with("foo", 123)

    def test_bounded_block_all_bits_used(self, w):
        serdes = SerDes(w)
        serdes.bitarray = Mock()

        # Open the block
        serdes.bounded_block_begin(123)

        # Correct length
        assert serdes.io.bits_remaining == 123

        # Use up all bits (and then some)
        serdes.io.write_nbits(200, (1 << 200) - 1)

        # Close the block
        serdes.bitarray.return_value = bitarray(0)
        serdes.bounded_block_end("foo")

        serdes.bitarray.assert_called_with("foo", 0)

    def test_bounded_block_context_manager(self, w):
        serdes = SerDes(w)
        serdes.bitarray = Mock()

        with serdes.bounded_block("foo", 123):
            assert serdes.io.bits_remaining == 123

        serdes.bitarray.assert_called_with("foo", 123)

    def test_subcontext_non_list(self):
        serdes = SerDes(None)

        serdes.declare_list("value")
        serdes.computed_value("value", 123)

        serdes.subcontext_enter("child_1")
        serdes.declare_list("value")
        serdes.computed_value("value", 1234)

        serdes.subcontext_enter("child_2")
        serdes.declare_list("value")
        serdes.computed_value("value", 12345)
        serdes.subcontext_leave()

        serdes.computed_value("value", 4321)
        serdes.subcontext_leave()

        serdes.computed_value("value", 321)

        assert serdes.context == {
            "value": [123, 321],
            "child_1": {"value": [1234, 4321], "child_2": {"value": [12345]}},
        }

    def test_subcontext_list(self):
        serdes = SerDes(None)

        serdes.declare_list("value")
        serdes.computed_value("value", 123)

        serdes.declare_list("children")

        serdes.subcontext_enter("children")
        serdes.declare_list("value")
        serdes.computed_value("value", 1234)
        serdes.computed_value("value", 4321)
        serdes.subcontext_leave()

        serdes.subcontext_enter("children")
        serdes.declare_list("value")
        serdes.computed_value("value", 12345)
        serdes.computed_value("value", 54321)
        serdes.subcontext_leave()

        serdes.computed_value("value", 321)

        assert serdes.context == {
            "value": [123, 321],
            "children": [{"value": [1234, 4321]}, {"value": [12345, 54321]}],
        }

    def test_subcontext_decorator(self):
        serdes = SerDes(None)

        serdes.declare_list("value")
        serdes.computed_value("value", 123)
        with serdes.subcontext("child_1"):
            serdes.declare_list("value")
            serdes.computed_value("value", 1234)
            with serdes.subcontext("child_2"):
                serdes.declare_list("value")
                serdes.computed_value("value", 12345)
            serdes.computed_value("value", 4321)
        serdes.computed_value("value", 321)

        assert serdes.context == {
            "value": [123, 321],
            "child_1": {"value": [1234, 4321], "child_2": {"value": [12345]}},
        }

    def test_subcontext_incomplete(self):
        serdes = SerDes(None, {"child": {"forget_to_use": 123}})

        serdes.subcontext_enter("child")

        # If we now try to leave without using the 'forget_to_use' value we
        # should fail
        with pytest.raises(
            exceptions.UnusedTargetError, match=r"dict\['child'\]\['forget_to_use'\]"
        ):
            serdes.subcontext_leave()

    def test_set_context_type(self):
        FixedDict = fixeddict(
            "FixedDict",
            Entry("a"),
            Entry("child"),
        )

        serdes = SerDes(None)

        serdes.set_context_type(FixedDict)
        with serdes.subcontext("child"):
            serdes.set_context_type(FixedDict)
            serdes.declare_list("child")
            with serdes.subcontext("child"):
                serdes.set_context_type(FixedDict)

        assert isinstance(serdes.context, FixedDict)
        assert isinstance(serdes.context["child"], FixedDict)
        assert isinstance(serdes.context["child"]["child"][0], FixedDict)

    def test_computed_value(self):
        serdes = SerDes(None)

        # Should have set the required value
        serdes.computed_value("value", 123)
        assert serdes.cur_context == {"value": 123}
        assert serdes._cur_context_indices == {"value": True}

        # Should fail on re-used value
        with pytest.raises(exceptions.ReusedTargetError, match=r"dict\['value'\]"):
            serdes.computed_value("value", 321)
        assert serdes.cur_context == {"value": 123}

    def test_is_target_complete_and_verify_target_complete(self, w):
        serdes = SerDes(w, {"foo": 123, "bar": [1, 2, 3]})

        # Value targets
        assert serdes.is_target_complete("foo") is False
        serdes.computed_value("foo", 123)
        assert serdes.is_target_complete("foo") is True

        # List targets
        serdes.declare_list("bar")
        assert serdes.is_target_complete("bar") is False
        serdes.computed_value("bar", 1)
        assert serdes.is_target_complete("bar") is False
        serdes.computed_value("bar", 2)
        assert serdes.is_target_complete("bar") is False
        serdes.computed_value("bar", 3)
        assert serdes.is_target_complete("bar") is True

    def test_verify_context_is_complete(self, w):
        serdes = SerDes(w)

        # Empty and therefore complete
        serdes._verify_context_is_complete()

        # Writing values of any kind an still should be complete
        serdes.computed_value("foo", 123)
        serdes._verify_context_is_complete()

        serdes.declare_list("bar")
        serdes._verify_context_is_complete()
        serdes.computed_value("bar", 10)
        serdes._verify_context_is_complete()
        serdes.computed_value("bar", 20)
        serdes._verify_context_is_complete()
        serdes.computed_value("bar", 30)
        serdes._verify_context_is_complete()

        # If there are any values in the context which haven't been indexed,
        # fail
        serdes = SerDes(w, {"baz": None})
        with pytest.raises(exceptions.UnusedTargetError, match=r"dict\['baz'\]"):
            serdes._verify_context_is_complete()
        serdes.computed_value("baz", 321)
        serdes._verify_context_is_complete()

        # If there are any list values which weren't used, fail
        serdes = SerDes(w, {"list": [1, 2, 3]})
        serdes.declare_list("list")
        with pytest.raises(
            exceptions.UnusedTargetError, match=r"dict\['list'\]\[0:3\]"
        ):
            serdes._verify_context_is_complete()
        serdes.computed_value("list", 10)
        with pytest.raises(
            exceptions.UnusedTargetError, match=r"dict\['list'\]\[1:3\]"
        ):
            serdes._verify_context_is_complete()
        serdes.computed_value("list", 20)
        with pytest.raises(
            exceptions.UnusedTargetError, match=r"dict\['list'\]\[2:3\]"
        ):
            serdes._verify_context_is_complete()
        serdes.computed_value("list", 30)
        serdes._verify_context_is_complete()

    def test_verify_complete(self, w):
        # Shouldn't fail if empty
        serdes = SerDes(w)
        serdes.verify_complete()

        # Should fail for reasons _verify_context_is_complete would fail
        serdes = SerDes(w, {"incomplete": w})
        with pytest.raises(exceptions.UnusedTargetError, match=r"dict\['incomplete'\]"):
            serdes.verify_complete()

        # Should fail if nesting isn't closed
        serdes = SerDes(w)
        serdes.subcontext_enter("child")
        with pytest.raises(
            exceptions.UnclosedNestedContextError, match=r"dict\['child'\]"
        ):
            serdes.verify_complete()

        # Should fail if bounded blocks aren't closed
        serdes = SerDes(w)
        serdes.bounded_block_begin(123)
        with pytest.raises(exceptions.UnclosedBoundedBlockError):
            serdes.verify_complete()

    def test_as_context_manager(self, w):
        # Works when used 'correctly'
        with SerDes(w) as serdes:
            serdes.computed_value("foo", 123)
        assert serdes.context == {"foo": 123}

        # Fails when left in inconsistent state
        with pytest.raises(exceptions.UnclosedNestedContextError):
            with SerDes(w) as serdes:
                serdes.subcontext_enter("unclosed")

    def test_context_is_root(self, w):
        serdes = SerDes(w)

        # Already in root context
        root = serdes.cur_context
        assert serdes.context is root

        # In child context
        serdes.subcontext_enter("child")
        assert serdes.cur_context is not root
        assert serdes.context is root

    def test_path(self):
        serdes = SerDes(None)

        # At root should work
        assert serdes.path() == []
        assert serdes.path("foo") == ["foo"]

        # List items in root should work
        serdes.declare_list("list")
        assert serdes.path("list") == ["list"]
        serdes.computed_value("list", 10)
        assert serdes.path("list") == ["list", 0]
        serdes.computed_value("list", 20)
        assert serdes.path("list") == ["list", 1]
        serdes.computed_value("list", 30)
        assert serdes.path("list") == ["list", 2]

        # When nested, the same should work
        serdes.subcontext_enter("child")

        assert serdes.path() == ["child"]
        assert serdes.path("foo") == ["child", "foo"]

        # List items in root should work
        serdes.declare_list("list")
        assert serdes.path("list") == ["child", "list"]
        serdes.computed_value("list", 10)
        assert serdes.path("list") == ["child", "list", 0]
        serdes.computed_value("list", 20)
        assert serdes.path("list") == ["child", "list", 1]
        serdes.computed_value("list", 30)
        assert serdes.path("list") == ["child", "list", 2]

        # When nested into an array, the same should work
        serdes.declare_list("child")
        serdes.subcontext_enter("child")
        assert serdes.path() == ["child", "child", 0]
        assert serdes.path("foo") == ["child", "child", 0, "foo"]

    def test_describe_path(self):
        serdes = SerDes(None)

        # At root should work
        assert serdes.describe_path() == "dict"

        # At one level should work
        assert serdes.describe_path("foo") == "dict['foo']"

        # List values should work
        serdes.declare_list("list")
        assert serdes.describe_path("list") == "dict['list']"
        serdes.computed_value("list", 10)
        assert serdes.describe_path("list") == "dict['list'][0]"
        serdes.computed_value("list", 20)
        assert serdes.describe_path("list") == "dict['list'][1]"
        serdes.computed_value("list", 30)
        assert serdes.describe_path("list") == "dict['list'][2]"

    def test_describe_path_custom_type(self):
        # With different types, prefix should be different
        FixedDict = fixeddict("FixedDict", Entry("child"))
        serdes = SerDes(None)

        serdes.set_context_type(FixedDict)
        assert serdes.describe_path() == "FixedDict"
        assert serdes.describe_path("foo") == "FixedDict['foo']"

        # When nested, outer-most dict defines the type
        serdes.subcontext_enter("child")
        assert serdes.describe_path() == "FixedDict['child']"
        assert serdes.describe_path("foo") == "FixedDict['child']['foo']"


def test_context_type():
    FixedDict = fixeddict("FixedDict", "a")

    @context_type(FixedDict)
    def func(serdes, value):
        serdes.computed_value("a", -value)

    assert func.context_type is FixedDict

    serdes = SerDes(None)

    func(serdes, 123)

    assert isinstance(serdes.context, FixedDict)
    assert serdes.context["a"] == -123


@pytest.mark.parametrize(
    "method,arguments,bitstream,exp_value,exp_tell",
    [
        # bool
        ("bool", tuple(), b"\x00", False, (0, 6)),
        ("bool", tuple(), b"\x80", True, (0, 6)),
        # nbits
        ("nbits", (8,), b"\xAB", 0xAB, (1, 7)),
        # uint_lit
        ("uint_lit", (1,), b"\xAB", 0xAB, (1, 7)),
        # bitarray
        ("bitarray", (8,), b"\xA0", bitarray("10100000"), (1, 7)),
        # bytes
        ("bytes", (2,), b"\xA0\xCD", b"\xA0\xCD", (2, 7)),
        # uint
        ("uint", tuple(), b"\x3F", 1, (0, 4)),
        # sint
        ("sint", tuple(), b"\x3F", -1, (0, 3)),
    ],
)
def test_deserialiser(method, arguments, bitstream, exp_value, exp_tell):
    r = BitstreamReader(BytesIO(bitstream))
    with Deserialiser(r) as serdes:
        assert getattr(serdes, method)("target", *arguments) == exp_value
    assert serdes.context == {"target": exp_value}
    assert r.tell() == exp_tell


class TestSerialiser(object):
    @pytest.mark.parametrize(
        "method,arguments,value,exp_bitstream,exp_tell",
        [
            # bool
            ("bool", tuple(), False, b"\x00", (0, 6)),
            ("bool", tuple(), True, b"\x80", (0, 6)),
            # nbits
            ("nbits", (8,), 0xAB, b"\xAB", (1, 7)),
            # uint_lit
            ("uint_lit", (1,), 0xAB, b"\xAB", (1, 7)),
            # bitarray
            ("bitarray", (8,), bitarray("10100000"), b"\xA0", (1, 7)),
            # bitarray (zero padding required)
            ("bitarray", (8,), bitarray("1010"), b"\xA0", (1, 7)),
            # bytes
            ("bytes", (2,), b"\xA0\xCD", b"\xA0\xCD", (2, 7)),
            # bytes (zero padding required)
            ("bytes", (2,), b"\xA0", b"\xA0\x00", (2, 7)),
            # uint
            ("uint", tuple(), 1, b"\x20", (0, 4)),
            # sint
            ("sint", tuple(), -1, b"\x30", (0, 3)),
        ],
    )
    def test_output_types(
        self, method, arguments, value, exp_bitstream, exp_tell, w, f
    ):
        with Serialiser(w, {"target": value}) as serdes:
            assert getattr(serdes, method)("target", *arguments) == value

        w.flush()
        assert f.getvalue() == exp_bitstream
        assert w.tell() == exp_tell
        assert serdes.context == {"target": value}

    def test_default_values(self, w, f):
        DictA = fixeddict("DictA", "a1", "a2", "a3")
        DictB = fixeddict("DictB", "b1", "b2")
        DictC = fixeddict("DictC", "c1")

        default_values = {
            DictA: {"a1": b"\xA1", "a2": b"\xA2"},
            DictB: {"b1": b"\xB1", "b2": b"\xB2"},
        }

        context = {
            "a": {"a1": b"\xAA", "a2": [b"\xA0"], "a3": b"\xA3"},
            "c": {"c1": b"\xCC"},
        }
        with Serialiser(w, context, default_values) as serdes:
            with serdes.subcontext("a"):
                serdes.set_context_type(DictA)
                serdes.bytes("a1", 1)
                serdes.declare_list("a2")
                serdes.bytes("a2", 1)
                serdes.bytes("a2", 1)
                serdes.bytes("a3", 1)
            with serdes.subcontext("b"):
                serdes.set_context_type(DictB)
                serdes.bytes("b1", 1)
                serdes.declare_list("b2")
                serdes.bytes("b2", 1)
                serdes.bytes("b2", 1)
            with serdes.subcontext("c"):
                serdes.set_context_type(DictC)
                serdes.bytes("c1", 1)

        assert f.getvalue() == (
            # A partially defaulted subcontext
            b"\xAA"  # An overridden non-list value
            b"\xA0"  # An overridden list value
            b"\xA2"  # A default value beyond the end of a partially defined list
            b"\xA3"  # A value with no default
            # A completely default-valued subcontext
            b"\xB1"  # A non list value
            b"\xB2"  # A list of default values
            b"\xB2"  # A list of default values
            # A dictionary whose type does not appear in the default values
            # list
            b"\xCC"
        )

    @pytest.mark.parametrize(
        "context,exp_exception",
        [
            # Missing values
            ({"b": [b"\xB1", b"\xB2"]}, KeyError),
            # Missing list items
            ({"a": b"\xAA"}, exceptions.ListTargetExhaustedError),
            ({"a": b"\xAA", "b": []}, exceptions.ListTargetExhaustedError),
            ({"a": b"\xAA", "b": [b"\xB1"]}, exceptions.ListTargetExhaustedError),
        ],
    )
    def test_still_fails_when_no_default_value(self, w, f, context, exp_exception):
        with pytest.raises(exp_exception):
            with Serialiser(w, context) as serdes:
                serdes.bytes("a", 1)
                serdes.declare_list("b")
                serdes.bytes("b", 1)
                serdes.bytes("b", 1)

    @pytest.mark.parametrize(
        "context",
        [
            # Extra non-list value
            {"a": [b"\xA1", b"\xA2"], "b": [b"\xB1"], "c": b"\x00"},
            # Extra value in list
            {"a": [b"\xA1", b"\xA2"], "b": [b"\xB1"]},
            # Extra value in list with default value defined
            {"a": [b"\xA1"], "b": [b"\xB1", b"\xB2"]},
        ],
    )
    def test_still_fails_when_excess_values(self, w, f, context):
        with pytest.raises(exceptions.UnusedTargetError):
            with Serialiser(w, context) as serdes:
                serdes.declare_list("a")
                serdes.bytes("a", 1)
                serdes.declare_list("b")
                serdes.bytes("b", 1)


@pytest.mark.parametrize(
    "T,make_io",
    [
        (MonitoredSerialiser, lambda: BitstreamWriter(BytesIO())),
        (MonitoredDeserialiser, lambda: BitstreamReader(BytesIO(b"\xFF"))),
    ],
)
@pytest.mark.parametrize(
    "method,arguments,value,exp_tell",
    [
        ("bool", tuple(), True, (0, 6)),
        ("nbits", (8,), 0xFF, (1, 7)),
        ("uint_lit", (1,), 0xFF, (1, 7)),
        ("bitarray", (8,), bitarray("11111111"), (1, 7)),
        ("bytes", (1,), b"\xFF", (1, 7)),
        ("uint", tuple(), 0, (0, 6)),
        ("sint", tuple(), 0, (0, 6)),
    ],
)
def test_monitored_serdes(T, make_io, method, arguments, value, exp_tell):
    tells = []
    monitor = Mock(
        side_effect=lambda serdes, target, value: tells.append(serdes.io.tell())
    )

    with T(monitor, make_io(), {"target": value}) as serdes:
        assert getattr(serdes, method)("target", *arguments) == value
    assert serdes.context == {"target": value}
    assert serdes.io.tell() == exp_tell

    # Monitor was called
    monitor.assert_called_with(serdes, "target", value)

    # Call occurred *after* the read/write
    assert tells == [exp_tell]
