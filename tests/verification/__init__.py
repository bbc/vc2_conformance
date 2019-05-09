"""
``tests/``:py:mod:`verification`: Automated Static Code Verification
====================================================================

.. py:currentmodule:: verification

This module (and embedded tests) implement automatic checks that the code in
:py:mod:`vc2_conformance` matches the pseudocode definitions in the VC-2
specification.

The ``tests/verification/test_equivalence.py`` test script (which is part of
the normal Pytest test suite) automatically finds functions in the
:py:mod:`vc2_conformance` codebase (using :py:mod:`vc2_conformance.metadata`)
and checks they match the equivalent function in the VC-2 specification (which
are copied out verbatim in ``tests/verification/reference_pseudocode.py``).

In some cases, a limited set of well-defined differences are allowed to exist
between the specification and the code used in :py:mod:`vc2_conformance`. For
example, docstrings need not match and in some cases, extra changes may be
allowed to facilitate, e.g. bitstream deserialisation. The specific comparator
used depends on the ``deviation`` parameter given in the metadata as follows:

* ``deviation=None``: :py:class:`verification.comparators.Identical`
* ``deviation="serdes"``: :py:class:`verification.comparators.SerdesChangesOnly`

Functions marked with all other ``deviation`` values will not undergo automatic
verification.

In some cases it is necessary for an implementation to differ arbitrarily from
the standard. For example, additional type checks may be added or certain
actions may be disabled (e.g. picture decoding during bitstream
deserialisation). Such deviations must be marked by special 'amendment
comments' which start with two or more ``#`` characters. For example::

    def example_function(a, b):
        # The following lines are not part of the standard and so must be
        # ignored when checking for equivalence
        ## Begin not in spec
        if b <= 0:
            raise Exception("'b' cannot be zero or negative!")
        ## End not in spec
        
        # For single-line snippets which are not in the standard you can use
        # the following end-of-line amendment comment
        assert b > 0  ## Not in spec
        
        # The following code is part of the standard but is disabled in this
        # example. Even though it is commented out, it will still be checked
        # against the standard. If the standard changes this check ensures that
        # the maintainer must revisit the commented-out code and re-evaluate
        # the suitability of any amendments made.
        ### if do_something(a):
        ###     do_something_else(b)
        
        return a / b

More details of the amendment comment syntax can be found in
:py:mod:`verification.amendment_comments`.


Internals
---------

This module does *not* attempt to perform general purpose functional
equivalence checking -- a known uncomputable problem. Instead, comparisons are
made at the Abstract Syntax Tree (AST) level. By performing checks at this
level semantically insignificant differences (e.g. whitespace and comments) are
ignored while all other changes are robustly identified. The Python built-in
:py:mod:`ast` module is used to produce ASTs ensuring complete support for all
Python language features.

To compare ASTs, this module provides the
:py:class:`verification.node_comparator.NodeComparator`.  Instances of this
class can be used to compare pairs of ASTs and report differences between them.

The subclasses in :py:mod:`verification.comparators` are similar but allow
certain well-defined differences to exist between ASTs. As an example,
:py:class:`verification.comparators.SerdesChangesOnly` will allow calls to the
``read_*`` functions to be swapped for their equivalent
:py:class:`vc2_conformance.bitstream.serdes.SerDes` method calls with otherwise
identical arguments.

To allow differences between function implementations and the specification,
functions are pre-processed according to the amendment comment syntax described
above. This preprocessing step is implemented in
:py:mod:`verification.amendment_comments` and uses the built-in Python
:py:mod:`tokenize` module to ensure correct interoperability with all other
Python language features.

Finally the :py:mod:`verification.compare` module provides the
:py:func:`~verification.compare.compare_functions` function which ties all of
the above components together and produces human-readable reports of
differences between functions.

All of the above functionality is tested by the other ``test_*.py`` test
scripts in this module's directory.


.. automodule::
    verification.node_comparator

.. automodule::
    verification.comparators

.. automodule::
    verification.amendment_comments

.. automodule::
    verification.compare
"""
