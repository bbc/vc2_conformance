import ast

from verification.ast_utils import (
    name_to_str,
    argument_to_str,
    with_to_items,
)


class TestNameToStr(object):
    
    def test_name(self):
        name = ast.Name("foo", ast.Load)
        assert name_to_str(name) == "foo"
    
    def test_attribute(self):
        value = ast.Name("foo", ast.Load)
        attr = ast.Attribute(value, "bar", ast.Load)
        assert name_to_str(attr) == "foo.bar"
    
    def test_str_subscript(self):
        value = ast.Name("foo", ast.Load)
        slice = ast.Index(ast.Str("bar"))
        subscript = ast.Subscript(value, slice, ast.Load)
        assert name_to_str(subscript) == "foo['bar']"
    
    def test_num_subscript(self):
        value = ast.Name("foo", ast.Load)
        slice = ast.Index(ast.Num(123))
        subscript = ast.Subscript(value, slice, ast.Load)
        assert name_to_str(subscript) == "foo[123]"
    
    def test_unsupported_subscript(self):
        # Just don't crash...
        value = ast.Name("foo", ast.Load)
        slice = ast.Index(ast.Name("bar", ast.Load))
        subscript = ast.Subscript(value, slice, ast.Load)
        assert isinstance(name_to_str(subscript), str)
    
    def test_unknown(self):
        # Just don't crash...
        value = ast.Num(123)
        assert isinstance(name_to_str(value), str)


def test_argument_to_str():
    arg_names = []
    class MyNV(ast.NodeVisitor):
        def visit_arguments(self, node):
            arg_names.append(list(map(argument_to_str, node.args)))
            self.generic_visit(node)
    v = MyNV()
    v.visit(ast.parse("def foo(bar, baz): return None"))
    
    assert arg_names == [["bar", "baz"]]


def test_with_to_items():
    with_items = []
    class MyNV(ast.NodeVisitor):
        def visit_With(self, node):
            with_items.extend(with_to_items(node))
            self.generic_visit(node)
    v = MyNV()
    v.visit(ast.parse("with foo() as bar, baz():\n  pass"))
    
    assert len(with_items) == 2
    
    assert isinstance(with_items[0][0], ast.Call)
    assert name_to_str(with_items[0][0].func) == "foo"
    assert isinstance(with_items[0][1], ast.Name)
    assert name_to_str(with_items[0][1]) == "bar"
    
    assert isinstance(with_items[1][0], ast.Call)
    assert name_to_str(with_items[1][0].func) == "baz"
    assert with_items[1][1] is None
