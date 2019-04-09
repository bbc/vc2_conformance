import pytest

from io import BytesIO

from bitarray import bitarray

from vc2_conformance.bitstream import (
    BitstreamReader,
    BitstreamWriter,
    BitstreamPadAndTruncate,
    BoundedReader,
    BoundedWriter,
    BoundedPadAndTruncate,
)

from vc2_conformance import exceptions

from vc2_conformance.structured_dict import structured_dict, Value

from vc2_conformance.bitstream.generator_io import (
    Return,
    TokenParserStateMachine,
    Token,
    TokenTypes,
    context_type,
    read,
    read_interruptable,
    write,
    write_interruptable,
    pad_and_truncate,
    pad_and_truncate_interruptable,
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

@pytest.fixture
def p(f):
    return BitstreamPadAndTruncate(f)


def test_return():
    
    def gen():
        yield 1
        yield 2
        yield 3
        raise Return(123)
    
    g = gen()
    assert next(g) == 1
    assert next(g) == 2
    assert next(g) == 3
    with pytest.raises(Return) as excinfo:
        next(g)
    assert excinfo.value.value == 123


class TestTokenParserStateMachine(object):
    
    def test_constructor(self, r):
        g = iter([])
        
        # Auto-create context
        fsm = TokenParserStateMachine(g, r)
        assert fsm.generator is g
        assert fsm.io is r
        assert fsm.context == {}
        
        # Use context if provided
        context = {}
        fsm = TokenParserStateMachine(g, r, context)
        assert fsm.generator is g
        assert fsm.io is r
        assert fsm.context is context
    
    def test_declare_context_value_is_list(self):
        context = {
            "empty_list": [],
            "populated_list": [1, 2, 3],
            "non_list_1": 123,
            "non_list_2": 321,
        }
        fsm = TokenParserStateMachine(None, None, context)
        
        # Declaring something not in the context should work
        fsm._declare_context_value_is_list("non_existant_list")
        assert fsm.context["non_existant_list"] == []
        assert fsm.context_indices["non_existant_list"] == 0
        
        # Declaring something already a list should work (including already
        # populated lists.
        fsm._declare_context_value_is_list("empty_list")
        assert fsm.context["empty_list"] == []
        assert fsm.context_indices["empty_list"] == 0
        
        fsm._declare_context_value_is_list("populated_list")
        assert fsm.context["populated_list"] == [1, 2, 3]
        assert fsm.context_indices["populated_list"] == 0
        
        # Declaring something already declared or used should fail
        fsm._set_context_value("non_list_1", 123)
        with pytest.raises(exceptions.ReusedTargetError, match=r"dict\['non_existant_list'\]"):
            fsm._declare_context_value_is_list("non_existant_list")
        with pytest.raises(exceptions.ReusedTargetError, match=r"dict\['empty_list'\]"):
            fsm._declare_context_value_is_list("empty_list")
        with pytest.raises(exceptions.ReusedTargetError, match=r"dict\['populated_list'\]"):
            fsm._declare_context_value_is_list("populated_list")
        with pytest.raises(exceptions.ReusedTargetError, match=r"dict\['non_list_1'\]"):
            fsm._declare_context_value_is_list("non_list_1")
        
        # Declaring something as a list which hasn't been used but which hasn't
        # got a list type in it should fail
        with pytest.raises(exceptions.ListTargetContainsNonListError, match=r"dict\['non_list_2'\]"):
            fsm._declare_context_value_is_list("non_list_2")
    
    def test_set_context_value(self):
        context = {
            "non_list_1": 123,
            "empty_list": [],
            "populated_list": [1, 2, 3],
        }
        fsm = TokenParserStateMachine(None, None, context)
        fsm._declare_context_value_is_list("empty_list")
        fsm._declare_context_value_is_list("populated_list")
        
        # Should be able to over-write something already there (the first time)
        fsm._set_context_value("non_list_1", 1234)
        assert fsm.context["non_list_1"] == 1234
        assert fsm.context_indices["non_list_1"] is True
        
        # Should be able to set a non-existant value
        fsm._set_context_value("non_list_2", 4321)
        assert fsm.context["non_list_2"] == 4321
        assert fsm.context_indices["non_list_2"] is True
        
        # Should be able to add to an empty list
        fsm._set_context_value("empty_list", 10)
        fsm._set_context_value("empty_list", 20)
        fsm._set_context_value("empty_list", 30)
        assert fsm.context["empty_list"] == [10, 20, 30]
        assert fsm.context_indices["empty_list"] == 3
        
        # Should be able to overwrite in a non-empty list
        fsm._set_context_value("populated_list", 100)
        assert fsm.context["populated_list"] == [100, 2, 3]
        assert fsm.context_indices["populated_list"] == 1
        
        # Should be able to write past end of non-empty list to add new items
        fsm._set_context_value("populated_list", 200)
        fsm._set_context_value("populated_list", 300)
        fsm._set_context_value("populated_list", 400)
        assert fsm.context["populated_list"] == [100, 200, 300, 400]
        assert fsm.context_indices["populated_list"] == 4
        
        # Shouldn't be able to re-set already set non-list property
        with pytest.raises(exceptions.ReusedTargetError, match=r"dict\['non_list_1'\]"):
            fsm._set_context_value("non_list_1", 0)
    
    def test_get_context_value(self):
        context = {
            "non_list": 123,
            "empty_list": [],
            "populated_list": [1, 2, 3],
        }
        fsm = TokenParserStateMachine(None, None, context)
        fsm._declare_context_value_is_list("empty_list")
        fsm._declare_context_value_is_list("populated_list")
        
        # Should be able to get non-list values (first time...)
        assert fsm._get_context_value("non_list") == 123
        assert fsm.context_indices["non_list"] is True
        
        # Should be able to get list items (from non-empty lists)
        assert fsm._get_context_value("populated_list") == 1
        assert fsm._get_context_value("populated_list") == 2
        assert fsm._get_context_value("populated_list") == 3
        assert fsm.context_indices["populated_list"] is 3
        
        # Should fail to get values which have already been accessed
        with pytest.raises(exceptions.ReusedTargetError, match=r"dict\['non_list'\]"):
            fsm._get_context_value("non_list")
        
        # Should fail to get values beyond the end of a list
        with pytest.raises(exceptions.ListTargetExhaustedError, match=r"dict\['empty_list'\]"):
            fsm._get_context_value("empty_list")
        with pytest.raises(exceptions.ListTargetExhaustedError, match=r"dict\['populated_list'\]"):
            fsm._get_context_value("populated_list")
    
    def test_peek_context_value(self):
        context = {
            "non_list": 123,
            "empty_list": [],
            "populated_list": [1, 2, 3],
        }
        fsm = TokenParserStateMachine(None, None, context)
        fsm._declare_context_value_is_list("empty_list")
        fsm._declare_context_value_is_list("populated_list")
        
        # Should be able to get non-list values
        assert fsm._peek_context_value("non_list") == 123
        assert fsm._peek_context_value("non_list") == 123
        assert "non_list" not in fsm.context_indices
        
        # Should get 'None' for absent values
        assert fsm._peek_context_value("non_existant") is None
        assert "non_existant" not in fsm.context_indices
        
        # Should be able to get list items (from non-empty lists) but shouldn't
        # advance the pointer
        assert fsm._peek_context_value("populated_list") == 1
        assert fsm._peek_context_value("populated_list") == 1
        assert fsm.context_indices["populated_list"] is 0
        
        # Should return None for values beyond the end of a list
        assert fsm._peek_context_value("empty_list") is None
        assert fsm.context_indices["empty_list"] is 0
    
    def test_setdefault_context_value(self):
        context = {
            "non_list": 123,
            "empty_list": [],
            "populated_list": [1, 2, 3],
        }
        fsm = TokenParserStateMachine(None, None, context)
        fsm._declare_context_value_is_list("empty_list")
        fsm._declare_context_value_is_list("populated_list")
        
        # Should be able to get non-list values (first time...)
        assert fsm._setdefault_context_value("non_list", 321) == 123
        assert fsm.context_indices["non_list"] is True
        
        # Should be able to get list values
        assert fsm._setdefault_context_value("populated_list", 321) == 1
        assert fsm._setdefault_context_value("populated_list", 321) == 2
        assert fsm._setdefault_context_value("populated_list", 321) == 3
        assert fsm.context_indices["populated_list"] == 3
        
        # Getting from non-existing value should create them
        assert fsm._setdefault_context_value("new_target", 321) == 321
        assert fsm.context_indices["new_target"] is True
        
        # Getting from non-existing list item should add them
        assert fsm._setdefault_context_value("empty_list", 100) == 100
        assert fsm.context_indices["empty_list"] == 1
        assert fsm._setdefault_context_value("populated_list", 40) == 40
        assert fsm.context_indices["populated_list"] == 4
        
        # Re-using a target should still fail
        with pytest.raises(exceptions.ReusedTargetError, match=r"dict\['non_list'\]"):
            assert fsm._setdefault_context_value("non_list", 321)
        with pytest.raises(exceptions.ReusedTargetError, match=r"dict\['new_target'\]"):
            assert fsm._setdefault_context_value("new_target", 321)
    
    @pytest.mark.parametrize("tell,expected_length", [
        # Already byte aligned
        ((0, 7), 0),
        ((1, 7), 0),
        # Not aligned
        ((0, 6), 7),
        ((1, 5), 6),
        ((2, 0), 1),
    ])
    def test_generator_send_byte_align(self, w, tell, expected_length):
        token = Token(TokenTypes.byte_align, None, "foo")
        def generator():
            yield token
        g = generator()
        
        w.seek(*tell)
        
        fsm = TokenParserStateMachine(g, w)
        
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        
        # Passed through
        assert original_token is token
        
        # Turned into a bitarray of correct length
        assert token_type is TokenTypes.bitarray
        assert token_argument == expected_length
        assert token_target == "foo"
    
    @pytest.mark.parametrize("make_io", [
        lambda: BitstreamReader(BytesIO()),
        lambda: BitstreamWriter(BytesIO()),
        BitstreamPadAndTruncate,
    ])
    def test_generator_send_bounded_block(self, make_io):
        token_begin = Token(TokenTypes.bounded_block_begin, 123, None)
        token_end = Token(TokenTypes.bounded_block_end, None, "foo")
        def generator():
            yield token_begin
            yield token_end
            yield token_begin
            yield token_end
        g = generator()
        
        io = make_io()
        fsm = TokenParserStateMachine(g, io)
        
        # Open the block
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        
        # Passed through
        assert original_token is token_begin
        
        # Stacked up I/O
        assert fsm.io_stack == [io]
        
        # Correct length
        assert fsm.io.bits_remaining == 123
        
        # Created bounded accessor of correct type
        if isinstance(io, BitstreamReader):
            assert isinstance(fsm.io, BoundedReader)
        elif isinstance(io, BitstreamWriter):
            assert isinstance(fsm.io, BoundedWriter)
        elif isinstance(io, BitstreamPadAndTruncate):
            assert isinstance(fsm.io, BoundedPadAndTruncate)
        else:
            assert False, "unreachable"
        
        # Passed through a nop
        assert token_type is TokenTypes.nop
        assert token_argument is None
        assert token_target is None
        
        # Close the block
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        
        assert original_token is token_end
        assert fsm.io_stack == []
        assert fsm.io is io
        
        # Passed through a bitarray of correct length
        assert token_type is TokenTypes.bitarray
        assert token_argument == 123
        assert token_target == "foo"
        
        # Repeat but this time read past end of block
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        assert original_token is token_begin
        if isinstance(io, BitstreamReader):
            fsm.io.read_nbits(256)
        elif isinstance(io, BitstreamWriter):
            fsm.io.write_nbits(256, (1<<256) - 1)
        elif isinstance(io, BitstreamPadAndTruncate):
            fsm.io.advance_bit_offset(256)
        else:
            assert False, "unreachable"
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        assert original_token is token_end
        
        # No bits should be read in padding
        assert token_type is TokenTypes.bitarray
        assert token_argument == 0
        assert token_target == "foo"
    
    def test_generator_send_declare_list(self, w):
        token = Token(TokenTypes.declare_list, None, "foo")
        def generator():
            yield token
        g = generator()
        
        fsm = TokenParserStateMachine(g, w)
        
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        
        # Passed through
        assert original_token is token
        
        # Effect has been had
        assert fsm.context["foo"] == []
        assert fsm.context_indices["foo"] == 0
        
        # Nop passed through
        assert token_type is TokenTypes.nop
        assert token_argument is None
        assert token_target is None
    
    def test_generator_send_declare_context_type(self, w):
        
        @structured_dict
        class StructuredDict(object):
            a = Value(default=123)
            child = Value(default=321)
        
        token_sd = Token(TokenTypes.declare_context_type, StructuredDict, None)
        token_enter = Token(TokenTypes.nested_context_enter, None, "child")
        token_leave = Token(TokenTypes.nested_context_leave, None, None)
        def generator():
            yield token_sd
            yield token_enter
            yield token_sd
            yield token_enter
            yield token_sd
            yield token_leave
            yield token_leave
            yield token_sd
        g = generator()
        
        fsm = TokenParserStateMachine(g, w)
        
        # Pre-set a value
        fsm._set_context_value("a", 100)
        
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        
        # Passed through
        assert original_token is token_sd
        
        # Type changed, existing value remains, default values ignored
        assert isinstance(fsm.context, StructuredDict)
        assert fsm.context.a == 100
        assert not hasattr(fsm.context, "child")
        
        # Nop output
        assert token_type is TokenTypes.nop
        assert token_argument is None
        assert token_target is None
        
        # Nest (tested more thoroughly elsewhere)
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        assert original_token is token_enter
        assert fsm.context_stack[0].child is fsm.context
        
        # Pre-set a value in newly nested context
        fsm._set_context_value("a", 1000)
        
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        
        # Passed through
        assert original_token is token_sd
        
        # Type changed, existing value remains, default values ignored
        assert isinstance(fsm.context, StructuredDict)
        assert fsm.context.a == 1000
        assert not hasattr(fsm.context, "child")
        
        # Value changed in parent (and value in parent is just a non-list
        # target
        assert fsm.context_stack[0]["child"] is fsm.context
        
        # Make child of inner list a list
        fsm._declare_context_value_is_list("child")
        fsm._set_context_value("child", 123)
        
        # Nest into list (tested more thoroughly elsewhere)
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        assert original_token is token_enter
        assert fsm.context_stack[1].child[1] is fsm.context
        
        # Change type and check parent is updated
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        assert original_token is token_sd
        assert isinstance(fsm.context, StructuredDict)
        assert fsm.context_stack[1].child[1] is fsm.context
        
        # Nop output
        assert token_type is TokenTypes.nop
        assert token_argument is None
        assert token_target is None
        
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        assert original_token is token_leave
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        assert original_token is token_leave
        
        # Finally, changing the type of a value to the type it already is
        # should not result in a copy being made
        orig_context = fsm.context
        
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        assert original_token is token_sd
        
        assert fsm.context is orig_context
    
    def test_generator_send_nested_context(self, w):
        token_enter = Token(TokenTypes.nested_context_enter, None, "child")
        token_leave = Token(TokenTypes.nested_context_leave, None, None)
        def generator():
            yield token_enter
            yield token_enter
            yield token_leave
            yield token_leave
        g = generator()
        
        fsm = TokenParserStateMachine(g, w)
        
        # Put something in original child to make it identifiable
        fsm._set_context_value("foo", 123)
        
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        assert original_token is token_enter
        
        # Should have created a new context in a non-list target
        assert fsm.context == {}
        assert fsm.context_indices == {}
        assert fsm.context_stack[0]["child"] is fsm.context
        assert fsm.context_stack == [{"foo": 123, "child": fsm.context}]
        assert fsm.context_indices_stack == [{"foo": True, "child": True}]
        
        # Passed on as nop
        assert token_type is TokenTypes.nop
        assert token_argument is None
        assert token_target is None
        
        # Create a list entry to nest into
        fsm._declare_context_value_is_list("child")
        fsm._set_context_value("child", {})
        
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        assert original_token is token_enter
        
        # Should have created a new nested context in new entry of list target
        assert fsm.context == {}
        assert fsm.context_indices == {}
        assert fsm.context_stack[1]["child"][1] is fsm.context
        assert fsm.context_stack == [
            {"foo": 123, "child": {"child": [{}, fsm.context]}},
            {"child": [{}, fsm.context]},
        ]
        assert fsm.context_indices_stack == [
            {"foo": True, "child": True},
            {"child": 2},
        ]
        
        # Passed on as nop
        assert token_type is TokenTypes.nop
        assert token_argument is None
        assert token_target is None
        
        # Leaving should recover one-less nested state
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        assert original_token is token_leave
        
        # Should have created a new context in a non-list target
        assert fsm.context == {"child": [{}, {}]}
        assert fsm.context_indices == {"child": 2}
        assert len(fsm.context_stack) == 1
        assert len(fsm.context_indices_stack) == 1
        
        # Passed on as nop
        assert token_type is TokenTypes.nop
        assert token_argument is None
        assert token_target is None
        
        # Leaving again should recover original state
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        assert original_token is token_leave
        
        # Should have created a new context in a non-list target
        assert fsm.context == {"foo": 123, "child": {"child": [{}, {}]}}
        assert fsm.context_indices == {"foo": True, "child": True}
        assert fsm.context_stack == []
        assert fsm.context_indices_stack == []
        
        # Passed on as nop
        assert token_type is TokenTypes.nop
        assert token_argument is None
        assert token_target is None
    
    def test_generator_send_nested_context_incomplete(self, w):
        token_enter = Token(TokenTypes.nested_context_enter, None, "child")
        token_leave = Token(TokenTypes.nested_context_leave, None, None)
        def generator():
            yield token_enter
            yield token_leave
        g = generator()
        
        fsm = TokenParserStateMachine(g, w, {"child": {"forget_to_use": 123}})
        
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        assert original_token is token_enter
        
        assert fsm.context == {"forget_to_use": 123}
        
        # If we now try to leave without using the 'forget_to_use' value we
        # should fail
        with pytest.raises(exceptions.UnusedTargetError, match=r"dict\['child'\]\['forget_to_use'\]"):
            fsm._generator_send(None)
    
    def test_generator_send_use(self, w):
        def generator(input_value):
            assert (yield Token(TokenTypes.nbits, input_value, "foo")) == 123
            if input_value > 0:
                output_value = yield Token(
                    TokenTypes.use,
                    generator(input_value - 1),
                    None,
                )
            else:
                output_value = 100
            
            raise Return(output_value + 1)
        
        g = generator(3)
        
        fsm = TokenParserStateMachine(g, w)
        
        assert fsm._generator_send(None)[2] == 3
        assert fsm._generator_send(123)[1] is TokenTypes.nop
        
        assert fsm._generator_send(None)[2] == 2
        assert fsm._generator_send(123)[1] is TokenTypes.nop
        
        assert fsm._generator_send(None)[2] == 1
        assert fsm._generator_send(123)[1] is TokenTypes.nop
        
        assert fsm._generator_send(None)[2] == 0
        
        with pytest.raises(StopIteration) as excinfo:
            fsm._generator_send(123)
        assert excinfo.value.value == 104
    
    def test_generator_send_nest(self, w):
        def sub_generator():
            yield Token(TokenTypes.declare_list, None, "list")
            raise Return(123)
        
        def generator():
            assert (yield Token(TokenTypes.nest, sub_generator(), "inner")) == 123
        
        g = generator()
        
        fsm = TokenParserStateMachine(g, w)
        
        try:
            while True:
                assert fsm._generator_send(None)[1] is TokenTypes.nop
        except StopIteration:
            pass
        
        assert fsm.context == {"inner": {"list": []}}
    
    def test_generator_send_computed_value(self, w):
        token_first = Token(TokenTypes.computed_value, 123, "first")
        token_second = Token(TokenTypes.computed_value, 321, "second")
        def generator():
            yield token_first
            yield token_second
            yield token_first
        
        g = generator()
        
        fsm = TokenParserStateMachine(g, w)
        
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        assert original_token is token_first
        
        # Should have set the required value
        assert fsm.context == {"first": 123}
        assert fsm.context_indices == {"first": True}
        
        # Passed on as nop
        assert token_type is TokenTypes.nop
        assert token_argument is None
        assert token_target is None
        
        original_token, token_type, token_argument, token_target = fsm._generator_send(None)
        assert original_token is token_second
        
        # Should have set the required value
        assert fsm.context == {"first": 123, "second": 321}
        assert fsm.context_indices == {"first": True, "second": True}
        
        # Passed on as nop
        assert token_type is TokenTypes.nop
        assert token_argument is None
        assert token_target is None
        
        # Should fail on re-used value
        with pytest.raises(exceptions.ReusedTargetError, match=r"dict\['first'\]"):
            original_token, token_type, token_argument, token_target = fsm._generator_send(None)
    
    def test_generator_throw(self, w):
        generator_bail_exc = []
        def generator_bail():
            try:
                yield Token(TokenTypes.nop, None, None)
            except Exception as e:
                generator_bail_exc.append(e)
                raise
        
        generator_catch_exc = []
        def generator_catch():
            try:
                yield Token(TokenTypes.nop, None, None)
            except Exception as e:
                generator_catch_exc.append(e)
        
        gb = generator_bail()
        gc = generator_catch()
        
        # When generator bails on exception, the exception makes it out
        fsm = TokenParserStateMachine(gb, w)
        fsm._generator_send(None)
        exc = Exception("Nope")
        with pytest.raises(Exception) as excinfo:
            fsm._generator_throw(exc)
        assert generator_bail_exc == [exc]
        assert excinfo.value is exc
        
        # When generator catches the exception, the exception is still thrown
        fsm = TokenParserStateMachine(gc, w)
        fsm._generator_send(None)
        exc = Exception("Nope")
        with pytest.raises(Exception) as excinfo:
            fsm._generator_throw(exc)
        assert generator_catch_exc == [exc]
        assert excinfo.value is exc
    
    def test_generator_close(self, w):
        generator_opened = []
        generator_closed = []
        def generator():
            generator_opened.append(None)
            try:
                yield Token(TokenTypes.use, generator(), None)
            finally:
                generator_closed.append(None)
        
        g = generator()
        
        # When generator bails on exception, the exception makes it out
        fsm = TokenParserStateMachine(g, w)
        
        # Start a few generators running
        fsm._generator_send(None)
        fsm._generator_send(None)
        fsm._generator_send(None)
        
        assert len(generator_opened) == 3
        assert len(generator_closed) == 0
        
        fsm._generator_close()
        
        assert len(generator_opened) == 3
        assert len(generator_closed) == 3
    
    def test_truncate_lists_if_required(self):
        # If everything is as expected, do nothing
        fsm = TokenParserStateMachine(None, None, truncate_lists=True)
        fsm._set_context_value("foo", 123)
        fsm._declare_context_value_is_list("bar")
        fsm._set_context_value("bar", 10)
        fsm._set_context_value("bar", 20)
        fsm._set_context_value("bar", 30)
        fsm._truncate_lists_if_required()
        assert fsm.context == {"foo": 123, "bar": [10, 20, 30]}
        
        # If have excess values, remove them (iff truncate_lists is True)
        fsm = TokenParserStateMachine(None, None, {"bar": [0, 0, 0, 0, 0]})
        fsm._set_context_value("foo", 123)
        fsm._declare_context_value_is_list("bar")
        fsm._set_context_value("bar", 10)
        fsm._set_context_value("bar", 20)
        fsm._set_context_value("bar", 30)
        assert fsm.context == {"foo": 123, "bar": [10, 20, 30, 0, 0]}
        fsm._truncate_lists_if_required()
        assert fsm.context == {"foo": 123, "bar": [10, 20, 30, 0, 0]}
        
        fsm.truncate_lists = True
        fsm._truncate_lists_if_required()
        assert fsm.context == {"foo": 123, "bar": [10, 20, 30]}
    
    def test_verify_context_is_complete(self):
        fsm = TokenParserStateMachine(None, None)
        
        # Empty and therefore complete
        fsm._verify_context_is_complete()
        
        # Writing values of any kind an still should be complete
        fsm._set_context_value("foo", 123)
        fsm._verify_context_is_complete()
        
        fsm._declare_context_value_is_list("bar")
        fsm._verify_context_is_complete()
        fsm._set_context_value("bar", 10)
        fsm._verify_context_is_complete()
        fsm._set_context_value("bar", 20)
        fsm._verify_context_is_complete()
        fsm._set_context_value("bar", 30)
        fsm._verify_context_is_complete()
        
        # If there are any values in the context which haven't been indexed,
        # fail
        fsm = TokenParserStateMachine(None, None, {"baz": None})
        with pytest.raises(exceptions.UnusedTargetError, match=r"dict\['baz'\]"):
            fsm._verify_context_is_complete()
        fsm._set_context_value("baz", 321)
        fsm._verify_context_is_complete()
        
        # If there are any list values which weren't used, fail
        fsm = TokenParserStateMachine(None, None, {"list": [1, 2, 3]})
        fsm._declare_context_value_is_list("list")
        with pytest.raises(exceptions.UnusedTargetError, match=r"dict\['list'\]\[0:3\]"):
            fsm._verify_context_is_complete()
        fsm._set_context_value("list", 10)
        with pytest.raises(exceptions.UnusedTargetError, match=r"dict\['list'\]\[1:3\]"):
            fsm._verify_context_is_complete()
        fsm._set_context_value("list", 20)
        with pytest.raises(exceptions.UnusedTargetError, match=r"dict\['list'\]\[2:3\]"):
            fsm._verify_context_is_complete()
        fsm._set_context_value("list", 30)
        fsm._verify_context_is_complete()
    
    def test_verify_complete(self):
        def generator_nest():
            yield Token(TokenTypes.nested_context_enter, None, "child")
        
        def generator_block():
            yield Token(TokenTypes.bounded_block_begin, 10, None)
        
        # Shouldn't fail if empty
        fsm = TokenParserStateMachine(None, None)
        fsm._verify_complete()
        
        # Should fail for reasons _verify_context_is_complete would fail
        fsm = TokenParserStateMachine(None, None, {"incomplete": None})
        with pytest.raises(exceptions.UnusedTargetError, match=r"dict\['incomplete'\]"):
            fsm._verify_complete()
        
        # Should fail if nesting isn't undone
        fsm = TokenParserStateMachine(generator_nest(), None)
        fsm._generator_send(None)
        with pytest.raises(exceptions.UnclosedNestedContextError, match=r"dict\['child'\]"):
            fsm._verify_complete()
        
        # Should fail if bounded blocks aren't closed
        fsm = TokenParserStateMachine(generator_block(), None)
        fsm._generator_send(None)
        with pytest.raises(exceptions.UnclosedBoundedBlockError, match=r"1 block left unclosed"):
            fsm._verify_complete()
    
    def test_root_context(self, w):
        def generator():
            yield Token(TokenTypes.nested_context_enter, None, "child")
        fsm = TokenParserStateMachine(generator(), w)
        
        # Already in root context
        root = fsm.context
        assert fsm.root_context is root
        
        # In child context
        fsm._generator_send(None)
        assert fsm.context is not root
        assert fsm.root_context is root
    
    def test_describe_path(self, w):
        def generator():
            yield Token(TokenTypes.nested_context_enter, None, "child")
            yield Token(TokenTypes.nested_context_enter, None, "child")
        fsm = TokenParserStateMachine(generator(), w)
        
        # At root should work
        assert fsm.describe_path() == "dict"
        assert fsm.describe_path("foo") == "dict['foo']"
        
        # List items in root should work
        fsm._declare_context_value_is_list("list")
        assert fsm.describe_path("list") == "dict['list']"
        fsm._set_context_value("list", 10)
        assert fsm.describe_path("list") == "dict['list'][0]"
        fsm._set_context_value("list", 20)
        assert fsm.describe_path("list") == "dict['list'][1]"
        fsm._set_context_value("list", 30)
        assert fsm.describe_path("list") == "dict['list'][2]"
        
        # When nested, the same should work
        fsm._generator_send(None)
        
        assert fsm.describe_path() == "dict['child']"
        assert fsm.describe_path("foo") == "dict['child']['foo']"
        
        # List items in root should work
        fsm._declare_context_value_is_list("list")
        assert fsm.describe_path("list") == "dict['child']['list']"
        fsm._set_context_value("list", 10)
        assert fsm.describe_path("list") == "dict['child']['list'][0]"
        fsm._set_context_value("list", 20)
        assert fsm.describe_path("list") == "dict['child']['list'][1]"
        fsm._set_context_value("list", 30)
        assert fsm.describe_path("list") == "dict['child']['list'][2]"
        
        # When nested into an array, the same should work
        fsm._declare_context_value_is_list("child")
        fsm._generator_send(None)
        assert fsm.describe_path() == "dict['child']['child'][0]"
        assert fsm.describe_path("foo") == "dict['child']['child'][0]['foo']"
        
        # With different types, prefix should be different
        @structured_dict
        class StructuredDict(object):
            child = Value(default=321)
        def generator():
            yield Token(TokenTypes.declare_context_type, StructuredDict, None)
            yield Token(TokenTypes.nested_context_enter, None, "child")
        fsm = TokenParserStateMachine(generator(), w)
        fsm._generator_send(None)
        
        assert fsm.describe_path() == "StructuredDict"
        assert fsm.describe_path("foo") == "StructuredDict['foo']"
        
        # When nested, outer-most dict defines the type
        fsm._generator_send(None)
        assert fsm.describe_path() == "StructuredDict['child']"
        assert fsm.describe_path("foo") == "StructuredDict['child']['foo']"


def test_context_type(w):
    @structured_dict
    class StructuredDict(object):
        a = Value()
    
    @context_type(StructuredDict)
    def generator(value):
        yield Token(TokenTypes.computed_value, -value, "a")
    fsm = TokenParserStateMachine(generator(123), w)
    
    try:
        while True:
            fsm._generator_send(None)
    except StopIteration:
        pass
    
    assert isinstance(fsm.context, StructuredDict)
    assert fsm.context.a == -123


class TestRead(object):
    
    def test_nop(self, r):
        def generator():
            assert (yield Token(TokenTypes.nop, None, None)) is None
        
        # Nothing put in context
        assert read(generator(), r) == {}
        
        # Nothing read
        assert r.tell() == (0, 7)
    
    @pytest.mark.parametrize("token_type,token_argument,bitstream,exp_value,exp_tell", [
        # bool
        (TokenTypes.bool, None, b"\x00", False, (0, 6)),
        (TokenTypes.bool, None, b"\x80", True, (0, 6)),
        # nbits
        (TokenTypes.nbits, 8, b"\xAB", 0xAB, (1, 7)),
        # bitarray
        (TokenTypes.bitarray, 8, b"\xA0", bitarray("10100000"), (1, 7)),
        # bytes
        (TokenTypes.bytes, 2, b"\xA0\xCD", b"\xA0\xCD", (2, 7)),
        # uint
        (TokenTypes.uint, None, b"\x3F", 1, (0, 4)),
        # sint
        (TokenTypes.sint, None, b"\x3F", -1, (0, 3)),
    ])
    def test_primitives(self, token_type, token_argument, bitstream,
                        exp_value, exp_tell):
        def generator():
            assert (yield Token(token_type, token_argument, "target")) == exp_value
        
        r = BitstreamReader(BytesIO(bitstream))
        assert read(generator(), r) == {"target": exp_value}
        assert r.tell() == exp_tell
    
    def test_bad_token(self, r):
        def generator():
            yield Token(None, None, None)
        
        with pytest.raises(exceptions.UnknownTokenTypeError, match=r"None"):
            read(generator(), r)
    
    def test_exceptions_propagate_to_generator(self, r):
        generator_failed = [False]
        def generator():
            try:
                yield Token(None, None, None)
            except exceptions.UnknownTokenTypeError:
                generator_failed[0] = True
        
        with pytest.raises(exceptions.UnknownTokenTypeError):
            read(generator(), r)
        
        assert generator_failed[0]
    
    def test_return_generator_return_value(self, r):
        def generator():
            yield Token(TokenTypes.nop, None, None)
            raise Return(123)
        
        read(generator(), r, return_generator_return_value=True) == ({}, 123)
    
    def test_checks_completeness(self, r):
        def generator():
            yield Token(TokenTypes.nested_context_enter, None, "foo")
        
        with pytest.raises(exceptions.UnclosedNestedContextError, match=r"dict\['foo'\]"):
            read(generator(), r)


def test_read_interruptable(r):
    def generator():
        assert (yield Token(TokenTypes.nbits, 8, "a")) == 0xAA
        assert (yield Token(TokenTypes.nbits, 8, "b")) == 0xBB
        assert (yield Token(TokenTypes.nbits, 8, "c")) == 0xCC
        assert (yield Token(TokenTypes.nbits, 8, "d")) == 0xDD
    
    r = BitstreamReader(BytesIO(b"\xAA\xBB\xCC\xDD"))
    
    def interrupt(fsm, token):
        if token.target == "c":
            return True
        elif fsm.io.tell()[0] == 2:
            return True
        else:
            return False
    
    g = read_interruptable(generator(), r, interrupt)
    
    # First stop should be on io.tell()[0] == 2
    fsm, token = next(g)
    assert fsm.root_context == {"a": 0xAA, "b": 0xBB}
    assert token.target == "b"  # 'b' should have been just written
    
    # Second stop should be on target == 'c'
    fsm, token = next(g)
    assert fsm.root_context == {"a": 0xAA, "b": 0xBB, "c": 0xCC}
    assert token.target == "c"
    
    # Final stop should be the end
    with pytest.raises(StopIteration) as excinfo:
        next(g)
    assert excinfo.value.value == {"a": 0xAA, "b": 0xBB, "c": 0xCC, "d": 0xDD}


class TestWrite(object):
    
    def test_nop(self, w):
        def generator():
            assert (yield Token(TokenTypes.nop, None, None)) is None
        
        # Nothing put in context
        assert write(generator(), w, {}) == {}
        
        # Nothing written
        assert w.tell() == (0, 7)
    
    @pytest.mark.parametrize("token_type,token_argument,value,exp_bitstream,exp_tell", [
        # bool
        (TokenTypes.bool, None, False, b"\x00", (0, 6)),
        (TokenTypes.bool, None, True, b"\x80", (0, 6)),
        # nbits
        (TokenTypes.nbits, 8, 0xAB, b"\xAB", (1, 7)),
        # bitarray
        (TokenTypes.bitarray, 8, bitarray("10100000"), b"\xA0", (1, 7)),
        # bytes
        (TokenTypes.bytes, 2, b"\xA0\xCD", b"\xA0\xCD", (2, 7)),
        # uint
        (TokenTypes.uint, None, 1, b"\x20", (0, 4)),
        # sint
        (TokenTypes.sint, None, -1, b"\x30", (0, 3)),
    ])
    def test_primitives(self, token_type, token_argument,
                        value, exp_bitstream, exp_tell):
        def generator():
            assert (yield Token(token_type, token_argument, "target")) == value
        
        f = BytesIO()
        w = BitstreamWriter(f)
        assert write(generator(), w, {"target": value}) == {"target": value}
        w.flush()
        assert f.getvalue() == exp_bitstream
        assert w.tell() == exp_tell
    
    def test_bad_token(self, w):
        def generator():
            yield Token(None, None, None)
        
        with pytest.raises(exceptions.UnknownTokenTypeError, match=r"None"):
            write(generator(), w, {})
    
    def test_returns_new_context(self, w):
        @structured_dict
        class StructuredDict(object):
            foo = Value()
        
        @context_type(StructuredDict)
        def generator():
            yield Token(TokenTypes.computed_value, 123, "foo")
        
        context = write(generator(), w, {})
        assert isinstance(context, StructuredDict)
        assert context.foo == 123
    
    def test_exceptions_propagate_to_generator(self, w):
        generator_failed = [False]
        def generator():
            try:
                yield Token(None, None, None)
            except exceptions.UnknownTokenTypeError:
                generator_failed[0] = True
        
        with pytest.raises(exceptions.UnknownTokenTypeError):
            write(generator(), w, {})
        
        assert generator_failed[0]
    
    def test_return_generator_return_value(self, w):
        def generator():
            yield Token(TokenTypes.nop, None, None)
            raise Return(123)
        
        write(generator(), w, {}, return_generator_return_value=True) == ({}, 123)
    
    def test_checks_completeness(self, w):
        def generator():
            yield Token(TokenTypes.nested_context_enter, None, "foo")
        
        with pytest.raises(exceptions.UnclosedNestedContextError, match=r"dict\['foo'\]"):
            write(generator(), w, {})


def test_write_interruptable(r):
    def generator():
        assert (yield Token(TokenTypes.nbits, 8, "a")) == 0xAA
        assert (yield Token(TokenTypes.nbits, 8, "b")) == 0xBB
        assert (yield Token(TokenTypes.nbits, 8, "c")) == 0xCC
        assert (yield Token(TokenTypes.nbits, 8, "d")) == 0xDD
    
    f = BytesIO()
    w = BitstreamWriter(f)
    
    def interrupt(fsm, token):
        if token.target == "c":
            return True
        elif fsm.io.tell()[0] == 2:
            return True
        else:
            return False
    
    g = write_interruptable(
        generator(),
        w,
        {"a": 0xAA, "b": 0xBB, "c": 0xCC, "d": 0xDD},
        interrupt,
    )
    
    # First stop should be on io.tell()[0] == 2
    fsm, token = next(g)
    assert token.target == "b"  # 'b' should have been just written
    assert f.getvalue() == b"\xAA\xBB"
    
    # Second stop should be on target == 'c'
    fsm, token = next(g)
    assert token.target == "c"
    assert f.getvalue() == b"\xAA\xBB\xCC"
    
    # Final stop should be the end
    with pytest.raises(StopIteration) as excinfo:
        next(g)
    assert excinfo.value.value == {"a": 0xAA, "b": 0xBB, "c": 0xCC, "d": 0xDD}
    assert f.getvalue() == b"\xAA\xBB\xCC\xDD"


class TestPadAndTruncate(object):
    
    def test_nop(self):
        def generator():
            assert (yield Token(TokenTypes.nop, None, None)) is None
        
        # Nothing put in context
        assert pad_and_truncate(generator(), {}) == {}
    
    @pytest.mark.parametrize("token_type,token_argument,value,exp_value", [
        # bool
        (TokenTypes.bool, None, False, False),
        (TokenTypes.bool, None, True, True),
        (TokenTypes.bool, None, 0, False),
        (TokenTypes.bool, None, 100, True),
        # nbits
        (TokenTypes.nbits, 8, 0xAB, 0xAB),
        (TokenTypes.nbits, 4, 0xAB, 0xB),
        (TokenTypes.nbits, 12, 0xAB, 0x0AB),
        # bitarray
        (TokenTypes.bitarray, 8, bitarray("10100000"), bitarray("10100000")),
        (TokenTypes.bitarray, 4, bitarray("10100101"), bitarray("0101")),
        (TokenTypes.bitarray, 12, bitarray("10100101"), bitarray("000010100101")),
        # bytes
        (TokenTypes.bytes, 2, b"\xA0\xCD", b"\xA0\xCD"),
        (TokenTypes.bytes, 1, b"\xA0\xCD", b"\xCD"),
        (TokenTypes.bytes, 3, b"\xA0\xCD", b"\x00\xA0\xCD"),
        # uint
        (TokenTypes.uint, None, 1, 1),
        (TokenTypes.uint, None, -1, 0),
        # sint
        (TokenTypes.sint, None, 1, 1),
        (TokenTypes.sint, None, -1, -1),
    ])
    def test_primitives(self, token_type, token_argument,
                        value, exp_value):
        def generator():
            assert (yield Token(token_type, token_argument, "target")) == exp_value
        
        assert pad_and_truncate(generator(), {"target": value}) == {"target": exp_value}
    
    def test_bad_token(self):
        def generator():
            yield Token(None, None, None)
        
        with pytest.raises(exceptions.UnknownTokenTypeError, match=r"None"):
            pad_and_truncate(generator(), {})
    
    def test_returns_new_context(self):
        @structured_dict
        class StructuredDict(object):
            foo = Value()
        
        @context_type(StructuredDict)
        def generator():
            yield Token(TokenTypes.computed_value, 123, "foo")
        
        context = pad_and_truncate(generator(), {})
        assert isinstance(context, StructuredDict)
        assert context.foo == 123
    
    def test_exceptions_propagate_to_generator(self):
        generator_failed = [False]
        def generator():
            try:
                yield Token(None, None, None)
            except exceptions.UnknownTokenTypeError:
                generator_failed[0] = True
        
        with pytest.raises(exceptions.UnknownTokenTypeError):
            pad_and_truncate(generator(), {})
        
        assert generator_failed[0]
    
    def test_return_generator_return_value(self):
        def generator():
            yield Token(TokenTypes.nop, None, None)
            raise Return(123)
        
        pad_and_truncate(generator(), {}, return_generator_return_value=True) == ({}, 123)
    
    def test_truncates_lists(self):
        def generator():
            yield Token(TokenTypes.declare_list, None, "list")
            yield Token(TokenTypes.uint, None, "list")
            yield Token(TokenTypes.uint, None, "list")
            yield Token(TokenTypes.uint, None, "list")
        
        assert pad_and_truncate(generator(), {"list": [1, 2, 3, 4, 5]}) == {"list": [1, 2, 3]}
    
    def test_populates_missing(self):
        def generator():
            yield Token(TokenTypes.uint, None, "value")
            yield Token(TokenTypes.declare_list, None, "list")
            yield Token(TokenTypes.uint, None, "list")
            yield Token(TokenTypes.uint, None, "list")
            yield Token(TokenTypes.uint, None, "list")
        
        assert pad_and_truncate(generator(), {"list": [1, 2]}) == {"value": 0, "list": [1, 2, 0]}
    
    def test_checks_completeness(self):
        def generator():
            yield Token(TokenTypes.nested_context_enter, None, "foo")
        
        with pytest.raises(exceptions.UnclosedNestedContextError, match=r"dict\['foo'\]"):
            pad_and_truncate(generator(), {})


def test_pad_and_truncate_interruptable(r):
    def generator():
        assert (yield Token(TokenTypes.nbits, 8, "a")) == 0xAA
        assert (yield Token(TokenTypes.nbits, 8, "b")) == 0xBB
        assert (yield Token(TokenTypes.nbits, 8, "c")) == 0xCC
        assert (yield Token(TokenTypes.nbits, 8, "d")) == 0xDD
    
    def interrupt(fsm, token):
        if token.target == "c":
            return True
        elif fsm.io.tell()[0] == 2:
            return True
        else:
            return False
    
    g = pad_and_truncate_interruptable(
        generator(),
        {"a": 0xAA, "b": 0xBB, "c": 0xCC, "d": 0xDD},
        interrupt,
    )
    
    # First stop should be on io.tell()[0] == 2
    fsm, token = next(g)
    assert token.target == "b"  # 'b' should have been just been reached
    
    # Second stop should be on target == 'c'
    fsm, token = next(g)
    assert token.target == "c"
    
    # Final stop should be the end
    with pytest.raises(StopIteration) as excinfo:
        next(g)
    assert excinfo.value.value == {"a": 0xAA, "b": 0xBB, "c": 0xCC, "d": 0xDD}
