"""
:py:mod:`vc2_conformance.bitstream.exceptions`
==============================================

Custom exception types related to bitstream parsing/serialisation.
"""


class OutOfRangeError(ValueError):
    """
    An exception thrown whenever an out-of-range value is passed to a bitstream
    writing function.
    """


class UnusedTargetError(ValueError):
    """
    Thrown by functions in :py:mod:`vc2_conformance.bitstream` when a
    value in a context dictionary was left used.
    """


class ReusedTargetError(ValueError):
    """
    Thrown by functions in :py:mod:`vc2_conformance.bitstream` when a
    target in a context dictionary is used more than once.
    """


class ListTargetExhaustedError(IndexError):
    """
    Thrown by functions in :py:mod:`vc2_conformance.bitstream` when a value
    beyond the end of a list target in a context dictionary is requested.
    """


class ListTargetContainsNonListError(ValueError):
    """
    Thrown by functions in :py:mod:`vc2_conformance.bitstream` when a
    target in a context dictionary has been declared to be a list but does not
    contain a value of the :py:class:`list` type.
    """


class UnclosedBoundedBlockError(ValueError):
    """
    Thrown by functions in :py:mod:`vc2_conformance.bitstream` when some
    :py:meth:`SerDes.bounded_block_begin` does not have corresponding
    :py:meth:`SerDes.bounded_block_end`.
    """


class UnclosedNestedContextError(ValueError):
    """
    Thrown by functions in :py:mod:`vc2_conformance.bitstream` when some
    :py:meth:`SerDes.subcontext_enter` does not have corresponding
    :py:meth:`SerDes.subcontext_leave`.
    """
