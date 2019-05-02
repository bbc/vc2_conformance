"""
Automated Static Code Verification
==================================

The 'verification' module (and embedded tests) implement automatic static
verification that the logic implemented in :py:mod:`vc2_conformance` matches
the pseudocode definitions in the VC-2 specification.

This module does *not* attempt to perform general purpose functional
equivalence checking. Instead, comparisons are made at the Abstract Syntax Tree
(AST) level. By performing checks at this level whitespace, comments and other
semantically irrelevant syntactic differences are ignored. Further, it is
possible to *allow* certain well-defined transformations (for example
redefining 'state' as a value which is passed-by-argument rather than a global
variable) or excuse explicitly flagged modifications (e.g. addition of error
reporting code).


Verification Software
---------------------

The underlying verification tools are split into three components:

* :py:mod:`verification.amendment_comments` includes facilities for using
  special comments to indicate intentional ammendments to a piece of code.
* :py:mod:`verification.node_comparator`
  :py:mod:`verification.ast_utils` and :py:mod:`verification.field_filters`
  form the basis of an AST comparison framework.
* :py:mod:`verification.comparators` implement the AST comparators used to test
  the :py:mod:`vc2_conformance` implementation.
* :py:mod:`verification.compare` provides utility functions which can drive the
  above and produce human-friendly difference information.
"""
