import pytest

import re
import sys
import inspect

from verification.compare import (
    compare_sources,
    compare_functions,
    format_summary,
    format_detailed_summary,
    ComparisonError,
    Difference,
)

from verification.comparators import Identical


################################################################################
# Example functions for use in the tests below
################################################################################

def f(a, b):
    """Example function"""
    return a + b
f1 = f

def f(a, b):
    """Same as f above"""
    a += 1  ## Not in spec
    return a + b
f2 = f

def f(a, b):
    """
    Different from f above!
    """
    return a - b
f3 = f

def f(a, b):
    ## Invalid amendment comment
    return a + b
f4 = f

def f5(a, b):
    """
    Function name isn't f1
    """
    return a - b

################################################################################

# Filename of this script (not its *.pyc file)
_test_script_filename = inspect.getsourcefile(sys.modules[__name__])

class TestFormatSummary(object):
    
    @pytest.fixture(params=[ComparisonError, Difference])
    def T(self, request):
        return request.param
    
    def test_just_message(self, T):
        assert format_summary(T("foobar")) == "foobar"
    
    def test_just_line_number(self, T):
        assert format_summary(T(
            "foobar",
            ref_row=123,
        )) == "foobar (in reference code, line 123)"
        assert format_summary(T(
            "foobar",
            imp_row=123,
        )) == "foobar (in implementation code, line 123)"
    
    def test_just_line_and_column_number(self, T):
        assert format_summary(T(
            "foobar",
            ref_row=123,
            ref_col=10,
        )) == "foobar (in reference code, line 123 col 10)"
        
        assert format_summary(T(
            "foobar",
            imp_row=123,
            imp_col=10,
        )) == "foobar (in implementation code, line 123 col 10)"

    def test_full_reference(self, T):
        def f():
            pass
        
        assert format_summary(T(
            "foobar",
            ref_row=1000,
            ref_col=10,
            ref_func=f,
        )) == "foobar (in reference code, line {} col 10 of {})".format(
            1000 + inspect.getsourcelines(f)[1],
            _test_script_filename,
        )
        
        assert format_summary(T(
            "foobar",
            imp_row=1000,
            imp_col=10,
            imp_func=f,
        )) == "foobar (in implementation code, line {} col 10 of {})".format(
            1000 + inspect.getsourcelines(f)[1],
            _test_script_filename,
        )
    
    def test_both_functions_at_once(self, T):
        assert format_summary(T(
            "foobar",
            ref_row=123,
            imp_row=321,
        )) == "foobar (in reference code, line 123 and implementation code, line 321)"


class TestFormatDetailedSummary(object):
    
    @pytest.fixture(params=[ComparisonError, Difference])
    def T(self, request):
        return request.param
    
    def test_fallback_without_functions(self, T):
        assert format_detailed_summary(T("foobar", ref_row=2)) ==(
            "foobar (in reference code, line 2)"
        )
    
    def test_just_message(self, T):
        assert format_detailed_summary(T("foobar", ref_func=f1, imp_func=f2)) == "foobar"
    
    def test_source_no_col(self, T):
        assert format_detailed_summary(T(
            "Different operators",
            ref_row=3,
            imp_row=5,
            ref_func=f1,
            imp_func=f3,
        )) == (
            'Different operators\n'
            '\n'
            'Reference source:\n'
            '    def f(a, b):\n'
            '        """Example function"""\n'
            '        return a + b\n'
            '--------^\n'
            '{file}:25\n'
            '\n'
            'Implementation source:\n'
            '    def f(a, b):\n'
            '        """\n'
            '        Different from f above!\n'
            '        """\n'
            '        return a - b\n'
            '--------^\n'
            '{file}:38'
        ).format(file=_test_script_filename)
    
    def test_source_with_col(self, T):
        assert format_detailed_summary(T(
            "Different operators",
            ref_row=3,
            ref_col=11,
            imp_row=5,
            imp_col=11,
            ref_func=f1,
            imp_func=f3,
        )) == (
            'Different operators\n'
            '\n'
            'Reference source:\n'
            '    def f(a, b):\n'
            '        """Example function"""\n'
            '        return a + b\n'
            '---------------^\n'
            '{file}:25 (col 11)\n'
            '\n'
            'Implementation source:\n'
            '    def f(a, b):\n'
            '        """\n'
            '        Different from f above!\n'
            '        """\n'
            '        return a - b\n'
            '---------------^\n'
            '{file}:38 (col 11)'
        ).format(file=_test_script_filename)


class TestCompareSources(object):
    
    def test_same(self):
        assert compare_sources(
            (
                "def foo(a, b, c):\n"
                "   return a + b + c\n"
            ),
            (
                "def foo(a,b,c): return a+b+c\n"
            ),
            Identical(),
        ) is True
    
    def test_amendment_makes_same(self):
        assert compare_sources(
            (
                "def foo(a, b, c):\n"
                "   return a + b + c\n"
            ),
            (
                "def foo(a, b, c):\n"
                "   print(a, b, c)  ## Not in spec\n"
                "   return a + b + c\n"
            ),
            Identical(),
        ) is True
    
    def test_ammendments_not_applied_to_reference(self):
        assert compare_sources(
            (
                "def foo(a, b, c):\n"
                "   print(a, b, c)  ## Not in spec\n"
                "   return a + b + c\n"
            ),
            (
                "def foo(a, b, c):\n"
                "   return a + b + c\n"
            ),
            Identical(),
        ) is not True
    
    def test_differing_node_types(self):
        assert format_summary(compare_sources(
            (
                "def foo(a, b):\n"
                "   return a + b\n"
            ),
            (
                "def foo(a, b): return a - b\n"
            ),
            Identical(),
        )) == (
            "Mismatched Add vs. Sub (in reference code, line 2 col 10 and implementation code, line 1 col 22)"
        )
    
    def test_differing_field_values(self):
        assert format_summary(compare_sources("a + b", "a+cde", Identical())) == (
            "Different id values (in reference code, line 1 col 4 and implementation code, line 1 col 2)"
        )
    
    def test_differing_field_lengths(self):
        assert format_summary(compare_sources("foo(a, b)", "foo(a, b, c, d)", Identical())) == (
            "2 extra values in implementation's args (in reference code, line 1 col 7 and implementation code, line 1 col 13)"
        )
        assert format_summary(compare_sources("foo(a, b, c)", "foo(a, b)", Identical())) == (
            "1 extra value in reference's args (in reference code, line 1 col 10 and implementation code, line 1 col 7)"
        )
    
    def test_tokenisation_errors(self):
        # Can only occur in implementation code since these come from
        # undo_amendments
        with pytest.raises(ComparisonError) as exc_info:
            compare_sources("", "[", Identical())
        assert format_summary(exc_info.value) == (
            "EOF in multi-line statement (in implementation code, line 2 col 0)"
        )
    
    def test_syntax_errors(self):
        # NB: Syntax error reported column numbers differ depending on the
        # python interpreter used.
        with pytest.raises(ComparisonError) as exc_info:
            compare_sources("1 +/", "", Identical())
        assert re.match(
            r"invalid syntax \(in reference code, line 1 col [34]\)",
            format_summary(exc_info.value),
        ) is not None
        
        with pytest.raises(ComparisonError) as exc_info:
            compare_sources("", "1 +/", Identical())
        assert re.match(
            r"invalid syntax \(in implementation code, line 1 col [34]\)",
            format_summary(exc_info.value),
        ) is not None
    
    def test_bad_amendment_comment(self):
        # Can only occur in implementation code since these come from
        # undo_amendments
        with pytest.raises(ComparisonError) as exc_info:
            compare_sources("", "## Foobar", Identical())
        assert format_summary(exc_info.value) == (
            "Unrecognised amendment comment '## Foobar' (in implementation code, line 1 col 0)"
        )
    
    def test_unmatched_not_in_spec_block(self):
        # Can only occur in implementation code since these come from
        # undo_amendments
        with pytest.raises(ComparisonError) as exc_info:
            compare_sources("", "## End not in spec", Identical())
        assert format_summary(exc_info.value) == (
            "No matching '## Begin not in spec' (in implementation code, line 1)"
        )
    
    def test_unclosed_not_in_spec_block(self):
        # Can only occur in implementation code since these come from
        # undo_amendments
        with pytest.raises(ComparisonError) as exc_info:
            compare_sources("", "## Begin not in spec", Identical())
        assert format_summary(exc_info.value) == (
            "'## Begin not in spec' block not closed (in implementation code, line 1)"
        )


class TestCompareFunctions(object):
    
    def test_same(self):
        assert compare_functions(f1, f2, Identical()) is True
    
    def test_different(self):
        match = compare_functions(f1, f3, Identical())
        
        assert match is not True
        
        assert match.message == "Mismatched Add vs. Sub"
        
        assert match.ref_row == 3
        assert match.ref_col == 11
        
        assert match.imp_row == 5
        assert match.imp_col == 11
        
        assert match.ref_func is f1
        assert match.imp_func is f3
    
    def test_parse_error(self):
        with pytest.raises(ComparisonError) as exc_info:
            compare_functions(f1, f4, Identical())
        
        assert exc_info.value.message == "Unrecognised amendment comment '## Invalid amendment comment'"
        
        assert exc_info.value.ref_row is None
        assert exc_info.value.ref_col is None
        
        assert exc_info.value.imp_row == 2
        assert exc_info.value.imp_col == 4
        
        assert exc_info.value.ref_func is f1
        assert exc_info.value.imp_func is f4
