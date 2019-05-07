import pytest

import ast

from verification.node_comparator import NodeComparator

from verification.field_filters import (
    cascade,
    ignore_docstrings,
    ignore_leading_arguments,
    ignore_leading_call_arguments,
    ignore_named_decorators,
    ignore_calls_to,
    ignore_first_n,
    unwrap_named_context_managers,
)


def test_cascade():
    def remove_last(lst):
        return lst[:-1]
    
    def reverse(lst):
        return lst[::-1]
    
    rem_rev = cascade(remove_last, reverse)
    
    assert rem_rev([1, 2, 3]) == [2, 1]
    
    rev_rem = cascade(reverse, remove_last)
    assert rev_rem([1, 2, 3]) == [3, 2]


class TestIgnoreDocstrings(object):
    
    @pytest.fixture
    def c(self):
        class MyNC(NodeComparator):
            def compare_FunctionDef(self, n1, n2):
                return self.generic_compare(n1, n2, filter_fields={
                    "body": ignore_docstrings,
                })
        
        return MyNC()
    
    def test_no_docstrings(self, c):
        n1 = ast.parse("def f():\n  return 123")
        n2 = ast.parse("def f(): return 123")
        n3 = ast.parse("def f():\n  return 321")
        
        assert c.compare(n1, n2) is True
        assert c.compare(n1, n3) is not True
    
    def test_one_has_docstrings(self, c):
        n1 = ast.parse('def f():\n  """foo"""\n  return 123')
        n2 = ast.parse("def f(): return 123")
        n3 = ast.parse('def f():\n  """foo"""\n  return 321')
        
        assert c.compare(n1, n2) is True
        assert c.compare(n1, n3) is not True
    
    def test_both_have_docstrings(self, c):
        n1 = ast.parse('def f():\n  """foo"""\n  return 123')
        n2 = ast.parse('def f():\n  """bar"""\n  return 123')
        n3 = ast.parse('def f():\n  """foo"""\n  return 321')
        
        assert c.compare(n1, n2) is True
        assert c.compare(n1, n3) is not True
    
    def test_multiple_docstrings(self, c):
        n1 = ast.parse('def f():\n  """foo"""\n  """bar"""\n  return 123')
        n2 = ast.parse('def f():\n  """bar"""\n  """baz"""\n  return 123')
        n3 = ast.parse('def f():\n  """foo"""\n  """bar"""\n  return 321')
        
        assert c.compare(n1, n2) is True
        assert c.compare(n1, n3) is not True


class TestIgnoreLeadingArguments(object):
    
    @pytest.fixture
    def c(self):
        class MyNC(NodeComparator):
            def compare_arguments(self, n1, n2):
                return self.generic_compare(n1, n2, filter_fields={
                    "args": ignore_leading_arguments("foo", "bar"),
                })
        
        return MyNC()
    
    def test_leading_arguments_not_present(self, c):
        n1 = ast.parse("def f(baz, qux):\n  return 123")
        n2 = ast.parse("def f(baz, qux): return 123")
        n3 = ast.parse("def f():\n  return 123")
        n4 = ast.parse("def f(quo):\n  return 123")
        
        assert c.compare(n1, n2) is True
        assert c.compare(n1, n3) is not True
        assert c.compare(n1, n4) is not True
    
    def test_not_all_leading_arguments_present(self, c):
        n1 = ast.parse("def f(baz, qux):\n  return 123")
        n2 = ast.parse("def f(foo, baz, qux):\n  return 123")
        n3 = ast.parse("def f(bar, baz, qux):\n  return 123")
        n4 = ast.parse("def f(bar, foo, baz, qux):\n  return 123")
        
        assert c.compare(n1, n2) is not True
        assert c.compare(n1, n3) is not True
        assert c.compare(n1, n4) is not True
    
    def test_leading_arguments_present(self, c):
        n1 = ast.parse("def f(baz, qux):\n  return 123")
        n2 = ast.parse("def f(foo, bar, baz, qux):\n  return 123")
        
        assert c.compare(n1, n1) is True
        assert c.compare(n1, n2) is True
        assert c.compare(n2, n1) is True


class TestIgnoreLeadingCallArguments(object):
    
    @pytest.fixture
    def c(self):
        class MyNC(NodeComparator):
            def compare_Call(self, n1, n2):
                return self.generic_compare(n1, n2, filter_fields={
                    "args": ignore_leading_call_arguments("foo", "bar"),
                })
        
        return MyNC()
    
    @pytest.mark.parametrize("case", [
        # Arguments are not names
        "f(1, 2, 3)",
        "f('foo')",
        "f('foo', 'bar')",
        "f(foo, 'bar')",
        "f('foo', bar)",
        # Not all arguments provided
        "f(foo, qux)",
        # Wrong order
        "f(bar, foo)",
    ])
    def test_leading_arguments_not_present(self, c, case):
        n1 = ast.parse(case)
        n2 = ast.parse("f()")
        
        assert c.compare(n1, n2) is not True
    
    def test_leading_arguments_not_present_but_match_anyway(self, c):
        n1 = ast.parse("f(baz, 123, qux)")
        n2 = ast.parse("f(baz,123,qux)")
        
        assert c.compare(n1, n2) is True
    
    def test_leading_arguments_present(self, c):
        n1 = ast.parse("f(baz, 123, qux)")
        n2 = ast.parse("f(foo, bar, baz, 123, qux)")
        
        assert c.compare(n1, n2) is True


class TestIgnoreNamedDecorators(object):
    
    @pytest.fixture
    def c(self):
        class MyNC(NodeComparator):
            def compare_FunctionDef(self, n1, n2):
                return self.generic_compare(n1, n2, filter_fields={
                    "decorator_list": ignore_named_decorators("foo.bar", "baz"),
                })
        
        return MyNC()
    
    def test_no_decorators(self, c):
        n1 = ast.parse("def f():\n  return 123")
        n2 = ast.parse("def f(): return 123")
        
        assert c.compare(n1, n2) is True
    
    def test_non_named_decorators(self, c):
        n1 = ast.parse("def f():\n  return 123")
        n2 = ast.parse("@qux\ndef f(): return 123")
        n3 = ast.parse("@quo\ndef f(): return 123")
        
        assert c.compare(n1, n2) is not True
        assert c.compare(n1, n3) is not True
        assert c.compare(n2, n3) is not True
    
    def test_named_decorators_only(self, c):
        n1 = ast.parse("def f():\n  return 123")
        n2 = ast.parse("@foo.bar\ndef f(): return 123")
        n3 = ast.parse("@baz\ndef f(): return 123")
        n4 = ast.parse("@foo.bar(1, 2, 3)\ndef f(): return 123")
        n5 = ast.parse("@baz(3, 2, 1)\ndef f(): return 123")
        n6 = ast.parse("@foo.bar\n@baz(1, 2, 3)\ndef f(): return 123")
        
        assert c.compare(n1, n2) is True
        assert c.compare(n1, n3) is True
        assert c.compare(n1, n4) is True
        assert c.compare(n1, n5) is True
        assert c.compare(n1, n6) is True
    
    def test_named_and_non_named(self, c):
        n1 = ast.parse("@ok\ndef f():\n  return 123")
        n2 = ast.parse("@foo.bar\n@ok\ndef f(): return 123")
        
        assert c.compare(n1, n2) is True


class TestIgnoreCallsTo(object):
    
    @pytest.fixture
    def c(self):
        class MyNC(NodeComparator):
            def compare_Module(self, n1, n2):
                return self.generic_compare(n1, n2, filter_fields={
                    "body": ignore_calls_to("foo.bar", "baz"),
                })
        
        return MyNC()
    
    def test_no_omitted_calls(self, c):
        n1 = ast.parse("foo()\nbar()\nqux()")
        n2 = ast.parse("nope()\nbar()\nqux()")
        
        assert c.compare(n1, n1) is True
        assert c.compare(n1, n2) is not True
    
    def test_ignore_omitted_calls(self, c):
        n1 = ast.parse("foo()\n1+2\nqux()")
        n2 = ast.parse("foo()\nfoo.bar()\n1+2\nbaz()\nqux()")
        n3 = ast.parse("foo()\n1-2\nqux()")
        
        assert c.compare(n1, n2) is True
        assert c.compare(n2, n3) is not True


class TestIgnoreFirstN(object):
    
    @pytest.fixture
    def c(self):
        class MyNC(NodeComparator):
            def compare_Module(self, n1, n2):
                return self.generic_compare(n1, n2, filter_fields={
                    "body": ignore_first_n(2),
                })
        
        return MyNC()
    
    def test_ignores_all_before_n(self, c):
        n1 = ast.parse("")
        n2 = ast.parse("1+1")
        n3 = ast.parse("1+1\n2+2")
        n4 = ast.parse("1+1\n2+2\n3+3")
        
        assert c.compare(n1, n2) is True
        assert c.compare(n1, n3) is True
        assert c.compare(n4, n4) is True
        
        assert c.compare(n1, n4) is not True
        assert c.compare(n2, n4) is not True
        assert c.compare(n3, n4) is not True


class TestUnwrapNamedContextManagers(object):
    
    @pytest.fixture
    def c(self):
        class MyNC(NodeComparator):
            def compare_Module(self, n1, n2):
                return self.generic_compare(n1, n2, filter_fields={
                    "body": unwrap_named_context_managers("foo", "bar", "qux.quo"),
                })
            
            def compare_With(self, n1, n2):
                return self.generic_compare(n1, n2, filter_fields={
                    "body": unwrap_named_context_managers("foo", "bar", "qux.quo"),
                })
        
        return MyNC()
    
    def test_no_context_manager(self, c):
        n1 = ast.parse("a + b")
        n2 = ast.parse("a+b")
        
        assert c.compare(n1, n2) is True
    
    def test_with_context_manager(self, c):
        n1 = ast.parse("1 + 2")
        n2 = ast.parse("with foo():\n  1 + 2")
        n3 = ast.parse("with bar():\n  1 + 2")
        n4 = ast.parse("with baz():\n  1 + 2")
        n5 = ast.parse("1 - 2")
        
        assert c.compare(n1, n2) is True
        assert c.compare(n1, n3) is True
        assert c.compare(n2, n3) is True
        
        assert c.compare(n1, n4) is not True
        assert c.compare(n2, n4) is not True
        
        assert c.compare(n1, n5) is not True
        assert c.compare(n2, n5) is not True
        assert c.compare(n3, n5) is not True
    
    def test_with_optional_vars(self, c):
        n1 = ast.parse("1 + 2")
        n2 = ast.parse("with foo() as baz:\n  1 + 2")
        n3 = ast.parse("1 - 2")
        
        assert c.compare(n1, n2) is True
        assert c.compare(n3, n2) is not True
    
    def test_with_nested_context_managers(self, c):
        n1 = ast.parse("1 + 2")
        n2 = ast.parse("with foo(), bar():\n  1 + 2")
        n3 = ast.parse("with foo():\n  with bar():\n    1 + 2")
        n4 = ast.parse("1 - 2")
        
        assert c.compare(n1, n2) is True
        assert c.compare(n1, n3) is True
        assert c.compare(n2, n3) is True
        
        assert c.compare(n2, n4) is not True
        assert c.compare(n3, n4) is not True
    
    def test_with_multi_line_block(self, c):
        n1 = ast.parse("1 + 2\n3 + 4")
        n2 = ast.parse("with foo():\n  1 + 2\n  3 + 4")
        n3 = ast.parse("1 - 2\n3 - 4")
        
        assert c.compare(n1, n2) is True
        assert c.compare(n3, n2) is not True
    
    def test_with_attribute_named_function(self, c):
        n1 = ast.parse("1 + 2\n3 + 4")
        n2 = ast.parse("with qux.quo():\n  1 + 2\n  3 + 4")
        n3 = ast.parse("1 - 2\n3 - 4")
        
        assert c.compare(n1, n2) is True
        assert c.compare(n3, n2) is not True
