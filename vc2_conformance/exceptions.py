"""
Exception types used in this library.
"""

class OutOfRangeError(ValueError):
    """
    An exception thrown whenever an out-of-range value is passed to a bitstream
    writing function.
    """

class UnknownTokenTypeError(ValueError):
    """
    Thrown by functions in :py:module:`vc2_conformance.bitstream` when an
    unrecognised :py:class:`TokenTypes` value is encountered.
    """

class UnusedTargetError(ValueError):
    """
    Thrown by functions in :py:module:`vc2_conformance.bitstream` when a
    value in a context dictionary was not used by any token.
    """

class ReusedTargetError(ValueError):
    """
    Thrown by functions in :py:module:`vc2_conformance.bitstream` when a
    target in a context dictionary is used more than once.
    """

class ListTargetContainsNonListError(ValueError):
    """
    Thrown by functions in :py:module:`vc2_conformance.bitstream` when a
    target in a context dictionary has been declared to be a list but does not
    contain a value of the :py:class:`list` type.
    """

class UnclosedBoundedBlockError(ValueError):
    """
    Thrown by functions in :py:module:`vc2_conformance.bitstream` when some
    :py:data:`TokenTypes.bounded_block_begin` tokens do not have corresponding
    :py:data:`TokenTypes.bounded_block_end` tokens.
    """

class UnclosedNestedContextError(ValueError):
    """
    Thrown by functions in :py:module:`vc2_conformance.bitstream` when some
    :py:data:`TokenTypes.nested_context_enter` tokens do not have corresponding
    :py:data:`TokenTypes.nested_context_leave` tokens.
    """
