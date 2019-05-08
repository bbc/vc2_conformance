import ast

from verification.comparators import (
    Identical,
    SerdesChangesOnly,
)


class TestIdentical(object):
    
    def test_allow_differing_decorators_and_docstrings(self):
        c = Identical()
        
        n1 = ast.parse("def func(arg1, args2): return 123")
        n2 = ast.parse("@ref_pseudocode('1.2.3')\ndef func(arg1, args2):\n  '''Docs'''\n  return 123")
        n3 = ast.parse("def func(arg1, args2): return 321")
        n4 = ast.parse("def func(arg1, args2):\n  '''Doc'''\n  return 123")
        
        assert c.compare(n1, n1) is True
        assert c.compare(n1, n2) is True
        
        assert c.compare(n1, n4) is True
        assert c.compare(n4, n1) is True
        
        # Different return value
        assert c.compare(n2, n3) is not True
        
        # First value not allowed to contain extra decorators (only second one
        # may have which may be ignored decorators)
        assert c.compare(n2, n1) is not True
    
    def test_allow_swapping_literals_for_named_constants(self):
        c = Identical()
        
        n1 = ast.parse("13")
        n2 = ast.parse("PARSE_INFO_HEADER_BYTES")
        
        n3 = ast.parse("0x10")
        n4 = ast.parse("ParseCodes.end_of_sequence")
        n5 = ast.parse("ParseCodes.end_of_sequence.value")
        
        assert c.compare(n1, n2) is True
        assert c.compare(n2, n1) is not True
        assert c.compare(n3, n2) is not True
        
        assert c.compare(n3, n4) is True
        assert c.compare(n3, n5) is True
        assert c.compare(n4, n3) is not True
        assert c.compare(n5, n3) is not True
        


class TestSerdesChangesOnly(object):
    
    def test_allow_differing_docstrings(self):
        # Allowed change no. 1
        c = SerdesChangesOnly()
        
        n1 = ast.parse("def func(a, b): return a + b")
        n2 = ast.parse("def func(a, b):\n  '''doc'''\n  return a + b")
        
        assert c.compare(n1, n2) is True
        assert c.compare(n2, n1) is True
    
    def test_allow_differing_generators(self):
        # Allowed change no. 2, 3
        c = SerdesChangesOnly()
        
        n1 = ast.parse("def func(a, b): return a + b")
        n2 = ast.parse("@context_type(Sequence)\n@ref_pseudocode(deviations='serdes')\ndef func(a, b): return a + b")
        
        assert c.compare(n1, n2) is True
        assert c.compare(n2, n1) is not True
    
    def test_allow_serdes_argument_def(self):
        # Allowed change no. 4
        c = SerdesChangesOnly()
        
        n1 = ast.parse("def func(a, b): return a + b")
        n2 = ast.parse("def func(serdes, a, b): return a + b")
        
        assert c.compare(n1, n2) is True
        assert c.compare(n2, n1) is not True
    
    def test_allow_serdes_argument_call(self):
        # Allowed change no. 4
        c = SerdesChangesOnly()
        
        n1 = ast.parse("func(123, 321)")
        n2 = ast.parse("func(serdes, 123, 321)")
        
        assert c.compare(n1, n2) is True
        assert c.compare(n2, n1) is not True
    
    def test_allow_with_blocks(self):
        # Allowed change no. 5
        c = SerdesChangesOnly()
        
        n1 = ast.parse(
            "def func(a, b):\n"
            "  while False:\n"
            "    a += 1\n"
            "  else:\n"
            "    b += 1\n"
            "  c = a + b\n"
            "  return c\n"
        )
        n2 = ast.parse(
            "def func(serdes, a, b):\n"
            "  while False:\n"
            "    a += 1\n"
            "  else:\n"
            "    with serdes.subcontext('foobar'):\n"
            "      b += 1\n"
            "  with serdes.subcontext('baz') as qux:\n"
            "    c = a + b\n"
            "  return c\n"
        )
        
        assert c.compare(n1, n2) is True
        assert c.compare(n2, n1) is not True
    
    def test_allow_ignoring_some_calls(self):
        # Allowed change no. 6
        c = SerdesChangesOnly()
        
        n1 = ast.parse(
            "def func(a, b):\n"
            "  return a + b\n"
        )
        n2 = ast.parse(
            "def func(serdes, a, b):\n"
            "  serdes.subcontext_enter('foo')\n"
            "  serdes.subcontext_leave()\n"
            "  serdes.set_context_type(Sequence)\n"
            "  serdes.declare_list('bar')\n"
            "  serdes.computed_value('baz', a + b)\n"
            "  return a + b\n"
        )
        
        assert c.compare(n1, n2) is True
        assert c.compare(n2, n1) is not True
    
    def test_allow_swap_state_bits_left_to_bounded_block_begin(self):
        # Allowed change no. 7
        c = SerdesChangesOnly()
        
        n1 = ast.parse(
            "def func(a, b):\n"
            "  state['bits_left'] = a + b\n"
        )
        n2 = ast.parse(
            "def func(serdes, a, b):\n"
            "  serdes.bounded_block_begin(a + b)\n"
        )
        
        assert c.compare(n1, n2) is True
        
        # Different operation
        n3 = ast.parse(
            "def func(serdes, a, b):\n"
            "  serdes.bounded_block_begin(a - b)\n"
        )
        
        # Different arguments
        n4 = ast.parse(
            "def func(serdes, a, b):\n"
            "  serdes.bounded_block_begin(a + b, bar=123)\n"
        )
        
        # Different function
        n5 = ast.parse(
            "def func(serdes, a, b):\n"
            "  bounded_block_begin(a + b)\n"
        )
        
        assert c.compare(n2, n1) is not True
        assert c.compare(n1, n3) is not True
        assert c.compare(n1, n4) is not True
        assert c.compare(n1, n5) is not True
    
    def test_allow_swap_in_serdes_functions(self):
        # Allowed change no. 8
        c = SerdesChangesOnly()
        
        n1 = ast.parse(
            "def func(state, a, b):\n"
            "  byte_align(state)\n"
            "  b = read_bool(state)\n"
            "  n = read_nbits(state, a + b)\n"
            "  l = read_uint_lit(state, a - b)\n"
            "  L = read_uint_lit(state, a - b)\n"
            "  u = read_uint(state)\n"
            "  s = read_sint(state)\n"
            "  U = read_uintb(state)\n"
            "  S = read_sintb(state)\n"
            "  flush_inputb(state)\n"
        )
        n2 = ast.parse(
            "def func(serdes, state, a, b):\n"
            "  serdes.byte_align('a')\n"
            "  b = serdes.bool('b')\n"
            "  n = serdes.nbits('n', a + b)\n"
            "  l = serdes.uint_lit('l', a - b)\n"
            "  L = serdes.bytes('L', a - b)\n"
            "  u = serdes.uint('u')\n"
            "  s = serdes.sint('s')\n"
            "  U = serdes.uint('U')\n"
            "  S = serdes.sint('S')\n"
            "  serdes.bounded_block_end('e')\n"
        )
        
        assert c.compare(n1, n2) is True
        assert c.compare(n2, n1) is not True
        
        # Argument differs
        n3 = ast.parse(
            "def func(serdes, state, a, b):\n"
            "  serdes.byte_align('a')\n"
            "  b = serdes.bool('b')\n"
            "  n = serdes.nbits('n', a - b)\n"
            "  l = serdes.uint_lit('l', a - b)\n"
            "  L = serdes.bytes('L', a - b)\n"
            "  u = serdes.uint('u')\n"
            "  s = serdes.sint('s')\n"
            "  U = serdes.uint('U')\n"
            "  S = serdes.sint('S')\n"
            "  serdes.bounded_block_end('e')\n"
        )
        
        assert c.compare(n1, n3) is not True
    
    def test_allow_swap_in_fixed_dicts(self):
        # Allowed change no. 9
        c = SerdesChangesOnly()
        
        n1 = ast.parse("a = {}")
        n2 = ast.parse("a = State()")
        assert c.compare(n1, n2) is True
        assert c.compare(n2, n1) is not True
        
        n1 = ast.parse("a = {}")
        n2 = ast.parse("a = VideoParameters()")
        assert c.compare(n1, n2) is True
        assert c.compare(n2, n1) is not True
        
        # Not one of the approved functions
        n1 = ast.parse("a = {}")
        n2 = ast.parse("a = Foobar()")
        assert c.compare(n1, n2) is not True
        
        # Non-empty dict
        n1 = ast.parse("a = {1: 2}")
        n2 = ast.parse("a = State()")
        assert c.compare(n1, n2) is not True
        
        # Non-empty arguments
        n1 = ast.parse("a = {}")
        n2 = ast.parse("a = State(1)")
        assert c.compare(n1, n2) is not True
        n1 = ast.parse("a = {}")
        n2 = ast.parse("a = State(a=1)")
        assert c.compare(n1, n2) is not True
        n1 = ast.parse("a = {}")
        n2 = ast.parse("a = State(*a)")
        assert c.compare(n1, n2) is not True
        n1 = ast.parse("a = {}")
        n2 = ast.parse("a = State(**k)")
        assert c.compare(n1, n2) is not True
