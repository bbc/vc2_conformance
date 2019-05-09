"""
:py:mod:`verification.node_comparator`: AST Comparison Framework
================================================================

.. py:currentmodule:: verification.node_comparator

The :py:class:`NodeComparator` class is intended to form the basis of
comparison routines which allow controlled differences between two ASTs to be
ignored.

For exapmle, the following can be used to compare two ASTs, ignoring docstrings
at the start of functions::

    from itertools import dropwhile
    
    from verification.node_comparator import NodeComparator

    class SameExceptDocstrings(NodeComparator):
        
        def compare_FunctionDef(self, n1, n2):
            def without_docstrings(body):
                return dropwhile(
                    lambda e: isinstance(e, ast.Expr) and isinstance(e.value, ast.Str),
                    body,
                )
            
            return self.generic_compare(n1, n2, filter_fields={"body": without_docstrings})

This can then be used like so::

    >>> func_1 = "def func(a, b):\\n    '''Add a and b'''\\n    return a + b"
    >>> func_2 = "def func(a, b):\\n    return a + b"
    
    >>> import ast
    >>> c = SameExceptDocstrings()
    >>> c.compare(ast.parse(func_1), ast.parse(func_2))
    True

:py:class:`NodeComparator` API
------------------------------

.. autoclass:: NodeComparator
    :members:

:py:class:`NodesDiffer` types
-----------------------------

.. autoclass:: NodesDiffer

.. autoclass:: NodeTypesDiffer

.. autoclass:: NodeFieldsDiffer

.. autoclass:: NodeFieldLengthsDiffer

.. autoclass:: NodeListFieldsDiffer

"""

import ast


class NodeComparator(object):
    """
    A :py:class:`ast.AST` visitor object (similar to
    :py:class:`ast.NodeVisitor` which simultaneously walks two ASTs, testing
    them for equivalence.
    
    The :py:meth:`compare` method of instances of this class may be used to
    recursively compare two AST nodes.
    """
    
    def __init__(self):
        # A stack of ast.AST nodes which are currently being visited.
        self._node_stack = []
    
    def get_row_col(self):
        """
        Find the current row and column offsets for the tokens currently being
        compared with :py:func:`compare`.
        """
        n1_lineno = None
        n1_col_offset = None
        for n1, _ in reversed(self._node_stack):
            if hasattr(n1, "lineno") and hasattr(n1, "col_offset"):
                n1_lineno = n1.lineno
                n1_col_offset = n1.col_offset
                break
        
        n2_lineno = None
        n2_col_offset = None
        for _, n2 in reversed(self._node_stack):
            if hasattr(n2, "lineno") and hasattr(n2, "col_offset"):
                n2_lineno = n2.lineno
                n2_col_offset = n2.col_offset
                break
        
        return ((n1_lineno, n1_col_offset), (n2_lineno, n2_col_offset))
    
    def compare(self, n1, n2):
        """
        Recursively compare two AST nodes.
        
        If ``n1`` has the type named N1Type and ``n2`` has the type named
        N2Type, this function will try to call one of the following methods:
        
        * ``compare_N1Type`` (if N1Type is the same as N2Type)
        * ``compare_N1Type_N2_type``
        * ``compare_N1Type_ANY``
        * ``compare_ANY_N2Type``
        * ``generic_compare``
        
        The first method to be found will be called and its return value
        returned. The various ``compare_*`` methods may be overridden by
        subclasses of :py:class:`NodeComparator` and should implement the same
        interface as this method.
        
        Parameters
        ==========
        n1, n2 : :py:class:`ast.AST`
            The nodes to compare
        
        Returns
        =======
        result : True or :py:class:`NodesDiffer`
            True if the ASTs are equal and :py:class:`NodesDiffer` (which is
            faslsey) otherwise.
        """
        try:
            self._node_stack.append((n1, n2))
            
            compare_same = getattr(self, "compare_{}".format(type(n1).__name__), None)
            if type(n1) is type(n2) and compare_same is not None:
                return compare_same(n1, n2)
            
            compare_n1_n2 = getattr(self, "compare_{}_{}".format(
                type(n1).__name__,
                type(n2).__name__,
            ), None)
            if compare_n1_n2 is not None:
                return compare_n1_n2(n1, n2)
            
            compare_n1_any = getattr(self, "compare_{}_ANY".format(type(n1).__name__), None)
            if compare_n1_any is not None:
                return compare_n1_any(n1, n2)
            
            compare_any_n2 = getattr(self, "compare_ANY_{}".format(type(n2).__name__), None)
            if compare_any_n2 is not None:
                return compare_any_n2(n1, n2)
            
            return self.generic_compare(n1, n2)
        finally:
            self._node_stack.pop()
    
    def generic_compare(self, n1, n2, ignore_fields=[], filter_fields={}):
        """
        Base implementation of recurisive comparison of two AST nodes.
        
        Compare the type of AST node and recursively compares field values.
        Recursion is via calls to :py:meth:`compare`.
        
        Options are provided for ignoring differences in certain fields of the
        passed AST nodes. Authors of custom ``compare_*`` methods may wish to
        use these arguments when calling :py:meth:`generic_compare` to allow
        certain fields to differ while still reporting equality.
        
        Parameters
        ==========
        n1, n2 : :py:class:`ast.AST`
            The nodes to compare
        ignore_fields : [str, ...]
            A list of field names to ignore while comparign the AST nodes.
        filter_fields : {fieldname: fn or (fn, fn) ...}
            When a list-containing field is encountered, functions may be
            provided for pre-filtering the entries of the lists being compared.
            For example, one might supply a filtering function which removes
            docstrings from function bodies.
            
            Entries in this dictionary may be either:
            
            * Functions which are passed the list contained by the field and
              should return a new list which should be compared (not modifying
              the one provided).
            * A pair of functions like the one above but the first will be used
              for filtering n1's field and the second for n2's field. Either
              may be None if no filtering is to take place for one of the
              nodes.
        
        Returns
        =======
        result : True or :py:class:`NodesDiffer`
            True if the ASTs are equal and :py:class:`NodesDiffer` (which is
            faslsey) otherwise.
        """
        if type(n1) is not type(n2):
            n1_row_col, n2_row_col = self.get_row_col()
            return NodeTypesDiffer(n1, n1_row_col, n2, n2_row_col)
        
        for field in n1._fields:
            if field in ignore_fields:
                continue
            
            v1 = getattr(n1, field)
            v2 = getattr(n2, field)
            
            if isinstance(v1, ast.AST) and isinstance(v2, ast.AST):
                match = self.compare(v1, v2)
                if not match:
                    return match
            elif isinstance(v1, list) and isinstance(v2, list):
                if field in filter_fields:
                    fns = filter_fields[field]
                    if callable(fns):
                        fn1 = fn2 = fns
                    else:
                        fn1, fn2 = fns
                    if fn1 is not None:
                        v1 = list(fn1(v1))
                    if fn2 is not None:
                        v2 = list(fn2(v2))
                
                if len(v1) != len(v2):
                    # Give line number of last child element so that when
                    # printing up-to-and-including the reported numbers the
                    # complete set of elements are visible
                    n1_row_col, n2_row_col = self.get_row_col()
                    if len(v1) and hasattr(v1[-1], "lineno") and hasattr(v1[-1], "col_offset"):
                        n1_row_col = (v1[-1].lineno, v1[-1].col_offset)
                    if len(v2) and hasattr(v2[-1], "lineno") and hasattr(v2[-1], "col_offset"):
                        n2_row_col = (v2[-1].lineno, v2[-1].col_offset)
                    return NodeFieldLengthsDiffer(
                        n1, n1_row_col,
                        n2, n2_row_col,
                        field,
                        v1, v2,
                    )
                else:
                    for i, (e1, e2) in enumerate(zip(v1, v2)):
                        if isinstance(e1, ast.AST) and isinstance(e2, ast.AST):
                            match = self.compare(e1, e2)
                            if not match:
                                return match
                        else:
                            if e1 != e2:
                                n1_row_col, n2_row_col = self.get_row_col()
                                return NodeListFieldsDiffer(
                                    n1, n1_row_col,
                                    n2, n2_row_col,
                                    field, i,
                                    v1, v2,
                                )
            else:
                if v1 != v2:
                    n1_row_col, n2_row_col = self.get_row_col()
                    return NodeFieldsDiffer(n1, n1_row_col, n2, n2_row_col, field)
        
        return True


class NodesDiffer(object):
    """
    A result from :py:class:`NodeComparator` indicating that two ASTs differ.
    
    This object is 'falsy' (i.e. calling :py:func:`bool` on a
    :py:class:`NodeComparator` instance returns False).
    
    Attributes
    ==========
    n1, n2 : :py:class:`ast.AST`
        The two ASTs being compared.
    n1_row_col, n2_row_col : (row, col) or (None, None)
        The row and column of the 'n1' and 'n2' tokens, or the values for the
        row and column of the nearest token with a known position.
    reason : str or None
        A string describing how the two nodes differ with a human-readable
        message.
    """
    
    def __init__(self, n1, n1_row_col, n2, n2_row_col, reason=None):
        self.n1 = n1
        self.n1_row_col = n1_row_col
        self.n2 = n2
        self.n2_row_col = n2_row_col
        self.reason = reason
    
    def __bool__(self):  # Py 3.x
        return False
    
    def __nonzero__(self):  # Py 2.x
        return False
    
    def __repr__(self):
        return "<{}{}>".format(
            type(self).__name__,
            "" if self.reason is None else ": {}".format(self.reason),
        )


class NodeTypesDiffer(NodesDiffer):
    """
    A pair of nodes have different types.
    """
    
    def __init__(self, n1, n1_row_col, n2, n2_row_col):
        super(NodeTypesDiffer, self).__init__(
            n1, n1_row_col, n2, n2_row_col,
            "Nodes have differing types ({} and {})".format(
                type(n1).__name__,
                type(n2).__name__,
            ),
        )


class NodeFieldsDiffer(NodesDiffer):
    """
    A pair of nodes differ in the value of a particular field.
    
    Attributes
    ==========
    field : str
        The field name where the AST nodes differ.
    """
    
    def __init__(self, n1, n1_row_col, n2, n2_row_col, field):
        self.field = field
        
        super(NodeFieldsDiffer, self).__init__(
            n1, n1_row_col, n2, n2_row_col,
            "Node {!r} fields differ: n1.{} == {!r} and n2.{} == {!r}".format(
                field,
                field,
                getattr(n1, field),
                field,
                getattr(n2, field),
            ),
        )


class NodeFieldLengthsDiffer(NodesDiffer):
    """
    A pair of nodes differ in the length of the list of values in a particular
    field.
    
    Attributes
    ==========
    field : str
        The field name where the AST nodes differ.
    v1, v2 : list
        The values of the fields (after any filtering has taken place).
    """
    
    def __init__(self, n1, n1_row_col, n2, n2_row_col, field, v1, v2):
        self.field = field
        self.v1 = v1
        self.v2 = v2
        
        super(NodeFieldLengthsDiffer, self).__init__(
            n1, n1_row_col, n2, n2_row_col,
            "Node {!r} fields have different lengths ({} and {})".format(
                self.field,
                len(self.v1),
                len(self.v2),
            ),
        )


class NodeListFieldsDiffer(NodesDiffer):
    """
    A pair of nodes differ in the value of a list field entry.
    
    Attributes
    ==========
    field : str
        The field name where the AST nodes differ.
    index : int
        The index of the value in the v1 and v2 lists.
    v1, v2 : list
        The values of the fields (after any filtering has taken place).
    """
    
    def __init__(self, n1, n1_row_col, n2, n2_row_col, field, index, v1, v2):
        self.field = field
        self.index = index
        self.v1 = v1
        self.v2 = v2
        
        super(NodeListFieldsDiffer, self).__init__(
            n1, n1_row_col, n2, n2_row_col,
            "Node {!r} fields have a differing entry at index {} ({!r} and {!r})".format(
                self.field,
                self.index,
                self.v1[self.index],
                self.v2[self.index],
            ),
        )
