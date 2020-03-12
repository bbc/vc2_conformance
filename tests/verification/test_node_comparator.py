import pytest

from verification.node_comparator import NodeComparator, NodesDiffer

import ast


class TestEquality(object):
    
    def test_types_differ(self):
        n1 = ast.parse("a + b + c")
        n2 = ast.parse("(\\\n      a+b-c\\\n)")
        
        match = NodeComparator().compare(n1, n2)
        assert match.reason == "Nodes have differing types (Add and Sub)"
        # In Python 3.8, the Add and Sub nodes ceased to have lineno/col_offset
        # attributes meaning that we instead can only get the position of the
        # containing BinOp.
        #                    Python v<3.8   v>=3.8
        assert match.n1_row_col in ((1, 6), (1, 0))
        assert match.n2_row_col in ((2, 9), (2, 6))
    
    def test_non_list_field_differs(self):
        n1 = ast.parse("abc")
        n2 = ast.parse("cba")
        
        match = NodeComparator().compare(n1, n2)
        assert match.reason == "Node 'id' fields differ: n1.id == 'abc' and n2.id == 'cba'"
        assert match.field == "id"
        assert match.n1_row_col == (1, 0)
        assert match.n2_row_col == (1, 0)
    
    def test_list_field_length_differs(self):
        n1 = ast.parse("foo(a,\nb,\nc)")
        n2 = ast.parse("foo(a,\nb)")
        
        match = NodeComparator().compare(n1, n2)
        assert match.reason == "Node 'args' fields have different lengths (3 and 2)"
        assert match.field == "args"
        assert len(match.v1) == 3
        assert len(match.v2) == 2
        # Should point to line with last element on it
        assert match.n1_row_col == (3, 0)
        assert match.n2_row_col == (2, 0)
    
    def test_list_field_value_differs(self):
        # NB: The current Python grammar does not include a node with a list of
        # non-AST element entries. Since it may in the future, this mock-driven
        # test checks behaviour in this case.
        class MockASTNode(ast.AST):
            _fields = ["somelist"]
            
            def __init__(self, somelist):
                self.somelist = somelist
        
        n1 = MockASTNode([1, 2, 3])
        n2 = MockASTNode([1, 123, 3])
        
        match = NodeComparator().compare(n1, n2)
        assert match.reason == "Node 'somelist' fields have a differing entry at index 1 (2 and 123)"
        assert match.field == "somelist"
        assert match.index == 1
        assert match.v1 == [1, 2, 3]
        assert match.v2 == [1, 123, 3]
        assert match.n1_row_col == (None, None)
        assert match.n2_row_col == (None, None)
    
    def test_equal_simple(self):
        n1 = ast.parse("a + (b + c)")
        n2 = ast.parse("a+(b+c)")
        assert NodeComparator().compare(n1, n2) is True
    
    def test_equal_less_simple(self):
        n1 = ast.parse("def foo(bar='baz'): return 123**321")
        n2 = ast.parse('def foo(bar="baz"):\n    return 123**321')
        assert NodeComparator().compare(n1, n2) is True


class TestOverides(object):
    
    def test_types_same(self):
        # A version which allows names to differ
        class MyNC(NodeComparator):
            def compare_Name(self, n1, n2):
                return True
        
        n1 = ast.parse("a + b - c")
        n2 = ast.parse("ay + bee - see")  # Different names
        n3 = ast.parse("a - b + c")  # Different operands
        
        c = MyNC()
        assert c.compare(n1, n2) is True
        assert c.compare(n1, n3) is not True
    
    def test_different_types(self):
        # A version which allows names to be swapped for numbers (but not the
        # other way around)
        class MyNC(NodeComparator):
            # Python v<3.8
            def compare_Name_Num(self, n1, n2):
                return self.compare_Name_Constant(n1, n2)
            
            # Python v>=3.8
            def compare_Name_Constant(self, n1, n2):
                return True
        
        n1 = ast.parse("a + b - c")
        n2 = ast.parse("1 + 2 - 3")  # Numbers, not names
        n3 = ast.parse("a - b + c")  # Different operands
        
        c = MyNC()
        assert c.compare(n1, n2) is True
        assert c.compare(n2, n1) is not True
        assert c.compare(n1, n3) is not True
    
    def test_wildcard_rhs(self):
        # A version which allows names to be swapped for anything
        class MyNC(NodeComparator):
            def compare_Name_ANY(self, n1, n2):
                return True
        
        n1 = ast.parse("a + b - c")
        n2 = ast.parse("ay + bee - see")  # Different names
        n3 = ast.parse("1 + 2 - 3")  # Numbers, not names
        n4 = ast.parse("(1+1) + (2+2) - (3+3)")  # Expressions, not names
        n5 = ast.parse("a - b + c")  # Different operands
        
        c = MyNC()
        assert c.compare(n1, n2) is True
        assert c.compare(n1, n3) is True
        assert c.compare(n1, n4) is True
        
        assert c.compare(n3, n1) is not True
        assert c.compare(n4, n1) is not True
        
        assert c.compare(n1, n5) is not True
    
    def test_wildcard_lhs(self):
        # A version which allows anything to be swapped out for a name
        class MyNC(NodeComparator):
            def compare_ANY_Name(self, n1, n2):
                return True
        
        n1 = ast.parse("a + b - c")
        n2 = ast.parse("ay + bee - see")  # Different names
        n3 = ast.parse("1 + 2 - 3")  # Numbers, not names
        n4 = ast.parse("(1+1) + (2+2) - (3+3)")  # Expressions, not names
        n5 = ast.parse("a - b + c")  # Different operands
        
        c = MyNC()
        assert c.compare(n2, n1) is True
        assert c.compare(n3, n1) is True
        assert c.compare(n4, n1) is True
        
        assert c.compare(n1, n3) is not True
        assert c.compare(n1, n4) is not True
        
        assert c.compare(n1, n5) is not True


class TestGenericCompare(object):
    
    def test_ignore_fields(self):
        c = NodeComparator()
        
        value = ast.Name("foo", ast.Load)
        a1 = ast.Attribute(value, "bar", ast.Load)
        a2 = ast.Attribute(value, "bar", ast.Del)
        
        assert c.generic_compare(a1, a2) is not True
        assert c.generic_compare(a1, a2, ignore_fields=["ctx"]) is True
    
    def test_filter_fields_one_function(self):
        c = NodeComparator()
        
        n1 = ast.Name("foo", ast.Store)
        n2 = ast.Name("bar", ast.Store)
        n3 = ast.Name("baz", ast.Store)
        
        n = ast.Name("qux", ast.Load)
        
        a1 = ast.Assign([n1, n2, n3], n)
        a2 = ast.Assign([n1, n2, n1], n)
        
        def drop_last(lst):
            return lst[:-1]
        
        assert c.generic_compare(a1, a2) is not True
        assert c.generic_compare(a1, a2, filter_fields={"targets": drop_last}) is True
    
    def test_filter_fields_two_functions(self):
        c = NodeComparator()
        
        n1 = ast.Name("foo", ast.Store)
        n2 = ast.Name("bar", ast.Store)
        n3 = ast.Name("baz", ast.Store)
        
        n = ast.Name("qux", ast.Load)
        
        a1 = ast.Assign([n1, n2, n3], n)
        a2 = ast.Assign([n2, n1], n)
        
        def drop_last(lst):
            return lst[:-1]
        
        def reverse(lst):
            return lst[::-1]
        
        assert c.generic_compare(a1, a2) is not True
        assert c.generic_compare(a1, a2, filter_fields={"targets": (drop_last, reverse)}) is True
    
    @pytest.mark.parametrize("none_first", [True, False])
    def test_filter_fields_one_none(self, none_first):
        c = NodeComparator()
        
        n1 = ast.Name("foo", ast.Store)
        n2 = ast.Name("bar", ast.Store)
        n3 = ast.Name("baz", ast.Store)
        
        n = ast.Name("qux", ast.Load)
        
        a1 = ast.Assign([n1, n2, n3], n)
        a2 = ast.Assign([n3, n2, n1], n)
        
        def reverse(lst):
            return lst[::-1]
        
        assert c.generic_compare(a1, a2) is not True
        assert c.generic_compare(a1, a2, filter_fields={
            "targets": (None if none_first else reverse,
                        reverse if none_first else None),
        }) is True
